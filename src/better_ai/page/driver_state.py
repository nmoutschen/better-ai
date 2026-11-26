"""Private on-disk session state and bounded operational history."""

from __future__ import annotations

import contextlib
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


def private_bytes(unit, name: str) -> bytes:
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
    target = unit.target(name)
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        os.replace(temporary, target)
    finally:
        with contextlib.suppress(FileNotFoundError):
            Path(temporary).unlink()


def read_driver_state(unit, harness=None, *, valid_session) -> dict:
    """A state file is useful only after we validate its mode, owner and adapter's session ID."""
    try:
        state = json.loads(private_bytes(unit, STATE))
    except (ValueError, UnicodeError):
        return {}
    if not isinstance(state, dict) or state.get("version") != 1:
        return {}
    stored_harness = state.get("harness")
    if not isinstance(stored_harness, str) or (harness is not None and harness != stored_harness):
        return {}
    if not valid_session(stored_harness, state.get("session")):
        return {}
    return state


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
