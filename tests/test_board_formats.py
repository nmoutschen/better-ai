"""Tests for the research board's files: brief.json, decisions.jsonl, questions/, claims/, sources/ and logs/.

The examples are the ones on the design's spec page (tests/fixtures/research_board_examples.json). Each is placed on a
small board whose other records are what the example points to, and must pass board.py's check; an invalid record of
each kind must be reported with its file, line and field while the rest of the board still loads.
"""

import contextlib
import copy
import functools
import io
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import better  # noqa: E402
import sweep  # noqa: E402
import wrong_types  # noqa: E402
from research_records import EXAMPLES, example, made_board  # noqa: E402

from better_ai import cli, page, paths, research, resources, schema  # noqa: E402
from better_ai.research import board  # noqa: E402

DOCS = schema.docs_for("research")
FILES = {
    "brief.json": "brief.json",
    "decisions.jsonl": "decisions.jsonl",
    "questions/<id>.json": "questions",
    "claims/<id>.json": "claims",
    "sources/<id>.json": "sources",
    "logs/<agent>.jsonl": "logs",
}
SKILL = "research-better"


def setUpModule():
    """A served board checks its brief every 0.05 s, not every second, so a test that waits for a tick waits briefly."""
    global _tick
    _tick = mock.patch.object(page, "TICK", 0.05)
    _tick.start()


def tearDownModule():
    _tick.stop()


def unit_folder(root: str) -> Path:
    """A board inside `root`, at `.research/b`, where a unit lives; `unit(folder)` is the unit the board reads."""
    folder = Path(root) / ".research" / "b"
    folder.mkdir(parents=True)
    write_json(folder, "brief.json", example("brief.json", "brief"))
    return folder


@functools.cache
def unit(folder: Path) -> paths.Unit:
    """The unit of a board folder, resolved once (resolving asks git for the repository)."""
    return paths.resolve_unit(str(folder), research.SKILL)


def check_in_process(folder: Path) -> int:
    """What `check` does, without a process: print each error, 1 if there is any."""
    errors = schema.check_paths([folder], docs=DOCS, now=datetime.now(timezone.utc))
    for error in errors:
        print(error)
    return 1 if errors else 0


def write_json(folder: Path, name: str, record: dict) -> None:
    (folder / name).parent.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(json.dumps(record) + "\n", encoding="utf-8")


def write_lines(folder: Path, name: str, records: list) -> None:
    (folder / name).parent.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")


FOLDER_OF = {"question": "questions", "claim": "claims", "source": "sources"}


def write_entry(folder: Path, record: dict) -> None:
    write_json(folder, f"{FOLDER_OF[record['type']]}/{record['id']}.json", record)


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


def serve_until_stopped(folder: Path, stderr: io.StringIO) -> threading.Thread:
    """`serve` on the board in a thread (no signal handling, no browser, 0.2 s linger); it ends by itself once the board
    is stopped."""
    info = resources.BuildInfo(SKILL, "research", "source", resources.cutoff())
    run = cli.Run(research.SKILL, info, stdout=io.StringIO(), stderr=stderr)
    args = mock.Mock(unit=str(folder), port=0, open=False, no_browser=True, linger=0.2, once=False)
    runner = threading.Thread(target=page.serve, args=(args, run), daemon=True)
    runner.start()
    return runner


def survives(folder: Path) -> dict:
    """`load` and `check` do not raise on the board, and what `load` returns is JSON a browser reads."""
    board.SCANS.clear()
    data = board.load(unit(folder))
    json.dumps(data, allow_nan=False)
    with contextlib.redirect_stdout(io.StringIO()):
        check_in_process(folder)
    return data


def check(folder: Path) -> subprocess.CompletedProcess:
    return better.call(SKILL, "check", str(folder))


class Scripts(HTMLParser):
    """The script elements of a page, as (attributes, text), the way a browser splits them."""

    def __init__(self):
        super().__init__()
        self.found, self.open = [], None

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.open = (dict(attrs), [])

    def handle_data(self, data):
        if self.open:
            self.open[1].append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.open:
            self.found.append((self.open[0], "".join(self.open[1])))
            self.open = None


