"""code-better's record commands: the coordinator and the agents write cards, log lines and replies only through
`better.pyz`, and `create` makes the change, copying the architect's spec into it.

`add <change> card|start|step|asked|blocked|handed_back --for <agent>` stamps `at` with the current UTC time, so no agent
types a time, and writes nothing that fails its schema. `reply --to` answers an item and sets its status in one write,
so no reply is left without one.
"""

import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import better as better_module  # noqa: E402
from better import call  # noqa: E402
from better import run as better  # noqa: E402
from code_records import AT, card, change, code, spec, write  # noqa: E402

UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def run(folder: Path, *args, stdin=None, process=False):
    """The command of code-better, in the folder that holds `.code/`: in this process, or with `process` as `better.pyz`
    is started, which each verb has in one test."""
    root = next(p.parent for p in (folder, *folder.parents) if p.name == ".code")
    return (better if process else call)("code-better", *args, stdin=stdin, cwd=root)


def add(folder: Path, kind: str, agent: str, fields: dict, *more, process=False):
    return run(folder, "add", str(folder), kind, "--for", agent, *more, stdin=json.dumps(fields), process=process)


def lines(path: Path) -> list:
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


class Card(unittest.TestCase):
    def test_card_writes_a_stamped_card(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            done = add(
                folder,
                "card",
                "builder-t1",
                {"role": "builder", "task": "T1", "branch": "feat/t1"},
                "--by",
                "coordinator",
                process=True,
            )
            self.assertEqual(done.returncode, 0, done.stderr)
            written = json.loads((folder / "logs" / "builder-t1.card.json").read_text())
        self.assertRegex(written.pop("at"), UTC)
        self.assertEqual(
            written, {"type": "card", "by": "coordinator", "role": "builder", "task": "T1", "branch": "feat/t1"}
        )

    def test_card_refuses_a_task_not_in_the_task_list_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            done = add(folder, "card", "builder-t9", {"role": "builder", "task": "T9", "branch": "b"})
            self.assertEqual(done.returncode, 1)
            self.assertIn("task", done.stdout + done.stderr)
            self.assertFalse((folder / "logs" / "builder-t9.card.json").exists())

    def test_card_refuses_a_name_another_agent_already_has(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            path = write(folder, "logs/builder-t1.card.json", [card("builder", "T1")], as_json=True)
            before = path.read_text()
            done = add(folder, "card", "builder-t1", {"role": "verifier", "task": "T1", "branch": "b"})
            self.assertEqual(done.returncode, 1)
            self.assertIn("exists already", done.stderr)
            self.assertEqual(path.read_text(), before)

    def test_card_refuses_a_name_that_has_a_log_and_no_card(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            write(folder, "logs/builder-t1.jsonl", [{"type": "start", "at": AT, "by": "builder-t1", "text": "x"}])
            done = add(folder, "card", "builder-t1", {"role": "builder", "task": "T1", "branch": "b"})
            self.assertEqual(done.returncode, 1)
            self.assertIn("exists already", done.stderr)
            self.assertFalse((folder / "logs" / "builder-t1.card.json").exists())

    def test_card_needs_for(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            done = run(
                folder,
                "add",
                str(folder),
                "card",
                "--by",
                "coordinator",
                stdin='{"role": "builder", "task": "T1", "branch": "b"}',
            )
            self.assertEqual(done.returncode, 1)
            self.assertIn("--for", done.stderr)


class Log(unittest.TestCase):
    def test_log_appends_a_stamped_line_by_the_agent(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            write(folder, "logs/builder-t1.card.json", [card("builder", "T1")], as_json=True)
            self.assertEqual(add(folder, "start", "builder-t1", {"text": "Reading the task"}).returncode, 0)
            done = add(folder, "handed_back", "builder-t1", {"text": "All checks pass", "result": "done"})
            self.assertEqual(done.returncode, 0, done.stderr)
            got = lines(folder / "logs" / "builder-t1.jsonl")
        for line in got:
            self.assertRegex(line.pop("at"), UTC)
        self.assertEqual(
            got,
            [
                {"type": "start", "by": "builder-t1", "text": "Reading the task"},
                {"type": "handed_back", "by": "builder-t1", "text": "All checks pass", "result": "done"},
            ],
        )

    def test_the_coordinator_writes_the_last_line_of_an_agent_that_stopped(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            write(folder, "logs/verifier-t1.card.json", [card("verifier", "T1")], as_json=True)
            write(
                folder,
                "logs/verifier-t1.jsonl",
                [{"type": "start", "at": "2026-11-21T10:00:00Z", "by": "verifier-t1", "text": "x"}],
            )
            done = add(
                folder,
                "handed_back",
                "verifier-t1",
                {"text": "Stopped by the user", "result": "fails"},
                "--by",
                "coordinator",
            )
            self.assertEqual(done.returncode, 0, done.stderr)
            last = lines(folder / "logs" / "verifier-t1.jsonl")[-1]
        self.assertEqual((last["type"], last["by"], last["result"]), ("handed_back", "coordinator", "fails"))

    def test_log_refuses_a_line_its_role_cannot_write_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            write(folder, "logs/verifier-t1.card.json", [card("verifier", "T1")], as_json=True)
            path = write(
                folder,
                "logs/verifier-t1.jsonl",
                [{"type": "start", "at": "2026-11-21T10:00:00Z", "by": "verifier-t1", "text": "x"}],
            )
            before = path.read_text()
            for kind, fields in (
                ("asked", {"text": "Which type?"}),
                ("handed_back", {"text": "ok", "result": "done"}),
                ("handed_back", {"text": "ok"}),
            ):
                with self.subTest(kind=kind, fields=fields):
                    done = add(folder, kind, "verifier-t1", fields)
                    self.assertEqual(done.returncode, 1)
                    self.assertEqual(path.read_text(), before)

    def test_log_refuses_an_agent_without_a_card(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            done = add(folder, "start", "builder-t1", {"text": "x"})
            self.assertEqual(done.returncode, 1)
            self.assertIn("card", done.stderr)
            self.assertFalse((folder / "logs" / "builder-t1.jsonl").exists())

    def test_log_ends_a_last_line_that_lacks_its_newline_before_it_appends(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            write(folder, "logs/builder-t1.card.json", [card("builder", "T1")], as_json=True)
            path = folder / "logs" / "builder-t1.jsonl"
            path.write_text(
                json.dumps({"type": "start", "at": "2026-11-21T10:00:00Z", "by": "builder-t1", "text": "x"})
            )
            self.assertEqual(add(folder, "step", "builder-t1", {"text": "y"}).returncode, 0)
            self.assertEqual([line["type"] for line in lines(path)], ["start", "step"])


class NextSteps(unittest.TestCase):
    STEP = {
        "step": "Add a size limit",
        "origin": {"type": "spec", "spec": "S1"},
        "if_nobody": "a 2 GB image stalls the resizer",
        "done_when": "an image over 50 MB is rejected",
        "priority": "high",
        "status": "proposed",
    }

    def test_next_step_is_its_own_record_type(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            done = run(folder, "add", str(folder), "next_step", "--by", "coordinator", stdin=json.dumps(self.STEP))
            self.assertEqual((done.returncode, done.stdout.strip()), (0, "N1"), done.stderr)
            self.assertEqual(lines(folder / "next-steps.jsonl")[0]["type"], "next_step")

    def test_step_is_a_log_line_and_needs_for(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            done = run(folder, "add", str(folder), "step", "--by", "coordinator", stdin=json.dumps(self.STEP))
            self.assertEqual(done.returncode, 1)
            self.assertIn("--for", done.stderr)
            self.assertFalse((folder / "next-steps.jsonl").exists())

    def test_the_spec_of_a_next_step_is_the_changes_own(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            bad = {**self.STEP, "origin": {"type": "spec", "spec": "S9"}}
            done = run(folder, "add", str(folder), "next_step", "--by", "coordinator", stdin=json.dumps(bad))
            self.assertEqual(done.returncode, 1)
            self.assertIn("dangling", done.stdout + done.stderr)


class Reply(unittest.TestCase):
    def comment(self, folder: Path, ident="m-1"):
        event = {"type": "comment", "at": "2026-11-21T10:00:00Z", "by": "user", "id": ident, "text": "why T2?"}
        event["on"] = {"kind": "agent", "id": "b1", "title": "b1"}
        with (folder / "conversation.jsonl").open("a") as f:
            f.write(json.dumps(event) + "\n")

    def statuses(self, folder: Path) -> list:
        return [(e.get("to"), e.get("status")) for e in lines(folder / "conversation.jsonl") if e["type"] == "status"]

    def test_a_reply_to_an_item_marks_it_done_in_the_same_write(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            self.comment(folder)
            done = run(folder, "reply", str(folder), "--to", "m-1", stdin="T2 holds the schema.", process=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            events = lines(folder / "conversation.jsonl")
            self.assertEqual([e["type"] for e in events], ["comment", "reply", "status"])
            self.assertEqual(self.statuses(folder), [("m-1", "done")])
            self.assertEqual(run(folder, "pending", str(folder)).stdout.count("m-1"), 0)

    def test_a_reply_that_asks_back_marks_the_item_asked(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            self.comment(folder)
            asked = run(folder, "reply", str(folder), "--to", "m-1", "--state", "asked", stdin="Which T2?")
            self.assertEqual(asked.returncode, 0, asked.stderr)
            self.assertEqual(self.statuses(folder), [("m-1", "asked")])

    def test_a_reply_to_an_unknown_item_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            self.comment(folder)
            before = (folder / "conversation.jsonl").read_text()
            done = run(folder, "reply", str(folder), "--to", "m-9", stdin="hi")
            self.assertEqual(done.returncode, 1)
            self.assertEqual((folder / "conversation.jsonl").read_text(), before)

    def test_a_reply_without_to_sets_no_status(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            self.assertEqual(run(folder, "reply", str(folder), stdin="T3 is merged.").returncode, 0)
            self.assertEqual([e["type"] for e in lines(folder / "conversation.jsonl")], ["reply"])


class ServedPage(unittest.TestCase):
    """`serve` shows the page, takes what the user sends in the schema's terms, and `pending` lists it."""

    def start(self, folder: Path):
        env = {**os.environ, "BETTER_AI_SKILL": "code-better"}
        cmd = better_module.command("serve", str(folder), "--no-browser")
        server = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
        self.addCleanup(lambda: (server.send_signal(signal.SIGTERM), server.communicate(timeout=10)))
        for _ in range(100):
            if (folder / ".server").exists():
                break
            time.sleep(0.1)
        return (folder / ".server").read_text().strip()

    def send(self, url, method, params):
        body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        headers = {"Content-Type": "application/json", "Origin": url.rstrip("/")}
        request = urllib.request.Request(url + "rpc", data=json.dumps(body).encode(), headers=headers)
        with urllib.request.urlopen(request, timeout=5) as r:
            return json.loads(r.read())

    def test_the_page_its_data_and_the_events_it_accepts(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            decision = {"type": "decision", "at": AT, "by": "coordinator", "id": "D1", "raised_by": "coordinator"}
            decision |= {"about": {"type": "change"}, "asked": "Count weekends?", "status": "waiting"}
            decision |= {"default": "No", "deadline": None}
            write(folder, "decisions.jsonl", [decision])
            url = self.start(folder)
            with urllib.request.urlopen(url, timeout=5) as r:
                page = r.read().decode()
            for part in ("/dashboard.js", "/page.js", 'id="tables"'):
                self.assertIn(part, page)
            self.assertNotIn("__PAGE_", page)
            with urllib.request.urlopen(url + "data", timeout=5) as r:
                data = json.loads(r.read())
            self.assertEqual(data["decisions"][0]["status"], "waiting")
            for asset in ("dashboard.js", "dashboard.css", "page.js", "page.css"):
                with urllib.request.urlopen(url + asset, timeout=5) as r:
                    self.assertEqual(r.status, 200)
            events = {
                "comment": {"id": "c-x", "text": "why?", "on": {"kind": "agent", "id": "b1", "title": "b1"}},
                "note": {"id": "m-x", "text": "hi", "to": None},
                "answer": {"id": "a-x", "decision": "D1", "text": "Business days only.", "default": False},
            }
            for method, params in events.items():
                self.assertEqual(self.send(url, method, params).get("result"), "saved", method)
            refused = self.send(url, "answer", {**events["answer"], "id": "a-y", "text": ""})
            self.assertEqual(refused["error"]["code"], -32602)
            self.assertIn("text", refused["error"]["message"])
            self.assertIn("error", self.send(url, "approve", {"id": "x"}))  # the page declares no approve
            out = run(folder, "pending", str(folder)).stdout
            items = [json.loads(line) for line in out.splitlines() if line.startswith("{")]
            answer = next(i for i in items if i["type"] == "answer")
            self.assertEqual((answer["decision"], answer["status"]), ("D1", "new"))
            self.assertEqual(run(folder, "check", str(folder)).returncode, 0)

    def test_a_line_in_the_format_before_this_change_is_a_notice_not_a_warning(self):
        old = {
            "type": "step",
            "at": "2026-11-21T10:00:00Z",
            "by": "coordinator",
            "id": "N1",
            "step": "x",
            "origin": {"type": "spec", "spec": "S1"},
            "if_nobody": "a",
            "done_when": "b",
            "priority": "low",
            "status": "asked",
        }
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            write(folder, "next-steps.jsonl", [old])
            checked = run(folder, "check", str(folder))
            self.assertEqual(checked.returncode, 0)
            self.assertIn("written in the format before this change", checked.stdout)
            env = {**os.environ, "BETTER_AI_SKILL": "code-better"}
            cmd = better_module.command("serve", str(folder), "--no-browser")
            server = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
            for _ in range(100):
                if (folder / ".server").exists():
                    break
                time.sleep(0.1)
            server.send_signal(signal.SIGTERM)
            _, err = server.communicate(timeout=10)
        self.assertIn("notice:", err)
        self.assertNotIn("warning:", err)

    def test_render_writes_one_page_with_its_data_and_no_link_to_a_server(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            done = run(folder, "render", str(folder), process=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            page = (folder / "dashboard.html").read_text()
        self.assertIn('id="page-data"', page)
        self.assertNotIn('src="/', page)
        self.assertNotIn('href="/', page)
        self.assertIn("Reject empty uploads", page)


class Create(unittest.TestCase):
    """`create` makes a change or an audit; a change whose design is an architect folder gets a copy of its spec."""

    def repo(self, d):
        root = Path(d)
        (root / ".git").mkdir()
        return root

    def head(self, design, mode="coordinate"):
        return json.dumps({"goal": "Uploads fail loudly", "design": design, "mode": mode})

    def design_spec(self, root: Path, records=None, folder="docs/designs/up"):
        write(root / folder, "spec.jsonl", records or [spec("S1"), spec("S2", "The service shall log it.")])

    ARCHITECT = {"type": "architect", "folder": "docs/designs/up"}

    def test_create_writes_the_head_and_the_folders(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.repo(d)
            folder = root / ".code" / "c"
            done = run(
                folder,
                "create",
                str(folder),
                "--by",
                "coordinator",
                stdin=self.head({"type": "request", "text": "x"}),
                process=True,
            )
            self.assertEqual(done.returncode, 0, done.stderr)
            head = json.loads((folder / "code.json").read_text())
            self.assertEqual((head["type"], head["by"], head["mode"]), ("code", "coordinator", "coordinate"))
            self.assertTrue((folder / "logs").is_dir())
            self.assertFalse((folder / "spec.jsonl").exists())

    def test_create_twice_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.repo(d)
            folder = root / ".code" / "c"
            head = self.head({"type": "request", "text": "x"})
            self.assertEqual(run(folder, "create", str(folder), "--by", "coordinator", stdin=head).returncode, 0)
            before = (folder / "code.json").read_text()
            again = run(folder, "create", str(folder), "--by", "coordinator", stdin=head)
            self.assertEqual(again.returncode, 1)
            self.assertIn("already holds a unit", again.stderr)
            self.assertEqual((folder / "code.json").read_text(), before)

    def test_create_copies_the_architect_spec_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.repo(d)
            self.design_spec(root)
            folder = root / ".code" / "c"
            done = run(folder, "create", str(folder), "--by", "coordinator", stdin=self.head(self.ARCHITECT))
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual((folder / "spec.jsonl").read_bytes(), (root / "docs/designs/up/spec.jsonl").read_bytes())
            self.assertEqual(run(folder, "check", str(folder)).returncode, 0)

    def test_create_writes_nothing_when_a_line_of_the_architect_spec_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.repo(d)
            bad = {k: v for k, v in spec("S2").items() if k != "statement"}
            self.design_spec(root, [spec("S1"), bad])
            folder = root / ".code" / "c"
            done = run(folder, "create", str(folder), "--by", "coordinator", stdin=self.head(self.ARCHITECT))
            self.assertEqual(done.returncode, 1)
            self.assertIn("spec.jsonl:2: statement", done.stderr)
            self.assertFalse(folder.exists())

    def test_create_refuses_a_design_folder_without_a_spec(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.repo(d)
            (root / "docs" / "designs" / "up").mkdir(parents=True)
            folder = root / ".code" / "c"
            done = run(folder, "create", str(folder), "--by", "coordinator", stdin=self.head(self.ARCHITECT))
            self.assertEqual(done.returncode, 1)
            self.assertIn("holds no spec.jsonl", done.stderr)
            self.assertFalse(folder.exists())

    def test_create_copies_a_spec_whose_sources_point_into_the_architect_folder(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.repo(d)
            source = {"type": "decision", "decision": "D1"}
            self.design_spec(root, [spec("S1", source=source)])
            folder = root / ".code" / "c"
            refused = run(folder, "create", str(folder), "--by", "coordinator", stdin=self.head(self.ARCHITECT))
            self.assertEqual(refused.returncode, 1)
            self.assertIn("dangling", refused.stderr)
            write(
                root / "docs" / "designs" / "up",
                "decisions.jsonl",
                [{"type": "decision", "at": AT, "by": "a", "id": "D1"}],
            )
            done = run(folder, "create", str(folder), "--by", "coordinator", stdin=self.head(self.ARCHITECT))
            self.assertEqual(done.returncode, 0, done.stderr)

    def test_create_refuses_a_design_folder_that_leaves_the_repository(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.repo(d)
            folder = root / ".code" / "c"
            for design_folder in ("../outside", "/etc", "docs/../../x"):
                with self.subTest(design_folder):
                    head = self.head({"type": "architect", "folder": design_folder})
                    done = run(folder, "create", str(folder), "--by", "coordinator", stdin=head)
                    self.assertEqual(done.returncode, 1)
                    self.assertFalse(folder.exists())

    def test_create_refuses_a_stray_spec_when_there_is_no_code_json(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.repo(d)
            self.design_spec(root)
            folder = root / ".code" / "c"
            write(folder, "spec.jsonl", [spec("S1")])
            done = run(folder, "create", str(folder), "--by", "coordinator", stdin=self.head(self.ARCHITECT))
            self.assertEqual(done.returncode, 1, done.stderr)
            self.assertIn(
                "it holds a spec.jsonl and no code.json. move spec.jsonl away, then run create again", done.stderr
            )
            self.assertFalse((folder / "code.json").exists())

    def test_create_refuses_a_design_folder_with_spaces_around_it(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.repo(d)
            self.design_spec(root)
            folder = root / ".code" / "c"
            for named in (" docs/designs/up", "docs/designs/up ", "\tdocs/designs/up\n"):
                with self.subTest(repr(named)):
                    head = self.head({"type": "architect", "folder": named})
                    done = run(folder, "create", str(folder), "--by", "coordinator", stdin=head)
                    self.assertEqual(done.returncode, 1, done.stderr)
                    self.assertIn("design.folder", done.stderr)
                    self.assertFalse(folder.exists())

    def test_a_design_folder_that_leaves_the_repository_says_repository_with_one_stop(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.repo(d)
            folder = root / ".code" / "c"
            done = run(
                folder,
                "create",
                str(folder),
                "--by",
                "coordinator",
                stdin=self.head({"type": "architect", "folder": "../x"}),
            )
            self.assertEqual(done.returncode, 1)
            self.assertIn("not a path inside the repository", done.stderr)
            self.assertNotIn("..", done.stderr.replace("../x", ""))

    def test_a_started_changes_own_decisions_never_answer_a_pointer_of_the_copied_spec(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.repo(d)
            self.design_spec(root, [spec("S1", source={"type": "decision", "decision": "D1"})])
            folder = root / ".code" / "c"
            write(folder, "code.json", [code("coordinate", self.ARCHITECT)], as_json=True)
            write(folder, "decisions.jsonl", [{"type": "decision", "at": AT, "by": "coordinator", "id": "D1"}])
            done = run(folder, "create", str(folder), "--by", "coordinator")
            self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
            self.assertIn("dangling", done.stderr)
            self.assertFalse((folder / "spec.jsonl").exists())

    def test_a_symlinked_design_folder_and_a_symlinked_spec_are_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.repo(d)
            elsewhere = root / "elsewhere"
            write(elsewhere, "spec.jsonl", [spec("S1")])
            (root / "docs" / "designs").mkdir(parents=True)
            os.symlink(elsewhere, root / "docs" / "designs" / "up")
            folder = root / ".code" / "c"
            done = run(folder, "create", str(folder), "--by", "coordinator", stdin=self.head(self.ARCHITECT))
            self.assertEqual(done.returncode, 1, done.stderr)
            self.assertIn("symlink", done.stderr)
            self.assertFalse(folder.exists())
            os.unlink(root / "docs" / "designs" / "up")
            (root / "docs" / "designs" / "up").mkdir()
            os.symlink(elsewhere / "spec.jsonl", root / "docs" / "designs" / "up" / "spec.jsonl")
            done = run(folder, "create", str(folder), "--by", "coordinator", stdin=self.head(self.ARCHITECT))
            self.assertEqual(done.returncode, 1, done.stderr)
            self.assertIn("symlink", done.stderr)
            self.assertFalse(folder.exists())

    def test_create_on_a_started_change_copies_only_the_spec(self):
        """An architect-led change that has code.json and no spec.jsonl gets that file, and nothing else is touched."""
        with tempfile.TemporaryDirectory() as d:
            root = self.repo(d)
            self.design_spec(root)
            folder = root / ".code" / "c"
            write(folder, "code.json", [code("coordinate", self.ARCHITECT)], as_json=True)
            write(folder, "tasks.jsonl", [{"type": "task", "at": AT}])
            before = {p.name: p.read_bytes() for p in folder.iterdir()}
            done = run(folder, "create", str(folder), "--by", "coordinator")
            self.assertEqual(done.returncode, 0, done.stderr)
            after = {p.name: p.read_bytes() for p in folder.iterdir()}
            self.assertEqual(set(after) - set(before), {"spec.jsonl"})
            self.assertEqual({k: v for k, v in after.items() if k != "spec.jsonl"}, before)
            again = run(folder, "create", str(folder), "--by", "coordinator")
            self.assertEqual(again.returncode, 1)
            self.assertIn("already holds a unit", again.stderr)

    def test_every_verb_but_create_refuses_a_change_that_has_no_copy_yet(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.repo(d)
            self.design_spec(root)
            folder = root / ".code" / "c"
            write(folder, "code.json", [code("coordinate", self.ARCHITECT)], as_json=True)
            task = '{"task": "x", "mode": "feature", "requirements": ["S1"], "check": "c", "status": "todo"}'
            commands = [
                ("add", str(folder), "task", "--by", "coordinator"),
                ("set", str(folder), "code"),
                ("check", str(folder)),
                ("serve", str(folder), "--no-browser", "--once"),
                ("render", str(folder)),
                ("pending", str(folder)),
                ("status", str(folder), "seen", "m-1"),
                ("reply", str(folder)),
                ("wait", str(folder), "--timeout", "1"),
            ]
            for command in commands:
                with self.subTest(command[0]):
                    done = run(folder, *command, stdin=task)
                    self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
                    self.assertIn("run create .code/c", done.stderr)
            self.assertEqual(run(folder, "create", str(folder), "--by", "coordinator").returncode, 0)
            self.assertEqual(run(folder, "check", str(folder)).returncode, 0)

    def test_create_makes_an_audit_with_not_read_null(self):
        with tempfile.TemporaryDirectory() as d:
            root = self.repo(d)
            folder = root / ".code" / "audit" / "2026-11-22"
            head = json.dumps({"goal": "Review the upload path", "commit": "abc1234", "not_read": None})
            done = run(folder, "create", str(folder), "--by", "builder", stdin=head)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertIsNone(json.loads((folder / "audit.json").read_text())["not_read"])
            self.assertEqual(run(folder, "check", str(folder)).returncode, 0)
            filled = run(folder, "set", str(folder), "audit", stdin='{"not_read": "the vendor folder"}')
            self.assertEqual(filled.returncode, 0, filled.stderr)
            self.assertEqual(json.loads((folder / "audit.json").read_text())["not_read"], "the vendor folder")


if __name__ == "__main__":
    unittest.main()
