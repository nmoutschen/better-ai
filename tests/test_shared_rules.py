"""The rules every skill shares, each in one place: an agent's last word and how long it may be quiet, who writes a
record type (`x-written-by`), a record's fingerprint, a public address (`x-public-url`), and the full-string patterns.

Run with `python3 tests/run.py test_shared_rules`.
"""

import hashlib
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))

from test_records import Repo, call  # noqa: E402

from better_ai import page, paths, records, research, schema  # noqa: E402
from better_ai.architect import model  # noqa: E402
from better_ai.design import canvas  # noqa: E402
from better_ai.research import board  # noqa: E402

SOURCE = {
    k: v
    for k, v in json.loads((HERE / "fixtures" / "research_board_examples.json").read_text())["sources/<id>.json"][0][
        "record"
    ].items()
    if k not in ("type", "at", "by", "id")
}


class LastWord(unittest.TestCase):
    def test_the_latest_at_among_the_records_the_agent_wrote(self):
        found = page.last_word(
            [
                {"by": "w1", "at": "2026-11-23T10:00:00Z"},
                {"by": "w1", "at": "2026-11-23T10:20:00Z"},
                {"by": "w2", "at": "2026-11-23T10:40:00Z"},
                {"by": "w1", "at": "not a time"},
                {"by": "w1"},
                "not a record",
            ],
            "w1",
        )
        self.assertEqual(found, datetime(2026, 11, 23, 10, 20, tzinfo=timezone.utc))

    def test_an_id_that_carries_the_agent_counts_when_the_prefix_is_given(self):
        records = [
            {"by": "coord", "id": "E-w1-3", "at": "2026-11-23T10:30:00Z"},
            {"by": "coord", "id": "S-w1-2", "at": "2026-11-23T10:10:00Z"},
            {"by": "coord", "id": "X-w1-9", "at": "2026-11-23T10:50:00Z"},
            {"by": "coord", "id": "E-w10-1", "at": "2026-11-23T10:55:00Z"},
            {"by": "coord", "id": "E-w1", "at": "2026-11-23T10:56:00Z"},
        ]
        self.assertIsNone(page.last_word(records, "w1"))
        self.assertEqual(
            page.last_word(records, "w1", id_prefixes=("E-", "S-")), datetime(2026, 11, 23, 10, 30, tzinfo=timezone.utc)
        )

    def test_none_when_the_agent_wrote_nothing(self):
        self.assertIsNone(page.last_word([{"by": "w2", "at": "2026-11-23T10:40:00Z"}], "w1"))

    def test_one_quiet_threshold_of_thirty_minutes_reaches_every_page(self):
        self.assertEqual(page.QUIET_AFTER, timedelta(minutes=30))
        text = page.static_page(board.SPEC, {"x": 1})
        data = json.loads(text.split('id="page-data">', 1)[1].split("</script>", 1)[0])
        self.assertEqual(data["quiet_after"], 1800)

    def test_no_page_script_holds_its_own_threshold(self):
        src = HERE.parent / "src" / "better_ai"
        for name in ("page/page.js", "code/dashboard.js", "research/board.js"):
            text = (src / name).read_text(encoding="utf-8")
            self.assertNotIn("QUIET_AFTER", text, name)
            self.assertNotIn(">= 30", text, name)
        self.assertNotIn("quietMinutes", (src / "code" / "dashboard.js").read_text(encoding="utf-8"))


class OpenDecisions(unittest.TestCase):
    def test_every_page_counts_its_open_questions_with_the_shared_rule(self):
        src = HERE.parent / "src" / "better_ai"
        self.assertIn("function pageOpenDecisions(", (src / "page" / "page.js").read_text(encoding="utf-8"))
        for name in ("research/board.js", "architect/page.js", "code/dashboard.js"):
            self.assertIn("pageOpenDecisions(", (src / name).read_text(encoding="utf-8"), name)