class Examples(unittest.TestCase):
    """Every example of the spec page is valid, one board each."""

    def test_every_example_validates(self):
        for file, items in EXAMPLES.items():
            for item in items:
                with self.subTest(file=file, example=item["label"]), tempfile.TemporaryDirectory() as d:
                    folder = unit_folder(d)
                    support(folder)
                    put(folder, file, item["record"])
                    self.assertEqual(board.load(unit(folder))["errors"], [])
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
    (
        "decisions.jsonl",
        "decision",
        broken("decisions.jsonl", "answered on the page", answer=...),
        "answer",
        "required",
    ),
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
                folder = unit_folder(d)
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
                errors = board.load(unit(folder))["errors"]
                mine = [e for e in errors if (e["file"], e["line"]) == expected]
                self.assertEqual([e["field"] for e in mine], [field], errors)
                self.assertIn(word, mine[0]["message"])
                self.assertEqual(mine[0]["by"], record["by"])
                result = check(folder)
                self.assertEqual(result.returncode, 1)
                self.assertIn(f"{expected[0]}:{expected[1]}: {field}: ", result.stdout)

    def test_a_board_with_one_bad_claim_still_shows_the_rest(self):
        with tempfile.TemporaryDirectory() as d:
            folder = unit_folder(d)
            support(folder)
            write_entry(folder, claim("C-w2-9", status="verified"))  # verified without a checker, a span or hard
            data = board.load(unit(folder))
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
                folder = unit_folder(d)
                support(folder)
                make = {"questions": seeded, "claims": claim, "sources": source}[kind]
                id = {"questions": "Q-w2-9", "claims": "C-w2-9", "sources": "S-w2-9"}[kind]
                write_entry(folder, {**make(id), **bad})
                data = board.load(unit(folder))
                shown = next(r for r in data[kind] if r["id"] == id)
                self.assertTrue(shown["_errors"])
                self.assertTrue(any(e["file"] == f"{kind}/{id}.json" for e in data["errors"]))

    def test_an_invalid_record_without_an_id_or_a_valid_at_is_still_shown(self):
        with tempfile.TemporaryDirectory() as d:
            folder = unit_folder(d)
            support(folder)
            write_json(folder, "claims/C-w2-9.json", {"claim": "x", "at": "yesterday"})
            shown = next(c for c in board.load(unit(folder))["claims"] if c.get("_errors"))
            self.assertEqual((shown["id"], shown["_born"]), ("C-w2-9", 0.0))

    def test_one_bad_file_never_empties_a_column_and_a_line_that_is_not_json_is_only_listed(self):
        with tempfile.TemporaryDirectory() as d:
            folder = unit_folder(d)
            support(folder)
            for n in (7, 8):
                write_entry(folder, claim(f"C-w2-{n}", status="nonsense"))  # every claim file is bad
            (folder / "claims" / "C-w2-5.json").write_text("{not json")
            write_lines(folder, "logs/w2.jsonl", [example("logs/<agent>.jsonl", "gap")])
            with (folder / "logs" / "w2.jsonl").open("a") as f:
                f.write("{broken\n")
            data = board.load(unit(folder))
            self.assertEqual(sorted(c["id"] for c in data["claims"]), ["C-w2-7", "C-w2-8"])
            self.assertEqual({e["file"] for e in data["errors"]} >= {"claims/C-w2-5.json", "logs/w2.jsonl"}, True)
            self.assertEqual([r["type"] for r in data["logs"]["w2"]["records"]], ["gap"])

    def test_a_source_date_may_be_a_year_and_month(self):
        with tempfile.TemporaryDirectory() as d:
            folder = unit_folder(d)
            support(folder)
            write_entry(folder, source("S-w2-8", date="2024-03"))
            self.assertEqual(board.load(unit(folder))["errors"], [])
            write_entry(folder, source("S-w2-9", date="2024-3"))
            self.assertEqual([e["file"] for e in board.load(unit(folder))["errors"]], ["sources/S-w2-9.json"])

    def test_what_is_shown_is_the_text_that_was_validated(self):
        """A file is read once; an agent writing after that read changes neither what is shown nor what is reported."""
        with tempfile.TemporaryDirectory() as d:
            folder = unit_folder(d)
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
            data = board.load(unit(folder))
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
            folder = unit_folder(d)
            support(folder)
            reply = {"type": "reply", "at": "yesterday", "by": "coordinator", "id": "r-1", "text": "hi", "to": None}
            with (folder / "conversation.jsonl").open("a") as f:
                f.write(json.dumps(reply) + "\n")
            data = board.load(unit(folder))
            self.assertEqual(
                [(e["file"], e["line"], e["field"]) for e in data["errors"]], [("conversation.jsonl", 2, "at")]
            )
            self.assertEqual(len(data["conversation"]), 2)  # the page still gets the events from the conversation
            result = check(folder)
            self.assertEqual(result.returncode, 1)
            self.assertIn("conversation.jsonl:2: at:", result.stdout)

    def test_a_record_nested_50000_deep_is_an_error_and_the_board_still_scans(self):
        with tempfile.TemporaryDirectory() as d:
            folder = unit_folder(d)
            support(folder)
            (folder / "questions").mkdir(exist_ok=True)
            (folder / "questions" / "Q-deep.json").write_text(
                '{"type": "question", "x": ' + "[" * 50000 + "]" * 50000 + "}"
            )
            data = board.scan(unit(folder))
        self.assertTrue(any(e["file"] == "questions/Q-deep.json" for e in data["errors"]))

    def test_a_tick_scans_once_and_board_json_reuses_a_scan_until_a_file_changes(self):
        with tempfile.TemporaryDirectory() as d:
            folder = unit_folder(d)
            support(folder)
            calls = []
            real = board.scan
            board.scan = lambda b: calls.append(1) or real(b)
            self.addCleanup(setattr, board, "scan", real)
            board.ANNOUNCED.clear()
            first = board.scan_cached(unit(folder))
            self.assertIs(board.scan_cached(unit(folder)), first)
            board.load(unit(folder))
            self.assertEqual(len(calls), 1)
            conv = board.conversation(unit(folder))
            board.announce_closes(conv, initial=False, data=first)
            self.assertTrue(board.board_stopped(unit(folder), {"brief": {"status": "stopped"}}))
            self.assertEqual(len(calls), 1)
            time.sleep(0.01)
            write_entry(folder, claim("C-w2-9"))
            self.assertEqual(len(board.scan_cached(unit(folder))["claims"]), 3)
            self.assertEqual(len(calls), 2)
            board.SCANS.clear()
            with mock.patch.object(board, "scan", side_effect=KeyError("bug")), self.assertRaises(KeyError):
                board.load(unit(folder))  # a bug in the board's own code is not a record error: it reaches the bug path

    def test_an_invalid_brief_is_kept_marked_and_its_status_still_stops_the_watch(self):
        with tempfile.TemporaryDirectory() as d:
            folder = unit_folder(d)
            support(folder)
            brief = {**example("brief.json", "brief"), "status": "stopped", "stop_at": "soon"}
            write_json(folder, "brief.json", brief)
            data = board.load(unit(folder))
            self.assertEqual((data["brief"]["title"], data["brief"]["status"]), (brief["title"], "stopped"))
            self.assertTrue(data["brief"]["_errors"][0].startswith("stop_at: "))
            self.assertEqual([e["file"] for e in data["errors"]], ["brief.json"])
            self.assertTrue(board.board_stopped(unit(folder)))
            with mock.patch.object(board.page, "stop_like_ctrl_c"):
                runner = serve_until_stopped(folder, io.StringIO())
                runner.join(15)
            self.assertFalse(runner.is_alive())  # the invalid brief's `stopped` ended it
            (folder / "brief.json").write_text("{not json")
            data = board.load(unit(folder))
            self.assertEqual((data["brief"], [e["file"] for e in data["errors"]]), ({}, ["brief.json"]))

    def test_the_watch_loop_goes_on_after_a_failed_tick(self):
        with tempfile.TemporaryDirectory() as d:
            folder = unit_folder(d)
            support(folder)
            brief = {**example("brief.json", "brief"), "status": "stopped"}
            write_json(folder, "brief.json", brief)
            real, calls = board.announce_closes, []

            def flaky(conv, initial, data=None):
                calls.append(1)
                if len(calls) == 1:  # the first tick
                    raise KeyError("status")
                return real(conv, initial, data)

            board.announce_closes = flaky
            self.addCleanup(setattr, board, "announce_closes", real)
            stderr = io.StringIO()
            with mock.patch.object(board.page, "stop_like_ctrl_c"):
                runner = serve_until_stopped(folder, stderr)
                runner.join(15)
            self.assertFalse(runner.is_alive())  # it stopped by itself, so it outlived the failed tick
            self.assertIn("KeyError", stderr.getvalue())

    def test_a_bad_line_in_a_log_hides_only_that_line(self):
        with tempfile.TemporaryDirectory() as d:
            folder = unit_folder(d)
            support(folder)
            lines = [example("logs/<agent>.jsonl", "search"), {"type": "search", "at": "x", "by": "w2"}]
            lines.append(example("logs/<agent>.jsonl", "gap"))
            write_lines(folder, "logs/w2.jsonl", lines)
            data = board.load(unit(folder))
            self.assertEqual([r["type"] for r in data["logs"]["w2"]["records"]], ["search", "gap"])
            self.assertEqual({e["line"] for e in data["errors"]}, {2})

    def test_a_wrong_pointer_or_checker_is_reported_with_its_file_and_field(self):
        for label, record, expected, said in (
            ("a claim checked by its author", claim("C-w2-9", status="checking", checker="w2"), "checker", "must differ from by"),
            ("a claim of no question", claim("C-w2-9", question="Q-w9-1"), "question", "dangling"),
            ("a merge without its target", {**seeded("Q-w3-2"), "status": "merged"}, "merged_into", 'required when status is "merged"'),
        ):  # fmt: skip
            with self.subTest(label), tempfile.TemporaryDirectory() as d:
                folder = unit_folder(d)
                support(folder)
                write_entry(folder, record)
                errors = board.load(unit(folder))["errors"]
                self.assertEqual(
                    [(e["file"], e["field"]) for e in errors],
                    [(f"{FOLDER_OF[record['type']]}/{record['id']}.json", expected)],
                )
                self.assertIn(said, errors[0]["message"])

    def test_a_withdrawn_claim_still_resolves_pointers_to_it(self):
        with tempfile.TemporaryDirectory() as d:
            folder = unit_folder(d)
            support(folder)
            write_entry(folder, claim("C-w3-1", status="withdrawn", replaced_by="C-w2-7"))
            write_entry(folder, claim("C-w3-2", status="withdrawn", replaced_by="C-w3-1"))
            lines = [{"type": "checked", "at": "2026-11-21T10:00:00Z", "by": "v1", "claim": "C-w3-1"}]
            write_lines(folder, "logs/v1.jsonl", lines)
            self.assertEqual(board.load(unit(folder))["errors"], [])

    def test_a_file_named_for_another_id_and_an_old_markdown_file_are_reported(self):
        with tempfile.TemporaryDirectory() as d:
            folder = unit_folder(d)
            support(folder)
            write_json(folder, "claims/C-w2-77.json", claim("C-w2-9"))
            (folder / "brief.md").write_text("topic: old\n")
            errors = board.load(unit(folder))["errors"]
            self.assertEqual({e["file"] for e in errors}, {"claims/C-w2-77.json", "brief.md"})

    def test_a_note_with_on_is_refused_by_the_board_events_schema(self):
        def check_record(record: dict) -> list:
            return [p.field for p in schema.validate_instance(record, DOCS["board-events.schema.json"], DOCS)]

        note = {"type": "note", "at": "2026-11-21T10:00:00Z", "by": "user", "id": "m-1", "text": "hi", "to": None}
        on = {"kind": "question", "id": "Q-w2-4", "title": "t"}
        self.assertEqual(check_record(note), [])
        self.assertEqual(check_record({**note, "on": on}), ["on"])


