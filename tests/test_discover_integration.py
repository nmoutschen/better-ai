"""discover-better: the rules meet where the records do (T14).

Run with `python3 tests/run.py test_discover_integration test_discover_integration_tests test_discover_integration_evidence`.
The world and the matrix are in `discover_matrix`; the three modules split the `set` matrix by record so they run in
parallel. This one holds `add`, the head, the items, options, moves, changes and briefs, and what the page and summary
share.
"""

import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))
import discover_matrix as M  # noqa: E402
import discover_records as R  # noqa: E402
from discover_matrix import ANALYST, COORD, COORDINATOR_ONLY, UNIT, VERIFIER, WRITERS, restore  # noqa: E402

from better_ai import page  # noqa: E402
from better_ai.discover import brief, summary  # noqa: E402


class Matrix(M.MatrixCase):
    def test_set_the_head_items_options_moves_changes_and_briefs(self):
        self.matrix(("item", "option", "move", "change", "brief", "discover"), ("item", "option", "brief", "discover"))

    def filled(self):
        """A new record of each type, every field filled, as the fields an agent gives to `add`."""
        answered = R.record(
            R.DECISION,
            about={"type": "item", "item": "B1"},
            default="Yes",
            status="answered",
            answer={"type": "chat", "text": "Yes."},
            answered_at="2020-01-01T00:00:00Z",
        )
        waiting = R.record(R.DECISION, about={"type": "item", "item": "P1"}, asked="Another question?", default="Yes")
        result = {"text": "Four of five.", "outcome": "holds", "evidence": ["E-a1-1"]}
        item = R.record(R.ITEM, id="P2", checker=ANALYST, since=R.AT, tries=[ANALYST], risks=[], alternative=None)
        new = {
            "item": [item],
            "option": [R.record(R.OPTION, move="shrink", updated_at=R.AT)],
            "move": [R.record(R.MOVE, answer={"type": "chat", "text": "Shrink it."})],
            "change": [R.record(R.CHANGE, field="importance", to="high", cause={"reasoning": "x"}, **{"from": None})],
            "brief": [R.record(R.BRIEF, decision="d", why="w", questions=["q"]), R.record(R.BRIEF, status="final")],
            "decision": [waiting, answered],
            "test": [
                R.record(R.TEST, id="X5", checker=ANALYST, since=R.AT),
                R.record(R.TEST, id="X5", status="running", checker=ANALYST, since=R.AT),
                R.record(R.TEST, id="X5", status="done", result=result),
                R.record(R.TEST, id="X5", status="removed", reason="No."),
            ],
            "source": [
                R.record(R.SOURCE, origin={"type": "web", "url": "https://example.org/a", "read": "raw"}),
                R.record(R.YOU_SOURCE, said_by_role="a teammate"),
            ],
            "evidence": [
                R.record(R.EVIDENCE, source="S-a1-1", words={"type": "quote", "text": "Hotel was slow."}, summary="s"),
                R.record(R.COUNTING, source="S-a1-1", words={"type": "quote", "text": "India was slow."}),
                R.record(
                    R.EVIDENCE, status="removed", source="S-a1-1", reason="x", words={"type": "quote", "text": "J."}
                ),
            ],
        }
        return new

    def test_add_a_filled_record_of_every_type_in_every_status(self):
        found = []
        before = self.start
        for kind, records in self.filled().items():
            for record in records:
                fields = json.dumps(R.without(record, "type", "at", "by", "id"))
                for name, who in WRITERS.items():
                    label = f"add {kind} {record.get('status', '')} as {name}"
                    args = ["add", UNIT, kind] + (["--by", who] if who else [])
                    done = R.run(self.root, *args, stdin=fields)
                    refused = None
                    if kind in COORDINATOR_ONLY and who != COORD:
                        refused = f"only the coordinator writes {kind}"
                    elif who is None:
                        refused = "a record needs --by"
                    elif kind == "evidence" and who == VERIFIER:
                        refused = "evidence is added by the coordinator or the analyst that checks its items"
                    elif kind == "source" and "given" in record.get("origin", {}) and who != COORD:
                        refused = "a source from you is added by the coordinator"
                    elif kind == "brief" and record["status"] == "final":
                        refused = "only the brief verb makes a brief final"
                    self.judge(label, done, before, refused, None, found)
        self.assertEqual(found, [])

    def test_add_an_answered_decision_gets_answered_at_stamped(self):
        answered = self.filled()["decision"][1]
        for given in ("2020-01-01T00:00:00Z", None):
            with self.subTest(answered_at=given):
                fields = R.without(answered, "type", "at", "by", "id", *(["answered_at"] if given is None else []))
                done = R.run(self.root, "add", UNIT, "decision", "--by", COORD, stdin=json.dumps(fields))
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                stored = [json.loads(x) for x in (self.unit / "decisions.jsonl").read_text().splitlines()][-1]
                self.assertNotEqual(stored["answered_at"], "2020-01-01T00:00:00Z")
                self.assertGreaterEqual(stored["answered_at"], R.AT)
                restore(self.unit, self.start)

    def test_the_page_and_summary_share_one_list_of_finished_states(self):
        self.assertIs(summary.FINISHED, page.FINISHED)
        self.assertIs(summary.REDACT_STATE, brief.STATE)


if __name__ == "__main__":
    unittest.main()
