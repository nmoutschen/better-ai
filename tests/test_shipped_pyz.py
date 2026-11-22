"""The committed skills/*/scripts/better.pyz files, as a user gets them: S27 (the verbs each offers) and S67 (each runs with
`python -I` from a copy of its skill folder alone)."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY310 = os.environ.get("BETTER_AI_PYTHON310", "python3.10")

COMMON = {"create", "add", "set", "check", "serve", "wait", "reply", "status", "pending"}
VERBS = {
    "architect-better": COMMON | {"render", "review", "specs", "register"},
    "code-better": COMMON | {"render"},
    "design-better": COMMON | {"render"},
    "research-better": COMMON | {"render"},
    "show-better": COMMON | {"render"},
}


class ShippedPyz(unittest.TestCase):
    def help_of(self, python: str, skill: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / skill
            shutil.copytree(ROOT / "skills" / skill, copy)
            return subprocess.run(
                [python, "-I", str(copy / "scripts" / "better.pyz"), "--help"], capture_output=True, text=True, cwd=copy
            )

    def test_each_skill_ships_one_pyz_and_it_lists_exactly_its_verbs(self):
        for skill, verbs in VERBS.items():
            with self.subTest(skill=skill):
                tracked = subprocess.run(
                    ["git", "ls-files", f"skills/{skill}/scripts"], cwd=ROOT, capture_output=True, text=True, check=True
                ).stdout.split()
                self.assertEqual(tracked, [f"skills/{skill}/scripts/better.pyz"])  # untracked caches do not ship
                done = self.help_of(sys.executable, skill)
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertRegex(done.stdout.splitlines()[0], rf"^better\.pyz {skill} [0-9a-f]{{16}}$")
                listed = set(re.findall(r"^    ([a-z]+) {2,}\S", done.stdout, re.M))
                self.assertEqual(listed, verbs)

    def test_each_runs_on_python_3_10_from_a_copy_of_its_skill_folder_alone(self):
        found = shutil.which(PY310) or (PY310 if Path(PY310).exists() else None)
        if not found:
            self.skipTest("no Python 3.10; set BETTER_AI_PYTHON310")
        for skill, verbs in VERBS.items():
            with self.subTest(skill=skill):
                done = self.help_of(found, skill)
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertEqual(set(re.findall(r"^    ([a-z]+) {2,}\S", done.stdout, re.M)), verbs)


if __name__ == "__main__":
    unittest.main()
