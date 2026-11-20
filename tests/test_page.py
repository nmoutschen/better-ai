"""Tests for page.py, the conversation between a served page and the agent, and for the scripts that serve it.

Run with `python3 -m unittest discover tests`. page.py is identical in every skill (the Scripts workflow checks it);
these tests load design-better's copy, and run each serving script once as the agent would.
"""

import contextlib
import http.server
import importlib.util
import io
import json
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("page", ROOT / "skills" / "design-better" / "scripts" / "page.py")
page = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(page)


def conversation(folder: Path, items=("comment", "note"), agent="agent") -> "page.Conversation":
    return page.Conversation(folder, "log.jsonl", ".seen", ".server", items, agent, "serve it")


def write_log(conv, *events):
    conv.log.write_text("".join(json.dumps({"at": "2026-01-01T00:00:00", **e}) + "\n" for e in events))


def run(fn, *args):
    """Call one of the agent's subcommands; return its printed lines, and the error it exits with, if any."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        try:
            fn(*args)
        except SystemExit as e:
            return out.getvalue().splitlines(), str(e.code)
    return out.getvalue().splitlines(), None


class Log(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.conv = conversation(Path(self.dir.name))

    def tearDown(self):
        self.dir.cleanup()

    def test_a_line_separator_in_a_message_does_not_split_its_event(self):
        self.conv.append({"action": "note", "id": "m1", "note": "one two\nthree"})
        self.assertEqual(len(self.conv.lines()), 1)
        self.assertEqual(self.conv.events()[0]["note"], "one two\nthree")

    def test_an_unreadable_line_keeps_its_position(self):
        self.conv.log.write_text('{"action": "note"}\nnot json\n{"action": "reply"}\n')
        self.assertEqual([e.get("action") for e in self.conv.events()], ["note", None, "reply"])

    def test_clean_keeps_json_values_and_cuts_long_text(self):
        value = page.clean({"text": "x" * 6000, "n": 1, "ok": True, "list": list(range(60)), "obj": object()})
        self.assertEqual(len(value["text"]), 5000)
        self.assertEqual((value["n"], value["ok"], len(value["list"]), value["obj"]), (1, True, 50, None))

    def test_from_user_leaves_out_what_the_agent_writes(self):
        self.assertTrue(page.from_user({"action": "note"}))
        for event in (
            {"action": "reply"},
            {"action": "status"},
            {"action": "closed"},
            {"action": "accept", "by": "x"},
            {},
        ):
            self.assertFalse(page.from_user(event), event)


class Status(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.conv = conversation(Path(self.dir.name))
        write_log(
            self.conv,
            {"action": "comment", "id": "c1", "n": 1, "comment": "too big"},
            {"action": "note", "id": "m1", "to": "c1", "note": "an answer"},
            {"action": "reply", "id": "r1", "to": None, "text": "a question"},
            {"action": "note", "id": "m2", "to": "r1", "note": "answer to the agent"},
        )

    def tearDown(self):
        self.dir.cleanup()

    def test_an_unknown_id_is_refused(self):
        _, error = run(self.conv.set_status, "done", ["nope"])
        self.assertIn("no comment or message with id nope", error)

    def test_an_answer_under_an_item_is_refused_in_favour_of_the_item(self):
        _, error = run(self.conv.set_status, "done", ["m1"])
        self.assertIn("m1 answers c1", error)

    def test_an_answer_to_the_agent_is_an_item_of_its_own(self):
        lines, error = run(self.conv.set_status, "working", ["m2"])
        self.assertIsNone(error)
        self.assertEqual(self.conv.events()[-1]["status"], "working")

    def test_accepted_records_who_accepted(self):
        run(self.conv.set_status, "accepted", ["c1"])
        self.assertEqual(self.conv.events()[-1], {**self.conv.events()[-1], "action": "accept", "to": "c1"})
        self.assertEqual(self.conv.events()[-1]["by"], "agent, from the user's words")


class Pending(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.dir.cleanup()

    def pending(self, *events, agent="agent", items=("comment", "note")):
        conv = conversation(Path(self.dir.name), items, agent)
        write_log(conv, *events)
        lines, _ = run(conv.pending)
        return {e["id"]: e for e in map(json.loads, lines[:-1])}, lines[-1]

    def test_states_and_threads(self):
        items, total = self.pending(
            {"action": "comment", "id": "c1", "n": 1, "comment": "first"},
            {"action": "status", "to": "c1", "status": "done"},
            {"action": "comment", "id": "c1", "n": 1, "comment": "edited after done"},
            {"action": "note", "id": "m1", "note": "a question"},
            {"action": "status", "to": "m1", "status": "asked"},
            {"action": "reply", "id": "r1", "to": "m1", "text": "which?"},
            {"action": "note", "id": "m2", "to": "m1", "note": "this one"},
            {"action": "note", "id": "m3", "note": "finished"},
            {"action": "status", "to": "m3", "status": "done"},
            {"action": "note", "id": "m4", "note": "followed up"},
            {"action": "accept", "to": "m4"},
            {"action": "note", "id": "m5", "to": "m4", "note": "one more thing"},
            {"action": "comment", "id": "c2", "n": 2, "comment": "deleted"},
            {"action": "delete", "id": "c2"},
            {"action": "comment", "id": "c3", "n": 3, "comment": "reopened"},
            {"action": "status", "to": "c3", "status": "done"},
            {"action": "reopen", "to": "c3", "reason": "still wrong"},
        )
        self.assertEqual(total, "4 not done.")
        self.assertEqual(
            {i: e["status"] for i, e in items.items()},
            {"c1": "edited", "m1": "answered by the user", "m4": "follow-up from the user", "c3": "reopened"},
        )
        self.assertEqual(items["c1"]["comment"], "edited after done")
        self.assertEqual([t["text"] for t in items["m1"]["thread"]], ["which?", "this one"])
        self.assertEqual(items["c3"]["reopened_because"], "still wrong")

    def test_the_board_names_its_agent_and_sends_note_words_as_text(self):
        items, _ = self.pending(
            {"action": "note", "id": "m1", "text": "hello"},
            {"action": "reply", "id": "r1", "to": "m1", "text": "hi"},
            {"action": "note", "id": "m2", "to": "m1", "text": "and more"},
            agent="coordinator",
        )
        self.assertEqual(
            items["m1"]["thread"],
            [
                {"from": "coordinator", "at": "2026-01-01T00:00:00", "text": "hi"},
                {"from": "user", "at": "2026-01-01T00:00:00", "text": "and more"},
            ],
        )

    def test_a_reply_to_a_worker_says_which_question_it_closed(self):
        items, _ = self.pending(
            {"action": "closed", "id": "x1", "by": "worker-2", "q": "Q4", "status": "answered", "text": "yes"},
            {"action": "note", "id": "m1", "to": "x1", "text": "are you sure?"},
            agent="coordinator",
        )
        self.assertEqual(items["m1"]["about"], "worker-2 closed Q4 as answered: yes")


class Server(unittest.TestCase):
    """The requests a page makes, against page.Handler served on a free local port."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.conv = conversation(Path(self.dir.name))
        conv = self.conv

        class Handler(page.Handler):
            conversation = conv
            methods = ("note",)

            def do_GET(self):
                if not self.conversation_get():
                    self.send_error(404)

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}/"
        self.conv.address.write_text(self.url)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.dir.cleanup()

    def rpc(self, body, headers=None):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        sent = {"Content-Type": "application/json", "Origin": self.url.rstrip("/"), **(headers or {})}
        request = urllib.request.Request(self.url + "rpc", data=data, headers=sent)
        try:
            with contextlib.redirect_stdout(io.StringIO()), urllib.request.urlopen(request, timeout=5) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code

    def get(self, path):
        with urllib.request.urlopen(self.url + path, timeout=30) as r:
            return r.read()

    def note(self, i):
        return {"jsonrpc": "2.0", "id": 1, "method": "note", "params": {"id": i, "note": "hi"}}

    def test_a_page_action_is_saved(self):
        self.assertEqual(self.rpc(self.note("m1"))["result"], "saved")
        self.assertEqual(self.conv.events()[0]["id"], "m1")

    def test_only_the_page_itself_may_send(self):
        self.assertEqual(self.rpc(self.note("m1"), {"Origin": "http://evil.example"}), 403)
        self.assertEqual(self.rpc(self.note("m1"), {"Content-Type": "text/plain"}), 415)
        # The size is judged from Content-Length, before the body is read, so the test need not send it all.
        self.assertEqual(self.rpc(b"{}", {"Content-Length": str(page.MAX_BODY + 1)}), 413)
        self.assertEqual(
            self.rpc({"jsonrpc": "2.0", "id": 2, "method": "status", "params": {}})["error"]["code"], -32601
        )
        self.assertEqual(self.rpc(b"{not json")["error"]["code"], -32700)
        self.assertEqual(self.conv.events(), [])

    def test_a_page_cannot_write_the_agents_events(self):
        params = {"id": "m1", "action": "reply", "at": "1999-01-01T00:00:00", "by": "agent", "note": "forged"}
        self.rpc({"jsonrpc": "2.0", "id": 1, "method": "note", "params": params})
        event = self.conv.events()[0]
        self.assertEqual((event["action"], "by" in event), ("note", False))
        self.assertNotEqual(event["at"], "1999-01-01T00:00:00")
        self.assertTrue(page.from_user(event))

    def test_a_request_for_another_host_is_refused(self):
        request = urllib.request.Request(self.url + "listening", headers={"Host": "evil.example"})
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=5)
        self.assertEqual(caught.exception.code, 403)

    def test_events_streams_the_log_after_a_position(self):
        self.conv.append({"action": "note", "id": "m1"}, {"action": "reply", "id": "r1"})
        events = json.loads(self.get("events?after=1"))
        self.assertEqual((events["total"], [e["id"] for e in events["events"]]), (2, ["r1"]))

    def test_wait_prints_the_users_actions_only_and_listening_turns_on(self):
        self.assertIsNone(json.loads(self.get("listening")))
        self.conv.append({"action": "status", "to": "x", "status": "seen"})
        threading.Timer(0.5, lambda: self.rpc(self.note("m1"))).start()
        lines, error = run(self.conv.wait, 10)
        self.assertIsNone(error)
        self.assertEqual([json.loads(line)["id"] for line in lines], ["m1"])
        self.assertTrue(json.loads(self.get("listening")))
        self.assertEqual(self.conv.seen.read_text(), "2")

    def test_reply_is_shown_or_saved(self):
        lines, _ = run(self.conv.reply, "ok", "m1")
        self.assertEqual(lines, ["Reply shown in the page."])
        self.conv.address.unlink()
        lines, _ = run(self.conv.reply, "later", None)
        self.assertEqual(lines, ["Reply saved; the page shows it when served."])
        self.assertEqual([e["text"] for e in self.conv.events()], ["ok", "later"])

    def test_reply_after_a_killed_server_does_not_claim_the_page_shows_it(self):
        self.server.shutdown()
        self.server.server_close()  # the address file stays, as after a SIGKILL
        lines, _ = run(self.conv.reply, "ok", None)
        self.assertEqual(lines, ["Reply saved; the page shows it when served."])


