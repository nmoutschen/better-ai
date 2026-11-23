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


class Unit(unittest.TestCase):
    """A repository with a code-better change and one decision."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        repo = Path(os.path.realpath(tmp.name)) / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        self.unit = repo / ".code" / "x"
        self.assertEqual(call("code-better", "create", self.unit, "--by", "coordinator", stdin=HEAD)[0], 0)
        self.assertEqual(call("code-better", "add", self.unit, "decision", "--by", "coordinator", stdin=DECISION)[0], 0)


class SetBy(Unit):
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


class SetRaw(Unit):
    """`set --raw <file>`: the path reaches the set steps as `ctx.raw`; a `--raw` that no step reads is refused."""

    def raw_seen(self, read):
        seen = []

        def step(ctx):
            seen.append(ctx.raw)
            ctx.raw_read = read

        with mock.patch.dict(records.SET_STEPS, {"code-better": [step]}):
            done = call("code-better", "set", self.unit, "D1", "--raw", "page.txt", stdin={"decision": "B"})
        return done, seen

    def test_a_step_reads_the_path(self):
        done, seen = self.raw_seen(True)
        self.assertEqual(done[0], 0, done)
        self.assertEqual(seen, ["page.txt"])

    def test_a_raw_no_step_reads_is_refused(self):
        done, seen = self.raw_seen(False)
        self.assertEqual(done[0], 1, done)
        self.assertIn("--raw is not used", done[2])

    def test_raw_is_none_without_it(self):
        seen = []
        with mock.patch.dict(records.SET_STEPS, {"code-better": [lambda ctx: seen.append(ctx.raw)]}):
            done = call("code-better", "set", self.unit, "D1", stdin={"decision": "B"})
        self.assertEqual((done[0], seen), (0, [None]))


class SetUnsets(Unit):
    """`set --unset <field>`: the fields to remove reach the set steps as `ctx.unsets`."""

    def seen(self, *args):
        seen = []
        with mock.patch.dict(records.SET_STEPS, {"code-better": [lambda ctx: seen.append(ctx.unsets)]}):
            done = call("code-better", "set", self.unit, "D1", *args, stdin={"asked": "which one?"})
        return done, seen

    def test_the_steps_see_the_unset_fields(self):
        done, seen = self.seen("--unset", "decision", "--unset", "default")
        self.assertEqual(seen, [("decision", "default")], done)

    def test_no_unset_is_an_empty_tuple(self):
        done, seen = self.seen()
        self.assertEqual((done[0], seen), (0, [()]))


if __name__ == "__main__":
    unittest.main()
