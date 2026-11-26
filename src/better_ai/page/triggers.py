"""Validated skill records that can wake a driven page.

A code hand-back is a handed_back entry. A research worker's stop or a verifier's checked entry reports completed
work. Those append-only logs have no record IDs, so the file and the physical line identify each trigger. Discover
evidence and waiting decisions keep their own IDs when their records change.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from datetime import datetime, timezone

from .. import paths, records, resources, schema
from ..paths import Unit


def _files(unit: Unit, folder: str, pattern: str) -> list[str]:
    try:
        return sorted(f"{folder}/{path.name}" for path in unit.target(folder).glob(pattern))
    except (OSError, paths.Refused):
        return []


def _read(unit: Unit, files: Iterable[str], now: datetime) -> Iterator[tuple[str, int, dict]]:
    docs, cutoff, cache = schema.docs_for(unit.skill.package), resources.cutoff(), {}
    for relative in files:
        read = schema.read_records(unit, relative, docs, cache, now, cutoff)
        for line, record in zip(read.lines, read.records, strict=True):
            yield relative, line, record


def _due(record: dict, now: datetime) -> bool:
    deadline = record.get("deadline")
    if record["status"] not in ("waiting", "pending") or deadline is None:
        return False
    try:
        return datetime.fromisoformat(deadline.removesuffix("Z") + "+00:00") <= now
    except ValueError:
        return False


def _logs_and_decisions(unit: Unit, *kinds: str) -> Iterator[dict]:
    now = datetime.now(timezone.utc)
    files = [*_files(unit, "logs", "*.jsonl"), "decisions.jsonl"]
    for relative, line, record in _read(unit, files, now):
        kind = record["type"]
        if kind in kinds:
            yield {"id": f"{relative}:{line}", "type": kind, "file": relative, "line": line}
        elif kind == "decision" and _due(record, now):
            yield {"id": f"decision:{record['id']}", "type": "deadline", "decision": record["id"]}


def code(unit: Unit) -> Iterator[dict]:
    return _logs_and_decisions(unit, "handed_back")


def research(unit: Unit) -> Iterator[dict]:
    return _logs_and_decisions(unit, "stop", "checked")


def discover(unit: Unit) -> Iterator[dict]:
    coordinator = records.written_by(unit, "coordinator")
    for relative, _, record in _read(unit, _files(unit, "evidence", "*.json"), datetime.now(timezone.utc)):
        if record["type"] == "evidence" and record["by"] not in ("user", coordinator):
            yield {"id": f"evidence:{record['id']}", "type": "evidence", "evidence": record["id"], "file": relative}