class Reading(unittest.TestCase):
    def test_the_board_reads_the_new_fields(self):
        with tempfile.TemporaryDirectory() as d:
            folder = unit_folder(d)
            support(folder)
            write_lines(folder, "logs/w2.jsonl", [example("logs/<agent>.jsonl", "search")] * 2)
            data = board.load(unit(folder))
            self.assertEqual(data["errors"], [])
            self.assertEqual({c["status"] for c in data["claims"]}, {"unchecked"})
            self.assertEqual({s["category"] for s in data["sources"]}, {"documentation"})
            self.assertEqual(len(data["logs"]["w2"]["searches"]), 2)

    def test_announce_closes_reads_the_question_files(self):
        with tempfile.TemporaryDirectory() as d:
            folder = unit_folder(d)
            support(folder)
            write_entry(folder, example("questions/<id>.json", "answered, contested, not found, unclear"))
            conv = board.conversation(unit(folder))
            board.ANNOUNCED.clear()
            board.announce_closes(conv, initial=False)
            closed = [e for e in conv.events() if e["type"] == "closed"]
            self.assertEqual([(e["question"], e["by"], e["status"]) for e in closed], [("Q-w2-4", "w2", "answered")])

    def test_check_exits_zero_on_a_valid_board_and_one_on_an_invalid_one(self):
        with tempfile.TemporaryDirectory() as d:
            folder = unit_folder(d)
            support(folder)
            self.assertEqual(better.run(SKILL, "check", str(folder)).returncode, 0)  # the one process run of `check`
            write_entry(folder, claim("C-w2-9", question="Q-w9-1"))
            result = check(folder)
            self.assertEqual(result.returncode, 1)
            self.assertIn("claims/C-w2-9.json:1: question: dangling", result.stdout)


class Stripped(unittest.TestCase):
    """A record that is kept although it is not valid reaches the page without the fields that failed."""

    def test_a_kept_invalid_record_loses_the_fields_that_failed(self):
        with tempfile.TemporaryDirectory() as d:
            folder = unit_folder(d)
            support(folder)
            write_entry(folder, claim("C-w2-9", question=["Q-w2-4"], span=5))
            write_entry(folder, {**seeded("Q-w2-9"), "title": 5, "origin": {"type": "question", "question": ["x"]}})
            write_entry(folder, {**source("S-w2-9"), "trust": ["x"]})
            write_json(folder, "brief.json", {**example("brief.json", "brief"), "stop_at": ["soon"]})
            data = board.load(unit(folder))
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
            folder = unit_folder(d)
            support(folder)
            write_json(folder, "claims/C-w2-9.json", {**claim("C-w2-9"), "id": ["x"]})
            data = board.load(unit(folder))
        self.assertEqual(sorted(c["id"] for c in data["claims"]), ["C-w2-7", "C-w2-8", "C-w2-9"])

    def test_a_kept_invalid_claim_with_a_list_question_does_not_crash_the_page(self):
        with tempfile.TemporaryDirectory() as d:
            folder = unit_folder(d)
            support(folder)
            write_entry(folder, claim("C-w2-9", question=["Q-w2-4"]))
            write_entry(folder, claim("C-w2-6", question={"k": 1}, source=5))
            data = board.load(unit(folder))
        wrong_types.render("render-board-payloads.js", [{"label": "list question", "data": data}], self)


COUNT = 2000 if sweep.full() else 500  # questions in the linear-work tests: the bounds are in COUNT, not in the speed


