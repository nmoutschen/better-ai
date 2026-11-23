"""discover-better: the rules for decisions, risks and changes, and who may write each record.

Run with `python3 tests/run.py test_discover_rules_changes`. Each test names the requirement it checks. A unit is made
by `create`; its records are added with `add`, as the coordinator does. Evidence is written into the unit's folder
directly: the rules for its statuses are not what these tests are about.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))
import discover_records as R  # noqa: E402

from better_ai import cli, paths  # noqa: E402
from better_ai.discover import SKILL  # noqa: E402
from better_ai.discover import rules_changes as rules  # noqa: E402

BODY = ("type", "at", "by", "id")


class Unit(unittest.TestCase):
    """A discovery with item P1 (risks R1 and R2), made by `create`; the helpers add and set records as a writer."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name)
        self.unit = R.made_unit(self.repo)
        self.ok(self.add("item", item(risks=[risk("R1"), risk("R2")])))

    # -- running verbs

    def verb(self, *args, fields=None):
        stdin = None if fields is None else json.dumps(fields)
        return R.run(self.repo, *args, stdin=stdin)

    def add(self, kind, fields, by=R.COORD):
        return self.verb("add", ".discover/d", kind, "--by", by, fields=R.without(fields, *BODY))

    def set(self, ref, fields, by=R.COORD, unset=()):
        args = ["set", ".discover/d", ref] + (["--by", by] if by else [])
        for name in unset:
            args += ["--unset", name]
        return self.verb(*args, fields=fields)

    def check(self):
        return self.verb("check", ".discover/d")

    def as_unit(self):
        return paths.Unit(self.unit.resolve(), self.repo.resolve(), SKILL.kinds[0], SKILL)

    # -- asserting

    def ok(self, done):
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return done

    def refused(self, done, *words):
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        text = done.stdout + done.stderr
        for word in words:
            self.assertIn(word, text)
        return text

    # -- files

    def lines(self, name):
        path = self.unit / name
        return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []

    def append(self, name, record):
        with (self.unit / name).open("a") as handle:
            handle.write(json.dumps(record) + "\n")

    def put(self, folder, record):
        (self.unit / folder).mkdir(exist_ok=True)
        (self.unit / folder / f"{record['id']}.json").write_text(json.dumps(record))

    def evidence(self, ident="E-a1-1", status="counts", direction="for", item="P1"):
        """A piece of evidence and its source, in the unit's folders."""
        source = R.record(R.SOURCE, id=f"S-{ident[2:]}")
        self.put("sources", source)
        base = R.COUNTING if status == "counts" else R.EVIDENCE
        record = R.record(
            base, id=ident, source=source["id"], bears_on=[{"item": item, "direction": direction}], status=status
        )
        if status in ("unverified", "not reachable", "removed"):
            record = R.without(record, "since")
            record["reason"] = "no longer holds"
        self.put("evidence", record)
        return ident

    def answer_event(self, decision, default, ident="a1"):
        self.append(
            "conversation.jsonl",
            {
                "type": "answer",
                "at": R.AT,
                "by": "user",
                "id": ident,
                "decision": decision,
                "text": "Accept the risk" if default else "I accept it, with a caveat",
                "default": default,
            },
        )
        return ident

    def ask(self, about, asked="Is this fine?", default="Yes"):
        return self.add("decision", R.record(R.DECISION, about=about, asked=asked, default=default))

    def ask_risk(self, risk_id="R1", item_id="P1"):
        about = {"type": "risk", "item": item_id, "risk": risk_id}
        return self.ask(about, f"Accept {risk_id}?", "Accept the risk")

    def answer_chat(self, ident):
        return self.ok(self.set(ident, {"status": "answered", "answer": {"type": "chat", "text": "Yes, accept it."}}))

    def answer_page(self, ident, default):
        event = self.answer_event(ident, default)
        return self.ok(self.set(ident, {"status": "answered", "answer": {"type": "page", "event": event}}))

    def accept(self, decision, risk_id="R1", item_id="P1", **over):
        return self.add("change", risk_change(decision, risk_id, item_id, **over))

    def state(self, to, cause, item_id="P1", **over):
        return self.add(
            "change", R.record(R.CHANGE, about={"type": "item", "item": item_id}, to=to, cause=cause, **over)
        )


def item(ident="P1", kind="problem", risks=(), **over):
    return R.record(R.ITEM, id=ident, kind=kind, risks=list(risks), **over)


def risk(ident, text=None):
    return {"id": ident, "kind": "value", "text": text or f"Risk {ident}."}


def risk_change(decision, risk_id="R1", item_id="P1", **over):
    return R.record(
        R.RISK_CHANGE,
        about={"type": "item", "item": item_id},
        risk=risk_id,
        cause={"answer": {"type": "decision", "id": decision}},
        **over,
    )


