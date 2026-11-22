"""dashboard.py's board commands: agents and the coordinator write cards, log lines and replies only through them.

`card` and `log` stamp `at` with the current UTC time, so no agent types a time, and write nothing that fails its
schema. `reply --to` answers an item and sets its status in one write, so no reply is left without one.
"""

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard_formats import SCRIPTS, card, change, write  # noqa: E402

UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def run(*args):
    cmd = [sys.executable, "-I", str(SCRIPTS / "dashboard.py"), *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30)


def lines(path: Path) -> list:
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


class Card(unittest.TestCase):
    def test_card_writes_a_stamped_card(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            done = run("card", str(folder), "builder-t1", "--role", "builder", "--task", "T1", "--branch", "feat/t1")
            self.assertEqual(done.returncode, 0, done.stderr)
            written = json.loads((folder / "logs" / "builder-t1.card.json").read_text())
        self.assertRegex(written.pop("at"), UTC)
        self.assertEqual(
            written, {"type": "card", "by": "coordinator", "role": "builder", "task": "T1", "branch": "feat/t1"}
        )

    def test_card_refuses_a_task_not_in_the_task_list_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            done = run("card", str(folder), "builder-t9", "--role", "builder", "--task", "T9", "--branch", "b")
            self.assertEqual(done.returncode, 1)
            self.assertIn("task", done.stderr)
            self.assertFalse((folder / "logs" / "builder-t9.card.json").exists())

    def test_card_refuses_a_name_another_agent_already_has(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            path = write(folder, "logs/builder-t1.card.json", [card("builder", "T1")], as_json=True)
            before = path.read_text()
            done = run("card", str(folder), "builder-t1", "--role", "verifier", "--task", "T1", "--branch", "b")
            self.assertEqual(done.returncode, 1)
            self.assertEqual(path.read_text(), before)


class Log(unittest.TestCase):
    def test_log_appends_a_stamped_line_by_the_agent(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            write(folder, "logs/builder-t1.card.json", [card("builder", "T1")], as_json=True)
            self.assertEqual(run("log", str(folder), "builder-t1", "start", "Reading the task").returncode, 0)
            done = run("log", str(folder), "builder-t1", "handed_back", "All checks pass", "--result", "done")
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
            done = run(
                "log",
                str(folder),
                "verifier-t1",
                "handed_back",
                "Stopped by the user",
                "--result",
                "fails",
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
            for args in (("asked", "Which type?"), ("handed_back", "ok", "--result", "done"), ("handed_back", "ok")):
                with self.subTest(args=args):
                    done = run("log", str(folder), "verifier-t1", *args)
                    self.assertEqual(done.returncode, 1)
                    self.assertEqual(path.read_text(), before)

    def test_log_refuses_an_agent_without_a_card(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            done = run("log", str(folder), "builder-t1", "start", "x")
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
            self.assertEqual(run("log", str(folder), "builder-t1", "step", "y").returncode, 0)
            self.assertEqual([line["type"] for line in lines(path)], ["start", "step"])


class Reply(unittest.TestCase):
    def comment(self, folder: Path, ident="m-1"):
        event = {"type": "comment", "at": "2026-11-21T10:00:00Z", "by": "user", "id": ident, "text": "why T2?"}
        with (folder / "conversation.jsonl").open("a") as f:
            f.write(json.dumps(event) + "\n")

    def statuses(self, folder: Path) -> list:
        return [(e.get("to"), e.get("status")) for e in lines(folder / "conversation.jsonl") if e["type"] == "status"]

    def test_a_reply_to_an_item_marks_it_done_in_the_same_write(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            self.comment(folder)
            done = run("reply", str(folder), "T2 holds the schema.", "--to", "m-1")
            self.assertEqual(done.returncode, 0, done.stderr)
            events = lines(folder / "conversation.jsonl")
            self.assertEqual([e["type"] for e in events], ["comment", "reply", "status"])
            self.assertEqual(self.statuses(folder), [("m-1", "done")])
            self.assertEqual(run("pending", str(folder)).stdout.count("m-1"), 0)

    def test_a_reply_that_asks_back_marks_the_item_asked(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            self.comment(folder)
            self.assertEqual(run("reply", str(folder), "Which T2?", "--to", "m-1", "--state", "asked").returncode, 0)
            self.assertEqual(self.statuses(folder), [("m-1", "asked")])

    def test_a_reply_to_an_unknown_item_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            self.comment(folder)
            before = (folder / "conversation.jsonl").read_text()
            done = run("reply", str(folder), "hi", "--to", "m-9")
            self.assertEqual(done.returncode, 1)
            self.assertEqual((folder / "conversation.jsonl").read_text(), before)

    def test_a_reply_without_to_sets_no_status(self):
        with tempfile.TemporaryDirectory() as d:
            folder = change(Path(d))
            self.assertEqual(run("reply", str(folder), "T3 is merged.").returncode, 0)
            self.assertEqual([e["type"] for e in lines(folder / "conversation.jsonl")], ["reply"])


if __name__ == "__main__":
    unittest.main()