class MergeCycles(unittest.TestCase):
    """A question merged into itself, or two merged into each other, stays on the page with its claims."""

    def test_a_question_merged_into_itself_is_reported_and_into_another_is_valid(self):
        with tempfile.TemporaryDirectory() as d:
            folder = unit_folder(d)
            support(folder)
            write_entry(folder, seeded("Q-w2-9", status="merged", merged_into="Q-w2-4"))
            self.assertEqual(board.load(unit(folder))["errors"], [])
            write_entry(folder, seeded("Q-w2-9", status="merged", merged_into="Q-w2-9"))
            board.SCANS.clear()
            errors = [e for e in board.load(unit(folder))["errors"] if e["file"] == "questions/Q-w2-9.json"]
        self.assertEqual([e["field"] for e in errors], ["merged_into"])

    def merged(self, folder: Path, links: dict) -> list:
        """Write a question for each id of `links`, merged into the id it maps to (None: not merged), and a claim
        for the first; the errors `board.load` reports for the questions."""
        support(folder)
        for one, other in links.items():
            write_entry(folder, seeded(one, status="merged", merged_into=other) if other else seeded(one))
        write_entry(folder, claim("C-w2-9", question=next(iter(links))))
        board.SCANS.clear()
        return board.load(unit(folder))

    def counting(self):
        """Patch the merge hook's one-file-a-step read, keeping it, and count the calls."""
        return mock.patch.object(board.checks, "_next_merge", wraps=board.checks._next_merge)

    def test_a_loop_of_questions_is_reported_for_each_member_in_linear_work(self):
        with tempfile.TemporaryDirectory() as d:
            folder = unit_folder(d)
            count = COUNT
            links = {f"Q-w2-{100 + k}": f"Q-w2-{100 + (k + 1) % count}" for k in range(count)}
            with self.counting() as steps:
                data = self.merged(folder, links)
            loops = [e for e in data["errors"] if "merge loop" in e["message"]]
        self.assertEqual(len(loops), count)
        self.assertLess(steps.call_count, 4 * count)  # one read a question, not one a question a step

    def test_a_chain_of_questions_reports_nothing_in_linear_work(self):
        with tempfile.TemporaryDirectory() as d:
            folder = unit_folder(d)
            count = COUNT
            links = {f"Q-w2-{100 + k}": f"Q-w2-{100 + k + 1}" for k in range(count)}
            with self.counting() as steps:
                data = self.merged(folder, links)
            loops = [e for e in data["errors"] if "merge loop" in e["message"]]
        self.assertEqual(loops, [])
        self.assertLess(steps.call_count, 4 * count)

    def test_misnamed_copies_that_link_elsewhere_are_linear_too(self):
        """Each question has its own file, and a copy named otherwise that merges two further on."""
        count = COUNT // 2
        for loop in (False, True):
            with self.subTest(loop=loop), tempfile.TemporaryDirectory() as d:
                folder = unit_folder(d)
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
                    data = board.load(unit(folder))
                loops = [e for e in data["errors"] if "merge loop" in e["message"]]
            self.assertEqual(len(loops), 2 * count if loop else 0)
            self.assertLess(steps.call_count, 8 * count)

    def test_two_questions_merged_into_each_other_are_both_reported_and_drawn_marked(self):
        with tempfile.TemporaryDirectory() as d:
            folder = unit_folder(d)
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
                self.assertEqual(check_in_process(folder), 1)
            self.assertEqual(out.getvalue().count("merge loop"), 2)
            result = check(folder)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout.count("merge loop"), 2)
        wrong_types.render("render-board-payloads.js", [{"label": "mutual merge", "data": data}], self)

    def test_a_loop_of_three_reports_each_member_and_not_a_question_merged_into_it(self):
        with tempfile.TemporaryDirectory() as d:
            folder = unit_folder(d)
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
            folder = unit_folder(d)
            support(folder)
            for one, other in (("Q-w2-1", "Q-w2-2"), ("Q-w2-2", "Q-w2-1")):
                write_entry(folder, seeded(one, status="merged", merged_into=other))
            write_json(folder, "questions/zz.json", {"id": "Q-w2-2", "type": "question"})
            board.SCANS.clear()
            files = {e["file"] for e in board.load(unit(folder))["errors"] if "merge loop" in e["message"]}
        self.assertEqual(files, {"questions/Q-w2-1.json", "questions/Q-w2-2.json"})

    def test_many_questions_merged_into_one_load_quickly(self):
        with tempfile.TemporaryDirectory() as d:
            folder = unit_folder(d)
            support(folder)
            for n in range(100, 100 + COUNT):
                write_entry(folder, seeded(f"Q-w2-{n}", status="merged", merged_into="Q-w2-4"))
            board.SCANS.clear()
            with self.counting() as steps:
                errors = board.load(unit(folder))["errors"]
        self.assertEqual(errors, [])
        self.assertLess(steps.call_count, 4 * COUNT)

    def test_a_long_chain_that_ends_is_not_a_loop(self):
        with tempfile.TemporaryDirectory() as d:
            folder = unit_folder(d)
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
        files = self.records()
        boards: dict = {}  # file name -> its board folder, made when the file is first written

        def put_file(name, records):
            if name not in boards:
                root = tempfile.TemporaryDirectory()
                self.addCleanup(root.cleanup)
                boards[name] = unit_folder(root.name)
                support(boards[name])
            as_json = files[name][1]
            (write_json if as_json else write_lines)(boards[name], name, records[0] if as_json else records)
            self.current = boards[name]

        payloads, total = wrong_types.fuzz(
            self,
            {name: records for name, (records, _) in files.items()},
            put_file,
            lambda label: survives(self.current),
            wrong=self.WRONG,
        )
        pairs = [(relative, raw) for relative in files for raw in wrong_types.RAW_LINES]
        for relative, raw in sweep.cases(pairs, key=lambda pair: pair[1]):  # each raw line once, across the files
            records, as_json = files[relative]
            with self.subTest(f"{relative}: raw {raw[:10]}"):
                # a single-JSON file holds the raw text alone; a JSONL file, the raw line before its records
                body = raw + "\n" + ("" if as_json else "".join(json.dumps(r) + "\n" for r in records))
                (boards[relative] / relative).write_text(body)
                self.current = boards[relative]
                payloads.append({"label": f"{relative}: raw {raw[:10]}", "data": survives(boards[relative])})
        self.assertGreater(total + len(pairs), 1000)
        wrong_types.render("render-board-payloads.js", payloads, self)


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
            folder = unit_folder(d)
            support(folder)
            write_lines(folder, "conversation.jsonl", self.events())
            board.SCANS.clear()
            data = board.load(unit(folder))
        self.assertEqual([e["line"] for e in data["errors"] if e["file"] == "conversation.jsonl"], [])
        self.assertEqual([e["type"] for e in data["conversation"]], [e["type"] for e in self.events()])

    def test_no_wrong_type_in_any_event_breaks_load_check_or_the_thread(self):
        with tempfile.TemporaryDirectory() as d:
            folder = unit_folder(d)
            support(folder)

            payloads, total = wrong_types.fuzz(
                self,
                {"conversation.jsonl": self.events()},
                lambda n, r: write_lines(folder, n, r),
                lambda label: survives(folder),
            )
        self.assertGreater(total, 500)
        wrong_types.render("render-board-thread.js", payloads, self)


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
                folder = unit_folder(d)
                support(folder)
                self.put_text(folder, relative, text)
                data = survives(folder)
                self.assertTrue([e for e in data["errors"] if e["file"] == relative], "the bad file is listed")
                payloads.append({"label": label, "data": json.loads(json.dumps(data, allow_nan=False))})
        wrong_types.render("render-board-payloads.js", payloads, self)