class Decisions(Unit):
    def test_S8_setting_a_decision_to_answered_stamps_answered_at(self):
        self.ok(self.ask({"type": "item", "item": "P1"}))
        self.answer_chat("D1")
        (record,) = self.lines("decisions.jsonl")
        self.assertEqual(record["status"], "answered")
        self.assertRegex(record["answered_at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_S8_a_typed_answered_at_is_replaced_by_the_stamp(self):
        self.ok(self.ask({"type": "item", "item": "P1"}))
        self.ok(
            self.set(
                "D1",
                {
                    "status": "answered",
                    "answer": {"type": "chat", "text": "Yes."},
                    "answered_at": "2020-01-01T00:00:00Z",
                },
            )
        )
        self.assertNotEqual(self.lines("decisions.jsonl")[0]["answered_at"], "2020-01-01T00:00:00Z")

    def test_S8_the_answer_is_a_page_answer_event_of_the_user_for_this_decision_or_chat_words(self):
        self.ok(self.ask({"type": "item", "item": "P1"}))
        self.ok(self.ask({"type": "item", "item": "P1"}, asked="Another question?"))
        self.answer_page("D1", True)
        self.assertEqual(self.lines("decisions.jsonl")[0]["answer"], {"type": "page", "event": "a1"})
        self.answer_event("D1", True, ident="a2")  # an event for D1 does not answer D2
        done = self.set("D2", {"status": "answered", "answer": {"type": "page", "event": "a2"}})
        self.refused(done, 'answers "D1", not "D2"')
        done = self.set("D2", {"status": "answered", "answer": {"type": "chat"}})
        self.assertEqual(done.returncode, 1)

    def test_S9_an_answered_decision_keeps_its_about_and_answer(self):
        self.ok(self.ask({"type": "item", "item": "P1"}))
        self.answer_chat("D1")
        self.refused(self.set("D1", {"about": {"type": "discovery"}}), "D1", "answered")
        self.refused(self.set("D1", {"answer": {"type": "chat", "text": "No."}}), "D1", "answered")
        self.refused(self.set("D1", {"status": "waiting"}), "D1", "answered")
        self.assertEqual(self.lines("decisions.jsonl")[0]["answer"]["text"], "Yes, accept it.")
        self.ok(self.set("D1", {"asked": "Is P1 fine, then?"}))  # what is not locked can change

    def test_S10_a_repeated_waiting_question_is_refused_and_names_the_open_one(self):
        about = {"type": "item", "item": "P1"}
        self.ok(self.ask(about))
        text = self.refused(self.ask(about), "D1")
        self.assertIn("already", text)
        self.assertEqual(len(self.lines("decisions.jsonl")), 1)
        self.ok(self.ask(about, asked="A different question?"))
        self.ok(self.ask({"type": "discovery"}))

    def test_S10_the_same_question_may_be_asked_again_once_it_is_answered(self):
        about = {"type": "item", "item": "P1"}
        self.ok(self.ask(about))
        self.answer_chat("D1")
        self.ok(self.ask(about))

    def test_S11_a_waiting_decision_stays_waiting_past_any_time(self):
        self.ok(self.ask({"type": "item", "item": "P1"}))
        self.ok(self.set("D1", {"default": "No"}))
        later = cli.Run.now
        with mock.patch.object(cli.Run, "now", lambda self: later(self).replace(year=2099)):
            self.ok(self.check())
            self.ok(self.set("D1", {"asked": "Still open?"}))
        (record,) = self.lines("decisions.jsonl")
        self.assertEqual(record["status"], "waiting")
        self.assertNotIn("answered_at", record)


class Risks(Unit):
    def test_S1_a_risk_is_accepted_by_the_answered_decision_about_that_risk(self):
        self.ok(self.ask_risk())
        self.answer_chat("D1")
        self.ok(self.accept("D1"))

    def test_S1_a_page_answer_with_the_default_accepts_the_risk(self):
        self.ok(self.ask_risk())
        self.answer_page("D1", True)
        self.ok(self.accept("D1"))

    def test_S1_a_change_that_cites_no_decision_is_refused(self):
        for cause in ({"reasoning": "It is small."}, {"answer": {"type": "chat", "text": "Fine."}}):
            done = self.add("change", R.record(risk_change("D1"), cause=cause))
            self.refused(done, "decision")
        self.assertEqual(self.lines("changes.jsonl"), [])

    def test_S1_a_decision_about_another_risk_or_item_is_refused(self):
        self.ok(self.ask_risk("R2"))
        self.answer_chat("D1")
        self.refused(self.accept("D1", "R1"), "D1", "R1")
        self.ok(self.ask({"type": "item", "item": "P1"}, asked="Plan a test?"))
        self.answer_chat("D2")
        self.refused(self.accept("D2", "R1"), "D2", "R1")
        self.assertEqual(self.lines("changes.jsonl"), [])

    def test_S1_a_decision_that_is_waiting_is_refused(self):
        self.ok(self.ask_risk())
        self.refused(self.accept("D1"), "D1", "not answered")

    def test_S1_a_decision_an_earlier_change_cites_is_refused(self):
        self.ok(self.ask_risk())
        self.ok(self.ask({"type": "item", "item": "P1"}, asked="Plan a test?"))
        self.answer_chat("D1")
        self.ok(self.state("waiting for you", {"answer": {"type": "decision", "id": "D1"}}))
        text = self.refused(self.accept("D1"), "D1")
        self.assertIn("earlier change", text)
        self.assertEqual(len(self.lines("changes.jsonl")), 1)

    def test_S1_a_typed_page_answer_is_refused_with_the_next_action(self):
        self.ok(self.ask_risk())
        self.answer_page("D1", False)
        self.refused(
            self.accept("D1"), "D1 was answered in words: confirm with the user in the chat and record their words"
        )
        self.assertEqual(self.lines("changes.jsonl"), [])

    def test_S1_a_risk_the_item_does_not_have_is_refused(self):
        self.ok(self.ask_risk("R9"))
        self.answer_chat("D1")
        self.refused(self.accept("D1", "R9"), "R9")

    def test_S2_risk_accepted_is_refused_as_a_state(self):
        done = self.state("risk accepted", {"reasoning": "The user is fine with it."})
        self.refused(done, "accept each risk with a risk change citing the user's answer")
        self.assertEqual(self.lines("changes.jsonl"), [])

    def test_S2_a_risk_change_to_anything_but_accepted_is_refused(self):
        self.ok(self.ask_risk())
        self.answer_chat("D1")
        self.assertEqual(self.accept("D1", to="open").returncode, 1)

    def test_S4_a_risk_a_decision_cites_cannot_be_removed_or_changed(self):
        self.ok(self.ask_risk("R1"))
        self.refused(self.set("P1", {"risks": [risk("R2")]}), "R1")
        self.refused(self.set("P1", {"risks": [risk("R1", "Different words."), risk("R2")]}), "R1")
        self.refused(self.set("P1", {"risks": [risk("R3"), risk("R2")]}), "R1")
        self.ok(self.set("P1", {"risks": [risk("R1"), risk("R2", "R2, said better."), risk("R3")]}))
        self.assertEqual([r["id"] for r in self.lines("items.jsonl")[0]["risks"]], ["R1", "R2", "R3"])

    def test_S4_a_risk_a_change_cites_cannot_be_removed_or_changed(self):
        self.ok(self.ask_risk("R2"))
        self.answer_chat("D1")
        self.ok(self.accept("D1", "R2"))
        self.refused(self.set("P1", {"risks": [risk("R1")]}), "R2")
        self.refused(self.set("P1", {"risks": [risk("R1"), risk("R2", "Changed.")]}), "R2")

    def test_S4_a_cited_risk_id_cannot_appear_twice_or_with_a_second_text(self):
        self.ok(self.ask_risk("R1"))
        self.refused(self.set("P1", {"risks": [risk("R1"), risk("R1", "Other."), risk("R2")]}), "R1")
        self.refused(self.set("P1", {"risks": [risk("R1", "Other."), risk("R1"), risk("R2")]}), "R1")
        self.refused(self.set("P1", {"risks": [risk("R1"), risk("R1"), risk("R2")]}), "R1")
        self.assertEqual([r["id"] for r in self.lines("items.jsonl")[0]["risks"]], ["R1", "R2"])

    def test_S4_a_risk_nothing_cites_can_be_removed(self):
        self.ok(self.set("P1", {"risks": [risk("R1")]}))
        self.assertEqual([r["id"] for r in self.lines("items.jsonl")[0]["risks"]], ["R1"])

    def test_S4_a_risk_of_another_item_is_not_locked_by_this_one(self):
        self.ok(self.add("item", item("P2", risks=[risk("R1")])))
        self.ok(self.ask_risk("R1", "P1"))
        self.ok(self.set("P2", {"risks": []}))

    def test_S6_check_applies_the_risk_rule_to_a_hand_written_risk_change(self):
        self.ok(self.ask_risk())  # D1 is still waiting
        self.append("changes.jsonl", risk_change("D1"))
        text = self.refused(self.check(), "D1")
        self.assertIn("changes.jsonl:1", text)
        self.assertIn("not answered", text)

    def test_S6_check_passes_a_risk_change_that_followed_the_rule(self):
        self.ok(self.ask_risk())
        self.answer_chat("D1")
        self.ok(self.accept("D1"))
        self.ok(self.check())

    def test_S6_check_refuses_a_decision_cited_by_two_changes(self):
        self.ok(self.ask_risk())
        self.answer_chat("D1")
        self.ok(self.accept("D1"))
        self.append("changes.jsonl", R.record(risk_change("D1"), at="2026-11-23T10:05:00Z"))
        text = self.refused(self.check(), "earlier change")
        self.assertIn("changes.jsonl:2", text)

    def test_S6_check_refuses_a_typed_page_answer(self):
        self.ok(self.ask_risk())
        self.answer_page("D1", False)
        self.append("changes.jsonl", risk_change("D1"))
        self.refused(self.check(), "answered in words")


class Changes(Unit):
    def test_S24_supported_needs_counting_evidence_for_the_item(self):
        cause = {"reasoning": "It looks right."}
        self.refused(self.state("supported", cause), "supported", "P1")
        evidence = self.evidence(status="checking")
        self.refused(self.state("supported", cause), "supported")
        self.evidence(evidence, status="counts", direction="against")
        self.refused(self.state("supported", cause), "supported")
        self.assertEqual(self.lines("changes.jsonl"), [])
        self.evidence("E-a1-2", status="counts", direction="for")
        text = self.refused(self.state("supported", cause), "E-a1-1")  # counting evidence against it still stands
        self.assertIn("against", text)

    def test_S24_supported_is_added_with_counting_evidence_for_and_none_against(self):
        self.evidence()
        self.ok(self.state("supported", {"evidence": ["E-a1-1"]}))

    def test_S24_contradicted_needs_counting_evidence_against(self):
        cause = {"reasoning": "It is wrong."}
        self.refused(self.state("contradicted", cause), "contradicted")
        self.evidence(direction="for")
        self.refused(self.state("contradicted", cause), "contradicted")
        self.evidence("E-a1-2", direction="against")
        self.ok(self.state("contradicted", {"evidence": ["E-a1-2"]}))

    def test_S24_checking_needs_a_checker_or_evidence_that_is_checking(self):
        cause = {"reasoning": "An analyst starts."}
        self.refused(self.state("checking", cause), "checking", "P1")
        self.evidence(status="counts")
        self.refused(self.state("checking", cause), "checking")
        self.evidence("E-a1-2", status="checking")
        self.ok(self.state("checking", cause))

    def test_S24_checking_is_added_for_an_item_with_a_checker(self):
        self.ok(self.add("item", item("P2", checker="analyst-1", since=R.AT, tries=["analyst-1"])))
        self.ok(self.state("checking", {"reasoning": "analyst-1 starts."}, item_id="P2"))

    def test_S24_waiting_for_you_needs_an_open_question_about_the_item(self):
        cause = {"reasoning": "Only the user can say."}
        self.refused(self.state("waiting for you", cause), "waiting for you")
        self.ok(self.ask({"type": "item", "item": "P1"}))
        self.ok(self.state("waiting for you", cause))

    def test_S24_a_question_about_a_risk_of_the_item_counts_and_an_answered_one_does_not(self):
        cause = {"reasoning": "Only the user can say."}
        self.ok(self.ask_risk())
        self.ok(self.state("waiting for you", cause))
        self.answer_chat("D1")
        self.ok(self.add("item", item("P2")))
        self.refused(self.state("waiting for you", cause, item_id="P2"), "waiting for you")

    def test_S24_needs_a_test_needs_a_test_that_settles_the_item(self):
        cause = {"reasoning": "A probe would settle it."}
        self.refused(self.state("needs a test", cause), "needs a test")
        self.ok(self.add("item", item("P2")))
        self.ok(self.add("test", R.record(R.TEST, settles=["P2"])))
        self.refused(self.state("needs a test", cause), "needs a test")
        self.ok(self.add("test", R.record(R.TEST, id="X2", settles=["P1"])))
        self.ok(self.state("needs a test", cause))

    def test_S24_a_test_that_was_removed_does_not_settle_the_item(self):
        self.ok(self.add("test", R.record(R.TEST, settles=["P1"])))
        self.ok(self.set("X1", {"status": "removed", "reason": "Too slow."}))
        self.refused(self.state("needs a test", {"reasoning": "x"}), "needs a test")

    def test_S24_unverified_and_importance_have_no_state_rule(self):
        self.ok(self.state("unverified", {"reasoning": "Back to the start."}))
        done = self.add(
            "change",
            R.record(
                R.CHANGE, field="importance", to="high", cause={"reasoning": "The core of the idea."}, **{"from": None}
            ),
        )
        self.ok(done)

    def test_S25_a_change_that_cites_evidence_that_does_not_count_is_refused(self):
        self.evidence(status="checking")
        self.refused(self.state("unverified", {"evidence": ["E-a1-1"]}), "E-a1-1", "does not count")
        self.evidence("E-a1-2", status="unverified")
        self.refused(self.state("unverified", {"evidence": ["E-a1-2"]}), "E-a1-2", "does not count")
        self.assertEqual(self.lines("changes.jsonl"), [])

    def test_S25_a_change_that_cites_evidence_that_does_not_bear_on_its_item_is_refused(self):
        self.ok(self.add("item", item("P2")))
        self.evidence(item="P2")
        self.refused(self.state("contradicted", {"evidence": ["E-a1-1"]}), "E-a1-1", "does not bear on P1")

    def test_S25_a_change_that_cites_evidence_that_counts_and_bears_on_its_item_is_added(self):
        self.evidence()
        self.evidence("E-a1-2", status="checking")
        self.ok(self.state("supported", {"evidence": ["E-a1-1"]}))
        self.ok(self.check())

    def test_S26_a_change_identical_to_the_last_change_for_the_field_is_refused(self):
        self.ok_checker()
        self.ok(self.state("checking", {"reasoning": "analyst-1 starts."}))
        self.refused(self.state("checking", {"reasoning": "Still."}), "already recorded: nothing to do")
        self.assertEqual(len(self.lines("changes.jsonl")), 1)

    def ok_checker(self):
        return self.ok(self.set("P1", {"checker": "analyst-1", "since": R.AT, "tries": ["analyst-1"]}))

    def test_S26_a_change_to_another_value_or_of_another_item_or_field_is_added(self):
        self.ok_checker()
        self.ok(self.add("item", item("P2", checker="analyst-2", since=R.AT, tries=["analyst-2"])))
        self.ok(self.state("checking", {"reasoning": "x"}))
        self.ok(self.state("checking", {"reasoning": "x"}, item_id="P2"))
        self.ok(self.state("unverified", {"reasoning": "x"}))
        done = self.add("change", R.record(R.CHANGE, field="importance", to="high", cause={"reasoning": "x"}))
        self.ok(done)
        self.refused(
            self.add("change", R.record(R.CHANGE, field="importance", to="high", cause={"reasoning": "y"})), "already"
        )

    def test_S30_a_change_about_the_discovery_is_accepted_and_a_repeat_of_the_latest_is_refused(self):
        def change(name, to, cause):
            return R.record(R.CHANGE, about={"type": "discovery"}, field=name, to=to, cause=cause, **{"from": "x"})

        said = {"answer": {"type": "chat", "text": "A month, not two weeks."}}
        for name, first, second in (
            ("appetite", "a month of one person", "two weeks"),
            ("setting", "internal", "external"),
        ):
            with self.subTest(name):
                self.ok(self.add("change", change(name, first, said)))
                self.refused(self.add("change", change(name, first, {"reasoning": "Again."})), "already recorded")
                self.ok(self.add("change", change(name, second, said)))
                self.ok(self.add("change", change(name, first, said)))  # not the latest any more: accepted

    def test_S26_accepting_the_same_risk_twice_is_refused(self):
        self.ok(self.ask_risk())
        self.answer_chat("D1")
        self.ok(self.accept("D1"))
        self.ok(
            self.ask({"type": "risk", "item": "P1", "risk": "R1"}, asked="Accept R1 again?", default="Accept the risk")
        )
        self.answer_chat("D2")
        self.refused(self.accept("D2"), "already recorded: nothing to do")

    def test_S28_a_set_on_a_move_is_refused(self):
        self.ok(self.add("option", R.OPTION))
        self.ok(self.add("move", R.MOVE))
        self.refused(self.set("M1", {"why": "Another reason."}), "M1", "move")
        self.assertEqual(self.lines("moves.jsonl")[0]["why"], R.MOVE["why"])

    def test_S28_a_set_on_a_change_is_refused(self):
        self.evidence()
        self.ok(self.state("supported", {"evidence": ["E-a1-1"]}))
        self.assertEqual(self.set("change", {"to": "checking"}).returncode, 1)
        self.assertEqual(self.lines("changes.jsonl")[0]["to"], "supported")

    def test_S29_a_stale_latest_state_is_a_warning_and_check_passes(self):
        self.evidence()
        self.ok(self.state("supported", {"evidence": ["E-a1-1"]}))
        self.ok(self.check())
        self.evidence("E-a1-2", direction="against")  # the normal round: counter-evidence comes in later
        done = self.ok(self.check())
        self.assertIn("warning", done.stderr)
        self.assertIn("P1's state is stale: add a change", done.stderr)
        self.assertNotIn("stale", done.stdout)

    def test_S29_stale_and_identical_read_the_latest_change_as_derive_does(self):
        """A state change to `risk accepted` is not a state (derive skips it): a hand-written one is not the latest."""
        self.evidence()
        self.ok(self.state("supported", {"evidence": ["E-a1-1"]}))
        self.append(
            "changes.jsonl",
            R.record(R.CHANGE, to="risk accepted", cause={"reasoning": "Hand-written."}, **{"from": "supported"}),
        )
        self.refused(self.state("supported", {"reasoning": "Again."}), "already recorded")
        self.assertEqual(rules.stale(self.as_unit()), [])
        self.evidence("E-a1-1", status="removed")
        (line,) = rules.stale(self.as_unit())
        self.assertIn("P1's state is stale: add a change", line)

    def test_S29_a_hand_written_change_with_a_to_that_is_not_text_is_not_the_latest(self):
        self.evidence()
        self.ok(self.state("supported", {"evidence": ["E-a1-1"]}))
        self.append("changes.jsonl", R.record(R.CHANGE, to=3, cause={"reasoning": "Hand-written."}))
        self.evidence("E-a1-1", status="removed")
        (line,) = rules.stale(self.as_unit())
        self.assertIn("state is stale", line)

    def test_S29_a_state_that_holds_gives_no_warning(self):
        self.evidence()
        self.ok(self.state("supported", {"evidence": ["E-a1-1"]}))
        self.assertNotIn("stale", self.ok(self.check()).stderr)

    def test_S29_only_the_latest_change_for_the_field_is_held_to_the_rules(self):
        self.evidence()
        self.ok(self.state("supported", {"evidence": ["E-a1-1"]}))
        self.evidence("E-a1-2", direction="against")
        self.ok(self.ask({"type": "item", "item": "P1"}))
        self.ok(self.state("waiting for you", {"reasoning": "Both sides have evidence."}))
        self.assertNotIn("stale", self.ok(self.check()).stderr)

    def test_S29_a_latest_change_whose_cited_evidence_no_longer_counts_is_stale(self):
        self.evidence()
        self.ok(self.state("supported", {"evidence": ["E-a1-1"]}))
        self.evidence("E-a1-1", status="removed")
        self.assertIn("P1's state is stale: add a change", self.ok(self.check()).stderr)

    def test_S29_an_importance_change_is_stale_when_its_evidence_no_longer_counts(self):
        self.evidence()
        done = self.add(
            "change",
            R.record(R.CHANGE, field="importance", to="high", cause={"evidence": ["E-a1-1"]}, **{"from": None}),
        )
        self.ok(done)
        self.evidence("E-a1-1", status="removed")
        self.assertIn("P1's importance is stale: add a change", self.ok(self.check()).stderr)

    def test_S29_stale_items_is_the_one_rule_check_and_brief_both_use(self):
        self.evidence()
        self.ok(self.state("supported", {"evidence": ["E-a1-1"]}))
        self.assertEqual(rules.stale_items(self.as_unit()), {})
        self.evidence("E-a1-1", status="removed")
        found = rules.stale_items(self.as_unit())
        self.assertEqual(list(found), ["P1"])
        self.assertIn("latest state change (supported) no longer holds", found["P1"])
        self.assertIn("E-a1-1", found["P1"])

    def test_S29_a_cited_evidence_that_is_not_in_the_unit_is_stale_too(self):
        self.evidence()
        self.ok(self.state("supported", {"evidence": ["E-a1-1"]}))
        (self.unit / "evidence" / "E-a1-1.json").unlink()
        self.assertIn("E-a1-1 is not in evidence/", rules.stale_items(self.as_unit())["P1"])


class Writers(Unit):
    def test_S31_only_the_coordinator_adds_items_changes_options_moves_briefs_and_decisions(self):
        cases = {
            "item": item("P2"),
            "change": R.record(R.CHANGE, field="importance", to="high", cause={"reasoning": "x"}),
            "option": R.OPTION,
            "move": R.MOVE,
            "brief": R.BRIEF,
            "decision": R.DECISION,
        }
        for kind, record in cases.items():
            with self.subTest(kind):
                self.refused(
                    self.add(kind, record, by="analyst-1"),
                    f"only {R.COORD} (discover.json coordinator) writes {kind}: use --by {R.COORD}",
                )

    def test_S31_nothing_is_written_when_the_writer_is_refused(self):
        self.add("decision", R.DECISION, by="analyst-1")
        self.assertEqual(self.lines("decisions.jsonl"), [])

    def test_S31_the_coordinator_may_add_each_of_them(self):
        self.ok(self.add("option", R.OPTION))
        self.ok(self.add("decision", R.DECISION))
        self.ok(self.add("move", R.MOVE))

    def test_S31_a_set_on_an_item_option_or_decision_by_another_agent_is_refused(self):
        self.ok(self.add("option", R.OPTION))
        self.ok(self.add("decision", R.DECISION))
        for ref, fields in (("P1", {"text": "x"}), ("K1", {"text": "x"}), ("D1", {"default": "No"})):
            with self.subTest(ref):
                self.refused(self.set(ref, fields, by="analyst-1"), "only coord (discover.json coordinator) writes")

    def test_S31_a_set_without_by_is_refused_with_the_next_action(self):
        self.refused(self.set("P1", {"text": "x"}, by=None), "use --by coord")
        self.assertEqual(self.lines("items.jsonl")[0]["text"], R.ITEM["text"])

    def test_S31_a_head_with_no_coordinator_refuses_every_coordinator_write(self):
        head = json.loads((self.unit / "discover.json").read_text())
        del head["coordinator"]
        (self.unit / "discover.json").write_text(json.dumps(head))
        text = "discover.json names no coordinator: fix discover.json, then run again"
        self.refused(self.add("decision", R.DECISION), text)
        self.refused(self.set("P1", {"text": "x"}), text)
        self.assertEqual(self.lines("decisions.jsonl"), [])

    def test_S31_a_head_that_does_not_parse_refuses_every_coordinator_write(self):
        (self.unit / "discover.json").write_text("{")
        self.refused(self.add("decision", R.DECISION), "discover.json names no coordinator")

    def test_S31_a_set_on_another_record_type_needs_no_coordinator(self):
        self.ok(self.add("test", R.TEST))
        self.ok(self.set("X1", {"cost": "a day"}, by="analyst-1"))
        self.ok(self.set("X1", {"cost": "two days"}, by=None))


class Stamps(Unit):
    def test_S38_a_set_on_an_item_stamps_updated_at(self):
        self.assertNotIn("updated_at", self.lines("items.jsonl")[0])
        self.ok(self.set("P1", {"text": "People lose track of what they checked, again."}))
        self.assertRegex(self.lines("items.jsonl")[0]["updated_at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_S38_a_typed_updated_at_is_replaced_by_the_stamp(self):
        self.ok(self.set("P1", {"text": "x", "updated_at": "2020-01-01T00:00:00Z"}))
        self.assertNotEqual(self.lines("items.jsonl")[0]["updated_at"], "2020-01-01T00:00:00Z")

    def test_S38_a_set_on_an_option_stamps_updated_at(self):
        self.ok(self.add("option", R.OPTION))
        self.assertNotIn("updated_at", self.lines("options.jsonl")[0])
        self.ok(self.set("K1", {"text": "Run the probe first."}))
        self.assertIn("updated_at", self.lines("options.jsonl")[0])

    def test_S38_adding_does_not_stamp_updated_at(self):
        self.ok(self.add("option", R.OPTION))
        self.assertNotIn("updated_at", self.lines("options.jsonl")[0])


class EveryLock(Unit):
    """A locked record stays as it is: every status it may not move to, and every unset of a field it keeps, is refused
    for the coordinator, and the file is the same afterwards."""

    def reach(self, status):
        """Put test X1 in `status` by allowed steps."""
        if status == "planned":
            return
        if status == "running":
            self.ok(self.set("X1", {"status": "running"}))
        elif status == "done":
            result = {"text": "Three of five found it.", "outcome": "holds", "evidence": [self.evidence()]}
            self.ok(self.set("X1", {"status": "done", "result": result}))
        else:
            self.ok(self.set("X1", {"status": "removed", "reason": "Too slow."}))

    def target(self, status, old):
        """A patch and unsets that are valid for a test in `status`, coming from `old`."""
        if status == "done":
            result = {"text": "Again.", "outcome": "holds", "evidence": ["E-a1-1"]}
            return {"status": "done", "result": result}, ["reason"] if old == "removed" else []
        if status == "removed":
            return {"status": "removed", "reason": "Another reason."}, ["result"] if old == "done" else []
        return {"status": status}, [
            x for x in ("result", "reason") if (old, x) in (("done", "result"), ("removed", "reason"))
        ]

    def untouched(self, name, attempt, *words):
        before = (self.unit / name).read_text()
        text = self.refused(attempt, *words)
        self.assertEqual((self.unit / name).read_text(), before, text)

    def test_a_test_goes_planned_running_done_and_any_to_removed_and_never_back(self):
        disallowed = {
            "running": ["planned"],
            "done": ["planned", "running"],
            "removed": ["planned", "running", "done"],
        }
        for old, news in disallowed.items():
            for new in news:
                with self.subTest(old=old, new=new):
                    self.setUp()
                    self.ok(self.add("test", R.TEST))
                    self.reach(old)
                    patch, unset = self.target(new, old)
                    self.untouched(
                        "tests.jsonl",
                        self.set("X1", patch, unset=unset),
                        "X1",
                        "add a new test and remove X1 with a reason",
                    )

    def test_a_test_that_is_not_planned_keeps_what_rule_and_settles_even_when_unset(self):
        for old in ("running", "done", "removed"):
            for name in ("what", "rule", "settles"):
                with self.subTest(old=old, field=name):
                    self.setUp()
                    self.ok(self.add("test", R.TEST))
                    self.reach(old)
                    self.untouched(
                        "tests.jsonl",
                        self.set("X1", {}, unset=[name]),
                        "add a new test and remove X1 with a reason",
                    )
                    self.untouched(
                        "tests.jsonl",
                        self.set("X1", {name: None}),
                        "add a new test and remove X1 with a reason",
                    )

    def test_an_answered_decision_never_leaves_answered_and_keeps_its_fields_even_when_unset(self):
        self.ok(self.ask({"type": "item", "item": "P1"}))
        self.answer_chat("D1")
        attempts = [
            ({"status": "waiting"}, ["answer", "answered_at"]),
            ({"status": "waiting"}, []),
            ({}, ["status"]),
            ({}, ["about"]),
            ({}, ["answer"]),
            ({}, ["answered_at"]),
            ({"about": None}, []),
            ({"answer": None}, []),
            ({"answered_at": None}, []),
            ({"answered_at": "2020-01-01T00:00:00Z"}, []),
            ({"about": {"type": "discovery"}}, []),
        ]
        for patch, unset in attempts:
            with self.subTest(patch=patch, unset=unset):
                self.untouched("decisions.jsonl", self.set("D1", patch, unset=unset), "D1", "ask a new question")

    def test_a_waiting_decision_cannot_lose_its_status(self):
        self.ok(self.ask({"type": "item", "item": "P1"}))
        self.untouched("decisions.jsonl", self.set("D1", {}, unset=["status"]), "D1", "ask a new question")

    def test_a_cited_risk_stays_even_when_the_risks_are_unset_or_nulled(self):
        self.ok(self.ask_risk("R1"))
        self.untouched("items.jsonl", self.set("P1", {}, unset=["risks"]), "R1")
        self.untouched("items.jsonl", self.set("P1", {"risks": None}), "R1")

    def test_a_move_and_a_change_are_never_edited_even_when_a_field_is_unset(self):
        self.ok(self.add("option", R.OPTION))
        self.ok(self.add("move", R.MOVE))
        self.untouched("moves.jsonl", self.set("M1", {}, unset=["why"]), "M1")
        self.untouched("moves.jsonl", self.set("M1", {"why": None}), "M1")

    def test_a_writer_that_is_not_the_coordinator_changes_nothing(self):
        self.ok(self.ask({"type": "item", "item": "P1"}))
        self.untouched("decisions.jsonl", self.set("D1", {}, by="analyst-1", unset=["default"]), "only coord")
        self.untouched("decisions.jsonl", self.set("D1", {}, by=None, unset=["default"]), "use --by coord")


class TestLock(Unit):
    def setUp(self):
        super().setUp()
        self.ok(self.add("test", R.TEST))

    def test_S61_a_planned_test_can_change_what_rule_and_settles(self):
        self.ok(self.set("X1", {"what": "Ask six people.", "rule": "Stop if none succeed.", "settles": ["P1"]}))

    def test_S61_a_test_that_is_not_planned_keeps_its_what_rule_and_settles(self):
        self.ok(self.set("X1", {"status": "running"}))
        for field, value in (("what", "Ask six people."), ("rule", "Stop if none succeed."), ("settles", [])):
            with self.subTest(field):
                self.refused(self.set("X1", {field: value}), "add a new test and remove X1 with a reason")
        self.assertEqual(self.lines("tests.jsonl")[0]["what"], R.TEST["what"])

    def test_S61_a_done_or_removed_test_keeps_them_too(self):
        evidence = self.evidence()
        done = {
            "status": "done",
            "result": {"text": "Three of five found it.", "outcome": "holds", "evidence": [evidence]},
        }
        self.ok(self.set("X1", done))
        self.refused(self.set("X1", {"what": "x"}), "add a new test and remove X1 with a reason")
        self.ok(self.add("test", R.record(R.TEST, id="X2")))
        self.ok(self.set("X2", {"status": "removed", "reason": "Too slow."}))
        self.refused(self.set("X2", {"rule": "x"}), "add a new test and remove X2 with a reason")

    def test_S61_what_is_not_locked_can_change_and_the_same_value_is_not_a_change(self):
        self.ok(self.set("X1", {"status": "running"}))
        self.ok(self.set("X1", {"cost": "a day", "what": R.TEST["what"], "settles": ["P1"]}))
        self.ok(self.set("X1", {"checker": "analyst-1", "since": R.AT}))


if __name__ == "__main__":
    unittest.main()
