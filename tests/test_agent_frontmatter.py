"""Every agent file of every skill has the frontmatter of PRINCIPLES 6.9, with a model and the reason for it."""

import re
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parent.parent / "skills"
FIELDS = ["name", "description", "capabilities", "edits", "model", "model_reason"]


def frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return {}
    out = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(":")
        out[key] = value.strip()
    return out


class AgentFrontmatter(unittest.TestCase):
    def test_each_agent_names_its_model_and_why(self):
        paths = sorted(SKILLS.glob("*/agents/*.md"))
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(str(path.relative_to(SKILLS))):
                head = frontmatter(path.read_text(encoding="utf-8"))
                self.assertEqual(list(head), FIELDS)
                self.assertEqual(head["name"], path.stem)
                self.assertTrue(head["model"].endswith(" or similar"))
                self.assertTrue(head["model_reason"].endswith("."))


if __name__ == "__main__":
    unittest.main()