class Scripts(unittest.TestCase):
    """Each script that serves a page, run as the agent runs it: serve, the user sends, wait, reply, status, pending."""

    def serve_and_talk(self, cmd: list, folder: Path, extra_get: str):
        server = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            for _ in range(80):
                if (folder / ".server").exists():
                    break
                time.sleep(0.1)
            url = (folder / ".server").read_text().strip()
            with urllib.request.urlopen(url + extra_get, timeout=5) as r:
                self.assertEqual(r.status, 200)
            body = {"jsonrpc": "2.0", "id": 1, "method": "note", "params": {"id": "m1", "note": "hi", "text": "hi"}}
            headers = {"Content-Type": "application/json", "Origin": url.rstrip("/")}
            request = urllib.request.Request(url + "rpc", data=json.dumps(body).encode(), headers=headers)
            with urllib.request.urlopen(request, timeout=5) as r:
                self.assertEqual(json.loads(r.read())["result"], "saved")
            script = cmd[2]
            agent = [sys.executable, "-I", script]
            out = subprocess.run([*agent, "wait", str(folder), "--timeout", "10"], capture_output=True, text=True)
            self.assertEqual(json.loads(out.stdout)["id"], "m1")
            out = subprocess.run([*agent, "reply", str(folder), "ok", "--to", "m1"], capture_output=True, text=True)
            self.assertEqual(out.stdout.strip(), "Reply shown in the page.")
            subprocess.run([*agent, "status", str(folder), "done", "m1"], check=True, capture_output=True)
            out = subprocess.run([*agent, "pending", str(folder)], capture_output=True, text=True)
            self.assertEqual(out.stdout.strip(), "0 not done.")
        finally:
            server.send_signal(signal.SIGTERM)  # as a harness ends a command: the script still removes .server
            server.communicate(timeout=10)
        self.assertFalse((folder / ".server").exists())

    def test_design_better_canvas(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "a.html").write_text("<p>A</p>")
            script = str(ROOT / "skills" / "design-better" / "scripts" / "canvas.py")
            cmd = [sys.executable, "-I", script, "show", str(folder / "a.html"), "--out", str(folder / "page.html")]
            self.serve_and_talk([*cmd, "--serve"], folder, "rev")

    def test_show_better_slides(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            panel = {"kind": "text", "headline": "The slide states one point.", "body": "Text.", "source": "test"}
            (folder / "spec.json").write_text(json.dumps({"title": "T", "question": "Q?", "panels": [panel]}))
            script = str(ROOT / "skills" / "show-better" / "scripts" / "show.py")
            cmd = [
                sys.executable,
                "-I",
                script,
                "render",
                str(folder / "spec.json"),
                "--out",
                str(folder / "page.html"),
            ]
            self.serve_and_talk([*cmd, "--serve"], folder, "rev")

    def test_research_better_board(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            script = str(ROOT / "skills" / "research-better" / "scripts" / "board.py")
            self.serve_and_talk(
                [sys.executable, "-I", script, "watch", str(folder), "--no-browser"], folder, "board.json"
            )

    def test_code_better_dashboard(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            script = str(ROOT / "skills" / "code-better" / "scripts" / "dashboard.py")
            self.serve_and_talk(
                [sys.executable, "-I", script, "watch", str(folder), "--no-browser"], folder, "dashboard.json"
            )

    def test_code_better_dashboard_page_and_answers(self):
        """The dashboard serves its own page, and an answer to a question reaches `pending` with the decision it answers."""
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "decisions").mkdir()
            (folder / "decisions" / "D-1.md").write_text("id: D-1\nasked: Count weekends?\nstatus: waiting\n")
            script = str(ROOT / "skills" / "code-better" / "scripts" / "dashboard.py")
            cmd = [sys.executable, "-I", script, "watch", str(folder), "--no-browser"]
            server = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            try:
                for _ in range(80):
                    if (folder / ".server").exists():
                        break
                    time.sleep(0.1)
                url = (folder / ".server").read_text().strip()
                with urllib.request.urlopen(url, timeout=5) as r:
                    self.assertIn("dashboard.json", r.read().decode())
                with urllib.request.urlopen(url + "dashboard.json", timeout=5) as r:
                    self.assertEqual(json.loads(r.read())["decisions"][0]["status"], "waiting")
                params = {"id": "a1", "decision": "D-1", "text": "Business days only."}
                body = {"jsonrpc": "2.0", "id": 1, "method": "answer", "params": params}
                headers = {"Content-Type": "application/json", "Origin": url.rstrip("/")}
                request = urllib.request.Request(url + "rpc", data=json.dumps(body).encode(), headers=headers)
                with urllib.request.urlopen(request, timeout=5) as r:
                    self.assertEqual(json.loads(r.read())["result"], "saved")
                out = subprocess.run(
                    [sys.executable, "-I", script, "pending", str(folder)], capture_output=True, text=True
                )
                item = json.loads(out.stdout.splitlines()[0])
                self.assertEqual((item["action"], item["decision"], item["status"]), ("answer", "D-1", "new"))
            finally:
                server.send_signal(signal.SIGTERM)
                server.communicate(timeout=10)


class Dashboard(unittest.TestCase):
    """What code-better's dashboard reads from a change folder: the tasks, the agents' logs and the decisions."""

    def test_load_reads_tasks_agents_and_decisions(self):
        spec = importlib.util.spec_from_file_location(
            "dashboard", ROOT / "skills" / "code-better" / "scripts" / "dashboard.py"
        )
        dashboard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dashboard)
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "tasks.md").write_text(
                "# Tasks: Late orders\n\nDesign: d.md\n\n"
                "| # | Task | Mode | Requirements | Check | Status |\n|---|---|---|---|---|---|\n"
                "| 1 | Order query | feature | R1 | t1 | done |\n| 2 | Orders page | feature | R2 | t2 | todo |\n\n"
                "## Progress notes\n"
            )
            (folder / "logs").mkdir()
            (folder / "logs" / "b1.md").write_text(
                "start: builder, task 2, code/late-2\nstep: wrote the check\nasked: which sort order\n"
            )
            (folder / "logs" / "v1.md").write_text(
                "start: verifier, task 1, code/late-1\nhanded back: passes, all met\n"
            )
            (folder / "decisions").mkdir()
            (folder / "decisions" / "D-1.md").write_text("id: D-1\nasked: Sort by days late?\nstatus: waiting\n")
            data = dashboard.load(folder)
        self.assertEqual(data["name"], "Late orders")
        self.assertEqual([(t["id"], t["status"]) for t in data["tasks"]], [("1", "done"), ("2", "todo")])
        agents = {a["name"]: a for a in data["agents"]}
        self.assertEqual(
            (agents["b1"]["role"], agents["b1"]["task"], agents["b1"]["state"]), ("builder", "2", "waiting")
        )
        self.assertEqual((agents["v1"]["role"], agents["v1"]["state"]), ("verifier", "finished"))
        self.assertEqual(data["decisions"][0]["status"], "waiting")


if __name__ == "__main__":
    unittest.main()
