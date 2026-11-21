"""Tests for the research board's files: brief.json, decisions.jsonl, questions/, claims/, sources/ and logs/.

The examples are the ones on the design's spec page (tests/fixtures/research_board_examples.json). Each is placed on a
small board whose other records are what the example points to, and must pass board.py's check; an invalid record of
each kind must be reported with its file, line and field while the rest of the board still loads.
"""

import copy
import importlib.util
import json
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "research-better" / "scripts" / "board.py"
EXAMPLES = json.loads((Path(__file__).parent / "fixtures" / "research_board_examples.json").read_text())
FILES = {
    "brief.json": "brief.json",
    "decisions.jsonl": "decisions.jsonl",
    "questions/<id>.json": "questions",
    "claims/<id>.json": "claims",
    "sources/<id>.json": "sources",
    "logs/<agent>.jsonl": "logs",
}

spec = importlib.util.spec_from_file_location("board_under_test", SCRIPT)
board = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(SCRIPT.parent))
spec.loader.exec_module(board)


def example(file: str, label: str) -> dict:
    return copy.deepcopy(next(e["record"] for e in EXAMPLES[file] if e["label"] == label))


def write_json(folder: Path, name: str, record: dict) -> None:
    (folder / name).parent.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(json.dumps(record) + "\n", encoding="utf-8")


def write_lines(folder: Path, name: str, records: list) -> None:
    (folder / name).parent.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")


def write_entry(folder: Path, record: dict) -> None:
    kind = {"question": "questions", "claim": "claims", "source": "sources"}[record["type"]]
    write_json(folder, f"{kind}/{record['id']}.json", record)


def question(id: str, **over) -> dict:
    return {**example("questions/<id>.json", "proposed, open, out of scope"), "id": id, **over}


def claim(id: str, **over) -> dict:
    return {**example("claims/<id>.json", "unchecked"), "id": id, **over}


def source(id: str, **over) -> dict:
    return {**example("sources/<id>.json", "source, a page with no identifier"), "id": id, **over}


def support(folder: Path) -> None:
    """What the examples point to: the questions, sources and claims they name and the user's answer a-lq3z."""
    for id in ("Q-w1-2", "Q-w2-4"):
        write_entry(folder, seeded(id))
    for id in ("S-w1-1", "S-w2-3"):
        write_entry(folder, source(id))
    for id in ("C-w2-7", "C-w2-8"):
        write_entry(folder, claim(id))
    answer = {"type": "answer", "at": "2026-11-21T10:05:00Z", "by": "user", "id": "a-lq3z", "decision": "D1"}
    write_lines(folder, "conversation.jsonl", [{**answer, "text": "go on", "default": False}])


def seeded(id: str) -> dict:
    """A seed question: no raised_in or lens."""
    record = question(id, kind="seed", origin={"type": "user"})
    record.pop("raised_in"), record.pop("lens")
    return record


def put(folder: Path, file: str, record: dict) -> None:
    """The example on the board, where the board keeps that kind."""
    where = FILES[file]
    if where == "brief.json":
        write_json(folder, "brief.json", record)
    elif where == "decisions.jsonl":
        write_lines(folder, "decisions.jsonl", [record])
    elif where == "logs":
        write_lines(folder, f"logs/{record['by']}.jsonl", [record])
    else:
        write_entry(folder, record)


