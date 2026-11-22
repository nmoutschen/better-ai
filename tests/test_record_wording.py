"""Skill text leads an agent to the command that adds a record, never to the file the record lives in.

D22 and D23 of the unified CLI: the shape of each record type is a format in `formats/`, a document the agent writes
is a template in `templates/`, and every line that tells an agent to put a record somewhere names the
`better.pyz add` or `set` command and the type, not a file.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
FIVE = ("architect-better", "code-better", "design-better", "research-better", "show-better")

WRITE_LIKE = re.compile(r"\b(?:write|writes|written|writing|save|saves|put|keep|record|add)\b", re.IGNORECASE)
RECORD_FILE = re.compile(r"[\w<>./*-]*\.jsonl?\b|\b(?:questions|claims|sources|logs)/<")
TEMPLATE_PATH = re.compile(r"\btemplates/([\w.-]+)")


def texts(*skills):
    """Each Markdown file of the given skills outside scripts/."""
    for skill in skills or FIVE:
        for path in sorted((SKILLS / skill).rglob("*.md")):
            if "scripts" not in path.relative_to(SKILLS / skill).parts:
                yield path


def lines(path):
    yield from enumerate(path.read_text().splitlines(), 1)


def sentences(line):
    return re.split(r"(?<=[.;:])\s+", line)


class RecordWording(unittest.TestCase):
    def test_no_template_holds_a_json_record_example_line(self):
        """Record shapes live in formats/; a template is a document."""
        found = [
            f"{path.relative_to(ROOT)}:{number}"
            for path in sorted(SKILLS.glob("*/templates/*"))
            for number, line in lines(path)
            if line.lstrip().startswith("{") and '"type"' in line
        ]
        self.assertEqual(found, [])

    def test_no_format_holds_a_fill_in_block_or_a_document_heading(self):
        formats = sorted(SKILLS.glob("*/formats/*.md"))
        self.assertEqual(len(formats), 12)
        for path in formats:
            text = path.read_text()
            with self.subTest(path.relative_to(ROOT)):
                self.assertNotIn("<HOW TO", text)
                self.assertNotIn("delete this block", text.casefold())
                self.assertIsNone(re.search(r"^#.*<short name", text, re.MULTILINE))
                self.assertIsNone(re.search(r"^# .*<", text, re.MULTILINE))

    def test_every_format_names_the_command_before_its_first_record_line(self):
        for path in sorted(SKILLS.glob("*/formats/*.md")):
            text = path.read_text()
            first = text.index("\n{") if "\n{" in text else len(text)
            with self.subTest(path.relative_to(ROOT)):
                self.assertTrue(re.search(r"better\.pyz (?:add|create|set)", text[:first]))

    def test_no_line_pairs_a_write_like_verb_with_a_record_file_without_a_command(self):
        found = [
            f"{path.relative_to(ROOT)}:{number}: {sentence.strip()[:100]}"
            for path in texts()
            for number, line in lines(path)
            for sentence in sentences(line)
            if WRITE_LIKE.search(sentence) and RECORD_FILE.search(sentence) and "better.pyz" not in sentence
        ]
        self.assertEqual(found, [])

    def test_the_word_template_only_points_at_a_file_under_templates(self):
        """In show-better, `template` is the layout field of a slide, not a file."""
        found = []
        for path in texts("architect-better", "code-better", "design-better", "research-better"):
            skill = SKILLS / path.relative_to(SKILLS).parts[0]
            for number, line in lines(path):
                if not re.search(r"\btemplates?\b", line, re.IGNORECASE):
                    continue
                named = TEMPLATE_PATH.findall(line)
                if not named or any(not (skill / "templates" / name).is_file() for name in named):
                    found.append(f"{path.relative_to(ROOT)}:{number}: {line.strip()[:100]}")
        self.assertEqual(found, [])

    def test_the_templates_that_remain_are_documents(self):
        names = sorted(f"{path.parent.parent.name}/{path.name}" for path in SKILLS.glob("*/templates/*.md"))
        for name in (
            "architect-better/decision.md",
            "architect-better/design.md",
            "design-better/brief.md",
            "design-better/design-language.md",
            "design-better/design.md",
        ):
            self.assertIn(name, names)
        for skill in ("code-better", "research-better", "show-better"):
            self.assertEqual(list((SKILLS / skill).glob("templates/*")), [])


if __name__ == "__main__":
    unittest.main()