class BoardsOfSize(unittest.TestCase):
    def test_a_large_valid_board_loads_in_seconds_and_its_watch_tick_does_too(self):
        """A bound far above what a scan takes (under a second here), to catch a scan that went quadratic."""
        with tempfile.TemporaryDirectory() as d:
            folder = unit_folder(d)
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
            data = board.load(unit(folder))
            loaded = time.monotonic() - started
            started = time.monotonic()
            board.board_stopped(unit(folder))
            board.announce_closes(board.conversation(unit(folder)), initial=True)
            ticked = time.monotonic() - started
        self.assertEqual(data["errors"], [])
        self.assertEqual(len(data["claims"]), 750 + 2)
        self.assertLess(loaded, 30)
        self.assertLess(ticked, 30)

    def test_a_question_merged_into_an_out_of_scope_one_is_drawn_with_its_claims(self):
        with tempfile.TemporaryDirectory() as d:
            folder = unit_folder(d)
            support(folder)
            write_entry(folder, seeded("Q-w2-8", status="merged", merged_into="Q-w2-9"))
            write_entry(folder, seeded("Q-w2-9", status="out of scope"))
            write_entry(folder, claim("C-w2-9", question="Q-w2-8"))
            data = board.load(unit(folder))
        self.assertEqual(data["errors"], [])
        self.assertIn("C-w2-9", [c["id"] for c in data["claims"]])
        wrong_types.render("render-board-payloads.js", [{"label": "merged into out of scope", "data": data}], self)


