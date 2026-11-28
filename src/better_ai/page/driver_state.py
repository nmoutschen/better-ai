"""The page driver's private state file (.driver) and its bounded history (.driver.log)."""

from __future__ import annotations

import contextlib
import copy
import json
import os
import stat
import tempfile
from pathlib import Path

from ..paths import NOFOLLOW, Refused

STATE = ".driver"
LOG = ".driver.log"
ACTIVE_DELIVERY = ".page-delivery"
MAX_LOG = 1024 * 1024
VERSION = 1

# The fields of .driver (S150) with the value a missing field takes (S124).
DEFAULTS = {
    "version": VERSION,
    "harness": None,
    "session": None,
    "server_pid": None,
    "server_started": None,
    "child_pid": None,
    "child_argv": [],
    "opened": 0,
    "delivered": {"id": None, "position": 0},
    "note": "",
    "fired": [],
    "handoff_delivered": False,
    "turn": None,
    "ended": {"at": None, "reason": None, "repeats": 0},
}


def private_bytes(unit, name: str) -> bytes:
    """The content of a file only the user can read and write, or nothing."""
    try:
        fd = os.open(unit.target(name), os.O_RDONLY | NOFOLLOW | os.O_NONBLOCK)
    except (OSError, Refused):
        return b""
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_mode & 0o077
            or info.st_size > MAX_LOG
        ):
            return b""
        return stream.read(MAX_LOG + 1)


def encode(record: dict) -> bytes:
    return (json.dumps(record, ensure_ascii=True) + "\n").encode("ascii")


def write_private(unit, name: str, data: bytes) -> None:
    """Replace a file atomically; mkstemp gives it the user-only mode."""
    target = unit.target(name)
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        os.replace(temporary, target)
    finally:
        with contextlib.suppress(FileNotFoundError):
            Path(temporary).unlink()


def _stored(unit) -> dict | None:
    try:
        state = json.loads(private_bytes(unit, STATE))
    except (ValueError, UnicodeError):
        return None
    return state if isinstance(state, dict) else None


def newer_version(unit) -> bool:
    """True when .driver was written by a newer better-ai: serve refuses it rather than overwrite it."""
    state = _stored(unit)
    return bool(state) and type(state.get("version")) is int and state["version"] > VERSION


def with_defaults(state: dict) -> dict:
    """The fields of S150 with defaults for what is missing, and every unknown field kept."""
    result = {**state}
    for name, default in DEFAULTS.items():
        value = result.get(name)
        if name not in result or (isinstance(default, dict) and not isinstance(value, dict)):
            result[name] = copy.deepcopy(default)
        elif isinstance(default, dict):
            result[name] = {**default, **value}
    result["version"] = VERSION
    return result


def load_state(unit) -> dict | None:
    """The saved state, or None when it is absent, owned by another user, open to others, or not version 1."""
    state = _stored(unit)
    if state is None or state.get("version") != VERSION:
        return None
    return with_defaults(state)


def save_state(unit, fields: dict) -> dict:
    """Write the state: missing fields take their defaults, and unknown fields already in the file are kept."""
    current = _stored(unit) or {}
    state = with_defaults({**current, **fields})
    write_private(unit, STATE, encode(state))
    return state


def delivered_field(position: int, events: list[dict]) -> dict:
    """The delivered position with the id of the last event delivered, so a reset log can be noticed."""
    ident = events[position - 1].get("id") if 0 < position <= len(events) else None
    return {"id": ident if isinstance(ident, str) else None, "position": position}


def delivered_position(delivered, events: list[dict]) -> int:
    """The position to resume after. The id decides when it and the stored position disagree (S125)."""
    if not isinstance(delivered, dict):
        return 0
    position, ident = delivered.get("position"), delivered.get("id")
    if type(position) is not int or position < 0:
        position = 0
    if ident is None:
        return position
    if 0 < position <= len(events) and events[position - 1].get("id") == ident:
        return position
    # Deliver again from the first event with that id: a repeat is harmless, a gap is a loss.
    for index, event in enumerate(events):
        if event.get("id") == ident:
            return index + 1
    return 0


def log_records(unit) -> list[dict]:
    records = []
    for line in private_bytes(unit, LOG).splitlines():
        try:
            record = json.loads(line)
        except (ValueError, UnicodeError):
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def recent_turn(records: list[dict], session: str | None) -> dict:
    return next(
        (r for r in reversed(records) if r.get("type") == "turn" and r.get("session") == session),
        {},
    )


def store_log(unit, records: list[dict]) -> list[dict]:
    """Write the newest records that fit in 1 MB, whole lines only."""
    lines = []
    total = 0
    for record in reversed(records):
        line = encode(record)
        if total + len(line) > MAX_LOG:
            break
        lines.append(line)
        total += len(line)
    write_private(unit, LOG, b"".join(reversed(lines)))
    return records[len(records) - len(lines) :]
