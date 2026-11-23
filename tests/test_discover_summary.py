"""discover-better: the `summary` verb and the warnings `check` and `summary` share.

Run with `python3 tests/run.py test_discover_summary`. Each test names the requirement it checks. Records a rule reads
are written straight into a unit made by `create`; the verbs run in this process.
"""

import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))
import better  # noqa: E402
import discover_populated as P  # noqa: E402
import discover_records as R  # noqa: E402

from better_ai.discover import brief, summary  # noqa: E402

SKILL = R.SKILL
UNIT = ".discover/d"
TIME = "%Y-%m-%dT%H:%M:%SZ"


def ago(minutes: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).strftime(TIME)


def put(unit: Path, name: str, rows: list[dict]) -> None:
    path = unit / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def put_json(unit: Path, name: str, record: dict) -> None:
    path = unit / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def status(to, state="done"):
    return {"type": "status", "at": R.AT, "by": R.COORD, "to": to, "status": state}


def reply(to, ident="rp1"):
    return {"type": "reply", "at": R.AT, "by": R.COORD, "id": ident, "text": "Done: see the record.", "to": to}


class Discovery(unittest.TestCase):
    """A discovery with one item and the source of the evidence the tests add."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.unit = R.made_unit(self.repo)
        put(self.unit, "items.jsonl", [R.ITEM])
        put_json(self.unit, "sources/S-a1-1.json", R.SOURCE)

    def summary(self):
        done = better.call(SKILL, "summary", UNIT, cwd=self.repo)
        lines = [json.loads(line) for line in done.stdout.splitlines()]
        return done, lines

    def warnings(self):
        _, lines = self.summary()
        return [(w["code"], w["about"]) for w in lines if w["type"] == "warning"]

    def warns(self, code, about):
        self.assertIn((code, about), self.warnings())

    def quiet(self, code):
        self.assertNotIn(code, [c for c, _ in self.warnings()])

    def head(self, **over):
        record = json.loads((self.unit / "discover.json").read_text())
        record.update(over)
        put_json(self.unit, "discover.json", record)

    def evidence(self, record=R.COUNTING):
        put_json(self.unit, f"evidence/{record['id']}.json", record)

    def expand(self, move_id="M1", at=R.AT):
        """An expand move, with the answered confirmation it needs."""
        decision = R.record(
            R.DECISION,
            id="D1",
            about={"type": "option", "option": "K2"},
            status="answered",
            default="Yes",
            answer={"type": "chat", "text": "Yes."},
            answered_at=R.AT,
        )
        put(self.unit, "decisions.jsonl", [decision])
        put(self.unit, "options.jsonl", [R.record(R.OPTION, id="K1"), R.record(R.OPTION, id="K2", move="expand")])
        return R.record(
            R.MOVE, id=move_id, option="K2", at=at, answer={"type": "chat", "text": "Go on.", "confirm": "D1"}
        )

    def final_brief(self, text="# Brief\n", ident="v1", move="M1"):
        path = self.unit / "brief" / f"{ident}.md"
        path.parent.mkdir(exist_ok=True)
        path.write_text(text, encoding="utf-8")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return R.record(R.BRIEF, id=ident, move=move, status="final", file=f"brief/{ident}.md", sha256=digest)


class Summary(Discovery):
    def compacted(self):
        """What a discovery looks like once an agent has lost its context: records only, no memory."""
        move = self.expand()
        put(self.unit, "moves.jsonl", [move])
        put(self.unit, "briefs.jsonl", [R.record(R.BRIEF, move="M1")])
        put(self.unit, "items.jsonl", [R.ITEM, R.BEHAVIOUR])
        put(
            self.unit,
            "changes.jsonl",
            [R.CHANGE, R.record(R.CHANGE, field="importance", **{"from": None, "to": "high"})],
        )
        decisions = [json.loads(x) for x in (self.unit / "decisions.jsonl").read_text().splitlines()]
        put(self.unit, "decisions.jsonl", [*decisions, R.record(R.DECISION, id="D2")])
        put(self.unit, "conversation.jsonl", [R.event("choose", id="c1", option="K1"), R.event("edit")])
        self.evidence(R.COUNTING)
        self.evidence(R.record(R.EVIDENCE, id="E-a1-2", verifier="v1", since=ago(1), tries=["v1"]))
        self.head(step="5")

    def test_S54_it_prints_typed_json_lines_head_first_with_the_coordinator(self):
        self.compacted()
        done, lines = self.summary()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(lines[0]["type"], "head")
        self.assertEqual(lines[0]["coordinator"], R.COORD)
        for key in ("step", "status", "handed", "idea", "appetite", "setting"):
            self.assertIn(key, lines[0])
        self.assertEqual((lines[0]["step"], lines[0]["status"], lines[0]["handed"]), ("5", "open", None))

    def test_S54_the_kinds_come_in_the_order_the_design_lists_them(self):
        self.compacted()
        _, lines = self.summary()
        kinds = [x["type"] for x in lines]
        order = ["head", "decision", "event", "move", "brief", "item", "evidence", "warning"]
        self.assertEqual(kinds, sorted(kinds, key=order.index))
        self.assertEqual(
            {k: kinds.count(k) for k in order},
            {
                "head": 1,
                "decision": 2,
                "event": 2,
                "move": 1,
                "brief": 1,
                "item": 2,
                "evidence": 1,
                "warning": kinds.count("warning"),
            },
        )

    def test_S54_items_carry_the_state_and_importance_derived_from_the_changes(self):
        self.compacted()
        _, lines = self.summary()
        items = {x["id"]: x for x in lines if x["type"] == "item"}
        self.assertEqual((items["P1"]["state"], items["P1"]["importance"]), ("supported", "high"))
        self.assertEqual((items["B1"]["state"], items["B1"]["importance"]), ("unverified", None))
        self.assertIn("checker", items["P1"])

    def test_S54_only_open_events_and_only_checking_evidence_are_listed(self):
        self.compacted()
        put(self.unit, "conversation.jsonl", [R.event("choose", id="c1", option="K1"), R.event("edit"), status("h1")])
        _, lines = self.summary()
        self.assertEqual([x["id"] for x in lines if x["type"] == "event"], ["c1"])
        self.assertEqual([x["id"] for x in lines if x["type"] == "evidence"], ["E-a1-2"])

    def events(self, *lines):
        put(self.unit, "conversation.jsonl", [R.event("add_evidence", id="a1"), status("a1"), *lines])
        _, out = self.summary()
        return [x for x in out if x["type"] == "event"]

    def test_S54_a_done_event_the_user_reopened_is_listed_as_reopened_with_the_reason(self):
        self.assertEqual(self.events(), [])
        reopen = {"type": "reopen", "at": R.AT, "by": "user", "to": "a1", "text": "You did not add it."}
        (found,) = self.events(reopen)
        self.assertEqual(
            (found["id"], found["state"], found["reopened_because"]), ("a1", "reopened", "You did not add it.")
        )

    def test_S54_a_follow_up_note_under_a_done_event_makes_it_open_as_followup(self):
        note = {"type": "note", "at": R.AT, "by": "user", "id": "n9", "to": "a1", "text": "Also this."}
        (found,) = self.events(note)
        self.assertEqual((found["id"], found["state"]), ("a1", "followup"))
        self.assertEqual(found["thread"][0]["text"], "Also this.")

    def test_S54_a_new_event_has_the_state_new(self):
        put(self.unit, "conversation.jsonl", [R.event("add_evidence", id="a1")])
        _, out = self.summary()
        self.assertEqual([x["state"] for x in out if x["type"] == "event"], ["new"])

    def test_S54_the_moves_name_their_move_and_the_briefs_their_move(self):
        self.compacted()
        _, lines = self.summary()
        move = next(x for x in lines if x["type"] == "move")
        self.assertEqual((move["id"], move["option"], move["move"]), ("M1", "K2", "expand"))
        brief = next(x for x in lines if x["type"] == "brief")
        self.assertEqual((brief["id"], brief["move"], brief["status"]), ("v1", "M1", "draft"))

    def test_S54_evidence_words_are_never_printed(self):
        self.compacted()
        done, _ = self.summary()
        self.assertNotIn("We lost a week", done.stdout)

    def test_S54_a_record_that_fails_its_schema_is_printed_around_and_the_last_line_names_the_file(self):
        self.compacted()
        decisions = [json.loads(x) for x in (self.unit / "decisions.jsonl").read_text().splitlines()]
        put(self.unit, "decisions.jsonl", [*decisions, R.record(R.DECISION, id="D3", status="open")])
        done, lines = self.summary()
        self.assertEqual(done.returncode, 1)
        self.assertEqual(lines[0]["type"], "head")
        self.assertTrue([x for x in lines if x["type"] == "item"])
        self.assertEqual(lines[-1]["type"], "invalid")
        self.assertEqual(lines[-1]["files"], ["decisions.jsonl"])
        self.assertIn("decisions.jsonl:3: status", lines[-1]["errors"][0])

    def test_S54_an_invalid_evidence_file_is_named_with_its_folder(self):
        self.evidence(R.record(R.COUNTING, sha256="short"))
        done, lines = self.summary()
        self.assertEqual(done.returncode, 1)
        self.assertEqual(lines[-1]["files"], ["evidence/E-a1-1.json"])
        self.assertEqual([x["id"] for x in lines if x["type"] == "item"], ["P1"])

    def test_S54_a_valid_discovery_exits_0_and_has_no_invalid_line(self):
        self.compacted()
        done, lines = self.summary()
        self.assertEqual(done.returncode, 0)
        self.assertNotIn("invalid", [x["type"] for x in lines])

    def test_S54_the_summary_is_a_verb_of_discover_better_only(self):
        done = better.call("code-better", "summary", ".code/x", cwd=self.repo)
        self.assertEqual(done.returncode, 2, done.stderr)


class Warnings(Discovery):
    def test_S55_counting_evidence_that_no_change_cites(self):
        self.evidence()
        self.warns("uncited-evidence", "E-a1-1")
        put(self.unit, "changes.jsonl", [R.CHANGE])
        self.quiet("uncited-evidence")

    def test_S55_evidence_checking_with_no_verifier(self):
        self.evidence(R.EVIDENCE)
        self.warns("evidence-without-verifier", "E-a1-1")
        self.evidence(R.record(R.EVIDENCE, verifier="v1", since=ago(1), tries=["v1"]))
        self.quiet("evidence-without-verifier")

    def test_a_reworded_quote_with_no_correction_yet(self):
        reworded = R.record(
            R.EVIDENCE, status="reworded", verifier="v1", tries=["v1"], reason="reworded", page_words="x y"
        )
        self.evidence(reworded)
        self.warns("reworded-without-correction", "E-a1-1")
        self.assertIn("E-a1-1 is reworded: add the corrected quote", self.summary()[1][-1]["text"])
        self.evidence(R.record(R.EVIDENCE, id="E-coord-1", by=R.COORD, corrects="E-a1-1"))
        self.quiet("reworded-without-correction")

    def test_a_correction_is_not_a_copy_of_the_page_words_it_quotes(self):
        words = "Over half said they mute the alerts."
        self.evidence(
            R.record(R.EVIDENCE, status="reworded", verifier="v1", tries=["v1"], reason="reworded", page_words=words)
        )
        self.evidence(
            R.record(R.EVIDENCE, id="E-coord-1", by=R.COORD, corrects="E-a1-1", words={"type": "quote", "text": words})
        )
        texts = [w["text"] for w in self.summary()[1] if w.get("type") == "warning"]
        self.assertFalse([t for t in texts if "also occur" in t], texts)

    def test_S55_an_item_checker_with_no_record_for_30_minutes(self):
        put(self.unit, "items.jsonl", [R.record(R.ITEM, checker="analyst-1", since=ago(120))])
        self.warns("no-word-from-agent", "P1")
        self.assertIn("No word from analyst-1 for 1", self.summary()[1][-1]["text"])
        put(self.unit, "items.jsonl", [R.record(R.ITEM, checker="analyst-1", since=ago(5))])
        self.quiet("no-word-from-agent")

    def test_S55_a_record_from_the_agent_since_then_ends_the_silence(self):
        put(self.unit, "items.jsonl", [R.record(R.ITEM, checker="analyst-1", since=ago(120))])
        self.evidence(R.record(R.EVIDENCE, id="E-analyst-1-1", by="analyst-1", at=ago(5), verifier="v1", since=ago(5)))
        self.quiet("no-word-from-agent")

    def test_S55_a_verifier_with_no_record_for_30_minutes(self):
        self.evidence(R.record(R.EVIDENCE, verifier="v1", since=ago(90), tries=["v1"]))
        self.warns("no-word-from-agent", "E-a1-1")
        self.evidence(R.record(R.EVIDENCE, verifier="v1", since=ago(2), tries=["v1"]))
        self.quiet("no-word-from-agent")

    def test_S55_a_test_that_runs_with_a_silent_checker(self):
        put(
            self.unit,
            "tests.jsonl",
            [R.record(R.TEST, status="running", runner="analyst", checker="analyst-3", since=ago(60))],
        )
        self.warns("no-word-from-agent", "X1")

    def test_S55_an_answered_risk_decision_that_no_change_cites(self):
        risk = R.record(
            R.DECISION,
            about={"type": "risk", "item": "P1", "risk": "R1"},
            default="Accept the risk",
            status="answered",
            answer={"type": "chat", "text": "Accept it."},
            answered_at=R.AT,
        )
        put(self.unit, "decisions.jsonl", [risk])
        self.warns("risk-answer-uncited", "D1")
        put(self.unit, "changes.jsonl", [R.RISK_CHANGE])
        self.quiet("risk-answer-uncited")

    def test_S55_a_waiting_risk_decision_is_not_yet_a_warning(self):
        waiting = R.record(R.DECISION, about={"type": "risk", "item": "P1", "risk": "R1"}, default="Accept the risk")
        put(self.unit, "decisions.jsonl", [waiting])
        self.quiet("risk-answer-uncited")

    def test_S55_a_behaviour_with_no_ambiguity(self):
        put(self.unit, "items.jsonl", [R.ITEM, R.BEHAVIOUR])
        self.warns("behaviour-without-ambiguity", "B1")
        put(self.unit, "items.jsonl", [R.ITEM, R.record(R.BEHAVIOUR, ambiguity="Which item changes?")])
        self.quiet("behaviour-without-ambiguity")

    def test_S55_a_move_that_writes_a_brief_and_has_no_final_brief(self):
        put(self.unit, "moves.jsonl", [self.expand()])
        self.warns("move-without-brief", "M1")
        put(self.unit, "briefs.jsonl", [R.BRIEF])
        self.assertIn("v1", [w["text"] for w in self.summary()[1] if w["type"] == "warning"][0])
        put(self.unit, "briefs.jsonl", [self.final_brief()])
        self.quiet("move-without-brief")

    def test_S55_a_move_that_writes_no_brief_needs_none(self):
        put(self.unit, "options.jsonl", [R.OPTION])
        put(self.unit, "moves.jsonl", [R.MOVE])
        self.quiet("move-without-brief")

    def test_S55_a_draft_brief_older_than_a_later_move(self):
        first = self.expand()
        put(self.unit, "moves.jsonl", [first])
        put(self.unit, "briefs.jsonl", [R.BRIEF])
        self.quiet("draft-brief-older")
        put(
            self.unit,
            "moves.jsonl",
            [first, R.record(R.MOVE, id="M2", at=R.AT, option="K1", answer={"type": "chat", "text": "Probe first."})],
        )
        self.warns("draft-brief-older", "v1")

    def test_S55_an_unfinished_redact(self):
        self.quiet("redact-unfinished")
        (self.unit / brief.STATE).write_text("{}", encoding="utf-8")
        self.warns("redact-unfinished", brief.STATE)

    def test_S55_a_redact_that_was_stopped_leaves_the_warning_and_a_finished_one_takes_it_away(self):
        root = self.repo / "redacting"
        root.mkdir()
        unit = P.populated(root)
        (unit / "conversation.jsonl").write_text(json.dumps(R.event("redact", id="d1", evidence="E-coord-1")) + "\n")
        label = str(unit.relative_to(root))

        def warnings():
            lines = better.call(SKILL, "summary", label, cwd=root).stdout.splitlines()
            return [json.loads(x)["code"] for x in lines if json.loads(x)["type"] == "warning"]

        with mock.patch.object(brief, "_after_place", mock.Mock(side_effect=KeyboardInterrupt)):
            R.run(root, "redact", label, "E-coord-1", "--request", "d1")
        self.assertIn("redact-unfinished", warnings())
        self.assertEqual(R.run(root, "redact", label, "E-coord-1", "--request", "d1").returncode, 0)
        self.assertNotIn("redact-unfinished", warnings())

    def test_D15_the_state_file_has_one_name_which_summary_takes_from_brief(self):
        self.assertEqual(summary.REDACT_STATE, brief.STATE)

    def test_S55_a_final_brief_holding_a_block_for_removed_evidence(self):
        gone = R.record(R.COUNTING, status="removed", reason="redact", words={"type": "quote", "text": "x"})
        self.evidence(R.without(gone, "checked_read", "span", "sha256", "verifier"))
        put(self.unit, "moves.jsonl", [self.expand()])
        put(self.unit, "briefs.jsonl", [self.final_brief("# B\n<!-- E-a1-1 -->words<!-- /E-a1-1 -->\n")])
        self.warns("brief-holds-removed", "v1")
        put(self.unit, "briefs.jsonl", [self.final_brief("# B\n[removed]\n")])
        self.quiet("brief-holds-removed")

    def test_S55_a_done_event_that_no_record_and_no_reply_points_to(self):
        put(self.unit, "conversation.jsonl", [R.event("add_evidence", id="a1"), status("a1")])
        self.warns("done-event-unanswered", "a1")
        put(self.unit, "conversation.jsonl", [R.event("add_evidence", id="a1"), status("a1"), reply("a1")])
        self.quiet("done-event-unanswered")

    def test_S55_a_record_that_points_to_the_event_answers_it(self):
        put(self.unit, "conversation.jsonl", [R.event("add_evidence", id="a1"), status("a1")])
        given = {"type": "page", "event": "a1"}
        put_json(self.unit, "sources/S-coord-1.json", R.record(R.YOU_SOURCE, origin={"type": "you", "given": given}))
        self.quiet("done-event-unanswered")

    def test_S55_a_done_event_the_user_followed_up_is_open_not_done(self):
        note = {"type": "note", "at": R.AT, "by": "user", "id": "n9", "to": "a1", "text": "Also this."}
        put(self.unit, "conversation.jsonl", [R.event("add_evidence", id="a1"), status("a1"), note])
        self.quiet("done-event-unanswered")
        reopen = {"type": "reopen", "at": R.AT, "by": "user", "to": "a1", "text": "No."}
        put(self.unit, "conversation.jsonl", [R.event("add_evidence", id="a1"), status("a1"), reopen])
        self.quiet("done-event-unanswered")

    def test_S55_an_open_event_is_not_a_done_event(self):
        put(self.unit, "conversation.jsonl", [R.event("add_evidence", id="a1")])
        self.quiet("done-event-unanswered")

    def test_S55_an_open_choose_event_older_than_a_later_move(self):
        put(self.unit, "options.jsonl", [R.OPTION])
        put(
            self.unit,
            "conversation.jsonl",
            [R.event("choose", id="c1", at=ago(60)), R.event("choose", id="c2", at=ago(30)), status("c2")],
        )
        put(self.unit, "moves.jsonl", [R.record(R.MOVE, at=ago(10), answer={"type": "page", "event": "c2"})])
        self.warns("open-event-older", "c1")
        self.assertNotIn(("open-event-older", "c2"), self.warnings())
        put(
            self.unit,
            "conversation.jsonl",
            [
                R.event("choose", id="c1", at=ago(60)),
                status("c1"),
                R.event("choose", id="c2", at=ago(30)),
                status("c2"),
            ],
        )
        self.quiet("open-event-older")

    def test_S55_an_open_answer_event_older_than_a_later_answer(self):
        older = {
            "type": "answer",
            "at": ago(60),
            "by": "user",
            "id": "n1",
            "decision": "D1",
            "text": "Yes",
            "default": True,
        }
        newer = {**older, "id": "n2", "at": ago(5), "decision": "D2"}
        put(self.unit, "conversation.jsonl", [older, newer])
        self.warns("open-event-older", "n1")
        self.assertNotIn(("open-event-older", "n2"), self.warnings())

    def test_S55_a_step_that_follows_a_move_when_none_is_recorded(self):
        self.head(step="5")
        self.quiet("step-disagrees")
        self.head(step="6")
        self.warns("step-disagrees", "discover.json")

    def test_S55_a_step_that_hands_a_brief_on_when_none_is_final(self):
        put(self.unit, "moves.jsonl", [self.expand()])
        self.head(step="8")
        self.quiet("step-disagrees")
        self.head(step="9")
        self.warns("step-disagrees", "discover.json")
        put(self.unit, "briefs.jsonl", [self.final_brief()])
        self.quiet("step-disagrees")

    def test_S55_step_10_follows_the_hand_on(self):
        put(self.unit, "moves.jsonl", [self.expand()])
        put(self.unit, "briefs.jsonl", [self.final_brief()])
        self.head(step="10")
        self.warns("step-disagrees", "discover.json")
        self.head(step="10", handed={"brief": "v1", "to": "design-better", "at": R.AT})
        self.quiet("step-disagrees")

    def test_S53_words_that_occur_in_another_record_are_warned(self):
        self.evidence()
        self.quiet("evidence-text-copied")
        put(self.unit, "items.jsonl", [R.record(R.ITEM, text="They said: we lost a  week to this.")])
        self.warns("evidence-text-copied", "E-a1-1")

    def test_S53_only_whole_words_count_as_a_copy(self):
        self.evidence(R.record(R.COUNTING, summary="No"))
        put(self.unit, "items.jsonl", [R.record(R.ITEM, text="Nobody would pay for it.")])
        self.quiet("evidence-text-copied")
        put(self.unit, "items.jsonl", [R.record(R.ITEM, text="Would they pay? No, they would not.")])
        self.warns("evidence-text-copied", "E-a1-1")

    def test_S53_a_summary_that_occurs_in_another_record_is_warned(self):
        self.evidence(R.record(R.COUNTING, summary="A teammate on payments lost a week."))
        put(
            self.unit,
            "decisions.jsonl",
            [R.record(R.DECISION, asked="Is it true that a teammate on payments lost a week.")],
        )
        self.warns("evidence-text-copied", "E-a1-1")

    def test_S53_the_users_own_source_and_event_hold_the_words_by_design(self):
        words = "I lost a week to this."
        put_json(self.unit, "sources/S-coord-1.json", R.YOU_SOURCE)
        put(self.unit, "conversation.jsonl", [R.event("add_evidence", id="a1", text=words), reply("a1")])
        self.evidence(R.record(R.COUNTING, id="E-a1-3", source="S-coord-1", words={"type": "quote", "text": words}))
        self.quiet("evidence-text-copied")


class CheckPrintsWarnings(Discovery):
    def test_S55_check_prints_each_warning_after_the_records_pass_and_still_exits_0(self):
        self.evidence()
        done = better.call(SKILL, "check", UNIT, cwd=self.repo)
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertIn("warning: E-a1-1 counts but no change cites it", done.stderr)

    def test_S55_check_says_nothing_when_nothing_is_wrong(self):
        done = better.call(SKILL, "check", UNIT, cwd=self.repo)
        self.assertEqual((done.returncode, done.stderr), (0, ""))

    def test_S55_check_shows_the_same_warnings_as_summary(self):
        self.evidence()
        put(self.unit, "items.jsonl", [R.ITEM, R.BEHAVIOUR])
        _, lines = self.summary_lines()
        from_summary = [w["text"] for w in lines if w["type"] == "warning"]
        done = better.call(SKILL, "check", UNIT, cwd=self.repo)
        self.assertEqual([x.removeprefix("warning: ") for x in done.stderr.splitlines()], from_summary)

    def summary_lines(self):
        done = better.call(SKILL, "summary", UNIT, cwd=self.repo)
        return done, [json.loads(x) for x in done.stdout.splitlines()]

    def test_S55_check_prints_no_warning_while_a_record_is_invalid(self):
        self.evidence()
        put(self.unit, "decisions.jsonl", [R.record(R.DECISION, status="open")])
        done = better.call(SKILL, "check", UNIT, cwd=self.repo)
        self.assertEqual(done.returncode, 1)
        self.assertNotIn("warning:", done.stderr)


if __name__ == "__main__":
    unittest.main()


class NoFalseCopyWarning(unittest.TestCase):
    """A result text that cites its evidence (D16) and the [removed] marks a redact leaves are not copies."""

    def assertNoCopyWarning(self, done):
        self.assertNotIn("also occur in", done.stdout + done.stderr)

    def test_a_page_result_and_its_redact_raise_no_copy_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            unit = P.populated(root)
            label = str(unit.relative_to(root))
            with (unit / "conversation.jsonl").open("a") as log:
                log.write(json.dumps(R.event("add_result", id="r1", text="A team found it fast.")) + "\n")
            R.run(root, "set", label, "X1", "--by", "coord", stdin=json.dumps({"status": "running"}))
            src = {
                "origin": {"type": "you", "given": {"type": "page", "event": "r1"}},
                "title": "You",
                "said_by_role": "a teammate",
            }
            self.assertEqual(R.run(root, "add", label, "source", "--by", "coord", stdin=json.dumps(src)).returncode, 0)
            sid = next(
                p.stem
                for p in (unit / "sources").glob("*.json")
                if json.loads(p.read_text())["origin"].get("given", {}).get("event") == "r1"
            )
            ev = {
                "source": sid,
                "words": {"type": "event", "event": "r1"},
                "summary": "a team found it fast",
                "kind": "did",
                "about": "your users",
                "bears_on": [{"item": "P1", "direction": "for"}],
                "status": "counts",
            }
            self.assertEqual(R.run(root, "add", label, "evidence", "--by", "coord", stdin=json.dumps(ev)).returncode, 0)
            eid = next(
                p.stem for p in (unit / "evidence").glob("*.json") if json.loads(p.read_text()).get("source") == sid
            )
            result = {"text": "A team found it fast.", "outcome": "holds", "evidence": [eid]}
            self.assertEqual(
                R.run(
                    root, "set", label, "X1", "--by", "coord", stdin=json.dumps({"status": "done", "result": result})
                ).returncode,
                0,
            )
            self.assertNoCopyWarning(R.run(root, "check", label))
            with (unit / "conversation.jsonl").open("a") as log:
                log.write(json.dumps(R.event("redact", id="d9", evidence=eid)) + "\n")
            self.assertEqual(R.run(root, "redact", label, eid, "--request", "d9").returncode, 0)
            self.assertNoCopyWarning(R.run(root, "check", label))

    def test_two_redacts_raise_no_copy_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            unit = P.populated(root)
            label = str(unit.relative_to(root))
            for i, e in enumerate(("E-coord-1", "E-coord-2")):
                with (unit / "conversation.jsonl").open("a") as log:
                    log.write(json.dumps(R.event("redact", id=f"d{i}", evidence=e)) + "\n")
                self.assertEqual(R.run(root, "redact", label, e, "--request", f"d{i}").returncode, 0)
            self.assertNoCopyWarning(R.run(root, "check", label))


class SaidOnce(unittest.TestCase):
    def test_an_evidence_cited_twice_gets_one_marker_pair(self):
        said = brief._said({"text": "words"}, ["E-a1-1", "E-a1-2", "E-a1-1"])
        self.assertEqual(said.count("<!-- E-a1-1 -->"), 1)
        self.assertEqual(said.count("<!-- /E-a1-1 -->"), 1)