class Verbs(unittest.TestCase):
    """The board through the command: what the research package adds to the shared verbs."""

    UTC = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_set_stamps_a_new_change_and_keeps_the_ones_it_is_given_back(self):
        with tempfile.TemporaryDirectory() as d:
            board_dir = made_board(Path(d))
            first = json.dumps({"changes": [{"text": "Dropped the wiki collection"}]})
            done = better.run(SKILL, "set", ".research/b", "brief", stdin=first, cwd=d)
            self.assertEqual(done.returncode, 0, done.stderr)
            changes = json.loads((board_dir / "brief.json").read_text())["changes"]
            self.assertEqual([c["text"] for c in changes], ["Dropped the wiki collection"])
            self.assertRegex(changes[0]["at"], self.UTC)
            second = json.dumps({"changes": [{"text": "Searched the archive too"}, changes[0]]})
            self.assertEqual(better.run(SKILL, "set", ".research/b", "brief", stdin=second, cwd=d).returncode, 0)
            kept = json.loads((board_dir / "brief.json").read_text())["changes"]
            self.assertEqual([c["text"] for c in kept], ["Searched the archive too", "Dropped the wiki collection"])
            self.assertEqual(kept[1], changes[0])
            self.assertRegex(kept[0]["at"], self.UTC)
            self.assertEqual(better.run(SKILL, "check", ".research/b", cwd=d).returncode, 0)

    def test_a_decision_is_added_with_a_deadline_in_minutes_and_shows_as_waiting(self):
        with tempfile.TemporaryDirectory() as d:
            made_board(Path(d))
            decision = {"raised_by": "coordinator", "about": {"type": "board"}, "asked": "Use the archive?"}
            decision |= {"status": "waiting", "default": "Skip it", "deadline": "+30m"}
            done = better.run(
                SKILL, "add", ".research/b", "decision", "--by", "coordinator", stdin=json.dumps(decision), cwd=d
            )
            self.assertEqual((done.returncode, done.stdout.strip()), (0, "D1"), done.stderr)
            data = board.load(unit(Path(d) / ".research" / "b"))
        (shown,) = data["decisions"]
        self.assertEqual((shown["status"], shown["default"]), ("waiting", "Skip it"))
        self.assertRegex(shown["deadline"], self.UTC)
        self.assertEqual(data["errors"], [])

    def test_decisions_in_the_old_format_are_counted_not_listed_and_the_board_still_loads(self):
        old = {"type": "decision", "at": "2026-11-19T17:12:37Z", "by": "coordinator", "asked": "Login?"}
        old |= {"default": "Go on", "deadline": "2026-11-19T17:22:37Z"}
        lines = [
            {**old, "id": "D1", "status": "pending"},
            {**old, "id": "D2", "status": "default"},
            {**old, "id": "D3", "status": "changed", "answer": {"type": "chat", "text": "go"}},
        ]
        with tempfile.TemporaryDirectory() as d:
            folder = unit_folder(d)
            support(folder)
            write_lines(folder, "decisions.jsonl", lines)
            data = board.load(unit(folder))
            with mock.patch.dict(os.environ, {"BETTER_AI_SKILL": "research-better"}):
                counted = page.old_count_of(unit(folder))
            checked = check(folder)
        self.assertEqual((data["errors"], counted), ([], 3))
        self.assertEqual([x["id"] for x in data["decisions"]], ["D1", "D2", "D3"])
        self.assertTrue(all(x["_old"] for x in data["decisions"]))
        self.assertEqual(checked.returncode, 0)
        self.assertEqual(checked.stdout.count("(format)"), 3)
        wrong_types.render("render-board-payloads.js", [{"label": "old decisions", "data": data}], self)

    def test_render_writes_one_page_into_the_board_with_the_data_in_it(self):
        quoted = "Quoting <!--<script> and </script> in a question"  # markup in a record must not end a script element
        with tempfile.TemporaryDirectory() as d:
            board_dir = made_board(Path(d))
            write_entry(board_dir, seeded("Q-w2-9", question=quoted))
            done = better.run(SKILL, "render", ".research/b", cwd=d)
            self.assertEqual(done.returncode, 0, done.stderr)
            text = (board_dir / "board.html").read_text()
            self.assertIn(".research/b/board.html", done.stdout)
            self.assertNotIn("BOARD_SNAPSHOT", text)
            self.assertNotIn('src="/', text)  # no file is linked: the page stands alone
            self.assertNotIn('href="/', text)
            scripts = Scripts()
            scripts.feed(text)
            carried = [body for attrs, body in scripts.found if attrs.get("id") == "page-data"]
            self.assertNotIn("<", carried[0])  # no record text can open or end a script element
            data = json.loads(carried[0])
            self.assertEqual([q["question"] for q in data["questions"]], [quoted])
            self.assertEqual(data["brief"]["topic"], example("brief.json", "brief")["topic"])
            code = [body for attrs, body in scripts.found if "src" not in attrs and "type" not in attrs]
            self.assertEqual(len(code), 2)  # page.js and board.js, both whole
            self.assertIn("function pageErrors", code[0])
            self.assertIn("pagePopup({", code[1])
            self.assertEqual(
                better.call(SKILL, "check", ".research/b", cwd=d).returncode, 0
            )  # the page is not a record
            empty = Path(d) / ".research" / "none"
            empty.mkdir()
            refused = better.call(SKILL, "render", ".research/none", cwd=d)
            self.assertEqual(refused.returncode, 1)
            self.assertFalse((empty / "board.html").exists())

    def served(self, board_dir: Path):
        process = subprocess.Popen(
            better.command("serve", str(board_dir), "--no-browser", "--linger", "0.2"),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env={**os.environ, "BETTER_AI_SKILL": SKILL},
        )
        self.addCleanup(process.communicate)
        self.addCleanup(process.send_signal, signal.SIGTERM)
        for _ in range(100):
            if (board_dir / ".server").exists():
                break
            time.sleep(0.1)
        return process, (board_dir / ".server").read_text().strip()

    def get(self, url: str):
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                return r.status, r.read().decode()
        except urllib.error.HTTPError as error:
            error.close()
            return error.code, ""

    def rpc(self, url: str, method: str, **params):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
        origin = url.rstrip("/")
        request = urllib.request.Request(
            url + "rpc", body, {"Content-Type": "application/json", "Origin": origin}, method="POST"
        )
        with urllib.request.urlopen(request, timeout=5) as r:
            return json.loads(r.read())

    def test_the_served_page_has_the_boards_files_takes_its_events_and_refuses_the_rest(self):
        with tempfile.TemporaryDirectory() as d:
            board_dir = made_board(Path(d))
            write_entry(
                board_dir, claim("C-w2-9", question="Q-w9-1")
            )  # a bad record: the page is served, with its error
            process, url = self.served(board_dir)
            status, text = self.get(url)
            self.assertEqual(status, 200)
            for linked in ('href="/board.css"', 'src="/board.js"', 'src="/page.js"', 'href="/page.css"', 'id="map"'):
                self.assertIn(linked, text)
            for asset in ("board.js", "board.css", "page.js", "page.css"):
                self.assertEqual(self.get(url + asset)[0], 200, asset)
            self.assertEqual(self.get(url + "board.html")[0], 404)  # only the fixed table is served
            self.assertEqual(self.get(url + "brief.json")[0], 404)
            status, text = self.get(url + "data")
            data = json.loads(text)
            self.assertEqual((status, data["brief"]["status"]), (200, "running"))
            self.assertEqual(({e["file"] for e in data["errors"]}, len(data["claims"])), ({"claims/C-w2-9.json"}, 1))
            self.assertIn("listening", data)
            closed = self.rpc(url, "closed", id="c-0", question="Q-w2-4", status="answered")  # the page may not send it
            self.assertEqual(closed["error"]["code"], -32601)
            self.assertFalse((board_dir / "conversation.jsonl").exists())
            for method in ("accept", "approve", "confirm", "delete"):  # shared parts this page does not declare
                self.assertEqual(self.rpc(url, method, to="c-1")["error"]["code"], -32601, method)

    def test_a_worker_closing_a_question_is_announced_once_and_the_board_stopped_ends_serve(self):
        with tempfile.TemporaryDirectory() as d:
            board_dir = made_board(Path(d))
            with mock.patch.object(board.page, "stop_like_ctrl_c"):
                runner = serve_until_stopped(board_dir, io.StringIO())
                time.sleep(0.3)  # the first tick takes the questions already closed as old news
                question = {
                    **seeded("Q-w2-4"),
                    "status": "answered",
                    "owner": "w2",
                    "summary": "It fell.",
                    "gist": "It fell.",
                }
                for key in ("id", "type", "at", "by"):
                    question.pop(key)
                done = better.call(
                    SKILL, "add", str(board_dir), "question", "--by", "w2", stdin=json.dumps(question), cwd=d
                )
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                log = board_dir / "conversation.jsonl"
                for _ in range(100):
                    if log.exists() and "closed" in log.read_text():
                        break
                    time.sleep(0.05)
                closed = [json.loads(x) for x in log.read_text().splitlines() if '"closed"' in x]
                self.assertEqual(
                    [(e["question"], e["by"], e["status"]) for e in closed], [("Q-w2-1", "w2", "answered")]
                )
                time.sleep(0.3)
                self.assertEqual(log.read_text().count('"closed"'), 1)  # once, not on every tick
                done = better.call(SKILL, "set", str(board_dir), "brief", stdin='{"status": "stopped"}', cwd=d)
                self.assertEqual(done.returncode, 0, done.stderr)
                runner.join(15)
            self.assertFalse(runner.is_alive())  # it ended by itself, after its linger


