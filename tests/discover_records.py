"""discover-better fixtures shared by its tests: one valid example of every record, and a unit made by `create`."""

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import better  # noqa: E402

SKILL = "discover-better"
AT = "2026-11-23T10:00:00Z"
COORD = "coord"


def stamped(**fields) -> dict:
    return {"at": AT, "by": COORD, **fields}


HEAD = stamped(
    type="discover",
    idea="a page that shows where an idea stands",
    appetite="two weeks of one person",
    setting="external",
    coordinator=COORD,
    step="1",
    status="open",
)

ITEM = stamped(
    type="item",
    id="P1",
    kind="problem",
    text="People lose track of what they checked.",
    rests_on=[],
    risks=[{"id": "R1", "kind": "value", "text": "Nobody would pay to fix it."}],
)
BEHAVIOUR = stamped(
    type="item",
    id="B1",
    kind="behaviour",
    text="Shows the state of each item.",
    rests_on=["P1"],
    risks=[],
    testable={"form": "ears", "text": "When an item changes, the page shall show its new state."},
)

CHANGE = stamped(
    type="change",
    about={"type": "item", "item": "P1"},
    field="state",
    **{"from": "unverified", "to": "supported"},
    cause={"evidence": ["E-a1-1"]},
)
RISK_CHANGE = stamped(
    type="change",
    about={"type": "item", "item": "P1"},
    field="risk",
    risk="R1",
    **{"from": "open", "to": "accepted"},
    cause={"answer": {"type": "decision", "id": "D1"}},
)

SOURCE = stamped(
    type="source",
    id="S-a1-1",
    origin={"type": "web", "url": "https://example.com/post", "read": "raw"},
    title="A post about the problem",
)
YOU_SOURCE = stamped(
    type="source",
    id="S-coord-1",
    origin={"type": "you", "given": {"type": "chat", "text": "I lost a week to this."}},
    title="You, in the chat",
)

EVIDENCE = stamped(
    type="evidence",
    id="E-a1-1",
    source="S-a1-1",
    words={"type": "quote", "text": "We lost a week to this."},
    kind="say",
    about="your users",
    bears_on=[{"item": "P1", "direction": "for"}],
    status="checking",
)
COUNTING = {
    **EVIDENCE,
    "status": "counts",
    "verifier": "v1",
    "checked_read": "raw",
    "span": "We lost a week to this.",
    "sha256": "a" * 64,
}

TEST = stamped(
    type="test",
    id="X1",
    what="Ask five people to find a past check.",
    kind="probe",
    settles=["P1"],
    cost="an afternoon",
    rule="Stop if fewer than two of five succeed.",
    runner="you",
    status="planned",
)
OPTION = stamped(
    type="option",
    id="K1",
    move="test first",
    text="Run the probe before building.",
    cost="an afternoon",
    speed="a day",
    upkeep="none",
    undo="nothing to undo",
    note="proposed",
)
MOVE = stamped(
    type="move",
    id="M1",
    option="K1",
    step="5",
    why="The probe is the cheapest way to settle P1.",
    answer={"type": "chat", "text": "Yes, run the probe."},
)
BRIEF = stamped(type="brief", id="v1", move="M1", status="draft")
DECISION = stamped(
    type="decision",
    id="D1",
    raised_by=COORD,
    about={"type": "item", "item": "P1"},
    asked="Should the probe come first?",
    status="waiting",
    default="Yes",
)

EVENTS = {
    "choose": {"id": "c1", "option": "K1", "revision": "abc123", "confirmed": False},
    "add_evidence": {
        "id": "a1",
        "text": "A teammate said they lost a week.",
        "source": "a teammate",
        "kind": "say",
        "about": "your users",
        "bears_on": [{"item": "P1", "direction": "for"}],
    },
    "add_result": {"id": "r1", "test": "X1", "text": "Three of five found it.", "outcome": "holds"},
    "remove": {"id": "m1", "record": "E-a1-1", "reason": "Wrong person."},
    "change": {"id": "h1", "record": "P1", "field": "text", "value": "People lose track."},
    "redact": {"id": "d1", "evidence": "E-a1-1"},
}


def event(name: str, **over) -> dict:
    return {"type": name, "at": AT, "by": "user", **copy.deepcopy(EVENTS[name]), **over}


def record(base: dict, **over) -> dict:
    """A copy of `base` with `over` applied; a key set to None is kept as null."""
    return {**copy.deepcopy(base), **copy.deepcopy(over)}


def without(base: dict, *keys: str) -> dict:
    return {k: copy.deepcopy(v) for k, v in base.items() if k not in keys}


def head_fields(**over) -> str:
    """The head as an agent gives it to `create`: its own fields, as JSON on stdin."""
    return json.dumps(without(record(HEAD, **over), "type", "at", "by"))


def make_repo(root: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def run(repo: Path, *args: str, stdin: str | None = None):
    return better.call(SKILL, *args, stdin=stdin, cwd=repo)


def made_unit(root: Path) -> Path:
    """A repository with a discovery made by `create`, as `.discover/d`."""
    make_repo(root)
    done = run(root, "create", ".discover/d", "--by", COORD, stdin=head_fields())
    assert done.returncode == 0, done.stderr
    return root / ".discover" / "d"


def temp_repo() -> tempfile.TemporaryDirectory:
    return tempfile.TemporaryDirectory()
