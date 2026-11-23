"""discover-better: what an item is, derived from the records and never copied (T6).

The one function `derive.derive` is what the page, `check`, `summary` and `brief` import. Run with
`python3 tests/run.py test_discover_derive`.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))
import discover_records as R  # noqa: E402
from better_ai.discover import derive  # noqa: E402


def item(ident="P1", risks=()):
    return R.record(R.ITEM, id=ident, risks=[{"id": r, "kind": "value", "text": f"risk {r}"} for r in risks])


def state(to, ident="P1"):
    return R.record(R.CHANGE, about={"type": "item", "item": ident}, to=to)


def importance(to, ident="P1"):
    return R.record(R.CHANGE, about={"type": "item", "item": ident}, field="importance", to=to)


def accept(risk, ident="P1"):
    return R.record(R.RISK_CHANGE, about={"type": "item", "item": ident}, risk=risk)


def one(items, changes=(), moves=(), ident="P1"):
    return derive.derive(items, changes, moves).items[ident]


class State(unittest.TestCase):
    def test_S23_an_item_with_no_state_change_is_unverified(self):
        view = one([item()])
        self.assertEqual(view.state, "unverified")
        self.assertEqual(view.recorded_state, "unverified")

    def test_S23_the_state_is_the_to_of_the_last_state_change(self):
        changes = [state("checking"), state("supported"), state("contradicted")]
        self.assertEqual(one([item()], changes).state, "contradicted")
        self.assertEqual(one([item()], changes[:2]).state, "supported")

    def test_S23_importance_is_the_to_of_the_last_importance_change_and_none_before_the_first(self):
        self.assertIsNone(one([item()]).importance)
        self.assertEqual(one([item()], [importance("high")]).importance, "high")
        self.assertEqual(one([item()], [importance("high"), importance("lower")]).importance, "lower")

    def test_S23_a_change_of_another_field_or_item_does_not_count(self):
        changes = [
            state("supported", "P2"),
            importance("high"),
            R.record(R.CHANGE, about={"type": "discovery"}, field="appetite", to="a month"),
        ]
        view = one([item(), item("P2")], changes)
        self.assertEqual((view.state, view.importance), ("unverified", "high"))

    def test_S23_each_item_has_its_own_state(self):
        derived = derive.derive([item("P1"), item("P2")], [state("supported", "P1"), state("checking", "P2")], [])
        self.assertEqual({k: v.state for k, v in derived.items.items()}, {"P1": "supported", "P2": "checking"})

    def test_S23_the_order_of_the_log_decides_not_the_time(self):
        early = R.record(state("supported"), at="2026-11-23T12:00:00Z")
        late = R.record(state("checking"), at="2026-11-23T09:00:00Z")
        self.assertEqual(one([item()], [early, late]).state, "checking")

    def test_the_inputs_are_not_changed(self):
        items, changes = [item(risks=["R1"])], [state("supported"), accept("R1")]
        before = json.dumps([items, changes])
        derive.derive(items, changes, [])
        self.assertEqual(json.dumps([items, changes]), before)


class RiskAccepted(unittest.TestCase):
    def test_S3_an_item_with_no_risk_is_never_risk_accepted(self):
        view = one([item(risks=[])], [state("needs a test")])
        self.assertFalse(view.risk_accepted)
        self.assertEqual(view.state, "needs a test")

    def test_S3_an_item_with_some_risks_accepted_is_not(self):
        view = one([item(risks=["R1", "R2"])], [state("needs a test"), accept("R1")])
        self.assertFalse(view.risk_accepted)
        self.assertEqual(view.state, "needs a test")
        self.assertEqual((view.accepted_risks, view.open_risks), (("R1",), ("R2",)))

    def test_S3_an_item_with_every_risk_accepted_shows_risk_accepted(self):
        view = one([item(risks=["R1", "R2"])], [state("needs a test"), accept("R1"), accept("R2")])
        self.assertTrue(view.risk_accepted)
        self.assertEqual(view.state, "risk accepted")
        self.assertEqual(view.recorded_state, "needs a test")
        self.assertEqual((view.accepted_risks, view.open_risks), (("R1", "R2"), ()))

    def test_S3_a_risk_change_of_another_item_or_an_unknown_risk_does_not_count(self):
        changes = [accept("R1", "P2"), accept("R9")]
        view = one([item(risks=["R1"]), item("P2", risks=["R1"])], changes)
        self.assertFalse(view.risk_accepted)
        self.assertEqual(view.open_risks, ("R1",))

    def test_S3_a_risk_accepted_twice_counts_once(self):
        view = one([item(risks=["R1", "R2"])], [accept("R1"), accept("R1")])
        self.assertFalse(view.risk_accepted)

    def test_S3_risk_accepted_is_derived_never_read_from_a_state_change(self):
        # a log that holds `to: risk accepted` as a state (check refuses it) does not make the item risk accepted
        bad = R.record(R.CHANGE, to="risk accepted")
        view = one([item(risks=["R1"])], [bad])
        self.assertFalse(view.risk_accepted)
        self.assertEqual(view.state, "unverified")


class Options(unittest.TestCase):
    def moves(self, *options):
        return [R.record(R.MOVE, id=f"M{n}", option=o) for n, o in enumerate(options, 1)]

    def test_the_chosen_option_comes_from_the_last_move(self):
        self.assertIsNone(derive.derive([], [], []).chosen)
        self.assertEqual(derive.derive([], [], self.moves("K1")).chosen, "K1")
        self.assertEqual(derive.derive([], [], self.moves("K1", "K3", "K2")).chosen, "K2")

    def test_the_move_of_each_option_is_listed(self):
        derived = derive.derive([], [], self.moves("K1", "K2", "K1"))
        self.assertEqual(derived.moves_by_option, {"K1": ("M1", "M3"), "K2": ("M2",)})


class Folder(unittest.TestCase):
    def test_a_folder_is_read_by_the_same_function(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "items.jsonl").write_text(json.dumps(item(risks=["R1"])) + "\n")
            (folder / "changes.jsonl").write_text(
                json.dumps(state("supported")) + "\n" + json.dumps(accept("R1")) + "\n"
            )
            (folder / "moves.jsonl").write_text(json.dumps(R.MOVE) + "\n")
            derived = derive.derive_folder(folder)
            self.assertEqual(derived.items["P1"].state, "risk accepted")
            self.assertEqual(derived.chosen, "K1")

    def test_a_missing_file_or_a_broken_line_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            self.assertEqual(derive.derive_folder(folder).items, {})
            (folder / "items.jsonl").write_text("not json\n" + json.dumps(item()) + "\n\n")
            self.assertEqual(list(derive.derive_folder(folder).items), ["P1"])


if __name__ == "__main__":
    unittest.main()