class Changes(unittest.TestCase):
    """The brief's `changes`: the agent types no time. The patch holds the new entries first, then every earlier entry
    as the brief shows it; the command stamps the new ones."""

    UTC = Verbs.UTC
    WHY = "changes must hold the new entries first, then every earlier entry as the brief shows it"

    def board_with_history(self, d):
        board_dir = made_board(Path(d))
        for text in ("Dropped the wiki", "Searched the archive"):
            earlier = json.loads((board_dir / "brief.json").read_text())["changes"]
            patch = json.dumps({"changes": [{"text": text}, *earlier]})
            done = better.call(SKILL, "set", ".research/b", "brief", stdin=patch, cwd=d)
            assert done.returncode == 0, done.stdout + done.stderr
        return board_dir

    def changes(self, board_dir):
        return json.loads((board_dir / "brief.json").read_text())["changes"]

    def set(self, d, changes):
        return better.call(SKILL, "set", ".research/b", "brief", stdin=json.dumps({"changes": changes}), cwd=d)

    def test_a_new_board_is_created_with_no_changes_so_no_agent_types_their_time(self):
        with tempfile.TemporaryDirectory() as d:
            board_dir = made_board(Path(d))
            brief = json.loads((board_dir / "brief.json").read_text())
            for key in ("type", "at", "by"):
                brief.pop(key, None)
            brief["changes"] = [{"text": "pre", "at": "2020-01-01T00:00:00Z"}]
            done = better.run(SKILL, "create", ".research/c", "--by", "coordinator", stdin=json.dumps(brief), cwd=d)
            self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
            self.assertIn("changes", done.stdout + done.stderr)
            self.assertFalse((Path(d) / ".research" / "c" / "brief.json").exists())

    def test_a_brief_without_changes_gets_its_first_entry_stamped(self):
        with tempfile.TemporaryDirectory() as d:
            board_dir = made_board(Path(d))
            brief = json.loads((board_dir / "brief.json").read_text())
            brief.pop("changes", None)
            (board_dir / "brief.json").write_text(json.dumps(brief))
            done = self.set(d, [{"text": "first"}])
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertTrue(self.changes(board_dir)[0]["at"].startswith("20"))

    def test_the_good_path_stamps_the_new_entry_and_keeps_the_earlier_ones_exactly(self):
        with tempfile.TemporaryDirectory() as d:
            board_dir = self.board_with_history(d)
            earlier = self.changes(board_dir)
            self.assertEqual([c["text"] for c in earlier], ["Searched the archive", "Dropped the wiki"])
            done = self.set(d, [{"text": "Narrowed the goal"}, *earlier])
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            now = self.changes(board_dir)
            self.assertEqual(now[1:], earlier)
            self.assertRegex(now[0]["at"], self.UTC)
            self.assertEqual(better.call(SKILL, "check", ".research/b", cwd=d).returncode, 0)

    def test_a_change_that_does_not_keep_the_history_is_refused_and_the_brief_stays(self):
        with tempfile.TemporaryDirectory() as d:
            board_dir = self.board_with_history(d)
            before = (board_dir / "brief.json").read_text()
            earlier = self.changes(board_dir)
            refused = [
                ("a time typed on a new entry", [{"text": "x", "at": "2020-01-01T00:00:00Z"}, *earlier], "remove 'at' from the new entries"),
                ("a time ahead", [{"text": "x", "at": "2099-01-01T00:00:00Z"}, *earlier], "remove 'at' from the new entries"),
                ("only the new entry", [{"text": "Only this"}], "Give the earlier entries back unchanged after the new ones"),
                ("a rewritten text", [{"text": "new"}, {**earlier[0], "text": "Rewritten"}, *earlier[1:]], self.WHY),
                ("a rewritten time", [{"text": "new"}, {**earlier[0], "at": "2020-01-01T00:00:00Z"}, *earlier[1:]], self.WHY),
                ("a reordered history", [{"text": "new"}, earlier[1], earlier[0]], self.WHY),
            ]  # fmt: skip
            for label, changes, said in refused:
                with self.subTest(label):
                    done = self.set(d, changes)
                    self.assertEqual(done.returncode, 1)
                    self.assertIn(said, done.stderr + done.stdout)
                    self.assertEqual((board_dir / "brief.json").read_text(), before)

    def test_a_patch_that_is_not_a_list_of_objects_is_left_to_the_schema(self):
        with tempfile.TemporaryDirectory() as d:
            made_board(Path(d))
            for bad in ("x", [1], [{"text": 5}]):
                with self.subTest(bad=bad):
                    done = self.set(d, bad)
                    self.assertEqual(done.returncode, 1)
                    self.assertNotIn("bug in", done.stderr)


class OldDecisions(unittest.TestCase):
    OLD = {"type": "decision", "at": "2026-11-19T17:12:37Z", "by": "coordinator", "id": "D1", "asked": "Login?"}
    OLD |= {"default": "Go on", "deadline": "2026-11-19T17:22:37Z", "status": "pending"}

    def board(self, d):
        board_dir = made_board(Path(d))
        write_lines(board_dir, "decisions.jsonl", [self.OLD])
        return board_dir

    def test_set_on_an_old_decision_names_the_missing_fields_and_works_once_it_gives_them(self):
        with tempfile.TemporaryDirectory() as d:
            board_dir = self.board(d)
            before = (board_dir / "decisions.jsonl").read_text()
            done = better.call(SKILL, "set", ".research/b", "D1", stdin='{"status": "defaulted"}', cwd=d)
            self.assertEqual(done.returncode, 1)
            said = done.stdout + done.stderr
            self.assertIn("written before this change", said)
            self.assertIn("raised_by", said)
            self.assertIn("about", said)
            self.assertEqual((board_dir / "decisions.jsonl").read_text(), before)
            patch = {"status": "defaulted", "raised_by": "coordinator", "about": {"type": "board"}}
            done = better.call(SKILL, "set", ".research/b", "D1", stdin=json.dumps(patch), cwd=d)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertEqual(better.call(SKILL, "check", ".research/b", cwd=d).returncode, 0)

    def test_the_old_status_words_are_refused_on_a_decision(self):
        for word in ("default", "pending", "changed"):
            with self.subTest(word=word), tempfile.TemporaryDirectory() as d:
                made_board(Path(d))
                decision = {"raised_by": "coordinator", "about": {"type": "board"}, "asked": "Use it?"}
                decision |= {"status": "waiting", "default": "Skip", "deadline": "+30m"}
                added = better.call(
                    SKILL, "add", ".research/b", "decision", "--by", "coordinator", stdin=json.dumps(decision), cwd=d
                )
                self.assertEqual(added.returncode, 0, added.stdout)
                done = better.call(SKILL, "set", ".research/b", "D1", stdin=json.dumps({"status": word}), cwd=d)
                self.assertEqual(done.returncode, 1)
                self.assertIn("status", done.stdout + done.stderr)


