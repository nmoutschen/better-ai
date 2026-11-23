"""discover-better: the rules for moves and briefs, and the errors `check` reports for them.

Run with `python3 tests/run.py test_discover_rules_moves`. Each test names the requirement it checks. Records are added
with `better.call`, which runs the command in this process; files a rule reads are written straight into the unit.
"""

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))
import better  # noqa: E402
import discover_records as R  # noqa: E402

from better_ai.discover import rules_moves  # noqa: E402

SKILL = R.SKILL
UNIT = ".discover/d"


def put(unit: Path, name: str, rows: list[dict]) -> None:
    """Write a unit's JSONL file as it is, as a coordinator with an older `better.pyz` could have left it."""
    path = unit / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def put_json(unit: Path, name: str, record: dict) -> None:
    path = unit / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def options() -> list[dict]:
    return [
        R.record(R.OPTION, id="K1", move="test first"),
        R.record(R.OPTION, id="K2", move="expand", text="Build it for the whole team."),
        R.record(R.OPTION, id="K3", move="shrink", text="Build it for owners only."),
        R.record(R.OPTION, id="K4", move="pause", text="Wait a month."),
    ]


def choose(ident="c1", option="K1", confirmed=False, revision="r", at=R.AT):
    return R.event("choose", id=ident, option=option, confirmed=confirmed, revision=revision, at=at)


def answered(ident="D1", option="K2"):
    return R.record(
        R.DECISION,
        id=ident,
        about={"type": "option", "option": option},
        asked=f"{option} costs a month and cannot be undone. Go on?",
        status="answered",
        default="Yes",
        answer={"type": "chat", "text": "Yes, go on."},
        answered_at=R.AT,
    )


