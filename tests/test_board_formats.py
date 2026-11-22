"""Tests for the research board's files: brief.json, decisions.jsonl, questions/, claims/, sources/ and logs/.

The examples are the ones on the design's spec page (tests/fixtures/research_board_examples.json). Each is placed on a
small board whose other records are what the example points to, and must pass board.py's check; an invalid record of
each kind must be reported with its file, line and field while the rest of the board still loads.
"""

import contextlib
import copy
import importlib.util
import io
import json
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sweep  # noqa: E402
import wrong_types  # noqa: E402


def schema_main(argv: list) -> tuple:
    """research-better's schema.py on the command line: its exit code and what it printed."""
    run = subprocess.run(
        [sys.executable, "-I", str(SCRIPT.parent / "schema.py"), *argv], capture_output=True, text=True, timeout=60
    )
    return run.returncode, run.stdout


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


def seeded(id: str, **over) -> dict:
    """A seed question: no raised_in or lens."""
    record = question(id, kind="seed", origin={"type": "user"})
    record.pop("raised_in"), record.pop("lens")
    return {**record, **over}


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
            self.assertEqual(sorted(c["id"] for c in data["claims"]), ["C-w2-7", "C-w2-8", "C-w2-9"])
            bad = next(c for c in data["claims"] if c["id"] == "C-w2-9")
            self.assertTrue(bad["_errors"][0].startswith("checker: "))
            self.assertFalse(any("_errors" in c for c in data["claims"] if c["id"] != "C-w2-9"))
            self.assertEqual(len(data["questions"]), 2)
            self.assertEqual(len(data["sources"]), 2)
            self.assertEqual({e["file"] for e in data["errors"]}, {"claims/C-w2-9.json"})
            self.assertTrue(any(e["field"] == "checker" for e in data["errors"]))

    def test_an_invalid_record_stays_on_the_board_marked_and_listed(self):
        for kind, bad in (
            ("questions", {"status": "unknown"}),
            ("claims", {"status": "verified"}),
            ("sources", {"trust": "x"}),
        ):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as d:
                folder = Path(d)
                support(folder)
                make = {"questions": seeded, "claims": claim, "sources": source}[kind]
                id = {"questions": "Q-w2-9", "claims": "C-w2-9", "sources": "S-w2-9"}[kind]
                write_entry(folder, {**make(id), **bad})
                data = board.load(folder)
                shown = next(r for r in data[kind] if r["id"] == id)
                self.assertTrue(shown["_errors"])
                self.assertTrue(any(e["file"] == f"{kind}/{id}.json" for e in data["errors"]))

    def test_an_invalid_record_without_an_id_or_a_valid_at_is_still_shown(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            write_json(folder, "claims/C-w2-9.json", {"claim": "x", "at": "yesterday"})
            shown = next(c for c in board.load(folder)["claims"] if c.get("_errors"))
            self.assertEqual((shown["id"], shown["_born"]), ("C-w2-9", 0.0))

    def test_one_bad_file_never_empties_a_column_and_a_line_that_is_not_json_is_only_listed(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            for n in (7, 8):
                write_entry(folder, claim(f"C-w2-{n}", status="nonsense"))  # every claim file is bad
            (folder / "claims" / "C-w2-5.json").write_text("{not json")
            write_lines(folder, "logs/w2.jsonl", [example("logs/<agent>.jsonl", "gap")])
            with (folder / "logs" / "w2.jsonl").open("a") as f:
                f.write("{broken\n")
            data = board.load(folder)
            self.assertEqual(sorted(c["id"] for c in data["claims"]), ["C-w2-7", "C-w2-8"])
            self.assertEqual({e["file"] for e in data["errors"]} >= {"claims/C-w2-5.json", "logs/w2.jsonl"}, True)
            self.assertEqual([r["type"] for r in data["logs"]["w2"]["records"]], ["gap"])

    def test_a_source_date_may_be_a_year_and_month(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            write_entry(folder, source("S-w2-8", date="2024-03"))
            self.assertEqual(board.load(folder)["errors"], [])
            write_entry(folder, source("S-w2-9", date="2024-3"))
            self.assertEqual([e["file"] for e in board.load(folder)["errors"]], ["sources/S-w2-9.json"])

    def test_what_is_shown_is_the_text_that_was_validated(self):
        """A file is read once; an agent writing after that read changes neither what is shown nor what is reported."""
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            log = folder / "logs" / "w2.jsonl"
            write_lines(folder, "logs/w2.jsonl", [example("logs/<agent>.jsonl", "search")])
            claim_file = folder / "claims" / "C-w2-7.json"
            late = json.dumps(
                {"type": "search", "at": "2026-11-21T10:00:00Z", "by": "w2", "query": "q", "question": "Q-w2-4"}
            )
            real = board.schema.read_checked

            def reading(path, lines):
                text = real(path, lines)
                if path.name == "w2.jsonl":  # an agent appends a bad line just after the read
                    with log.open("a") as f:
                        f.write(late + "\n")
                if path.name == "C-w2-7.json":  # and rewrites a claim
                    claim_file.write_text(
                        json.dumps({**claim("C-w2-7"), "claim": "rewritten", "status": "bogus"}) + "\n"
                    )
                return text

            board.schema.read_checked = reading
            self.addCleanup(setattr, board.schema, "read_checked", real)
            data = board.load(folder)
            self.assertEqual(
                [r["query"] for r in data["logs"]["w2"]["searches"]], ["checkout address step october release"]
            )
            shown = next(c for c in data["claims"] if c["id"] == "C-w2-7")
            self.assertEqual(
                (shown["claim"], "_errors" in shown),
                ("The October release added an address step before payment.", False),
            )
            self.assertEqual(data["errors"], [])

    def test_the_conversation_is_checked_for_errors_too(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            reply = {"type": "reply", "at": "yesterday", "by": "coordinator", "id": "r-1", "text": "hi", "to": None}
            with (folder / "conversation.jsonl").open("a") as f:
                f.write(json.dumps(reply) + "\n")
            data = board.load(folder)
            self.assertEqual(
                [(e["file"], e["line"], e["field"]) for e in data["errors"]], [("conversation.jsonl", 2, "at")]
            )
            self.assertEqual(len(data["conversation"]), 2)  # the page still gets the events from the conversation
            result = check(folder)
            self.assertEqual(result.returncode, 1)
            self.assertIn("conversation.jsonl:2: at:", result.stdout)

    def test_a_record_nested_50000_deep_is_an_error_and_the_board_still_scans(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            (folder / "questions").mkdir(exist_ok=True)
            (folder / "questions" / "Q-deep.json").write_text(
                '{"type": "question", "x": ' + "[" * 50000 + "]" * 50000 + "}"
            )
            data = board.scan(folder)
        self.assertTrue(any(e["file"] == "questions/Q-deep.json" for e in data["errors"]))

    def test_a_tick_scans_once_and_board_json_reuses_a_scan_until_a_file_changes(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            calls = []
            real = board.scan
            board.scan = lambda b: calls.append(1) or real(b)
            self.addCleanup(setattr, board, "scan", real)
            board.ANNOUNCED.clear()
            first = board.scan_cached(folder)
            self.assertIs(board.scan_cached(folder), first)
            board.load(folder)
            self.assertEqual(len(calls), 1)
            conv = board.conversation(folder)
            board.announce_closes(conv, initial=False, data=first)
            self.assertTrue(board.board_stopped(folder, {"brief": {"status": "stopped"}}))
            self.assertEqual(len(calls), 1)
            time.sleep(0.01)
            write_entry(folder, claim("C-w2-9"))
            self.assertEqual(len(board.scan_cached(folder)["claims"]), 3)
            self.assertEqual(len(calls), 2)

    def test_an_invalid_brief_is_kept_marked_and_its_status_still_stops_the_watch(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            brief = {**example("brief.json", "brief"), "status": "stopped", "stop_at": "soon"}
            write_json(folder, "brief.json", brief)
            data = board.load(folder)
            self.assertEqual((data["brief"]["title"], data["brief"]["status"]), (brief["title"], "stopped"))
            self.assertTrue(data["brief"]["_errors"][0].startswith("stop_at: "))
            self.assertEqual([e["file"] for e in data["errors"]], ["brief.json"])
            self.assertTrue(board.board_stopped(folder))
            with (
                mock.patch.object(board.page, "stop_like_ctrl_c"),
                mock.patch.object(board.webbrowser, "open"),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                runner = threading.Thread(target=board.watch, args=(folder, 0, False, 0.2), daemon=True)
                runner.start()
                runner.join(15)
            self.assertFalse(runner.is_alive())  # the invalid brief's `stopped` ended it
            (folder / "brief.json").write_text("{not json")
            data = board.load(folder)
            self.assertEqual((data["brief"], [e["file"] for e in data["errors"]]), ({}, ["brief.json"]))

    def test_the_watch_loop_goes_on_after_a_failed_tick(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            brief = {**example("brief.json", "brief"), "status": "stopped"}
            write_json(folder, "brief.json", brief)
            real, calls = board.announce_closes, []

            def flaky(conv, initial, data=None):
                calls.append(1)
                if len(calls) == 2:  # the first tick of the loop
                    raise KeyError("status")
                return real(conv, initial, data)

            board.announce_closes = flaky
            self.addCleanup(setattr, board, "announce_closes", real)
            stderr = io.StringIO()
            with (
                mock.patch.object(board.page, "stop_like_ctrl_c"),
                mock.patch.object(board.webbrowser, "open"),
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(stderr),
            ):
                runner = threading.Thread(target=board.watch, args=(folder, 0, False, 0.2), daemon=True)
                runner.start()
                runner.join(15)
            self.assertFalse(runner.is_alive())  # it stopped by itself, so it outlived the failed tick
            self.assertIn("KeyError", stderr.getvalue())

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
                self.assertEqual(len(data["claims"]), 3)
            finally:
                server.send_signal(signal.SIGTERM)
                server.communicate(timeout=10)


def render(payloads: list) -> subprocess.CompletedProcess:
    """The research board's page drawn, in node, for each {label, data}; None where node is not installed."""
    node = shutil.which("node")
    if not node:
        return None
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "payloads.json"
        path.write_text(json.dumps(payloads))
        script = ROOT / "tests" / "render-board-payloads.js"
        return subprocess.run([node, str(script), str(path)], capture_output=True, text=True, timeout=300)


class Stripped(unittest.TestCase):
    """A record that is kept although it is not valid reaches the page without the fields that failed."""

    def test_a_kept_invalid_record_loses_the_fields_that_failed(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            write_entry(folder, claim("C-w2-9", question=["Q-w2-4"], span=5))
            write_entry(folder, {**seeded("Q-w2-9"), "title": 5, "origin": {"type": "question", "question": ["x"]}})
            write_entry(folder, {**source("S-w2-9"), "trust": ["x"]})
            write_json(folder, "brief.json", {**example("brief.json", "brief"), "stop_at": ["soon"]})
            data = board.load(folder)
        bad = next(c for c in data["claims"] if c["id"] == "C-w2-9")
        self.assertNotIn("question", bad)
        self.assertNotIn("span", bad)
        self.assertTrue(bad["_errors"])
        self.assertEqual(bad["claim"], claim("C-w2-9")["claim"])
        asked = next(q for q in data["questions"] if q["id"] == "Q-w2-9")
        self.assertNotIn("title", asked)
        self.assertNotIn("origin", asked)
        self.assertNotIn("trust", next(s for s in data["sources"] if s["id"] == "S-w2-9"))
        self.assertNotIn("stop_at", data["brief"])
        self.assertTrue(data["brief"]["_errors"])

    def test_a_record_whose_id_failed_is_shown_by_its_file_name(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            write_json(folder, "claims/C-w2-9.json", {**claim("C-w2-9"), "id": ["x"]})
            data = board.load(folder)
        self.assertEqual(sorted(c["id"] for c in data["claims"]), ["C-w2-7", "C-w2-8", "C-w2-9"])

    def test_a_kept_invalid_claim_with_a_list_question_does_not_crash_the_page(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            write_entry(folder, claim("C-w2-9", question=["Q-w2-4"]))
            write_entry(folder, claim("C-w2-6", question={"k": 1}, source=5))
            data = board.load(folder)
        result = render([{"label": "list question", "data": data}])
        if result:
            self.assertEqual(result.returncode, 0, result.stderr[:3000])


class MergeCycles(unittest.TestCase):
    """A question merged into itself, or two merged into each other, stays on the page with its claims."""

    def test_a_question_merged_into_itself_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            write_entry(folder, seeded("Q-w2-9", status="merged", merged_into="Q-w2-9"))
            errors = [e for e in board.load(folder)["errors"] if e["file"] == "questions/Q-w2-9.json"]
        self.assertEqual([e["field"] for e in errors], ["merged_into"])

    def test_a_merge_into_another_question_is_valid(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            write_entry(folder, seeded("Q-w2-9", status="merged", merged_into="Q-w2-4"))
            self.assertEqual(board.load(folder)["errors"], [])

    def merged(self, folder: Path, links: dict) -> list:
        """Write a question for each id of `links`, merged into the id it maps to (None: not merged), and a claim
        for the first; the errors `board.load` reports for the questions."""
        support(folder)
        for one, other in links.items():
            write_entry(folder, seeded(one, status="merged", merged_into=other) if other else seeded(one))
        write_entry(folder, claim("C-w2-9", question=next(iter(links))))
        board.SCANS.clear()
        return board.load(folder)

    def counting(self):
        """Patch the merge hook's one-file-a-step read, keeping it, and count the calls."""
        return mock.patch.object(board.schema, "_next_merge", wraps=board.schema._next_merge)

    def test_a_loop_of_2000_questions_is_reported_for_each_member_in_linear_work(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            count = 2000
            links = {f"Q-w2-{100 + k}": f"Q-w2-{100 + (k + 1) % count}" for k in range(count)}
            with self.counting() as steps:
                data = self.merged(folder, links)
            loops = [e for e in data["errors"] if "merge loop" in e["message"]]
        self.assertEqual(len(loops), count)
        self.assertLess(steps.call_count, 4 * count)  # one read a question, not one a question a step

    def test_a_chain_of_2000_questions_reports_nothing_in_linear_work(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            count = 2000
            links = {f"Q-w2-{100 + k}": f"Q-w2-{100 + k + 1}" for k in range(count)}
            with self.counting() as steps:
                data = self.merged(folder, links)
            loops = [e for e in data["errors"] if "merge loop" in e["message"]]
        self.assertEqual(loops, [])
        self.assertLess(steps.call_count, 4 * count)

    def test_misnamed_copies_that_link_elsewhere_are_linear_too(self):
        """Each question has its own file, and a copy named otherwise that merges two further on."""
        count = 2000 if sweep.full() else 500  # the bounds are in `count`; one of the slowest tests
        for loop in (False, True):
            with self.subTest(loop=loop), tempfile.TemporaryDirectory() as d:
                folder = Path(d)
                support(folder)
                one = lambda k: f"Q-w2-{100 + k % count}"  # noqa: E731
                for k in range(count):
                    last = k == count - 1 and not loop
                    write_entry(
                        folder, seeded(one(k)) if last else seeded(one(k), status="merged", merged_into=one(k + 1))
                    )
                for k in range(count - (0 if loop else 2)):
                    copy = seeded(one(k), status="merged", merged_into=one(k + 2))
                    write_json(folder, f"questions/{one(k)}-copy.json", copy)
                board.SCANS.clear()
                with self.counting() as steps:
                    data = board.load(folder)
                loops = [e for e in data["errors"] if "merge loop" in e["message"]]
            self.assertEqual(len(loops), 2 * count if loop else 0)
            self.assertLess(steps.call_count, 8 * count)

    def test_two_questions_merged_into_each_other_are_both_reported_and_drawn_marked(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            data = self.merged(folder, {"Q-w2-8": "Q-w2-9", "Q-w2-9": "Q-w2-8"})
            errors = [(e["file"], e["field"], e["message"]) for e in data["errors"]]
            self.assertEqual(
                sorted(errors),
                [
                    ("questions/Q-w2-8.json", "merged_into", "merge loop: Q-w2-8 → Q-w2-9 → Q-w2-8"),
                    ("questions/Q-w2-9.json", "merged_into", "merge loop: Q-w2-9 → Q-w2-8 → Q-w2-9"),
                ],
            )
            drawn = {q["id"]: q for q in data["questions"]}
            self.assertTrue(drawn["Q-w2-8"]["_errors"] and drawn["Q-w2-9"]["_errors"])
            self.assertEqual(sorted(c["id"] for c in data["claims"]), ["C-w2-7", "C-w2-8", "C-w2-9"])
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(board.check(folder), 1)
            self.assertEqual(out.getvalue().count("merge loop"), 2)
            result = schema_main(["check", str(folder / "questions")])
            self.assertEqual(result[0], 1)
            self.assertEqual(result[1].count("merge loop"), 2)
        result = render([{"label": "mutual merge", "data": data}])
        if result:
            self.assertEqual(result.returncode, 0, result.stderr[:3000])

    def test_a_loop_of_three_reports_each_member_and_not_a_question_merged_into_it(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            data = self.merged(folder, {"Q-w2-1": "Q-w2-2", "Q-w2-2": "Q-w2-3", "Q-w2-3": "Q-w2-1", "Q-w2-5": "Q-w2-1"})
            errors = {e["file"]: e["message"] for e in data["errors"]}
        self.assertEqual(
            errors,
            {
                "questions/Q-w2-1.json": "merge loop: Q-w2-1 → Q-w2-2 → Q-w2-3 → Q-w2-1",
                "questions/Q-w2-2.json": "merge loop: Q-w2-2 → Q-w2-3 → Q-w2-1 → Q-w2-2",
                "questions/Q-w2-3.json": "merge loop: Q-w2-3 → Q-w2-1 → Q-w2-2 → Q-w2-3",
            },
        )

    def test_a_stray_file_with_a_question_id_does_not_hide_a_loop(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            for one, other in (("Q-w2-1", "Q-w2-2"), ("Q-w2-2", "Q-w2-1")):
                write_entry(folder, seeded(one, status="merged", merged_into=other))
            write_json(folder, "questions/zz.json", {"id": "Q-w2-2", "type": "question"})
            board.SCANS.clear()
            files = {e["file"] for e in board.load(folder)["errors"] if "merge loop" in e["message"]}
        self.assertEqual(files, {"questions/Q-w2-1.json", "questions/Q-w2-2.json"})

    def test_two_thousand_questions_merged_into_one_load_quickly(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            for n in range(100, 2100):
                write_entry(folder, seeded(f"Q-w2-{n}", status="merged", merged_into="Q-w2-4"))
            board.SCANS.clear()
            with self.counting() as steps:
                errors = board.load(folder)["errors"]
        self.assertEqual(errors, [])
        self.assertLess(steps.call_count, 4 * 2000)

    def test_a_long_chain_that_ends_is_not_a_loop(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            ids = [f"Q-w2-{n}" for n in range(1, 8)]
            data = self.merged(folder, {**dict(zip(ids, ids[1:], strict=False)), ids[-1]: None})
        self.assertEqual(data["errors"], [])


class WrongTypes(unittest.TestCase):
    """For every field of every kind of record the board reads, each wrong type, one at a time, and the field
    deleted, and an extra field: `check` and `load` do not fail, the payload is JSON, and the page draws it."""

    WRONG = [[1], [[1]], {"k": 1}, 5, True, None, "x"]

    def records(self) -> dict:
        """One file for each example, as (records, written as one JSON record)."""
        files: dict = {}
        for file, items in EXAMPLES.items():
            for item in items:
                record = item["record"]
                where = FILES[file]
                if where == "brief.json":
                    files["brief.json"] = ([record], True)
                elif where == "decisions.jsonl":
                    files.setdefault("decisions.jsonl", ([], False))[0].append(record)
                elif where == "logs":
                    files.setdefault(f"logs/{record['by']}.jsonl", ([], False))[0].append(record)
                else:
                    files[f"{where}/{record['id']}.json"] = ([record], True)
        note = {"type": "note", "at": "2026-11-21T10:00:00Z", "by": "user", "id": "m-1", "text": "hi", "to": None}
        answer = {"type": "answer", "at": "2026-11-21T10:05:00Z", "by": "user", "id": "a-lq3z", "decision": "D1"}
        comment = {**note, "id": "c-1", "type": "comment", "on": {"kind": "question", "id": "Q-w2-4", "title": "t"}}
        files["conversation.jsonl"] = ([{**answer, "text": "go on", "default": False}, note, comment], False)
        return files

    def test_no_wrong_type_breaks_check_load_or_the_page(self):
        """Each file on a board of its own (the records its pointers need, and that file), so a scan reads few files."""
        payloads = []
        total = 0

        def put_file(folder, relative, records, as_json):
            (write_json if as_json else write_lines)(folder, relative, records[0] if as_json else records)

        for relative, (records, as_json) in self.records().items():
            with tempfile.TemporaryDirectory() as d:
                folder = Path(d)
                support(folder)
                put_file(folder, relative, records, as_json)
                every = list(wrong_types.variants(records, self.WRONG))
                total += len(every)
                keys = [lambda v: wrong_types.wrong_kind(v[0]), lambda v: wrong_types.field_of(v[0])]
                for label, changed in sweep.cases(every, key=keys):
                    with self.subTest(f"{relative}: {label}"):
                        put_file(folder, relative, changed, as_json)
                        payloads.append({"label": f"{relative}: {label}", "data": self.survives(folder)})
                put_file(folder, relative, records, as_json)
                total += len(wrong_types.RAW_LINES)
                for raw in sweep.cases(wrong_types.RAW_LINES, key=lambda raw: raw[:2]):
                    with self.subTest(f"{relative}: raw {raw[:10]}"):
                        # a single-JSON file holds the raw text alone; a JSONL file, the raw line before its records
                        (folder / relative).write_text(
                            raw + "\n" + ("" if as_json else "".join(json.dumps(r) + "\n" for r in records))
                        )
                        payloads.append({"label": f"{relative}: raw {raw[:10]}", "data": self.survives(folder)})
        self.assertGreater(total, 1000)
        result = render(payloads)
        if result:
            self.assertEqual(result.returncode, 0, result.stderr[:3000])

    def survives(self, folder: Path) -> dict:
        """`load` and `check` do not raise, and what `load` returns is JSON a browser reads."""
        board.SCANS.clear()
        data = board.load(folder)
        json.dumps(data, allow_nan=False)
        with contextlib.redirect_stdout(io.StringIO()):
            board.check(folder)
        return data


class ConversationEvents(unittest.TestCase):
    """Every kind of event the board's conversation holds (the verifier of the strip fix found events of some kinds
    never tried), each field given each wrong value: `load` and `check` do not fail and the page's thread draws it."""

    AT = "2026-11-21T10:00:00Z"

    def events(self) -> list:
        at = self.AT
        return [
            {"type": "note", "at": at, "by": "user", "id": "m-1", "text": "hi", "to": None},
            {"type": "comment", "at": at, "by": "user", "id": "c-1", "text": "t", "on": {"kind": "question", "id": "Q-w2-4", "title": "t"}},
            {"type": "reply", "at": at, "by": "coordinator", "id": "r-1", "text": "ok", "to": "m-1"},
            {"type": "status", "at": at, "by": "coordinator", "to": "m-1", "status": "done"},
            {"type": "status", "at": at, "by": "coordinator", "to": "c-1", "status": "asked"},
            {"type": "accepted", "at": at, "by": "coordinator", "to": "c-1", "text": "fine"},
            {"type": "closed", "at": at, "by": "w2", "id": "x-1", "question": "Q-w2-4", "status": "answered"},
            {"type": "answer", "at": at, "by": "user", "id": "a-lq3z", "decision": "D1", "text": "go on", "default": False},
        ]  # fmt: skip

    def test_the_events_are_valid_as_written(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            write_lines(folder, "conversation.jsonl", self.events())
            board.SCANS.clear()
            data = board.load(folder)
        self.assertEqual([e["line"] for e in data["errors"] if e["file"] == "conversation.jsonl"], [])
        self.assertEqual([e["type"] for e in data["conversation"]], [e["type"] for e in self.events()])

    def test_no_wrong_type_in_any_event_breaks_load_check_or_the_thread(self):
        payloads = []
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            every = list(wrong_types.variants(self.events()))
            keys = [lambda v: wrong_types.wrong_kind(v[0]), lambda v: wrong_types.field_of(v[0])]
            for label, changed in sweep.cases(every, key=keys):
                with self.subTest(label):
                    write_lines(folder, "conversation.jsonl", changed)
                    board.SCANS.clear()
                    data = board.load(folder)
                    json.dumps(data, allow_nan=False)
                    with contextlib.redirect_stdout(io.StringIO()):
                        board.check(folder)
                    payloads.append({"label": label, "data": data})
        self.assertGreater(len(every), 500)
        node = shutil.which("node")
        if node:
            with tempfile.TemporaryDirectory() as d:
                path = Path(d) / "payloads.json"
                path.write_text(json.dumps(payloads))
                script = ROOT / "tests" / "render-board-thread.js"
                run = subprocess.run([node, str(script), str(path)], capture_output=True, text=True, timeout=300)
            self.assertEqual(run.returncode, 0, run.stderr[:3000])


class RawFiles(unittest.TestCase):
    """What a JSON entry or a log can hold instead of a record (NaN, Infinity, nesting 100,000 deep, an array, a line
    that is not JSON): `load`, `check` and the JSON the board serves do not fail, and the page draws what is left."""

    def put_text(self, folder: Path, relative: str, text: str) -> None:
        (folder / relative).parent.mkdir(parents=True, exist_ok=True)
        (folder / relative).write_text(text, encoding="utf-8")

    def cases(self) -> list:
        deep = "[" * 100000 + "]" * 100000
        one = json.dumps(seeded("Q-w9-1"))
        when = "2026-11-21T10:00:00Z"
        return [
            ("question raw NaN", "questions/Q-w9-1.json", "NaN"),
            ("question title NaN", "questions/Q-w9-1.json", one.replace('"title": ', '"title": NaN, "t2": ')),
            ("question extra NaN", "questions/Q-w9-1.json", one[:-1] + ', "extra": NaN}'),
            ("question priority Infinity", "questions/Q-w9-1.json", one.replace('"priority": "high"', '"priority": Infinity')),
            ("question deep", "questions/Q-w9-1.json", deep),
            ("question deep in a field", "questions/Q-w9-1.json", one[:-1] + ', "extra": ' + deep + "}"),
            ("question array", "questions/Q-w9-1.json", "[1]"),
            ("question status 5", "questions/Q-w9-1.json", json.dumps(seeded("Q-w9-1", status=5))),
            ("question status not a status", "questions/Q-w9-1.json", json.dumps(seeded("Q-w9-1", status="answred"))),
            ("brief not JSON", "brief.json", "{"),
            ("brief NaN", "brief.json", '{"status": NaN}'),
            ("brief status a list", "brief.json", '{"status": ["stopped"]}'),
            ("decisions NaN", "decisions.jsonl", '{"id":"D9","x":NaN}\n'),
            ("log NaN", "logs/w2.jsonl", '{"type":"search","by":"w2","question":NaN}\n'),
            ("log wrong types", "logs/w2.jsonl", json.dumps({"type": "search", "at": when, "by": "w2", "question": ["Q-w2-4"], "query": "x", "new_terms": 5}) + "\n"),
            ("conversation note NaN text", "conversation.jsonl", '{"type":"note","at":"' + when + '","by":"user","id":"m-1","text":NaN,"to":null}\n'),
            ("conversation note extra NaN", "conversation.jsonl", '{"type":"note","at":"' + when + '","by":"user","id":"m-1","text":"hi","to":null,"x":NaN}\n'),
            ("conversation unknown type NaN", "conversation.jsonl", '{"type":"zzz","at":"' + when + '","by":"user","x":NaN}\n'),
            ("conversation deep", "conversation.jsonl", deep + "\n"),
        ]  # fmt: skip

    def test_no_file_breaks_load_check_the_served_json_or_the_page(self):
        payloads = []
        for label, relative, text in self.cases():
            with self.subTest(label), tempfile.TemporaryDirectory() as d:
                folder = Path(d)
                support(folder)
                self.put_text(folder, relative, text)
                board.SCANS.clear()
                data = board.load(folder)
                json.dumps(data, allow_nan=False)
                with contextlib.redirect_stdout(io.StringIO()):
                    board.check(folder)
                self.assertTrue([e for e in data["errors"] if e["file"] == relative], "the bad file is listed")
                payloads.append({"label": label, "data": json.loads(json.dumps(data, allow_nan=False))})
        result = render(payloads)
        if result:
            self.assertEqual(result.returncode, 0, result.stderr[:3000])


class BoardsOfSize(unittest.TestCase):
    def test_a_large_valid_board_loads_in_seconds_and_its_watch_tick_does_too(self):
        """A bound far above what a scan takes (under a second here), to catch a scan that went quadratic."""
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            for i in range(150):
                write_entry(folder, seeded(f"Q-w1-{i + 10}"))
            for i in range(300):
                write_entry(folder, source(f"S-w1-{i + 10}"))
            for i in range(750):
                write_entry(
                    folder, claim(f"C-w1-{i + 10}", question=f"Q-w1-{10 + i % 150}", source=f"S-w1-{10 + i % 300}")
                )
            search = example("logs/<agent>.jsonl", "search")
            for agent in range(4):
                write_lines(folder, f"logs/w{agent}.jsonl", [{**search, "by": f"w{agent}"}] * 200)
            board.SCANS.clear()
            started = time.monotonic()
            data = board.load(folder)
            loaded = time.monotonic() - started
            started = time.monotonic()
            board.board_stopped(folder)
            board.announce_closes(board.conversation(folder), initial=True)
            ticked = time.monotonic() - started
        self.assertEqual(data["errors"], [])
        self.assertEqual(len(data["claims"]), 750 + 2)
        self.assertLess(loaded, 30)
        self.assertLess(ticked, 30)

    def test_a_question_merged_into_an_out_of_scope_one_is_drawn_with_its_claims(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            support(folder)
            write_entry(folder, seeded("Q-w2-8", status="merged", merged_into="Q-w2-9"))
            write_entry(folder, seeded("Q-w2-9", status="out of scope"))
            write_entry(folder, claim("C-w2-9", question="Q-w2-8"))
            data = board.load(folder)
        self.assertEqual(data["errors"], [])
        self.assertIn("C-w2-9", [c["id"] for c in data["claims"]])
        result = render([{"label": "merged into out of scope", "data": data}])
        if result:
            self.assertEqual(result.returncode, 0, result.stderr[:3000])


if __name__ == "__main__":
    unittest.main()
