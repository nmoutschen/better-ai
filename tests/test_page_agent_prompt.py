"""The shared page-agent prompt and the copy shipped with each skill."""

import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESOURCE = "better_ai/page/page-agent.md"


class PageAgentPromptTest(unittest.TestCase):
    def test_prompt_is_shipped_unchanged_in_every_zipapp(self):
        prompt = (ROOT / "src" / RESOURCE).read_bytes()
        archives = sorted(ROOT.glob("skills/*/scripts/better.pyz"))
        self.assertTrue(archives)
        for archive in archives:
            with self.subTest(skill=archive.parent.parent.name), zipfile.ZipFile(archive) as contents:
                self.assertEqual(contents.read(RESOURCE), prompt)

    def test_prompt_defines_inputs_and_turn_rules(self):
        prompt = (ROOT / "src" / RESOURCE).read_text(encoding="utf-8")
        _, inputs, output = prompt.partition("## Input\n")
        self.assertTrue(inputs)
        inputs, separator, output = output.partition("## Output\n")
        self.assertTrue(separator)
        for field in ("SKILL.md", "Unit", "Current step", "Hand-off note", "Verb command", "Working directory", "Items"):
            with self.subTest(field=field):
                self.assertIn(field, inputs)
        for rule in (
            "PUT every word for the user through `reply`",
            "ADD `--state asked`",
            "NEVER run `serve` or `wait`",
            "END the turn once the items are handled",
            "END the turn once you start workers",
            "After a denial, DO NOT repeat the call",
            "ASK with `reply --state asked`",
        ):
            with self.subTest(rule=rule):
                self.assertIn(rule, output)