class Malformed(unittest.TestCase):
    """`render` and `check` on boards that are not what they should be: a clean exit and no bug line, whatever is there."""

    def files(self) -> list:
        """(file, its bytes) pairs; a lone surrogate is written as the bytes the OS would not decode, and some files are
        not UTF-8 at all."""
        deep = "[" * 100000 + "]" * 100000
        question = json.dumps(seeded("Q-w9-1"))
        text = [
            ("questions/Q-w9-1.json", deep),
            ("questions/Q-w9-1.json", '{"a":' * 50000 + "1" + "}" * 50000),
            ("questions/Q-w9-1.json", question.replace("high", "\ud800")),  # a lone surrogate, escaped
            ("questions/Q-w9-1.json", '{"type": "question", "\ud800": 1}'),
            ("brief.json", '{"title": "\ud800", "status": "\ud800"}'),
            ("decisions.jsonl", '{"id": "D1", "asked": "\ud800"}\n' + "[" * 100000 + "\n"),
            ("logs/w9.jsonl", '{"type": "search", "query": "\ud800"}\n'),
            ("conversation.jsonl", '{"type": "note", "text": "\ud800"}\n' + "[" * 100000 + "\n"),
        ]
        raw = [
            ("claims/C-w9-1.json", b"\xff\xfe"),  # not UTF-8
            ("sources/S-w9-1.json", b"\x00\x00"),
            ("brief.json", question.encode() + b"\xff"),  # JSON, then a byte that is not UTF-8
            ("logs/w9.jsonl", b'{"type": "search"}\n\xc3\x28\n'),
        ]
        return [(name, body.encode("utf-8", "surrogatepass")) for name, body in text] + raw

    def test_render_and_check_never_raise_on_a_malformed_file(self):
        for relative, body in self.files():
            with self.subTest(file=relative, start=body[:12]), tempfile.TemporaryDirectory() as d:
                board_dir = made_board(Path(d))
                target = board_dir / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(body)
                for verb in ("check", "render"):
                    done = better.call(SKILL, verb, ".research/b", cwd=d)
                    self.assertIn(done.returncode, (0, 1), f"{verb}: {done.stderr[:300]}")
                    self.assertNotIn("bug in better.pyz", done.stderr)
                    self.assertNotIn("Traceback", done.stderr)
                    if verb == "check" and not body.isascii():
                        self.assertEqual(done.returncode, 1, relative)  # the file that cannot be read is reported
                        self.assertIn(relative, done.stdout)

    def test_a_lone_surrogate_in_a_record_is_reported_and_the_page_still_renders_it(self):
        with tempfile.TemporaryDirectory() as d:
            board_dir = made_board(Path(d))
            text = json.dumps(seeded("Q-w9-1")).replace("high", "\\ud800")
            (board_dir / "questions").mkdir(exist_ok=True)
            (board_dir / "questions" / "Q-w9-1.json").write_text(text, encoding="utf-8")
            checked = better.call(SKILL, "check", ".research/b", cwd=d)
            self.assertEqual(checked.returncode, 1)
            self.assertIn("Q-w9-1.json", checked.stdout)
            self.assertEqual(better.call(SKILL, "render", ".research/b", cwd=d).returncode, 0)
            data = board.load(unit(board_dir))
            json.dumps(data)  # what the page is given is plain JSON


def surrogate_places(value) -> list:
    """Each string value and each key of a JSON value as (kind, path to the object holding it, key or index)."""
    found, pending = [], [(value, ())]
    while pending:
        item, path = pending.pop()
        if isinstance(item, dict):
            for key, child in item.items():
                found.append(("key", path, key))
                pending.append((child, (*path, key)))
        elif isinstance(item, list):
            pending.extend((child, (*path, i)) for i, child in enumerate(item))
        elif isinstance(item, str) and path:
            found.append(("value", path[:-1], path[-1]))
    return found


def with_a_surrogate(record: dict, place: tuple) -> tuple:
    record = copy.deepcopy(record)
    kind, path, key = place
    holder = record
    for step in path:
        holder = holder[step]
    if kind == "value":
        holder[key] = "\ud800"
        return record, (*path, key)
    renamed = {(key + "\ud800" if k == key else k): v for k, v in holder.items()}
    holder.clear()
    holder.update(renamed)
    return record, (*path, key + "\ud800")


class Surrogates(unittest.TestCase):
    """A lone surrogate in a string or a key of every example record of the research schemas is reported on that field,
    in a message that can be printed, and the record can still be stripped and serialised for the page."""

    def test_every_example_with_a_lone_surrogate_is_reported_and_stripped(self):
        docs = DOCS
        every = []
        for file, items in EXAMPLES.items():
            sample = file.replace("<id>", "X-1").replace("<agent>", "agent")
            for item in items:
                every += [(file, sample, item["record"], place) for place in surrogate_places(item["record"])]
        picked = sweep.cases(every, key=[lambda c: (c[0], c[3][0]), lambda c: c[3][2]])
        self.assertGreater(len(picked), 20)
        for file, sample, record, place in picked:
            changed, at = with_a_surrogate(record, place)
            field = schema._render(at)
            with self.subTest(file=file, place=field):
                found = schema._match(Path("/folder") / sample, docs)
                self.assertTrue(found, f"{sample}: no schema")
                problems = schema.validate_record(changed, [doc for _, doc in found], docs, None)
                self.assertIn(field, {p.field for p in problems})
                errors = [schema.Error("f", 1, p.field, p.message) for p in problems]
                for error in errors:
                    str(error).encode("utf-8")  # printable
                json.dumps(schema.strip_invalid(changed, errors), ensure_ascii=False).encode("utf-8")


class Replies(unittest.TestCase):
    def test_reply_and_status_answer_the_users_item_as_the_coordinator(self):
        with tempfile.TemporaryDirectory() as d:
            board_dir = made_board(Path(d))
            event = {"type": "comment", "at": "2026-11-21T10:00:00Z", "by": "user", "id": "c-1", "text": "why?"}
            event["on"] = {"kind": "question", "id": "Q-w2-4", "title": "t"}
            write_lines(board_dir, "conversation.jsonl", [event])
            pending = better.run(SKILL, "pending", str(board_dir), cwd=d)
            self.assertIn("c-1", pending.stdout)
            done = better.run(SKILL, "reply", str(board_dir), "--to", "c-1", stdin="Because it fell.", cwd=d)
            self.assertEqual(done.returncode, 0, done.stderr)
            events = [json.loads(x) for x in (board_dir / "conversation.jsonl").read_text().splitlines()]
            self.assertEqual(
                [(e["type"], e["by"]) for e in events],
                [("comment", "user"), ("reply", "coordinator"), ("status", "coordinator")],
            )
            self.assertNotIn("c-1", better.run(SKILL, "pending", str(board_dir), cwd=d).stdout)


if __name__ == "__main__":
    unittest.main()
