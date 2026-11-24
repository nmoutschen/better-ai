"""S35: every served page shows the lines in the format before this change as one count, from the shared shell and
page.js, and no skill draws a count of its own. Each skill's page is served as an agent serves it (`serve`, no browser)
on a unit holding one line in that skill's old format."""

import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

import better  # noqa: E402
import pyz  # noqa: E402

sys.path.insert(0, str(HERE.parent / "tools"))
import smoke  # noqa: E402

from better_ai import page  # noqa: E402

SRC = HERE.parent / "src" / "better_ai"
UNITS = HERE / "fixtures" / "units"
OLD_AT = "2026-11-01T10:00:00Z"


def prepare(skill, repo, count):
    """A git repository holding the skill's fixture files and the first `count` steps of its smoke fixture run."""
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    fixture = UNITS / skill
    spec = json.loads((fixture / "smoke.json").read_text())
    smoke.place_repo_files(spec, fixture, repo)
    for step in spec["steps"][:count]:
        args, stdin = smoke.step_input(step, fixture, repo)
        done = better.run(skill, *args, stdin=stdin, cwd=repo)
        assert done.returncode == 0, done.stdout + done.stderr


def lines(folder, name, *records):
    (folder / name).write_text("".join(json.dumps(r) + "\n" for r in records))


def old_code(folder):
    lines(
        folder,
        "next-steps.jsonl",
        {
            "type": "step",
            "at": OLD_AT,
            "by": "coordinator",
            "id": "N1",
            "step": "x",
            "origin": {"type": "spec", "spec": "S1"},
            "if_nobody": "a",
            "done_when": "b",
            "priority": "low",
            "status": "asked",
        },
    )


def old_research(folder):
    decision = {"type": "decision", "at": OLD_AT, "by": "coordinator", "asked": "Login?", "id": "D1"}
    lines(folder, "decisions.jsonl", {**decision, "default": "Go on", "deadline": OLD_AT, "status": "pending"})


def old_design(folder):
    decide = {"type": "decide", "at": OLD_AT, "by": "user", "id": "d1", "option": "A", "label": "Build A"}
    lines(folder, "conversation.jsonl", {**decide, "carries": [], "text": None})


def old_show(folder):
    spec = json.loads((UNITS / "show-better" / "spec.json").read_text())
    (folder / "spec.json").write_text(json.dumps(spec))


CASES = {
    "code-better": (".code/demo", 2, old_code, 1),  # the unit and its spec S1, which the old line points to
    "research-better": (".research/demo", 1, old_research, 1),
    "design-better": (".design/demo", 1, old_design, 1),
    "show-better": (".show/demo", 1, old_show, 1),
    "architect-better": (".architect/demo", 1, None, 0),  # architect keeps no format from before this change
    "discover-better": (".discover/demo", 1, None, 0),  # discover has always used the current format
}


def served(skill, repo, unit):
    full = {**os.environ, "BETTER_AI_SKILL": skill}
    return subprocess.Popen(
        better.command("serve", unit, "--no-browser"),
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=full,
    )


class OldFormatCountTest(unittest.TestCase):
    def test_every_shipped_skill_has_an_old_format_count_case(self):
        self.assertEqual(set(CASES), set(pyz.skill_names()))

    def test_every_page_carries_the_shared_count_and_serves_it_S35(self):
        for skill, (unit, setup, make_old, expected) in CASES.items():
            with self.subTest(skill), tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)
                prepare(skill, repo, setup)
                folder = repo / unit
                if make_old:
                    make_old(folder)
                server = served(skill, repo, unit)
                try:
                    address = folder / ".server"
                    url = ""
                    for _ in range(100):
                        if address.exists():
                            url = address.read_text().strip()
                            if url:
                                break
                        time.sleep(0.1)
                    self.assertTrue(url, "serve did not publish its address")
                    with urllib.request.urlopen(url + "old", timeout=10) as response:  # noqa: S310
                        self.assertEqual(json.loads(response.read()), expected)
                    with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310
                        shell = response.read().decode()
                    self.assertEqual(len(re.findall(r'id="oldnote"', shell)), 1)
                finally:
                    server.terminate()
                    server.communicate(timeout=10)

    def test_a_rendered_page_carries_the_same_count_as_the_served_one(self):
        outputs = {
            "code-better": "dashboard.html",
            "research-better": "board.html",
            "design-better": "index.html",
            "show-better": "page.html",
        }
        for skill, name in outputs.items():
            unit, setup, make_old, expected = CASES[skill]
            with self.subTest(skill), tempfile.TemporaryDirectory() as tmp:
                repo = Path(tmp)
                prepare(skill, repo, setup)
                make_old(repo / unit)
                done = better.run(skill, "render", unit, cwd=repo)
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                text = (repo / unit / name).read_text()
                # The count is in the page as it opens, not only in data a script may never read.
                self.assertRegex(
                    text, r'<p class="oldnote" id="oldnote" role="status">1 record in the format before this'
                )

    def test_no_skill_draws_a_count_of_its_own(self):
        for path in SRC.glob("*/*"):
            if path.suffix in (".js", ".html", ".css") and path.parent.name != "page":
                # A static page that does not use the shell holds the shared empty element, which render fills.
                text = path.read_text().replace(page.OLD_NOTE, "")
                self.assertNotIn("format before this change", text, path.name)
                self.assertNotIn("oldnote", text, path.name)


if __name__ == "__main__":
    unittest.main()
