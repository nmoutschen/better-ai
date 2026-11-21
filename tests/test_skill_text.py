"""Tests for the text of the skills that name the files an agent writes for bookkeeping.

research-better: its SKILL.md, worker and verifier prompts, board template and docs name the JSON board's files and
fields and none of the old Markdown board's, every step that writes tells the writer to run `schema.py check`, the
template has a placeholder line for every record type and status in the schemas, and every board the evals plant
passes the schema check.
"""

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "skills" / "research-better"
SCHEMAS = RESEARCH / "schemas"
SCHEMA_PY = RESEARCH / "scripts" / "schema.py"
TEXTS = [
    RESEARCH / "SKILL.md",
    RESEARCH / "agents" / "worker.md",
    RESEARCH / "agents" / "verifier.md",
    RESEARCH / "templates" / "board.md",
    ROOT / "docs" / "research-better.md",
]
OLD_FILES = [
    r"brief\.md",
    r"questions/(<id>|\*)?\.?md",
    r"claims/(<id>|\*)?\.?md",
    r"sources/(<id>|\*)?\.?md",
    r"decisions/",
    r"logs/(<[^>]+>|\*)\.md",
    r"<YOUR NAME>\.md",
    r"`key: value`",
    r"one `key: value`",
]
OLD_FIELDS = [
    r"done-when",
    r"trust-reason",
    r"stop-at",
    r"verified:",
    r"verified line",
    r"\banswer:",
    r"\banswer line",
]
RECORD_FILES = {
    "brief": "brief.schema.json",
    "question": "questions.schema.json",
    "claim": "claims.schema.json",
    "source": "sources.schema.json",
    "decision": "decisions.schema.json",
}


def template_records() -> list[dict]:
    """The JSON lines in the template's code blocks, with each `<placeholder>` left as text."""
    records = []
    for line in (RESEARCH / "templates" / "board.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("{"):
            records.append(json.loads(line))
    return records


def schema_json(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


class ResearchBetterText(unittest.TestCase):
    def test_no_old_board_file_is_named(self) -> None:
        """The text names no brief.md, questions/*.md, claims/*.md, sources/*.md, decisions/, logs/*.md or key: value."""
        for path in TEXTS:
            text = path.read_text(encoding="utf-8")
            for pattern in OLD_FILES:
                with self.subTest(file=path.name, pattern=pattern):
                    self.assertIsNone(re.search(pattern, text), f"{path.name} still names {pattern}")

    def test_no_old_field_is_named(self) -> None:
        """The text names no done-when, trust-reason, stop-at, `verified:` claim state or `answer:` on a question."""
        for path in TEXTS:
            text = path.read_text(encoding="utf-8")
            for pattern in OLD_FIELDS:
                with self.subTest(file=path.name, pattern=pattern):
                    self.assertIsNone(re.search(pattern, text), f"{path.name} still names {pattern}")

    def test_the_json_files_and_fields_are_named(self) -> None:
        """The skill text names the JSON board's files and the fields that replaced the old ones."""
        text = "\n".join(p.read_text(encoding="utf-8") for p in TEXTS[:4])
        for name in (
            "brief.json",
            "decisions.jsonl",
            "questions/<id>.json",
            "claims/<id>.json",
            "sources/<id>.json",
            "logs/<agent>.jsonl",
            "done_when",
            "trust_reason",
            "stop_at",
            "raised_in",
            "withdrawn",
            "duplicate",
            "merged_into",
            "empty_lenses",
        ):
            with self.subTest(name=name):
                self.assertIn(name, text)

    def test_every_write_step_runs_schema_check(self) -> None:
        """Each prompt, the coordinator's board steps and the template tell the writer to run `schema.py check`."""
        for path in TEXTS[:4]:
            with self.subTest(file=path.name):
                self.assertIn("schema.py check", path.read_text(encoding="utf-8"))
        skill = (RESEARCH / "SKILL.md").read_text(encoding="utf-8")
        for start, end in (("#### 5.2.", "#### 5.3."), ("#### 6.2.", "### 7.")):
            section = skill[skill.index(start) : skill.index(end)]
            with self.subTest(section=start):
                self.assertIn("schema.py check", section)
        for name, markers in (
            ("worker.md", ("After each search or page read", "## Adding questions")),
            ("verifier.md", ("Before you write",)),
        ):
            text = (RESEARCH / "agents" / name).read_text(encoding="utf-8")
            for marker in markers:
                paragraph = text[text.index(marker) :].split("\n## ")[0]
                with self.subTest(file=name, step=marker):
                    self.assertIn("schema.py check", paragraph)

    def test_no_step_deletes_a_record_others_point_to(self) -> None:
        """The coordinator's steps withdraw, mark a duplicate or merge; none says to delete."""
        skill = (RESEARCH / "SKILL.md").read_text(encoding="utf-8")
        section = skill[skill.index("#### 6.2.") : skill.index("### 7.")]
        self.assertNotRegex(section, r"\bDELETE\b")
        self.assertIn("merged_into", section)
        self.assertIn("withdrawn", section)

    def test_template_has_a_line_for_every_record_type_and_status(self) -> None:
        """One placeholder line per record type, and a line naming each status the schemas give a record's shape."""
        records = template_records()
        types = {r["type"] for r in records}
        logs = schema_json("logs.schema.json")["properties"]["type"]["enum"]
        self.assertEqual(types, set(RECORD_FILES) | set(logs))
        for kind, name in RECORD_FILES.items():
            if kind == "brief":
                continue  # its status does not change which fields it has
            for status in schema_json(name)["properties"]["status"]["enum"]:
                with self.subTest(kind=kind, status=status):
                    lines = [r["status"] for r in records if r["type"] == kind]
                    self.assertTrue(any(status in line for line in lines), f"no {kind} line for status {status}")

    def test_template_lines_use_only_the_schemas_fields(self) -> None:
        """Each placeholder line holds every field its record type requires and no field its schema lacks."""
        schemas = {kind: schema_json(name) for kind, name in RECORD_FILES.items()}
        defs = schema_json("logs.schema.json")["$defs"]
        shared = {"challenge": "after", "chain": "after", "strategy": "text", "stop": "text"}
        for record in template_records():
            kind = record["type"]
            doc = schemas[kind] if kind in schemas else defs[shared.get(kind, kind)]
            with self.subTest(type=kind, status=record.get("status")):
                self.assertLessEqual(set(record), set(doc["properties"]))
                self.assertLessEqual(set(doc["required"]), set(record))

    def test_every_planted_eval_board_passes_the_schema_check(self) -> None:
        """Each board under evals/cases/research-better/*/repo/.research/ has a brief.json and no schema error."""
        boards = sorted((ROOT / "evals" / "cases" / "research-better").glob("*/repo/.research/*"))
        self.assertTrue(boards)
        for board in boards:
            with self.subTest(board=str(board.relative_to(ROOT))):
                self.assertTrue((board / "brief.json").is_file(), "no brief.json")
                done = subprocess.run(
                    [sys.executable, "-I", str(SCHEMA_PY), "check", str(board)], capture_output=True, text=True
                )
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)


if __name__ == "__main__":
    unittest.main()
