"""Skill trigger registration and the common page handoff rule."""

import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import discover_records as discovery  # noqa: E402

from better_ai import page  # noqa: E402
from better_ai.code import SKILL as CODE  # noqa: E402
from better_ai.discover import SKILL as DISCOVER  # noqa: E402
from better_ai.paths import Unit  # noqa: E402
from better_ai.research import SKILL as RESEARCH  # noqa: E402

AT = "2026-06-01T12:00:00Z"
WORDING = {
    "architect-better/modes/design.md": "## 2.",
    "code-better/modes/coordinate.md": "## 2. Start the builders",
    "design-better/SKILL.md": "### Show versions on one page",
    "discover-better/SKILL.md": "## General rules",
    "research-better/SKILL.md": "## General rules",
    "show-better/SKILL.md": "## 6. Work with the user in the page",
}


class SkillDrivingTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def unit(self, skill):
        kind = skill.kinds[0]
        return Unit(self.root / kind.folder / "unit", self.root, kind, skill)

    def write(self, unit, relative, *records):
        path = unit.path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")

    def trigger_ids(self, unit):
        return [record["id"] for record in page.spec_of(unit.skill).triggers(unit)]

    def test_code_handbacks_are_stable_and_distinct(self):
        unit = self.unit(CODE)
        self.write(
            unit,
            "logs/builder.card.json",
            {"type": "card", "at": AT, "by": "coordinator", "role": "builder", "task": "T7", "branch": "example"},
        )
        base = {"at": AT, "by": "builder", "text": "D12 handed_back"}
        step = {**base, "type": "step"}
        handback = {**base, "type": "handed_back", "result": "done"}
        invalid = {**handback, "result": "unknown"}
        self.write(unit, "logs/builder.jsonl", step, handback, invalid, handback)
        ids = ["logs/builder.jsonl:2", "logs/builder.jsonl:4"]
        self.assertEqual(self.trigger_ids(unit), ids)
        self.write(unit, "logs/builder.jsonl", step, handback, invalid, handback, step)
        self.assertEqual(self.trigger_ids(unit), ids)

    def test_research_stop_and_checked_wake_but_strategy_does_not(self):
        unit = self.unit(RESEARCH)
        self.write(unit, "claims/C-verifier-1.json", {"type": "claim", "id": "C-verifier-1"})
        base = {"at": AT, "by": "worker"}
        self.write(
            unit,
            "logs/worker.jsonl",
            {**base, "type": "strategy", "text": "stop checked"},
            {**base, "type": "stop", "text": "Finished"},
            {**base, "type": "checked", "claim": "C-verifier-1"},
            {**base, "type": "checked", "claim": "C-verifier-12"},
        )
        self.assertEqual(self.trigger_ids(unit), ["logs/worker.jsonl:2", "logs/worker.jsonl:3"])

    def test_discovery_uses_the_evidence_id_once_across_updates(self):
        unit = self.unit(DISCOVER)
        self.write(unit, "discover.json", {"coordinator": discovery.COORD})
        self.write(unit, "items.jsonl", discovery.ITEM)
        self.write(unit, "sources/S-a1-1.json", discovery.SOURCE)
        self.write(unit, "sources/S-coord-1.json", discovery.YOU_SOURCE)
        evidence = {**discovery.EVIDENCE, "by": "a1"}
        self.write(unit, "evidence/E-a1-1.json", evidence)
        self.write(
            unit,
            "evidence/E-coord-1.json",
            {**discovery.EVIDENCE, "by": discovery.COORD, "id": "E-coord-1", "source": "S-coord-1", "status": "counts"},
        )
        self.write(unit, "evidence/E-a1-12.json", evidence)
        self.assertEqual(self.trigger_ids(unit), ["evidence:E-a1-1"])
        self.write(unit, "evidence/E-a1-1.json", {**evidence, "verifier": "verifier"})
        self.assertEqual(self.trigger_ids(unit), ["evidence:E-a1-1"])

    def test_only_waiting_decisions_wake_at_or_after_the_deadline(self):
        for skill, about in [(CODE, "change"), (RESEARCH, "board")]:
            with self.subTest(skill=skill.name):
                unit = self.unit(skill)
                record = {
                    "type": "decision",
                    "at": AT,
                    "by": "coordinator",
                    "raised_by": "coordinator",
                    "about": {"type": about},
                    "asked": "When to proceed?",
                    "status": "waiting",
                    "default": "Proceed",
                }
                self.write(
                    unit,
                    "decisions.jsonl",
                    {**record, "id": "D1", "deadline": AT},
                    {**record, "id": "D12", "deadline": "2026-06-01T12:00:01Z"},
                    {**record, "id": "D2", "deadline": None, "default": None},
                    {**record, "id": "D3", "deadline": AT, "status": "defaulted"},
                    {**record, "id": "D4", "deadline": "2026-06-01T11:59:59Z"},
                )
                with patch("better_ai.page.triggers.datetime", wraps=datetime) as clock:
                    clock.now.return_value = clock.fromisoformat(AT.replace("Z", "+00:00"))
                    self.assertEqual(self.trigger_ids(unit), ["decision:D1", "decision:D4"])

    def test_all_six_page_rules_are_identical_and_in_the_right_sections(self):
        rules = []
        for name, section in WORDING.items():
            with self.subTest(skill=name):
                text = (ROOT / "skills" / name).read_text(encoding="utf-8")
                blocks = text.split("\n\n")
                matching = [block for block in blocks if "serve <unit> --drive auto" in block]
                self.assertEqual(len(matching), 1)
                block = matching[0]
                self.assertLess(text.index(section), text.index(block))
                self.assertEqual(text.count("STREAM the serve command"), 1)
                rules.append(block)
        self.assertEqual(len(rules), len(WORDING))
        self.assertEqual(len(set(rules)), 1)
        for wording in (
            "hand-off note on stdin",
            "`driver: on`",
            "the page has its own agent",
            "END the turn",
            "`driver: off <kind>`",
            "kind and its action in one line",
            "STREAM the serve command",
            "wait <unit>",
            'say "sent"',
            "30 seconds",
            "`driver: off crashed`",
            "enrollment address",
            "immediately",
            "120 seconds from startup",
            '"ask it in the page"',
            "a session opened by the page",
            "DO NOT run `serve`",
        ):
            self.assertIn(wording, rules[0])

    def test_existing_wait_steps_are_preserved(self):
        architect = (ROOT / "skills/architect-better/modes/design.md").read_text(encoding="utf-8")
        self.assertIn(
            "WAIT for the user's confirmation or correction and APPLY any corrections. DO NOT start step 3 before "
            "the user confirms or corrects Before: HANDLE other actions and START `wait` again;",
            architect,
        )
        discover = (ROOT / "skills/discover-better/SKILL.md").read_text(encoding="utf-8")
        self.assertEqual(discover.count("WAIT for the analysts' and the quote verifiers' hand-backs."), 2)
        research = (ROOT / "skills/research-better/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("WAIT for them, THEN SET the brief's `status` to `stopped`", research)
