"""A discovery with every kind of record in place, for the tests of the verbs that read or edit them.

`populated(root)` makes a unit with `create`, then writes the records straight into its files, so a test does not
depend on the rules that guard `add`: the verbs under test read the files as they are.
"""

import json
from pathlib import Path

import discover_records as R

QUOTE = "We lost a week to this."
GIVEN = "I lost a week to this, and Dana from payments did too."
EVENT_TEXT = "A teammate said they lost a week."


def write_json(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def write_lines(path: Path, records: list[dict]) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")


def set_setting(unit: Path, setting: str) -> None:
    head = json.loads((unit / "discover.json").read_text())
    head["setting"] = setting
    write_json(unit / "discover.json", head)


def populated(root: Path, *, setting: str = "external", users: bool = True) -> Path:
    """A unit whose item P1 is supported by E-a1-1 (a web quote that counts) and, with `users`, by E-coord-1 (what the
    user typed in the chat) and E-coord-2 (what the user gave on the page, held in a conversation event)."""
    unit = R.made_unit(root)
    set_setting(unit, setting)
    items = [
        R.ITEM,
        R.record(R.BEHAVIOUR, rests_on=["P1"]),
    ]
    write_lines(unit / "items.jsonl", items)
    cites = ["E-a1-1"] + (["E-coord-1", "E-coord-2"] if users else [])
    write_lines(
        unit / "changes.jsonl",
        [R.record(R.CHANGE, cause={"evidence": cites}), R.record(R.RISK_CHANGE)],
    )
    write_lines(unit / "options.jsonl", [R.record(R.OPTION, move="shrink")])
    write_lines(unit / "moves.jsonl", [R.MOVE])
    write_lines(unit / "tests.jsonl", [R.TEST])
    write_lines(
        unit / "briefs.jsonl",
        [
            R.record(
                R.BRIEF,
                decision="Test first, with a probe.",
                why="The probe is the cheapest way to settle P1.",
                questions=["Who owns the probe?"],
            )
        ],
    )
    write_lines(
        unit / "decisions.jsonl",
        [
            R.record(
                R.DECISION,
                about={"type": "risk", "item": "P1", "risk": "R1"},
                default="Accept the risk",
                status="answered",
                answer={"type": "chat", "text": "Yes, run the probe."},
                answered_at=R.AT,
            )
        ],
    )
    write_json(unit / "sources" / "S-a1-1.json", R.SOURCE)
    write_json(unit / "evidence" / "E-a1-1.json", R.record(R.COUNTING, about="elsewhere"))
    if users:
        write_json(
            unit / "sources" / "S-coord-1.json",
            R.record(
                R.YOU_SOURCE,
                origin={"type": "you", "given": {"type": "chat", "text": GIVEN}},
                said_by_role="a teammate on payments",
            ),
        )
        write_json(
            unit / "evidence" / "E-coord-1.json",
            R.record(
                R.EVIDENCE,
                id="E-coord-1",
                source="S-coord-1",
                words={"type": "quote", "text": GIVEN},
                summary="a teammate on payments lost a week",
                status="counts",
            ),
        )
        write_json(
            unit / "sources" / "S-coord-2.json",
            R.record(
                R.YOU_SOURCE,
                id="S-coord-2",
                origin={"type": "you", "given": {"type": "page", "event": "a1"}},
                said_by_role="a teammate on payments",
            ),
        )
        write_json(
            unit / "evidence" / "E-coord-2.json",
            R.record(
                R.EVIDENCE,
                id="E-coord-2",
                source="S-coord-2",
                words={"type": "event", "event": "a1"},
                summary="a teammate lost a week",
                status="counts",
            ),
        )
        write_lines(
            unit / "conversation.jsonl",
            [R.event("add_evidence", text=EVENT_TEXT, source="Dana, in the hallway")],
        )
        for name in ("E-coord-1", "E-coord-2"):  # a user's own evidence counts at once: no verifier fields
            path = unit / "evidence" / f"{name}.json"
            record = json.loads(path.read_text())
            for key in ("verifier", "checked_read", "span", "sha256"):
                record.pop(key, None)
            write_json(path, record)
    return unit


def files_under(unit: Path) -> dict[str, bytes]:
    """Every file of the unit by relative name, for a test that shows nothing was written or two runs agree. The head
    is left out: `create` stamps it with the clock."""
    return {
        str(p.relative_to(unit)): p.read_bytes()
        for p in sorted(unit.rglob("*"))
        if p.is_file() and p.name != "discover.json"
    }
