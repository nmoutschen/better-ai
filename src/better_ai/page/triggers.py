"""Validated skill records that can wake a driven page, and the workers a page agent has started.

A code hand-back is a handed_back entry. A research worker's stop or a verifier's checked entry reports completed
work. Discover evidence and waiting decisions keep their own IDs when their records change. A trigger's id comes from
the fields of its record, never from its place in a file, so a log that is reordered fires nothing again.

A worker runs while its log holds a line after its last end line of the skill. One that
has no new line for LIMIT, or an item left working while no worker runs, gives an overdue trigger. A line that is not JSON, or a file that
cannot be read, gives an unreadable trigger, once.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Iterator
from datetime import datetime, timedelta, timezone

from .. import paths, records, resources, schema
from ..paths import Unit

LIMIT = timedelta(minutes=30)
# The line that ends a worker's log, by skill package. A skill without logs has no workers.
ENDS = {"code": "handed_back", "research": "stop"}
# The errors that mean a line or file could not be read at all; a record that parses but breaks a schema rule is not one.
READ_FAILED = (schema.ROOT, "(file)")


def _files(unit: Unit, folder: str, pattern: str) -> list[str]:
    try:
        return sorted(f"{folder}/{path.name}" for path in unit.target(folder).glob(pattern))
    except (OSError, paths.Refused):
        return []


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:16]


def _read(unit: Unit, files: Iterable[str], now: datetime) -> Iterator[tuple[str, dict | None, dict | None]]:
    """Each record as (file, record, None), and each line that failed its checks as (file, None, error)."""
    docs, cutoff, cache = schema.docs_for(unit.skill.package), resources.cutoff(), {}
    for relative in files:
        read = schema.read_records(unit, relative, docs, cache, now, cutoff)
        for record in read.records:
            yield relative, record, None
        for error in read.errors:
            yield relative, None, error


def _moment(text) -> datetime | None:
    try:
        return datetime.fromisoformat(text.removesuffix("Z") + "+00:00")
    except (AttributeError, ValueError):
        return None


def _due(record: dict, now: datetime) -> bool:
    deadline = record.get("deadline")
    if record["status"] not in ("waiting", "pending") or deadline is None:
        return False
    moment = _moment(deadline)
    return moment is not None and moment <= now


def _unreadable(unit: Unit, relative: str, error: dict) -> dict:
    try:
        text = unit.target(relative).read_text(encoding="utf-8", errors="replace").splitlines()[error["line"] - 1]
    except (OSError, IndexError, paths.Refused):
        text = ""
    return {
        "id": f"unreadable:{relative}:{_digest([text, error['field'], error['message']])}",
        "type": "unreadable",
        "file": relative,
        "line": error["line"],
        "problem": f"{error['field']}: {error['message']}",
    }


def _scan(unit: Unit, files: list[str], kinds: tuple[str, ...], now: datetime) -> Iterator[dict]:
    for relative, record, error in _read(unit, files, now):
        if error is not None:
            if error["field"] in READ_FAILED:
                yield _unreadable(unit, relative, error)
        elif record["type"] in kinds:
            yield {"id": f"{relative}:{_digest(record)}", "type": record["type"], "file": relative}
        elif record["type"] == "decision" and _due(record, now):
            yield {"id": f"decision:{record['id']}", "type": "deadline", "decision": record["id"]}


def _logs_and_decisions(unit: Unit, *kinds: str) -> Iterator[dict]:
    now = datetime.now(timezone.utc)
    yield from _scan(unit, [*_files(unit, "logs", "*.jsonl"), "decisions.jsonl"], kinds, now)
    yield from _overdue(unit, now)


def code(unit: Unit) -> Iterator[dict]:
    return _logs_and_decisions(unit, "handed_back")


def research(unit: Unit) -> Iterator[dict]:
    return _logs_and_decisions(unit, "stop", "checked")


def discover(unit: Unit) -> Iterator[dict]:
    coordinator = records.written_by(unit, "coordinator")
    for relative, record, error in _read(unit, _files(unit, "evidence", "*.json"), datetime.now(timezone.utc)):
        if error is not None:
            if error["field"] in READ_FAILED:
                yield _unreadable(unit, relative, error)
        elif record["type"] == "evidence" and record["by"] not in ("user", coordinator):
            yield {"id": f"evidence:{record['id']}", "type": "evidence", "evidence": record["id"], "file": relative}


# ---------------------------------------------------------------- workers


def _lines(unit: Unit, relative: str) -> list[dict]:
    """The lines of a log that parse, without checking them: a worker row only needs their types and times."""
    try:
        text = unit.target(relative).read_text(encoding="utf-8", errors="replace")
    except (OSError, paths.Refused):
        return []
    found = []
    for line in text.splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            found.append(value)
    return found


def _card_task(unit: Unit, name: str) -> str | None:
    try:
        card = json.loads(unit.target(f"logs/{name}.card.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, paths.Refused):
        return None
    task = card.get("task") if isinstance(card, dict) else None
    return task if isinstance(task, str) else None


def _running(unit: Unit, now: datetime) -> list[tuple[str, datetime | None]]:
    """The workers with a line after their last end line (a worker started again after a hand-back runs again), each
    with the time of the last of those lines."""
    end = ENDS.get(unit.skill.package)
    if end is None:
        return []
    running = []
    for relative in _files(unit, "logs", "*.jsonl"):
        lines = _lines(unit, relative)
        ended = max((n for n, line in enumerate(lines) if line.get("type") == end), default=-1)
        since = lines[ended + 1 :]
        if since:
            last = max((m for m in (_moment(line.get("at")) for line in since) if m), default=None)
            running.append((relative.rsplit("/", 1)[-1].removesuffix(".jsonl"), last))
    return running


def workers(unit: Unit, now: datetime | None = None, limit: timedelta = LIMIT) -> list[dict]:
    """A row for each running worker: {name, item, waiting, silent_min}. `silent_min` is the minutes since its last line
    once that is past `limit`, else None. The driver fills `waiting`."""
    now = now or datetime.now(timezone.utc)
    return [
        {
            "name": name,
            "item": _card_task(unit, name),
            "waiting": False,
            "silent_min": int((now - last).total_seconds() // 60) if last and now - last >= limit else None,
        }
        for name, last in _running(unit, now)
    ]


def _working_items(unit: Unit) -> list[tuple[str, datetime | None]]:
    """The user's items whose state is working, each with the time of its last status event."""
    from . import Conversation, all_items, load_docs, spec_of

    conv = Conversation(unit, spec_of(unit.skill), load_docs(unit.skill))
    events = conv.events()
    at = {e.get("to"): e.get("at") for e in events if e.get("type") == "status"}
    return [
        (item["id"], _moment(at.get(item["id"])))
        for item, state, extra in all_items(events, conv.items, conv.agent)
        if state == "agent" and extra["step"] == "working"
    ]


def _overdue(unit: Unit, now: datetime) -> Iterator[dict]:
    if unit.skill.package not in ENDS:
        return
    running = _running(unit, now)
    for name, last in running:
        if last and now - last >= LIMIT:
            yield {
                "id": f"overdue:worker:{name}:{last.isoformat()}",
                "type": "overdue",
                "worker": name,
                "silent_min": int((now - last).total_seconds() // 60),
            }
    if not running:
        for ident, since in _working_items(unit):
            if since is not None and now - since >= LIMIT:
                yield {"id": f"overdue:item:{ident}:{since.isoformat()}", "type": "overdue", "item": ident}
