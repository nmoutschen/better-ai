"""discover-better: the world and the harness of the cross-record matrix (T14), used by `test_discover_integration*`.

`World` is a discovery that holds one valid, fully filled record of every type in every status. The matrix tries, on a
copy of it, every way to change every field of every record: `add` of a filled record, and `set` with a new value, with
null and with `--unset`, as the coordinator, an analyst, a verifier and with no `--by`. Three things are asserted for
each attempt:

1. the stated rules (STATED below) hold: what they refuse is refused;
2. a refused write leaves every file of the unit byte for byte as it was;
3. a write that is accepted leaves a unit that `check` accepts, and the record keeps its `type`, `at`, `by` and `id`.

The rules are written out here again, from the design and the schemas, and not read from the code under test.
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
import discover_populated as P  # noqa: E402
import discover_records as R  # noqa: E402

UNIT = ".discover/d"
COORD, ANALYST, VERIFIER = R.COORD, "a1", "v1"
WRITERS = {"coordinator": COORD, "analyst": ANALYST, "verifier": VERIFIER, "nobody": None}
STAMPED = ("type", "at", "by", "id")
AT2 = "2026-11-24T10:00:00Z"
COORDINATOR_ONLY = ("item", "change", "option", "move", "brief", "decision", "test")


# ---------------------------------------------------------------- the world


def build(root: Path) -> Path:
    """A discovery with every record type, each in every status, and `check` accepts it."""
    unit = R.made_unit(root)
    head = json.loads((unit / "discover.json").read_text())
    head["brought"] = "Some notes."
    head["handed"] = {"brief": "brief/v1.md", "to": "design-better", "at": R.AT}
    P.write_json(unit / "discover.json", head)
    problem = R.record(
        R.ITEM,
        risks=[
            {"id": "R1", "kind": "value", "text": "Nobody pays."},
            {"id": "R2", "kind": "feasibility", "text": "Too slow."},
        ],
        alternative=None,
        checker=ANALYST,
        since=R.AT,
        tries=[ANALYST],
        updated_at=R.AT,
    )
    behaviour = R.record(R.BEHAVIOUR, rests_on=["P1"], ambiguity="Which page?", updated_at=R.AT)
    P.write_lines(unit / "items.jsonl", [problem, behaviour])
    P.write_lines(unit / "options.jsonl", [R.record(R.OPTION, move="shrink", updated_at=R.AT)])
    P.write_lines(unit / "moves.jsonl", [R.MOVE])
    text = b"# Brief v1\n"
    (unit / "brief").mkdir()
    (unit / "brief" / "v1.md").write_bytes(text)
    final = R.record(
        R.BRIEF,
        status="final",
        decision="Shrink.",
        why="Cheaper.",
        questions=["Who?"],
        file="brief/v1.md",
        sha256=hashlib.sha256(text).hexdigest(),
        redacted=["a" * 64],
    )
    draft = R.record(R.BRIEF, id="v2", decision="Shrink.", why="Cheaper.", questions=["Who?"])
    P.write_lines(unit / "briefs.jsonl", [final, draft])
    answered = R.record(
        R.DECISION,
        about={"type": "risk", "item": "P1", "risk": "R1"},
        default="Accept the risk",
        status="answered",
        answer={"type": "chat", "text": "Yes."},
        answered_at=R.AT,
    )
    waiting = R.record(
        R.DECISION, id="D2", about={"type": "item", "item": "B1"}, asked="Which page?", default="The first"
    )
    P.write_lines(unit / "decisions.jsonl", [answered, waiting])
    P.write_lines(unit / "changes.jsonl", [R.record(R.CHANGE, cause={"evidence": ["E-a1-1"]}), R.RISK_CHANGE])
    result = {"text": "Three of five.", "outcome": "holds", "evidence": ["E-a1-1"]}
    P.write_lines(
        unit / "tests.jsonl",
        [
            R.record(R.TEST, checker=ANALYST, since=R.AT),
            R.record(R.TEST, id="X2", status="running", checker=ANALYST, since=R.AT),
            R.record(R.TEST, id="X3", status="done", result=result),
            R.record(R.TEST, id="X4", status="removed", reason="Not needed."),
        ],
    )
    P.write_json(unit / "sources" / "S-a1-1.json", R.record(R.SOURCE, by=ANALYST))
    P.write_json(unit / "sources" / "S-coord-1.json", R.record(R.YOU_SOURCE, said_by_role="a teammate"))

    def evidence(number, words, **fields):
        return R.record(
            R.EVIDENCE, id=f"E-a1-{number}", by=ANALYST, words={"type": "quote", "text": words}, summary="s", **fields
        )

    shown = {
        1: ("Alpha was slow.", dict(status="counts", verifier=VERIFIER, tries=[VERIFIER], checked_read="raw")),
        2: ("Bravo was slow.", dict(status="checking", verifier=VERIFIER, tries=[VERIFIER], since=R.AT)),
        3: ("Charlie was slow.", dict(status="unverified", verifier=VERIFIER, tries=[VERIFIER], reason="No read.")),
        4: ("Delta was slow.", dict(status="not reachable", verifier=VERIFIER, tries=[VERIFIER], reason="Timeout.")),
        5: ("Echo was slow.", dict(status="removed", reason="Wrong person.")),
    }
    for number, (words, fields) in shown.items():
        if fields["status"] == "counts":
            fields = {**fields, "span": words, "sha256": "a" * 64}
        P.write_json(unit / "evidence" / f"E-a1-{number}.json", evidence(number, words, **fields))
    you = R.record(
        R.EVIDENCE,
        id="E-coord-1",
        source="S-coord-1",
        words={"type": "quote", "text": "Foxtrot lost a week."},
        summary="s",
        status="counts",
    )
    P.write_json(unit / "evidence" / "E-coord-1.json", you)
    return unit


def files_of(unit: Path) -> dict[str, bytes]:
    return {str(p.relative_to(unit)): p.read_bytes() for p in sorted(unit.rglob("*")) if p.is_file()}


def restore(unit: Path, before: dict[str, bytes]) -> None:
    for path in sorted(unit.rglob("*")):
        if path.is_file() and str(path.relative_to(unit)) not in before:
            path.unlink()
    for name, data in before.items():
        path = unit / name
        if not path.is_file() or path.read_bytes() != data:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)


def records_of(unit: Path) -> list[tuple[str, dict]]:
    """Every record of the unit with the ref `set` takes: its id, or `discover` for the head."""
    found = [("discover", json.loads((unit / "discover.json").read_text()))]
    for name in ("items", "options", "moves", "briefs", "decisions", "tests", "changes"):
        for line in (unit / f"{name}.jsonl").read_text().splitlines():
            record = json.loads(line)
            found.append((record.get("id") or "change", record))
    for folder in ("sources", "evidence"):
        for path in sorted((unit / folder).glob("*.json")):
            record = json.loads(path.read_text())
            found.append((record["id"], record))
    return found


# ---------------------------------------------------------------- what the rules say, written out again

STATUS_FORWARD = {"planned": ("running", "done", "removed"), "running": ("done", "removed"), "done": ("removed",)}


def alternatives(kind: str, record: dict, field: str) -> list[dict]:
    """New values for the field, as the patches a writer would send: one that is valid, and where a rule is about the
    field, one the rule is about."""
    value = record[field]
    status = record.get("status")
    table: dict[tuple[str, str], list[dict]] = {
        ("test", "status"): [{"status": s} for s in ("planned", "running", "removed") if s != status]
        + ([{"status": "removed", "reason": "Not needed."}] if status != "removed" else []),
        ("test", "settles"): [{"settles": ["B1"]}],
        ("test", "result"): [{"result": {"text": "Four of five.", "outcome": "changes", "evidence": ["E-a1-1"]}}],
        ("test", "reason"): [{"reason": "Another reason."}],
        ("decision", "about"): [{"about": {"type": "item", "item": "P1"}}],
        ("decision", "answer"): [{"answer": {"type": "chat", "text": "No."}}],
        ("decision", "answered_at"): [{"answered_at": AT2}],
        ("decision", "status"): (
            [{"status": "answered", "answer": {"type": "chat", "text": "Ok."}}]
            if status == "waiting"
            else [{"status": "waiting"}]
        ),
        ("decision", "default"): [{"default": "Another"}],
        ("brief", "status"): [{"status": "draft" if status == "final" else "final"}],
        ("brief", "file"): [{"file": "brief/v9.md"}],
        ("brief", "sha256"): [{"sha256": "b" * 64}],
        ("brief", "redacted"): [{"redacted": ["b" * 64]}],
        ("brief", "move"): [{"move": "M1"}],
        ("item", "risks"): [{"risks": [{"id": "R1", "kind": "value", "text": "Changed."}]}, {"risks": []}],
        ("item", "kind"): [{"kind": "problem"}],
        ("option", "move"): [{"move": "expand"}],
        ("option", "note"): [{"note": "ruled out by your appetite"}],
        ("source", "origin"): [{"origin": {"type": "web", "url": "https://example.org/other", "read": "raw"}}],
        ("discover", "coordinator"): [{"coordinator": "another"}],
        ("discover", "setting"): [{"setting": "internal"}],
        ("discover", "status"): [{"status": "finished"}],
        ("discover", "step"): [{"step": "2"}],
        ("discover", "handed"): [{"handed": {"brief": "brief/v2.md", "to": "design-better", "at": R.AT}}],
        ("evidence", "status"): [{"status": s, "reason": "No."} for s in ("unverified", "removed") if s != status]
        + [{"status": "checking", "verifier": "v2"}],
        ("evidence", "kind"): [{"kind": "did"}],
        ("evidence", "about"): [{"about": "elsewhere"}],
        ("evidence", "bears_on"): [{"bears_on": [{"item": "B1", "direction": "for"}]}],
        ("evidence", "source"): [{"source": "S-coord-1" if record.get("source") == "S-a1-1" else "S-a1-1"}],
        ("evidence", "words"): [{"words": {"type": "quote", "text": "Golf was slow."}}],
        ("evidence", "verifier"): [{"verifier": "v2"}],
        ("evidence", "tries"): [{"tries": ["v1", "v2"]}],
        ("evidence", "since"): [{"since": AT2}],
        ("evidence", "reason"): [{"reason": "Another reason."}],
        ("evidence", "checked_read"): [{"checked_read": "raw"}],
    }
    if (kind, field) in table:
        return table[(kind, field)]
    if isinstance(value, str):
        return [{field: value + " more"}]
    if isinstance(value, list):
        return [{field: []}] if value else [{field: ["x"]}]
    if isinstance(value, dict):
        return [{field: {**value, "text": "more"}}]
    return [{field: "x"}]


def must_be_refused(kind: str, record: dict, op: str, patch: dict, writer: str | None) -> str | None:
    """The rule that refuses this write, or None when the rules do not say it is refused."""
    field = next(iter(patch)) if patch else None
    fields = set(patch)
    status = record.get("status")
    if kind in COORDINATOR_ONLY and writer != COORD:
        return f"only the coordinator writes {kind}"
    if kind == "discover" and "coordinator" in fields:
        return "the coordinator named in the head cannot change"
    if kind in ("change", "move"):
        return f"a {kind} is never edited"
    if kind == "brief":
        if status == "final":
            return "a final brief is never changed by set"
        if fields & {"status", "file", "sha256", "redacted"}:
            return "a draft never gains status, file, sha256 or redacted by set"
    if kind == "test":
        if status != "planned" and fields & {"what", "rule", "settles"}:
            return "a test that is not planned keeps what, rule and settles"
        moved = patch.get("status", status)
        if status != "planned" and moved != status and moved not in STATUS_FORWARD.get(status, ()):
            return "a test's status only moves forward"
    if kind == "decision" and status == "answered":
        if fields & {"about", "answer", "answered_at"}:
            return "an answered decision keeps its about, answer and answered_at"
        if patch.get("status") == "waiting":
            return "an answered decision stays answered"
    kept = any(r.get("id") == "R1" and r.get("text") == "Nobody pays." for r in patch.get("risks") or [])
    if kind == "item" and field == "risks" and record["id"] == "P1" and not kept:
        return "a risk a decision or change cites keeps its id and text"
    if kind == "source":
        if "origin" in fields:
            return "the origin of a source is fixed"
        if op != "patch" and field in record:
            return "nothing of a source is removed"
        if "said_by_role" in fields and writer != COORD:
            return "only the coordinator changes said_by_role"
        if "title" in fields and writer not in (COORD, record["by"]):
            return "only the coordinator or the adder changes the title"
    if kind == "evidence":
        if writer is None:
            return "setting evidence needs --by"
        if op != "patch" and field in record:
            return "nothing of evidence is removed with null or --unset"
        if fields & {"tries", "sha256"}:
            return "tries and sha256 are kept by better.pyz"
        if fields & {"summary", "verifier", "since"} and writer != COORD:
            return "only the coordinator writes summary, verifier and since"
        if fields & {"source", "words", "bears_on", "kind", "about"}:
            if status != "checking":
                return "the words, source, items, kind and about are fixed once checking is over"
            if writer not in (COORD, record["by"]):
                return "only the coordinator or the adder changes them while checking"
        if fields & {"reason", "checked_read", "span"} and "status" not in fields:
            return "reason, checked_read and span are set only with the change of status that holds them"
        if "status" in fields and writer == record["by"] and writer != COORD:
            return "the analyst that added evidence does not change its status"
    return None


def cases(kind: str, record: dict):
    """Every write to try on a record: (op, patch, unset field or None)."""
    for field in record:
        if field in STAMPED:
            continue
        for patch in alternatives(kind, record, field):
            if any(
                record.get(name) != value for name, value in patch.items()
            ):  # a patch that changes nothing is no write
                yield "patch", patch, None
        yield "null", {field: None}, None
        yield "unset", {}, field
    for field in STAMPED:
        yield "patch", {field: {"id": "P9", "at": AT2}.get(field, "x") if field != "type" else "item"}, None


# ---------------------------------------------------------------- the harness


class MatrixCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.unit = build(cls.root)
        done = R.run(cls.root, "check", UNIT)
        assert done.returncode == 0, done.stdout + done.stderr
        cls.start = files_of(cls.unit)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_check(self) -> int:
        return R.run(self.root, "check", UNIT).returncode

    def attempt(self, args, stdin, who):
        full = [*args, *(["--by", who] if who else [])]
        return R.run(self.root, *full, stdin=stdin)

    def judge(self, label, done, before, refused_by, keeps, found) -> None:
        """The three assertions for one attempt; failures are collected in `found`."""
        after = files_of(self.unit)
        if done.returncode != 0:
            if after != before:
                found.append(f"{label}: refused but the files changed")
        else:
            if refused_by:
                found.append(f"{label}: accepted, but {refused_by}")
            if self.run_check() != 0:
                found.append(f"{label}: accepted, and check no longer passes")
            if keeps is not None and not keeps(self.unit):
                found.append(f"{label}: accepted, and the record's type, at, by or id changed")
        if after != before:
            restore(self.unit, before)

    def sets(self, kinds):
        found = []
        before = self.start
        self.accepted = {}
        for ref, record in records_of(self.unit):
            kind = record["type"]
            if kind not in kinds:
                continue
            for op, patch, unset in cases(kind, record):
                for name, who in WRITERS.items():
                    args = ["set", UNIT, ref]
                    if unset:
                        args += ["--unset", unset]
                    label = f"set {kind} {ref} {record.get('status', '')} {op} {patch or unset} as {name}"
                    done = self.attempt(args, json.dumps(patch), who)
                    stamp = {f: record[f] for f in STAMPED if f in record}
                    keeps = (
                        None
                        if kind == "discover" and ref == "discover"
                        else (
                            lambda unit, ref=ref, stamp=stamp: all(
                                r.get(f) == v for i, r in records_of(unit) if i == ref for f, v in stamp.items()
                            )
                        )
                    )
                    if done.returncode == 0 and who == COORD and files_of(self.unit) != before:
                        self.accepted[kind] = self.accepted.get(kind, 0) + 1
                    self.judge(label, done, before, must_be_refused(kind, record, op, patch, who), keeps, found)
        return found

    def matrix(self, kinds, changing):
        """The writes to the records of these kinds; the coordinator still makes some write of each kind that `changing`
        names, so a rule that refuses everything does not pass."""
        self.assertEqual(self.sets(kinds), [])
        for kind in changing:
            self.assertGreater(self.accepted.get(kind, 0), 0, f"the coordinator can change no {kind} at all")
