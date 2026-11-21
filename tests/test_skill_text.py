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
import tempfile
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
CHECK_SENTENCE = (
    "After every write to the board, run `python3 <skill dir>/scripts/schema.py check <file>` "
    "and fix every error before your next step."
)
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

    def test_each_loop_starts_with_the_schema_check_sentence(self) -> None:
        """SKILL.md step 2, the worker's loop and the verifier's loop each say once, up front, to check every write."""
        for path in TEXTS[:3]:
            with self.subTest(file=path.name):
                self.assertIn(CHECK_SENTENCE, path.read_text(encoding="utf-8"))
        for name in ("worker.md", "verifier.md"):
            text = (RESEARCH / "agents" / name).read_text(encoding="utf-8")
            loop = text[text.index("## Loop") :]
            with self.subTest(file=name):
                self.assertTrue(
                    loop[len("## Loop") :].lstrip().startswith(CHECK_SENTENCE), "not at the head of the loop"
                )
        skill = (RESEARCH / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("from this skill's directory", skill)

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
            lines = {value.strip(" <>") for r in records if r["type"] == kind for value in str(r["status"]).split("|")}
            for status in schema_json(name)["properties"]["status"]["enum"]:
                with self.subTest(kind=kind, status=status):
                    self.assertIn(status, lines, f"no {kind} line for status {status}")

    def test_template_has_placeholders_only(self) -> None:
        """The template holds no example IDs, and its challenge question has a question as origin."""
        text = (RESEARCH / "templates" / "board.md").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"\b[QCS]-w\d", text), "an example ID")
        for record in template_records():
            if record["type"] == "question" and record["kind"] == "<seed | challenge>":
                self.assertNotIn("user", str(record["origin"]["type"]))

    def test_null_date_is_accepted_and_planted_in_the_missing_field_board(self) -> None:
        """A source with date null passes the schema check, and S-w2-2 of findings-missing-field has none."""
        planted = ROOT / "evals/cases/research-better/findings-missing-field/repo/.research/checkout-drop/sources"
        record = json.loads((planted / "S-w2-2.json").read_text(encoding="utf-8"))
        self.assertIsNone(record["date"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sources" / "S-w2-2.json"
            path.parent.mkdir()
            path.write_text(json.dumps(record), encoding="utf-8")
            done = subprocess.run(
                [sys.executable, "-I", str(SCHEMA_PY), "check", str(path)], capture_output=True, text=True
            )
            self.assertEqual(done.returncode, 0, done.stdout)

    def test_planted_challenge_questions_are_not_owned_by_the_answerer(self) -> None:
        """A planted challenge question is not owned by the agent that owns the question it challenges."""
        for path in sorted((ROOT / "evals/cases/research-better").glob("*/repo/.research/*/questions/*.json")):
            q = json.loads(path.read_text(encoding="utf-8"))
            if q["kind"] != "challenge" or "owner" not in q:
                continue
            origin = json.loads((path.parent / (q["origin"]["question"] + ".json")).read_text(encoding="utf-8"))
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertNotEqual(q["owner"], origin.get("owner"))

    def test_eval_board_lib_reads_a_pretty_printed_json_file(self) -> None:
        """board_lib.entry reads a .json file that spans several lines, as schema.py does."""
        sys.path.insert(0, str(ROOT / "evals/cases/research-better/_checks"))
        try:
            import board_lib
        finally:
            sys.path.pop(0)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Q-w1-1.json"
            path.write_text(json.dumps({"id": "Q-w1-1", "status": "open"}, indent=2), encoding="utf-8")
            self.assertEqual(board_lib.entry(path)["status"], "open")

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
