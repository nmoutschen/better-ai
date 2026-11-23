"""`set --by`: the writer of a change reaches the skill's set steps as `ctx.by`; the record's own `by` never changes."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

from better import call as in_process  # noqa: E402

from better_ai import code, records  # noqa: E402,F401

HEAD = {"goal": "g", "design": {"type": "request", "text": "t"}, "mode": "coordinate"}
DECISION = {
    "raised_by": "coordinator",
    "about": {"type": "change"},
    "asked": "which?",
    "status": "decided",
    "decision": "A",
}


def call(skill, *args, stdin=None):
    done = in_process(skill, *args, stdin=json.dumps(stdin) if isinstance(stdin, dict) else stdin)
    return done.returncode, done.stdout, done.stderr


class SetBy(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        repo = Path(os.path.realpath(tmp.name)) / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        self.unit = repo / ".code" / "x"
        self.assertEqual(call("code-better", "create", self.unit, "--by", "coordinator", stdin=HEAD)[0], 0)
        self.assertEqual(call("code-better", "add", self.unit, "decision", "--by", "coordinator", stdin=DECISION)[0], 0)

    def seen_by(self, *args):
        seen = []
        with mock.patch.dict(records.SET_STEPS, {"code-better": [lambda ctx: seen.append(ctx.by)]}):
            done = call("code-better", "set", self.unit, "D1", *args, stdin={"decision": "B"})
        return done, seen

    def test_s32_a_set_step_reads_the_writer(self):
        done, seen = self.seen_by("--by", "writer-1")
        self.assertEqual(done[0], 0, done)
        self.assertEqual(seen, ["writer-1"])

    def test_s32_by_is_optional_and_none_without_it(self):
        done, seen = self.seen_by()
        self.assertEqual(done[0], 0, done)
        self.assertEqual(seen, [None])

    def test_s32_the_stored_by_is_the_creators(self):
        self.seen_by("--by", "writer-1")
        (line,) = [json.loads(x) for x in (self.unit / "decisions.jsonl").read_text().splitlines()]
        self.assertEqual((line["by"], line["decision"]), ("coordinator", "B"))

    def test_s32_by_is_checked_as_add_checks_it(self):
        for bad in ("user", "A b"):
            done, seen = self.seen_by("--by", bad)
            self.assertEqual(done[0], 1, done)
            self.assertEqual(seen, [])


if __name__ == "__main__":
    unittest.main()
