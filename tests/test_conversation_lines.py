"""Every reader of conversation.jsonl that the thread states are computed from keeps each event's line position.

A status's `read` is a line index of the log. A reader that dropped a line it cannot read would shift every later
index, so a stale `asked` would count as fresh and hide the user's message. Each caller here reads one log with a
cut-off line and must give the threads that the positional reading (`Conversation.events`) gives: `pending`, `wait`,
discover's `summary`, the data of the code dashboard, the research board and the discover page, and page.js on that
data.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

import architect_records as rec  # noqa: E402
import better  # noqa: E402
import code_records  # noqa: E402
import discover_populated  # noqa: E402
import research_records  # noqa: E402

from better_ai import architect, code, discover, page, paths, research, resources  # noqa: E402
from better_ai.code import dashboard  # noqa: E402
from better_ai.discover import pagespec  # noqa: E402
from better_ai.research import board  # noqa: E402

AT = "2026-11-28T10:00:00Z"
NOTE_1 = {"type": "note", "at": AT, "by": "user", "id": "m1", "text": "Make it smaller.", "to": None}
NOTE_2 = {"type": "note", "at": AT, "by": "user", "id": "m2", "text": "And blue.", "to": "m1"}
# Decided after line 1 (the cut-off line), before line 2, the user's note: a stale question.
STALE = {"type": "status", "at": AT, "by": "coordinator", "to": "m1", "status": "asked", "read": 1}
CUT = '{"type": "note", "at": "2026-11-28T10:00:00Z", "by": "user", "id": "m9", "te'
LINES = [json.dumps(NOTE_1), CUT, json.dumps(NOTE_2), json.dumps(STALE)]


def write_log(folder: Path, lines=LINES) -> None:
    (folder / "conversation.jsonl").write_text("".join(line + "\n" for line in lines))


def states(threads) -> list:
    return [[t["id"], t["state"], t["step"]] for t in threads if not t["deleted"]]


class ConversationLines(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(os.path.realpath(tmp.name))
        self.payloads = []

    def test_the_architect_render_keeps_line_positions(self):
        """The events `render` embeds, which architect/page.js reads, give the positional thread states."""
        folder = rec.example_folder(self.root / "architect")
        write_log(folder)
        code_, _, err = rec.run_cli("render", str(folder))
        self.assertEqual(code_, 0, err)
        text = (folder / "render" / "index.html").read_text()
        data = json.loads(re.search(r'id="page-data">(.*?)</script>', text, re.S).group(1))
        spec = page.spec_of(architect.SKILL)
        self.assertIn(["m1", "agent", "new"], states(page.threads(data["events"], (*spec.tracked(), "note"))))

    def test_the_static_architect_page_gets_the_events_with_their_lines(self):
        """architect-better's `render` embeds `Conversation.logged()`: the readable events, each with its line."""
        folder = code_records.change(self.root / "logged")
        write_log(folder)
        unit = paths.resolve_unit(str(folder), code.SKILL)
        conv = page.Conversation(unit, dashboard.SPEC, {})
        self.assertEqual([e.get("_i") for e in conv.logged()], [0, 2, 3])
        self.assertEqual(states(page.threads(conv.logged(), ("note",))), [["m1", "agent", "new"]])

    def positional(self, unit, spec) -> list:
        """The thread states of the unit's log read by line position, as `pending` reads it."""
        return states(page.threads(page.Conversation(unit, spec, {}).events(), spec.tracked()))

    def served(self, label, unit, spec, data) -> None:
        """The data a page serves gives the positional thread states in Python, and is queued for page.js."""
        expected = self.positional(unit, spec)
        self.assertEqual(expected[0], ["m1", "agent", "new"], label)  # the stale question does not hide m2
        self.assertEqual(states(page.threads(data["conversation"], spec.tracked())), expected, label)
        self.payloads.append(
            {
                "label": label,
                "kinds": list(spec.tracked()),
                "decisions": data.get("decisions") or [],
                "conversation": data["conversation"],
                "positional": page.Conversation(unit, spec, {}).events(),
            }
        )

    def test_every_reader_of_the_log_keeps_line_positions(self):
        # pending and wait, on a code change: the CLI's own reading.
        folder = code_records.change(self.root / "code")
        unit = paths.resolve_unit(str(folder), code.SKILL)
        write_log(folder)
        done = better.call("code-better", "pending", str(folder))
        listed = [json.loads(line) for line in done.stdout.splitlines()[:-1]]
        self.assertEqual([(e["id"], e["status"]) for e in listed], [("m1", "new")], done.stderr)
        self.assertEqual((folder / ".conversation-read").read_text(), "3")  # the cut-off line counts
        self.served("code dashboard", unit, dashboard.SPEC, dashboard.load(unit))
        self.wait_counts_the_cut_off_line(folder, unit)

        # discover: the summary and the page's data.
        folder = discover_populated.populated(self.root / "discover")
        unit = paths.resolve_unit(str(folder), discover.SKILL)
        write_log(folder)
        done = better.call("discover-better", "summary", str(folder), cwd=self.root / "discover")
        events = [json.loads(line) for line in done.stdout.splitlines() if line.startswith('{"type": "event"')]
        self.assertEqual([(e["id"], e["state"], e["step"]) for e in events], [("m1", "agent", "new")], done.stderr)
        self.served("discover page", unit, pagespec.SPEC, pagespec.load(unit))

        # the research board's data.
        (self.root / "research").mkdir()
        folder = research_records.made_board(self.root / "research")
        unit = paths.resolve_unit(str(folder), research.SKILL)
        write_log(folder)
        self.served("research board", unit, board.SPEC, board.load(unit))

        # page.js on the data each page serves.
        node = shutil.which("node")
        if not node:
            self.skipTest("node is not installed: page.js not run")
        payloads = self.root / "payloads.json"
        payloads.write_text(json.dumps(self.payloads))
        run = subprocess.run(
            [node, str(HERE / "threads-of.js"), str(payloads)], capture_output=True, text=True, timeout=120
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        for drawn in json.loads(run.stdout):
            self.assertIn(["m1", "agent", "new"], drawn["threads"], drawn["label"])
            self.assertEqual(drawn["threads"], drawn["positional"], drawn["label"])

    def wait_counts_the_cut_off_line(self, folder, unit):
        """`wait` records the last line it showed, counting the cut-off line, so the agent's next status counts."""
        write_log(folder, LINES[:2])
        (folder / ".conversation-seen").write_text("2")  # an earlier wait showed m1 and the cut-off line
        (folder / ".conversation-read").unlink(missing_ok=True)
        conv = page.Conversation(unit, dashboard.SPEC, {})  # it only serves: nothing is checked
        skill = mock.patch.dict(os.environ, {"BETTER_AI_SKILL": "code-better"})
        skill.start()
        self.addCleanup(skill.stop)
        server = page.make_server(unit, dashboard.SPEC, conv, resources.build_info())
        threading.Thread(target=server.serve_forever, kwargs={"poll_interval": page.POLL}, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        page.publish(unit, server)

        def user_writes():
            with (folder / "conversation.jsonl").open("a") as handle:
                handle.write(json.dumps(NOTE_2) + "\n")

        writer = threading.Timer(0.5, user_writes)
        writer.start()
        self.addCleanup(writer.cancel)
        done = better.call("code-better", "wait", str(folder), "--timeout", "20")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual((folder / ".conversation-read").read_text(), "2")
        self.assertEqual(better.call("code-better", "status", str(folder), "asked", "m1").returncode, 0)
        (m1,) = page.threads(conv.events(), dashboard.SPEC.tracked())
        self.assertEqual((m1["state"], m1["step"]), ("you", "new"))
        write_log(folder)


if __name__ == "__main__":
    unittest.main()
