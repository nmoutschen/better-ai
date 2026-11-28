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