class Unit(unittest.TestCase):
    """A discovery in a repository, with one item, four options and no move."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.unit = R.made_unit(self.repo)
        put(self.unit, "items.jsonl", [R.ITEM])
        put(self.unit, "options.jsonl", options())
        put(self.unit, "conversation.jsonl", [choose()])

    def add(self, kind, fields, by=R.COORD):
        return better.call(SKILL, "add", UNIT, kind, "--by", by, stdin=json.dumps(fields), cwd=self.repo)

    def set(self, ident, fields):
        return better.call(SKILL, "set", UNIT, ident, "--by", R.COORD, stdin=json.dumps(fields), cwd=self.repo)

    def check(self):
        return better.call(SKILL, "check", UNIT, cwd=self.repo)

    def move(self, answer, option="K1", step="5"):
        return self.add("move", {"option": option, "step": step, "why": "The user chose it.", "answer": answer})

    def page(self, event="c1"):
        return {"type": "page", "event": event}

    def chat(self, text="Yes, go on.", confirm=None):
        return {"type": "chat", "text": text, **({"confirm": confirm} if confirm else {})}

    def choose_now(self, option, ident="c1", confirmed=True):
        """A choose event whose revision is what the option and items are now."""
        revision = rules_moves.revision_in(self.unit, option)
        put(self.unit, "conversation.jsonl", [choose(ident, option, confirmed, revision)])

    def accepted(self, done):
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)

    def refused(self, done, *words):
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        text = done.stdout + done.stderr
        for word in words:
            self.assertIn(word, text)


class PageMoves(Unit):
    def test_S34_a_page_move_whose_event_names_a_different_option_is_refused(self):
        self.choose_now("K1")
        self.refused(self.move(self.page(), option="K3"), "c1 chose K1, not K3", "mark it done")

    def test_S34_an_expand_whose_event_was_not_confirmed_is_refused_with_the_next_action(self):
        self.choose_now("K2", confirmed=False)
        self.refused(self.move(self.page(), option="K2"), "not confirmed", "ask the user to choose again")

    def test_S34_a_move_that_needs_no_second_click_is_added_without_it(self):
        self.choose_now("K1", confirmed=False)
        self.accepted(self.move(self.page(), option="K1"))

    def test_S34_a_revision_that_differs_is_refused_and_says_to_confirm_again(self):
        put(self.unit, "conversation.jsonl", [choose("c1", "K2", True, "not-the-revision")])
        self.refused(self.move(self.page(), option="K2"), "changed since the user chose it", "confirm again")

    def test_S34_a_revision_goes_stale_when_an_item_changes_after_the_user_chose(self):
        self.choose_now("K2")
        put(self.unit, "changes.jsonl", [R.record(R.CHANGE, field="importance", to="high", cause={"reasoning": "x"})])
        self.refused(self.move(self.page(), option="K2"), "changed since the user chose it")

    def test_S34_a_confirmed_move_with_the_current_revision_is_added(self):
        self.choose_now("K2")
        self.accepted(self.move(self.page(), option="K2"))
        self.assertEqual(self.check().returncode, 0, self.check().stdout)

    def test_S34_the_revision_is_the_same_for_the_same_records_and_differs_for_a_changed_option(self):
        first = rules_moves.revision_in(self.unit, "K2")
        self.assertEqual(first, rules_moves.revision_in(self.unit, "K2"))
        self.assertNotEqual(first, rules_moves.revision_in(self.unit, "K3"))
        put(self.unit, "options.jsonl", [*options()[:1], R.record(options()[1], cost="two months"), *options()[2:]])
        self.assertNotEqual(first, rules_moves.revision_in(self.unit, "K2"))
        self.assertIsNone(rules_moves.revision_in(self.unit, "K9"))

    def test_S34_check_repeats_the_event_and_confirmed_rules_on_a_move_written_by_hand(self):
        self.choose_now("K1")
        put(self.unit, "moves.jsonl", [R.record(R.MOVE, option="K3", answer=self.page())])
        done = self.check()
        self.refused(done, "moves.jsonl:1: answer.event", "c1 chose K1, not K3")
        self.choose_now("K2", confirmed=False)
        put(self.unit, "moves.jsonl", [R.record(R.MOVE, option="K2", answer=self.page())])
        self.refused(self.check(), "not confirmed")

    def test_S34_check_does_not_hold_a_recorded_move_to_a_revision_the_items_have_since_left(self):
        self.choose_now("K2")
        self.accepted(self.move(self.page(), option="K2"))
        put(self.unit, "changes.jsonl", [R.record(R.CHANGE, field="importance", to="high", cause={"reasoning": "x"})])
        self.assertEqual(self.check().returncode, 0, self.check().stdout)

    def test_S36_a_second_move_for_the_same_event_is_refused_naming_the_first(self):
        self.choose_now("K1")
        self.accepted(self.move(self.page(), option="K1"))
        self.refused(self.move(self.page(), option="K1"), "already recorded as M1", "mark the event done")

    def test_S36_check_reports_two_moves_on_one_event(self):
        self.choose_now("K1")
        put(
            self.unit,
            "moves.jsonl",
            [R.record(R.MOVE, answer=self.page()), R.record(R.MOVE, id="M2", answer=self.page())],
        )
        self.refused(self.check(), "already recorded as M1", "already recorded as M2")


class ChatMoves(Unit):
    def setUp(self):
        super().setUp()
        put(self.unit, "decisions.jsonl", [R.DECISION])

    def test_S35_a_chat_expand_without_a_confirm_is_refused(self):
        self.refused(self.move(self.chat(), option="K2"), "chat expand needs a confirmation", "how hard it is to undo")

    def test_S35_a_chat_adopt_and_stop_need_one_too(self):
        put(
            self.unit,
            "options.jsonl",
            [*options(), R.record(R.OPTION, id="K5", move="adopt"), R.record(R.OPTION, id="K6", move="stop")],
        )
        self.refused(self.move(self.chat(), option="K5"), "chat adopt needs")
        self.refused(self.move(self.chat(), option="K6"), "chat stop needs")

    def test_S35_a_confirm_that_is_still_waiting_is_refused(self):
        waiting = R.record(R.without(answered(), "answer", "answered_at"), status="waiting")
        put(self.unit, "decisions.jsonl", [waiting])
        self.refused(self.move(self.chat(confirm="D1"), option="K2"), "D1 is still waiting")

    def test_S35_a_confirm_about_another_option_is_refused(self):
        put(self.unit, "decisions.jsonl", [answered("D1", "K3")])
        self.refused(self.move(self.chat(confirm="D1"), option="K2"), "D1 is not about K2")

    def test_S35_a_confirm_about_an_item_is_refused(self):
        self.refused(self.move(self.chat(confirm="D1"), option="K2"), "D1 is not about K2")

    def test_S35_a_chat_expand_with_an_answered_confirm_about_its_option_is_added(self):
        put(self.unit, "decisions.jsonl", [answered("D1", "K2")])
        self.accepted(self.move(self.chat(confirm="D1"), option="K2"))
        self.assertEqual(self.check().returncode, 0, self.check().stdout)

    def test_S35_check_reports_a_chat_expand_written_without_a_confirm(self):
        put(self.unit, "moves.jsonl", [R.record(R.MOVE, option="K2", answer=self.chat())])
        self.refused(self.check(), "moves.jsonl:1: answer.confirm", "chat expand needs a confirmation")

    def test_S35_a_chat_move_that_needs_no_confirm_is_added_without_one(self):
        self.accepted(self.move(self.chat("Run the probe."), option="K1"))

    def test_S36_a_confirm_that_another_move_rests_on_is_refused_naming_it(self):
        put(self.unit, "decisions.jsonl", [answered("D1", "K2")])
        self.accepted(self.move(self.chat("Yes, go on.", confirm="D1"), option="K2"))
        self.refused(self.move(self.chat("Really go on.", confirm="D1"), option="K2"), "D1 already confirms M1")

    def test_S36_a_chat_move_that_repeats_an_existing_option_and_words_is_refused_naming_it(self):
        self.accepted(self.move(self.chat("Run the probe."), option="K1"))
        self.refused(self.move(self.chat("  run the  PROBE. "), option="K1"), "already recorded as M1")

    def test_S36_the_same_words_for_another_option_are_a_new_move(self):
        self.accepted(self.move(self.chat("Yes."), option="K1"))
        self.accepted(self.move(self.chat("Yes."), option="K4"))


class Briefs(Unit):
    def setUp(self):
        super().setUp()
        put(self.unit, "decisions.jsonl", [answered("D1", "K2")])
        self.accepted(self.move(self.chat("Run the probe."), option="K1"))
        self.accepted(self.move(self.chat("Yes, go on.", confirm="D1"), option="K2"))

    def brief(self, move, **over):
        return self.add("brief", {"move": move, "status": "draft", **over})

    def final(self, ident="v1", move="M2", text="# Brief\n", name="brief/v1.md", digest=None):
        path = self.unit / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        found = digest or hashlib.sha256(text.encode("utf-8")).hexdigest()
        put(
            self.unit, "briefs.jsonl", [R.record(R.BRIEF, id=ident, move=move, status="final", file=name, sha256=found)]
        )

    def test_S87_a_brief_for_a_move_that_writes_none_is_refused(self):
        self.refused(self.brief("M1"), "M1 is a test first move", "writes no brief")

    def test_S87_a_brief_for_an_expand_move_is_added(self):
        self.accepted(self.brief("M2", decision="Build it for the team."))

    def test_S87_check_reports_a_brief_written_for_a_move_that_writes_none(self):
        put(self.unit, "briefs.jsonl", [R.record(R.BRIEF, move="M1")])
        self.refused(self.check(), "briefs.jsonl:1: move", "writes no brief")

    def test_S39_a_second_brief_for_a_move_is_refused_naming_the_first(self):
        self.accepted(self.brief("M2"))
        self.refused(self.brief("M2"), "v1 is already the draft brief for M2")

    def test_S39_a_new_version_for_a_move_whose_brief_is_final_is_added(self):
        self.final()
        self.accepted(self.brief("M2"))
        self.assertEqual(self.check().returncode, 0, self.check().stdout)
        self.refused(self.brief("M2"), "v2 is already the draft brief for M2")

    def test_S39_check_reports_a_second_brief_added_while_the_first_is_a_draft(self):
        put(self.unit, "briefs.jsonl", [R.record(R.BRIEF, move="M2"), R.record(R.BRIEF, id="v2", move="M2")])
        self.refused(self.check(), "briefs.jsonl:2: move", "v1 is already the draft brief for M2")

    def test_S39_set_cannot_move_a_draft_onto_a_move_that_has_a_draft(self):
        put(
            self.unit,
            "moves.jsonl",
            [
                *self.rows("moves.jsonl"),
                R.record(R.MOVE, id="M3", option="K3", answer={"type": "chat", "text": "Owners only."}),
            ],
        )
        self.accepted(self.brief("M2"))
        self.accepted(self.brief("M3"))
        before = (self.unit / "briefs.jsonl").read_bytes()
        self.refused(self.set("v1", {"move": "M3"}), "v2 is already the draft brief for M3", "change it with set")
        self.assertEqual((self.unit / "briefs.jsonl").read_bytes(), before)

    def test_S39_check_reports_a_hand_written_second_draft_on_both_lines(self):
        put(self.unit, "briefs.jsonl", [R.record(R.BRIEF, move="M2"), R.record(R.BRIEF, id="v2", move="M2")])
        done = self.check()
        self.refused(done, "briefs.jsonl:1: move", "briefs.jsonl:2: move")

    def rows(self, name):
        return [json.loads(x) for x in (self.unit / name).read_text().splitlines()]

    def test_S42_set_refuses_status_final_and_names_the_brief_verb(self):
        self.accepted(self.brief("M2"))
        self.refused(self.set("v1", {"status": "final"}), "set cannot make v1 final", "better.pyz brief")
        self.assertIn('"status": "draft"', (self.unit / "briefs.jsonl").read_text())

    def set_unset(self, ident, fields, *unsets):
        args = [a for field in unsets for a in ("--unset", field)]
        return better.call(
            SKILL, "set", UNIT, ident, "--by", R.COORD, *args, stdin=json.dumps(fields) if fields else "", cwd=self.repo
        )

    def test_S42_a_final_brief_refuses_every_set_and_every_unset_and_stays_as_it_was(self):
        self.final()
        briefs, text = (self.unit / "briefs.jsonl").read_bytes(), (self.unit / "brief" / "v1.md").read_bytes()
        patches = {
            "move": "M1",
            "status": "draft",
            "decision": "x",
            "why": "x",
            "questions": ["x"],
            "file": "brief/other.md",
            "sha256": "c" * 64,
            "redacted": ["d" * 64],
        }
        for name, value in patches.items():
            with self.subTest(patch=name):
                self.refused(self.set("v1", {name: value}), "v1 is final, and set cannot change it", "redact")
        for name in (*patches, "file"):
            with self.subTest(unset=name):
                self.refused(self.set_unset("v1", None, name), "v1 is final, and set cannot change it")
        with self.subTest(case="back to draft, unsetting file and sha256"):
            self.refused(
                self.set_unset("v1", {"status": "draft"}, "file", "sha256"), "v1 is final, and set cannot change it"
            )
        self.assertEqual((self.unit / "briefs.jsonl").read_bytes(), briefs)
        self.assertEqual((self.unit / "brief" / "v1.md").read_bytes(), text)
        self.assertEqual(self.check().returncode, 0, self.check().stdout)

    def test_S42_a_draft_never_gains_status_file_or_sha256_through_set(self):
        self.accepted(self.brief("M2"))
        for name, value in {
            "status": "draft",
            "file": "brief/v1.md",
            "sha256": "c" * 64,
            "redacted": ["d" * 64],
        }.items():
            with self.subTest(patch=name):
                self.refused(self.set("v1", {name: value}), "set cannot change")

    def test_S28_a_move_refuses_every_set_and_every_unset(self):
        before = (self.unit / "moves.jsonl").read_bytes()
        self.refused(self.set("M1", {"why": "Another reason."}), "M1 is a move, and set cannot change it")
        self.refused(self.set_unset("M1", None, "why"), "set cannot change it")
        self.refused(self.set_unset("M1", {"why": "x"}, "answer"), "set cannot change it")
        self.assertEqual((self.unit / "moves.jsonl").read_bytes(), before)

    def test_S42_set_still_changes_the_text_of_a_draft(self):
        self.accepted(self.brief("M2"))
        self.accepted(self.set("v1", {"why": "Because the probe held."}))

    def test_S42_add_refuses_a_brief_that_is_final(self):
        self.refused(self.brief("M2", status="final", file="brief/v1.md", sha256="a" * 64), "add cannot make v1 final")

    def test_S46_a_final_brief_with_its_file_and_hash_passes_check(self):
        self.final()
        self.assertEqual(self.check().returncode, 0, self.check().stdout)

    def test_S46_check_reports_a_final_brief_whose_file_is_missing(self):
        self.final()
        (self.unit / "brief" / "v1.md").unlink()
        self.refused(self.check(), "briefs.jsonl:1: file", "brief/v1.md is missing")

    def test_S46_check_reports_a_final_brief_whose_bytes_do_not_match_the_hash(self):
        self.final(digest="b" * 64)
        self.refused(self.check(), "briefs.jsonl:1: sha256", "does not have the recorded sha256")
        self.final()
        (self.unit / "brief" / "v1.md").write_text("# Edited by hand\n", encoding="utf-8")
        self.refused(self.check(), "does not have the recorded sha256")

    def test_S46_a_file_outside_the_discovery_is_an_error(self):
        self.final(name="../outside.md")
        self.refused(self.check(), "not a path inside the discovery")


class References(unittest.TestCase):
    """Every id a record cites must exist: `check` names the dangling one."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.unit = R.made_unit(self.repo)
        put(self.unit, "items.jsonl", [R.ITEM, R.BEHAVIOUR])
        put(self.unit, "options.jsonl", [R.OPTION])
        put(self.unit, "tests.jsonl", [R.TEST])
        put_json(self.unit, "sources/S-a1-1.json", R.SOURCE)
        put_json(self.unit, "evidence/E-a1-1.json", R.COUNTING)

    def dangling(self, where):
        done = better.call(SKILL, "check", UNIT, cwd=self.repo)
        self.assertEqual(done.returncode, 1, done.stdout)
        self.assertIn(where, done.stdout)
        self.assertIn("dangling", done.stdout)

    def test_S72_a_valid_unit_passes(self):
        self.assertEqual(better.call(SKILL, "check", UNIT, cwd=self.repo).returncode, 0)

    def test_S72_rests_on(self):
        put(self.unit, "items.jsonl", [R.ITEM, R.record(R.BEHAVIOUR, rests_on=["P9"])])
        self.dangling("items.jsonl:2: rests_on[0]")

    def test_S72_bears_on(self):
        put_json(self.unit, "evidence/E-a1-1.json", R.record(R.COUNTING, bears_on=[{"item": "P9", "direction": "for"}]))
        self.dangling("bears_on[0].item")

    def test_S72_cause_evidence(self):
        put(self.unit, "changes.jsonl", [R.record(R.CHANGE, cause={"evidence": ["E-a1-9"]})])
        self.dangling("cause.evidence[0]")

    def test_S72_cause_test(self):
        put(self.unit, "changes.jsonl", [R.record(R.CHANGE, cause={"test": "X9"})])
        self.dangling("cause.test")

    def test_S72_cause_answer_decision(self):
        put(self.unit, "changes.jsonl", [R.record(R.RISK_CHANGE, cause={"answer": {"type": "decision", "id": "D9"}})])
        self.dangling("cause.answer.id")

    def test_S72_move_option(self):
        put(self.unit, "moves.jsonl", [R.record(R.MOVE, option="K9")])
        self.dangling("moves.jsonl:1: option")

    def test_S72_brief_move(self):
        put(self.unit, "briefs.jsonl", [R.record(R.BRIEF, move="M9")])
        self.dangling("briefs.jsonl:1: move")

    def test_S72_evidence_source(self):
        put_json(self.unit, "evidence/E-a1-1.json", R.record(R.COUNTING, source="S-a1-9"))
        self.dangling("source")

    def test_S72_a_source_and_evidence_from_an_event(self):
        given = {"type": "page", "event": "a9"}
        put_json(self.unit, "sources/S-coord-1.json", R.record(R.YOU_SOURCE, origin={"type": "you", "given": given}))
        self.dangling("origin.given.event")
        put_json(self.unit, "sources/S-coord-1.json", R.YOU_SOURCE)
        put_json(self.unit, "evidence/E-a1-1.json", R.record(R.COUNTING, words={"type": "event", "event": "a9"}))
        self.dangling("words.event")

    def test_S72_a_record_that_fails_its_schema_is_an_error(self):
        put(self.unit, "moves.jsonl", [R.without(R.MOVE, "why")])
        done = better.call(SKILL, "check", UNIT, cwd=self.repo)
        self.assertEqual(done.returncode, 1)
        self.assertIn("moves.jsonl:1: why", done.stdout)


if __name__ == "__main__":
    unittest.main()
