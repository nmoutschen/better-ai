"""Tests for page.py, the conversation between a served page and the agent, and for the scripts that serve it.

Run with `python3 -m unittest discover tests`. page.py is identical in every skill (the Scripts workflow checks it);
these tests load design-better's copy, and run each serving script once as the agent would.
"""

import contextlib
import http.server
import importlib.util
import io
import json
import re
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
SCRIPTS = ROOT / "skills" / "design-better" / "scripts"
SPEC = importlib.util.spec_from_file_location("page", SCRIPTS / "page.py")
page = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(page)
UTC = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")


def load(skill: str, script: str):
    """A page's serving script, as its own skill ships it."""
    path = ROOT / "skills" / skill / "scripts" / script
    spec = importlib.util.spec_from_file_location(script.removesuffix(".py"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def conversation(folder: Path, items=("comment", "note"), agent="agent") -> "page.Conversation":
    return page.Conversation(
        folder,
        "conversation.jsonl",
        ".conversation-seen",
        ".server",
        items,
        agent,
        "serve it",
        schemas=SCRIPTS.parent / "schemas",
        events="canvas-events.schema.json",
    )


def write_log(conv, *events):
    conv.log.write_text("".join(json.dumps({"at": "2026-01-01T00:00:00Z", **e}) + "\n" for e in events))


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
        self.conv.append({"type": "note", "by": "user", "id": "m1", "text": "one two\nthree", "to": None})
        self.assertEqual(len(self.conv.lines()), 1)
        self.assertEqual(self.conv.events()[0]["text"], "one two\nthree")

    def test_an_event_gets_the_time_in_utc_with_z(self):
        self.conv.append({"type": "note", "by": "user", "id": "m1", "text": "hi", "to": None})
        self.assertRegex(self.conv.events()[0]["at"], UTC)
        self.assertRegex(page.now(), UTC)

    def test_an_unreadable_line_keeps_its_position(self):
        self.conv.log.write_text('{"type": "note"}\nnot json\n{"type": "reply"}\n')
        self.assertEqual([e.get("type") for e in self.conv.events()], ["note", None, "reply"])

    def test_an_event_that_fails_its_schema_is_not_written(self):
        with self.assertRaises(page.EventError) as caught:
            self.conv.append({"type": "note", "by": "user", "id": "m1", "to": None})
        self.assertIn("text", str(caught.exception))
        self.assertEqual(self.conv.lines(), [])

    def test_clean_keeps_json_values_and_cuts_long_text(self):
        value = page.clean({"text": "x" * 6000, "n": 1, "ok": True, "list": list(range(60)), "obj": object()})
        self.assertEqual(len(value["text"]), 5000)
        self.assertEqual((value["n"], value["ok"], len(value["list"]), value["obj"]), (1, True, 50, None))

    def test_from_user_is_what_the_page_sent_for_the_user(self):
        self.assertTrue(page.from_user({"type": "note", "by": "user"}))
        for event in (
            {"type": "reply", "by": "agent"},
            {"type": "status", "by": "agent"},
            {"type": "closed", "by": "w2"},
            {"type": "accepted", "by": "agent"},
            {"type": "note"},
            {},
        ):
            self.assertFalse(page.from_user(event), event)


class Status(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.conv = conversation(Path(self.dir.name))
        write_log(
            self.conv,
            {"type": "comment", "by": "user", "id": "c1", "n": 1, "text": "too big"},
            {"type": "note", "by": "user", "id": "m1", "to": "c1", "text": "an answer"},
            {"type": "reply", "by": "agent", "id": "r1", "to": None, "text": "a question"},
            {"type": "note", "by": "user", "id": "m2", "to": "r1", "text": "answer to the agent"},
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
        last = self.conv.events()[-1]
        self.assertEqual((last["type"], last["to"], last["status"], last["by"]), ("status", "m2", "working", "agent"))

    def test_accepted_is_an_event_with_the_users_words_written_by_the_agent(self):
        _, error = run(self.conv.set_status, "accepted", ["c1"], "yes, that is fine")
        self.assertIsNone(error)
        last = self.conv.events()[-1]
        self.assertEqual(
            {k: last[k] for k in ("type", "to", "by", "text")},
            {"type": "accepted", "to": "c1", "by": "agent", "text": "yes, that is fine"},
        )

    def test_accepted_without_the_users_words_is_refused(self):
        before = self.conv.lines()
        _, error = run(self.conv.set_status, "accepted", ["c1"])
        self.assertIn("words", error)
        self.assertEqual(self.conv.lines(), before)


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
        user, bot = {"by": "user"}, {"by": "agent"}
        items, total = self.pending(
            {"type": "comment", "id": "c1", "n": 1, "text": "first", **user},
            {"type": "status", "to": "c1", "status": "done", **bot},
            {"type": "comment", "id": "c1", "n": 1, "text": "edited after done", **user},
            {"type": "note", "id": "m1", "text": "a question", "to": None, **user},
            {"type": "status", "to": "m1", "status": "asked", **bot},
            {"type": "reply", "id": "r1", "to": "m1", "text": "which?", **bot},
            {"type": "note", "id": "m2", "to": "m1", "text": "this one", **user},
            {"type": "note", "id": "m3", "text": "finished", "to": None, **user},
            {"type": "status", "to": "m3", "status": "done", **bot},
            {"type": "note", "id": "m4", "text": "followed up", "to": None, **user},
            {"type": "accept", "to": "m4", **user},
            {"type": "note", "id": "m5", "to": "m4", "text": "one more thing", **user},
            {"type": "comment", "id": "c2", "n": 2, "text": "deleted", **user},
            {"type": "delete", "to": "c2", **user},
            {"type": "comment", "id": "c3", "n": 3, "text": "reopened", **user},
            {"type": "status", "to": "c3", "status": "done", **bot},
            {"type": "reopen", "to": "c3", "text": "still wrong", **user},
        )
        self.assertEqual(total, "4 not done.")
        self.assertEqual(
            {i: e["status"] for i, e in items.items()},
            {"c1": "edited", "m1": "answered by the user", "m4": "follow-up from the user", "c3": "reopened"},
        )
        self.assertEqual(items["c1"]["text"], "edited after done")
        self.assertEqual([t["text"] for t in items["m1"]["thread"]], ["which?", "this one"])
        self.assertEqual(items["c3"]["reopened_because"], "still wrong")

    def test_an_accepted_event_from_the_chat_ends_the_item(self):
        items, total = self.pending(
            {"type": "note", "id": "m1", "text": "ok?", "to": None, "by": "user"},
            {"type": "accepted", "to": "m1", "by": "agent", "text": "yes"},
        )
        self.assertEqual((items, total), ({}, "0 not done."))

    def test_the_board_names_its_agent(self):
        items, _ = self.pending(
            {"type": "note", "id": "m1", "text": "hello", "to": None, "by": "user"},
            {"type": "reply", "id": "r1", "to": "m1", "text": "hi", "by": "coordinator"},
            {"type": "note", "id": "m2", "to": "m1", "text": "and more", "by": "user"},
            agent="coordinator",
        )
        self.assertEqual(
            items["m1"]["thread"],
            [
                {"from": "coordinator", "at": "2026-01-01T00:00:00Z", "text": "hi"},
                {"from": "user", "at": "2026-01-01T00:00:00Z", "text": "and more"},
            ],
        )

    def test_a_reply_to_a_worker_says_which_question_it_closed(self):
        items, _ = self.pending(
            {"type": "closed", "id": "x1", "by": "worker-2", "question": "Q4", "status": "answered"},
            {"type": "note", "id": "m1", "to": "x1", "text": "are you sure?", "by": "user"},
            agent="coordinator",
        )
        self.assertEqual(items["m1"]["about"], "worker-2 closed Q4 as answered")


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
        # A short poll, so each shutdown does not wait half a second.
        threading.Thread(target=self.server.serve_forever, args=(0.01,), daemon=True).start()

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

    def note(self, i, **extra):
        params = {"id": i, "text": "hi", "to": None, **extra}
        return {"jsonrpc": "2.0", "id": 1, "method": "note", "params": params}

    def test_a_page_action_is_saved_as_the_users_event(self):
        self.assertEqual(self.rpc(self.note("m1"))["result"], "saved")
        event = self.conv.events()[0]
        self.assertEqual((event["type"], event["by"], event["id"], event["text"]), ("note", "user", "m1", "hi"))
        self.assertRegex(event["at"], UTC)

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

    def test_a_page_supplied_by_is_rejected(self):
        answer = self.rpc(self.note("m1", by="agent"))
        self.assertEqual(answer["error"]["code"], -32602)
        self.assertIn("by", answer["error"]["message"])
        self.assertEqual(self.conv.events(), [])

    def test_the_type_and_the_time_come_from_the_server(self):
        self.rpc(self.note("m1", type="reply", at="1999-01-01T00:00:00Z"))
        event = self.conv.events()[0]
        self.assertEqual((event["type"], event["by"]), ("note", "user"))
        self.assertNotEqual(event["at"], "1999-01-01T00:00:00Z")
        self.assertTrue(page.from_user(event))

    def test_an_event_that_fails_its_schema_is_answered_with_invalid_params_and_not_written(self):
        answer = self.rpc({"jsonrpc": "2.0", "id": 1, "method": "note", "params": {"id": "m1", "to": None}})
        self.assertEqual(answer["error"]["code"], -32602)
        self.assertIn("text", answer["error"]["message"])
        self.assertEqual(self.conv.events(), [])

    def test_a_request_for_another_host_is_refused(self):
        request = urllib.request.Request(self.url + "listening", headers={"Host": "evil.example"})
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=5)
        self.assertEqual(caught.exception.code, 403)

    def test_events_streams_the_log_after_a_position(self):
        self.conv.append(
            {"type": "note", "by": "user", "id": "m1", "text": "a", "to": None},
            {"type": "reply", "by": "agent", "id": "r1", "text": "b", "to": "m1"},
        )
        events = json.loads(self.get("events?after=1"))
        self.assertEqual((events["total"], [e["id"] for e in events["events"]]), (2, ["r1"]))

    def test_wait_prints_the_users_actions_only_and_listening_turns_on(self):
        self.assertIsNone(json.loads(self.get("listening")))
        self.conv.append({"type": "status", "by": "agent", "to": "x", "status": "seen"})
        threading.Timer(0.5, lambda: self.rpc(self.note("m1"))).start()
        lines, error = run(self.conv.wait, 10)
        self.assertIsNone(error)
        self.assertEqual([json.loads(line)["id"] for line in lines], ["m1"])
        self.assertTrue(json.loads(self.get("listening")))
        self.assertEqual(self.conv.seen.read_text(), "2")

    def test_reply_is_shown_or_saved_under_the_agents_name(self):
        lines, _ = run(self.conv.reply, "ok", "m1")
        self.assertEqual(lines, ["Reply shown in the page."])
        self.conv.address.unlink()
        lines, _ = run(self.conv.reply, "later", None)
        self.assertEqual(lines, ["Reply saved; the page shows it when served."])
        events = self.conv.events()
        self.assertEqual([e["text"] for e in events], ["ok", "later"])
        self.assertEqual({(e["type"], e["by"]) for e in events}, {("reply", "agent")})

    def test_reply_after_a_killed_server_does_not_claim_the_page_shows_it(self):
        self.server.shutdown()
        self.server.server_close()  # the address file stays, as after a SIGKILL
        lines, _ = run(self.conv.reply, "ok", None)
        self.assertEqual(lines, ["Reply saved; the page shows it when served."])


# What each page sends, by method, as its own script and page.js send it (the page adds type, by and at).
ANCHOR = {"kind": "question", "id": "Q1", "title": "Why did it drop?"}
VALID = {
    "architect": {
        "comment": {"id": "c1-x", "n": 1, "text": "unclear", "on": {"id": "req-F1", "title": "F1", "key": "k"}},
        "note": {"id": "m-x", "text": "hi", "to": None},
        "approve": {"id": "approval-x", "again": False, "perspectives": ["security"], "changes": [], "text": "ok"},
        "confirm": {"id": "confirm-x", "requirement": "F1", "wording": "abc", "text": "Confirmed requirement F1."},
        "delete": {"to": "c1-x"},
        "accept": {"to": "c1-x"},
    },
    "canvas": {
        "comment": {
            "id": "c1-x",
            "n": 1,
            "text": "too small",
            "on": {"version": "A", "screen": "390x844", "target": {"selector": "#pay"}, "spot": {"fx": 0.5, "fy": 0.5}},
        },
        "note": {"id": "m-x", "text": "hi", "to": None},
        "verdict": {"version": "A", "verdict": "up"},
        "decide": {"id": "d-x", "option": "A", "label": "Build A", "carries": ["c1-x"], "text": None},
        "delete": {"to": "c1-x"},
        "accept": {"to": "c1-x"},
        "reopen": {"to": "c1-x", "text": "still wrong"},
    },
    "board": {
        "comment": {"id": "c-x", "text": "check this", "on": ANCHOR},
        "note": {"id": "m-x", "text": "hi", "to": None},
        "answer": {"id": "a-x", "decision": "D1", "text": "Use the default.", "default": True},
    },
}
# The records of the architect folder the architect page's events point to, by id.
_BASE = {"at": "2026-11-21T10:00:00Z", "by": "architect"}
ARCHITECT_FILES = {
    "perspectives.jsonl": {
        "type": "perspective",
        **_BASE,
        "id": "security",
        "name": "Security",
        "applies": True,
        "why": "A local server takes input.",
        "from": {"type": "built_in"},
    },
    "requirements.jsonl": {
        "type": "requirement",
        **_BASE,
        "id": "F1",
        "kind": "functional",
        "text": "Show the agents.",
        "source": {"type": "guessed"},
    },
}
# One event per page the schemas must refuse, and the field the answer names.
INVALID = {
    "architect": ("confirm", {"id": "confirm-x", "requirement": "F1", "text": "t"}, "wording"),
    "canvas": ("comment", {**VALID["canvas"]["comment"], "text": None}, "verdict"),
    "board": ("answer", {"id": "a-x", "text": "t", "default": False}, "decision"),
}


class Pages(unittest.TestCase):
    """Each of the five pages, through its own serving script's conversation: what its methods send is accepted, what
    its schema forbids is answered with invalid params, and the log is conversation.jsonl, valid as a file."""

    def modules(self):
        return {
            "architect": load("architect-better", "architect.py"),
            "canvas": load("design-better", "canvas.py"),
            "board": load("research-better", "board.py"),
        }

    def serve(self, module, folder):
        conv = module.conversation(folder)

        class Handler(module.page.Handler):
            conversation = conv
            methods = module.METHODS

            def do_GET(self):
                self.send_error(404)

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        # A short poll, so each shutdown does not wait half a second.
        threading.Thread(target=server.serve_forever, args=(0.01,), daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return conv, f"http://127.0.0.1:{server.server_address[1]}"

    def send(self, base, method, params):
        body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        headers = {"Content-Type": "application/json", "Origin": base}
        request = urllib.request.Request(base + "/rpc", data=json.dumps(body).encode(), headers=headers)
        with contextlib.redirect_stdout(io.StringIO()), urllib.request.urlopen(request, timeout=5) as r:
            return json.loads(r.read())

    def test_every_method_of_every_page_has_a_valid_event_and_it_is_accepted(self):
        for name, module in self.modules().items():
            with self.subTest(page=name), tempfile.TemporaryDirectory() as d:
                self.assertEqual(
                    set(module.METHODS), set(VALID[name]), "a method without a check, or a check without one"
                )
                conv, base = self.serve(module, Path(d))
                for method, params in VALID[name].items():
                    answer = self.send(base, method, params)
                    self.assertEqual(answer.get("result"), "saved", f"{name} {method}: {answer}")
                events = conv.events()
                self.assertEqual([e["type"] for e in events], list(VALID[name]))
                self.assertEqual({e["by"] for e in events}, {"user"})

    def test_each_page_writes_conversation_jsonl_and_never_answers_jsonl(self):
        for name, module in self.modules().items():
            with self.subTest(page=name), tempfile.TemporaryDirectory() as d:
                folder = Path(d)
                conv, base = self.serve(module, folder)
                self.send(base, "note", VALID[name]["note"])
                self.assertEqual((conv.log.name, conv.seen.name), ("conversation.jsonl", ".conversation-seen"))
                self.assertEqual(sorted(p.name for p in folder.iterdir()), ["conversation.jsonl"])
                for old in ("answers.jsonl", ".answers-seen"):
                    self.assertFalse((folder / old).exists())

    def test_what_each_page_writes_is_a_valid_conversation_file(self):
        for name, module in self.modules().items():
            with self.subTest(page=name), tempfile.TemporaryDirectory() as d:
                conv, base = self.serve(module, Path(d))
                if name == "architect":  # the approve event names a perspective, the confirmation a requirement
                    Path(d, "perspectives.jsonl").write_text(json.dumps(ARCHITECT_FILES["perspectives.jsonl"]) + "\n")
                    Path(d, "requirements.jsonl").write_text(json.dumps(ARCHITECT_FILES["requirements.jsonl"]) + "\n")
                for method, params in VALID[name].items():
                    self.send(base, method, params)
                conv.reply("seen it", None)
                conv.set_status("done", ["m-x"])
                conv.set_status("accepted", ["m-x"], "fine")
                skill_schema = load_schema(module)
                errors = skill_schema.check_paths([conv.log], Path(module.__file__).parent.parent / "schemas")
                self.assertEqual([str(e) for e in errors], [])

    def test_an_event_its_schema_forbids_is_answered_with_invalid_params_naming_the_field(self):
        for name, module in self.modules().items():
            with self.subTest(page=name), tempfile.TemporaryDirectory() as d:
                conv, base = self.serve(module, Path(d))
                method, params, field = INVALID[name]
                answer = self.send(base, method, params)
                self.assertEqual(answer["error"]["code"], -32602, answer)
                self.assertIn(field, answer["error"]["message"])
                self.assertEqual(conv.events(), [])

    def test_a_page_supplied_by_is_rejected_on_every_page(self):
        for name, module in self.modules().items():
            with self.subTest(page=name), tempfile.TemporaryDirectory() as d:
                conv, base = self.serve(module, Path(d))
                answer = self.send(base, "note", {**VALID[name]["note"], "by": "agent"})
                self.assertEqual(answer["error"]["code"], -32602)
                self.assertIn("by", answer["error"]["message"])
                self.assertEqual(conv.events(), [])

    def test_a_reused_comment_id_is_a_new_version_of_the_comment(self):
        for name, module in self.modules().items():
            with self.subTest(page=name), tempfile.TemporaryDirectory() as d:
                conv, base = self.serve(module, Path(d))
                first = VALID[name]["comment"]
                self.send(base, "comment", first)
                self.send(base, "comment", {**first, "text": "edited"})
                self.assertEqual([e["id"] for e in conv.events()], [first["id"]] * 2)
                skill_schema = load_schema(module)
                errors = skill_schema.check_paths([conv.log], Path(module.__file__).parent.parent / "schemas")
                self.assertEqual([str(e) for e in errors], [])
                lines, _ = run(conv.pending)
                shown = [json.loads(line) for line in lines[:-1]]
                self.assertEqual([(e["id"], e["text"]) for e in shown], [(first["id"], "edited")])

    def test_a_verdict_only_comment_is_the_canvas_only_comment_without_text(self):
        with tempfile.TemporaryDirectory() as d:
            conv, base = self.serve(load("design-better", "canvas.py"), Path(d))
            thumbs = {**VALID["canvas"]["comment"], "id": "c2-x", "text": None, "verdict": "up"}
            self.assertEqual(self.send(base, "comment", thumbs).get("result"), "saved")
        for name in ("board",):
            with tempfile.TemporaryDirectory() as d:
                conv, base = self.serve(self.modules()[name], Path(d))
                thumbs = {**VALID[name]["comment"], "text": None, "verdict": "up"}
                self.assertEqual(self.send(base, "comment", thumbs)["error"]["code"], -32602)

    def test_the_researchers_closing_message_carries_its_question(self):
        module = self.modules()["board"]
        with tempfile.TemporaryDirectory() as d:
            conv, _ = self.serve(module, Path(d))
            conv.append({"type": "closed", "by": "w2", "id": "c-1", "question": "Q-w2-4", "status": "answered"})
            self.assertEqual(
                {k: conv.events()[0][k] for k in ("type", "by", "id", "question", "status")},
                {"type": "closed", "by": "w2", "id": "c-1", "question": "Q-w2-4", "status": "answered"},
            )
            with self.assertRaises(module.page.EventError):
                conv.append({"type": "closed", "by": "w2", "id": "c-2", "q": "Q-w2-4", "status": "answered"})


def load_schema(module):
    """The skill's own schema.py, loaded under a name of its own."""
    path = Path(module.__file__).parent / "schema.py"
    spec = importlib.util.spec_from_file_location("schema_of_" + path.parent.parent.name.replace("-", "_"), path)
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


class Scripts(unittest.TestCase):
    """Each script that serves a page, run as the agent runs it: serve, the user sends, wait, reply, status, pending."""

    def serve_and_talk(self, cmd: list, folder: Path, extra_get: str, note_extra: dict | None = None):
        server = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            for _ in range(80):
                if (folder / ".server").exists():
                    break
                time.sleep(0.1)
            url = (folder / ".server").read_text().strip()
            with urllib.request.urlopen(url + extra_get, timeout=5) as r:
                self.assertEqual(r.status, 200)
            params = {"id": "m1", "text": "hi", "to": None, **(note_extra or {})}
            body = {"jsonrpc": "2.0", "id": 1, "method": "note", "params": params}
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
            out = subprocess.run(
                [*agent, "status", str(folder), "accepted", "m1", "--text", "good"], capture_output=True, text=True
            )
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertEqual(
                json.loads((folder / "conversation.jsonl").read_text().splitlines()[-1])["type"], "accepted"
            )
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

    def test_research_better_board(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            script = str(ROOT / "skills" / "research-better" / "scripts" / "board.py")
            self.serve_and_talk(
                [sys.executable, "-I", script, "watch", str(folder), "--no-browser"], folder, "board.json"
            )


if __name__ == "__main__":
    unittest.main()