class ResearchLastWord(Repo):
    def test_the_board_gives_each_agent_its_last_word(self):
        unit = self.board()
        self.assertEqual(call("research-better", "add", unit, "source", "--by", "w2", stdin=SOURCE)[0], 0)
        data = board.load(paths.resolve_unit(str(unit), research.SKILL))
        self.assertIn("w2", data["last_word"])
        self.assertRegex(data["last_word"]["w2"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")


class WrittenBy(Repo):
    def test_only_the_coordinator_sets_the_brief(self):
        unit = self.board()
        done = call("research-better", "set", unit, "brief", "--by", "w1", stdin={"status": "stopped"})
        self.assertEqual(done[0], 1, done)
        self.assertIn("only coordinator writes brief: use --by coordinator", done[1] + done[2])
        done = call("research-better", "set", unit, "brief", stdin={"status": "stopped"})
        self.assertEqual(done[0], 1, done)
        self.assertIn("use --by coordinator", done[1] + done[2])
        done = call("research-better", "set", unit, "brief", "--by", "coordinator", stdin={"status": "stopped"})
        self.assertEqual(done[0], 0, done)

    def test_unset_is_held_to_the_same_rule(self):
        unit = self.board()
        done = call("research-better", "set", unit, "brief", "--by", "w1", "--unset", "limit")
        self.assertEqual(done[0], 1, done)
        self.assertIn("only coordinator writes brief", done[1] + done[2])

    def test_add_is_held_to_it_and_a_type_without_it_is_not(self):
        rule = {"x-written-by": "coordinator"}
        schema._audit_extensions(rule, "here")  # a known keyword with its value is accepted
        with self.assertRaises(schema.SchemaError):
            schema._audit_extensions({"x-written-by": ""}, "here")
        unit = self.board()
        self.assertEqual(call("research-better", "add", unit, "source", "--by", "w2", stdin=SOURCE)[0], 0)

    def test_the_name_comes_from_the_head_when_it_names_a_coordinator(self):
        unit = paths.resolve_unit(str(self.board()), research.SKILL)
        self.assertEqual(records.written_by(unit, "coordinator"), "coordinator")
        head = json.loads((unit.path / "brief.json").read_text())
        (unit.path / "brief.json").write_text(json.dumps({**head, "coordinator": "lead"}))
        self.assertEqual(records.written_by(unit, "coordinator"), "lead")


class Fingerprint(unittest.TestCase):
    def test_canonical_json_without_at_and_by(self):
        value = {"b": "é", "a": 1, "at": "x", "by": "y"}
        want = hashlib.sha256(
            json.dumps({"a": 1, "b": "é"}, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        self.assertEqual(schema.fingerprint(value), want)
        self.assertNotEqual(schema.fingerprint(value, drop=()), want)
        self.assertEqual(schema.fingerprint("text"), hashlib.sha256(b'"text"').hexdigest())

    def test_architect_uses_it(self):
        self.assertIs(model.fingerprint, schema.fingerprint)

    def test_a_review_stored_before_this_change_still_matches(self):
        requirement = {"id": "R1", "text": "x", "at": "t", "by": "b"}
        old = hashlib.sha256(json.dumps({"id": "R1", "text": "x"}, sort_keys=True).encode()).hexdigest()
        key = "requirement:R1"
        texts = {key: schema.fingerprint(requirement)}
        self.assertEqual(model.changed_texts(texts, {"texts": {key: old}}, {key: old}), [])
        self.assertEqual(model.changed_texts(texts, {"texts": {key: "other"}}, {key: old}), [key])


class PublicUrl(unittest.TestCase):
    def test_a_field_with_the_hook_takes_only_a_public_http_address(self):
        rule = {"type": "object", "properties": {"url": {"type": "string", "x-public-url": True}}}
        schema._audit(rule, "here")
        for url in (
            "file:///etc/passwd",
            "http://localhost:8000/x",
            "http://127.0.0.1/",
            "http://10.0.0.4/a",
            "ftp://x.org/",
        ):
            problems = schema.validate_instance({"url": url}, rule, {})
            self.assertEqual([p.field for p in problems], ["url"], url)
        self.assertEqual(schema.validate_instance({"url": "https://doi.org/10.1/x"}, rule, {}), [])
        with self.assertRaises(schema.SchemaError):
            schema._audit({"x-public-url": "yes"}, "here")

    def test_the_rule(self):
        self.assertIsNone(schema.url_problem("https://doi.org/10.1/x"))
        for bad in (
            "http://[::1]/",
            "http://192.168.1.1/",
            "https://a.localhost/",
            "http://0x7f.1/",
            "https://x y.org/",
        ):
            self.assertIsNotNone(schema.url_problem(bad), bad)


class FullString(unittest.TestCase):
    """L3: a `$`-anchored pattern matched with `match` takes a trailing newline; fullmatch does not."""

    def test_deadline(self):
        self.assertIsNotNone(records.DEADLINE.fullmatch("+30m"))
        self.assertIsNone(records.DEADLINE.fullmatch("+30m\n"))

    def test_deadline_with_a_newline_is_refused(self):
        clock = mock.Mock(now=lambda: datetime.now(timezone.utc))
        with self.assertRaises(records.Refused):
            records._deadline({"deadline": "+30m\n"}, clock, mock.Mock(label="u"))

    def test_the_id_scan_skips_an_id_with_a_trailing_newline(self):
        self.assertEqual(records.assign_id({"prefix": "D"}, {}, None, ["D1", "D7\n"]), "D2")

    def test_canvas_size(self):
        self.assertIsNotNone(canvas.SIZE.fullmatch("1280x800"))
        self.assertIsNone(canvas.SIZE.fullmatch("1280x800\n"))
        with mock.patch.object(canvas, "read_head", return_value={"widths": ["1280x800\n", "375"]}):
            data, _ = canvas.data_of(None)
        self.assertEqual([s["w"] for s in data["sizes"]], [375])


if __name__ == "__main__":
    unittest.main()


class StrictPatterns(unittest.TestCase):
    """L3: a `$` in a schema pattern ends the string; it does not match before a final newline."""

    def test_a_pattern_refuses_a_trailing_newline(self):
        rule = {"type": "string", "pattern": "^D\\d+$"}
        self.assertEqual(schema.validate_instance("D1", rule, {}), [])
        self.assertNotEqual(schema.validate_instance("D1\n", rule, {}), [])