def check(folder: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", str(SCRIPT), "check", str(folder)], capture_output=True, text=True)


class Examples(unittest.TestCase):
    """Every example of the spec page is valid, one board each."""

    def test_every_example_validates(self):
        for file, items in EXAMPLES.items():
            for item in items:
                with self.subTest(file=file, example=item["label"]), tempfile.TemporaryDirectory() as d:
                    folder = Path(d)
                    support(folder)
                    put(folder, file, item["record"])
                    self.assertEqual(board.load(folder)["errors"], [])
                    result = check(folder)
                    self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_the_examples_cover_every_kind_of_file(self):
        self.assertEqual(set(EXAMPLES), set(FILES))


def broken(file: str, label: str, **over) -> dict:
    record = example(file, label)
    for key, value in over.items():
        if value is ...:
            record.pop(key)
        else:
            record[key] = value
    return record


# One invalid record per kind: the file it is in, the record, the field the error names and a word of its message.
INVALID = [
    ("brief.json", "brief", broken("brief.json", "brief", stop_at="soon"), "stop_at", "must be one of"),
    ("decisions.jsonl", "decision", broken("decisions.jsonl", "pending", status="changed"), "answer", "required"),
    (
        "questions",
        "question",
        broken("questions/<id>.json", "answered, contested, not found, unclear", gist=...),
        "gist",
        "required",
    ),
    ("claims", "claim", broken("claims/<id>.json", "verified", span=...), "span", "required"),
    (
        "sources",
        "source",
        broken("sources/<id>.json", "source, a duplicate", replaced_by=...),
        "replaced_by",
        "required",
    ),
    ("logs", "log line", broken("logs/<agent>.jsonl", "search", new_terms="none"), "new_terms", "expected array"),
]


class Invalid(unittest.TestCase):
    def test_one_invalid_record_of_each_kind_is_reported_with_its_file_line_and_field(self):
        for where, kind, record, field, word in INVALID:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as d:
                folder = Path(d)
                support(folder)
                file = next(f for f, w in FILES.items() if w == where)
                if where == "logs":
                    good = example(file, "challenge")
                    write_lines(folder, f"logs/{record['by']}.jsonl", [good, record])
                    expected = (f"logs/{record['by']}.jsonl", 2)
                elif where in ("brief.json", "decisions.jsonl"):
                    put(folder, file, record)
                    expected = (where, 1)
                else:
                    put(folder, file, record)
                    expected = (f"{where}/{record['id']}.json", 1)
                errors = board.load(folder)["errors"]
                mine = [e for e in errors if (e["file"], e["line"]) == expected]
                self.assertEqual([e["field"] for e in mine], [field], errors)
                self.assertIn(word, mine[0]["message"])
                self.assertEqual(mine[0]["by"], record["by"])
                result = check(folder)
                self.assertEqual(result.returncode, 1)
                self.assertIn(f"{expected[0]}:{expected[1]}: {field}: ", result.stdout)

    def test_a_board_with_one_bad_claim_still_shows_the_rest(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            write_entry(folder, claim("C-w2-9", status="verified"))  # verified without a checker, a span or hard
            data = board.load(folder)
            self.assertEqual(sorted(c["id"] for c in data["claims"]), ["C-w2-7", "C-w2-8"])
            self.assertEqual(len(data["questions"]), 2)
            self.assertEqual(len(data["sources"]), 2)
            self.assertEqual({e["file"] for e in data["errors"]}, {"claims/C-w2-9.json"})
            self.assertTrue(any(e["field"] == "checker" for e in data["errors"]))

    def test_a_bad_line_in_a_log_hides_only_that_line(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            lines = [example("logs/<agent>.jsonl", "search"), {"type": "search", "at": "x", "by": "w2"}]
            lines.append(example("logs/<agent>.jsonl", "gap"))
            write_lines(folder, "logs/w2.jsonl", lines)
            data = board.load(folder)
            self.assertEqual([r["type"] for r in data["logs"]["w2"]["records"]], ["search", "gap"])
            self.assertEqual({e["line"] for e in data["errors"]}, {2})

    def test_a_claim_whose_checker_is_its_author_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            write_entry(folder, claim("C-w2-9", status="checking", checker="w2"))
            errors = board.load(folder)["errors"]
            self.assertEqual([(e["file"], e["field"]) for e in errors], [("claims/C-w2-9.json", "checker")])
            self.assertIn("must differ from by", errors[0]["message"])

    def test_a_withdrawn_claim_still_resolves_pointers_to_it(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            write_entry(folder, claim("C-w3-1", status="withdrawn", replaced_by="C-w2-7"))
            write_entry(folder, claim("C-w3-2", status="withdrawn", replaced_by="C-w3-1"))
            lines = [{"type": "checked", "at": "2026-11-21T10:00:00Z", "by": "v1", "claim": "C-w3-1"}]
            write_lines(folder, "logs/v1.jsonl", lines)
            self.assertEqual(board.load(folder)["errors"], [])

    def test_a_question_merged_without_merged_into_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            write_entry(folder, {**seeded("Q-w3-2"), "status": "merged"})
            errors = board.load(folder)["errors"]
            self.assertEqual([(e["file"], e["field"]) for e in errors], [("questions/Q-w3-2.json", "merged_into")])
            self.assertIn('required when status is "merged"', errors[0]["message"])

    def test_a_dangling_claim_question_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            write_entry(folder, claim("C-w2-9", question="Q-w9-1"))
            errors = board.load(folder)["errors"]
            self.assertEqual([(e["file"], e["field"]) for e in errors], [("claims/C-w2-9.json", "question")])
            self.assertIn("dangling", errors[0]["message"])

    def test_a_file_named_for_another_id_and_an_old_markdown_file_are_reported(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            write_json(folder, "claims/C-w2-77.json", claim("C-w2-9"))
            (folder / "brief.md").write_text("topic: old\n")
            errors = board.load(folder)["errors"]
            self.assertEqual({e["file"] for e in errors}, {"claims/C-w2-77.json", "brief.md"})

    def test_a_note_with_on_is_refused_by_the_board_events_schema(self):
        schema = SCRIPT.parent / "schema.py"
        spec = importlib.util.spec_from_file_location("schema_of_board_test", schema)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        note = {"type": "note", "at": "2026-11-21T10:00:00Z", "by": "user", "id": "m-1", "text": "hi", "to": None}
        on = {"kind": "question", "id": "Q-w2-4", "title": "t"}
        self.assertEqual(module.check_record(note, ["board-events.schema.json"]), [])
        problems = module.check_record({**note, "on": on}, ["board-events.schema.json"])
        self.assertEqual([field for field, _ in problems], ["on"])


class Reading(unittest.TestCase):
    def test_the_board_reads_the_new_fields(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            write_lines(folder, "logs/w2.jsonl", [example("logs/<agent>.jsonl", "search")] * 2)
            data = board.load(folder)
            self.assertEqual(data["errors"], [])
            self.assertEqual({c["status"] for c in data["claims"]}, {"unchecked"})
            self.assertEqual({s["category"] for s in data["sources"]}, {"documentation"})
            self.assertEqual(len(data["logs"]["w2"]["searches"]), 2)

    def test_announce_closes_reads_the_question_files(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            write_entry(folder, example("questions/<id>.json", "answered, contested, not found, unclear"))
            conv = board.conversation(folder)
            board.ANNOUNCED.clear()
            board.announce_closes(conv, initial=False)
            closed = [e for e in conv.events() if e["type"] == "closed"]
            self.assertEqual([(e["question"], e["by"], e["status"]) for e in closed], [("Q-w2-4", "w2", "answered")])

    def test_check_exits_zero_on_a_valid_board_and_one_on_an_invalid_one(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            self.assertEqual(check(folder).returncode, 0)
            write_entry(folder, claim("C-w2-9", question="Q-w9-1"))
            result = check(folder)
            self.assertEqual(result.returncode, 1)
            self.assertIn("claims/C-w2-9.json:1: question: dangling", result.stdout)

    def test_the_served_board_json_answers_with_errors_not_with_a_failure(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            write_entry(folder, claim("C-w2-9", question="Q-w9-1"))
            server = subprocess.Popen(
                [sys.executable, "-I", str(SCRIPT), "watch", str(folder), "--no-browser"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            try:
                for _ in range(80):
                    if (folder / ".server").exists():
                        break
                    time.sleep(0.1)
                url = (folder / ".server").read_text().strip()
                with urllib.request.urlopen(url + "board.json", timeout=5) as r:
                    self.assertEqual(r.status, 200)
                    data = json.loads(r.read())
                self.assertEqual([e["file"] for e in data["errors"]], ["claims/C-w2-9.json"])
                self.assertEqual(len(data["claims"]), 2)
            finally:
                server.send_signal(signal.SIGTERM)
                server.communicate(timeout=10)


if __name__ == "__main__":
    unittest.main()
