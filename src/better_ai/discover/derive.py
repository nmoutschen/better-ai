"""What an item is, derived from the records and never copied: the one function every reader imports.

The page, `check`, `summary` and `brief` all call `derive`, so they cannot disagree about an item:

- an item's **state** is the `to` of the last change for the field `state` that names the item, and `unverified` when
  there is none; its **importance** is the `to` of the last change for the field `importance`, and None before the
  first;
- **Risk accepted** is derived and never written: an item with at least one risk, every one of them accepted by a
  change with the field `risk`, shows `risk accepted` in place of its recorded state;
- the **chosen option** is the option of the last move.

"Last" is the order of the log, not the time on a line: `changes.jsonl` is append only. `derive` reads lists of records
and changes none of them; `derive_folder` reads them from a unit's folder first, skipping a file that is not there and a
line that does not parse (`check` reports those).
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

UNVERIFIED = "unverified"
RISK_ACCEPTED = "risk accepted"
ACCEPTED = "accepted"


@dataclass(frozen=True)
class ItemView:
    """One item as the records say it is."""

    id: str
    state: str  # what a reader shows: `risk accepted` once every risk is accepted, else the recorded state
    recorded_state: str  # the `to` of the last state change, `unverified` when there is none
    importance: str | None  # `high`, `lower`, or None before the first importance change
    risk_accepted: bool
    accepted_risks: tuple[str, ...]  # the item's risks that have an accepted risk change, in the item's order
    open_risks: tuple[str, ...]  # the others
    last_state_change: Mapping[str, Any] | None = (
        None  # the change `recorded_state` is the `to` of; None before the first
    )
    last_importance_change: Mapping[str, Any] | None = None  # likewise for `importance`


@dataclass(frozen=True)
class Derived:
    items: Mapping[str, ItemView] = field(default_factory=dict)
    chosen: str | None = None  # the option of the last move
    moves_by_option: Mapping[str, tuple[str, ...]] = field(default_factory=dict)  # option id -> its move ids, in order


def _last_change(changes: Iterable[Mapping[str, Any]], item: str, name: str) -> Mapping[str, Any] | None:
    """The last change of `name` that names the item, and the only place that finds it: what `check` and the rules
    compare with is this change. A state change to `risk accepted` is skipped: that state is derived from the risk
    changes, and `check` refuses a log that writes it. So is a change whose `to` is not text."""
    found = None
    for change in changes:
        about = change.get("about")
        to = change.get("to")
        named = change.get("field") == name and isinstance(about, Mapping) and about.get("item") == item
        if named and isinstance(to, str) and not (name == "state" and to == RISK_ACCEPTED):
            found = change
    return found


def _accepted(changes: Iterable[Mapping[str, Any]], item: str) -> set[str]:
    done = set()
    for change in changes:
        about = change.get("about")
        if (
            change.get("field") == "risk"
            and change.get("to") == ACCEPTED
            and isinstance(about, Mapping)
            and about.get("item") == item
            and isinstance(change.get("risk"), str)
        ):
            done.add(change["risk"])
    return done


def _view(item: Mapping[str, Any], changes: list[Mapping[str, Any]]) -> ItemView:
    ident = item["id"]
    ids = [r["id"] for r in item.get("risks") or [] if isinstance(r, Mapping) and isinstance(r.get("id"), str)]
    accepted = _accepted(changes, ident)
    done = tuple(r for r in dict.fromkeys(ids) if r in accepted)
    open_ = tuple(r for r in dict.fromkeys(ids) if r not in accepted)
    risk_accepted = bool(ids) and not open_
    last_state = _last_change(changes, ident, "state")
    last_importance = _last_change(changes, ident, "importance")
    recorded = last_state["to"] if last_state else UNVERIFIED
    return ItemView(
        id=ident,
        state=RISK_ACCEPTED if risk_accepted else recorded,
        recorded_state=recorded,
        importance=last_importance["to"] if last_importance else None,
        risk_accepted=risk_accepted,
        accepted_risks=done,
        open_risks=open_,
        last_state_change=last_state,
        last_importance_change=last_importance,
    )


def derive(
    items: Iterable[Mapping[str, Any]],
    changes: Iterable[Mapping[str, Any]] = (),
    moves: Iterable[Mapping[str, Any]] = (),
) -> Derived:
    """The derived view of a discovery from its item, change and move records, each in the order of its log."""
    log = [c for c in changes if isinstance(c, Mapping)]
    views = {i["id"]: _view(i, log) for i in items if isinstance(i, Mapping) and isinstance(i.get("id"), str)}
    by_option: dict[str, list[str]] = {}
    chosen = None
    for move in moves:
        if isinstance(move, Mapping) and isinstance(move.get("option"), str):
            chosen = move["option"]
            by_option.setdefault(chosen, []).append(move.get("id"))
    return Derived(views, chosen, {k: tuple(v) for k, v in by_option.items()})


def _read_lines(path: Path) -> list[dict]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    records = []
    for line in text.splitlines():
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def derive_folder(folder: Path) -> Derived:
    """`derive` over `items.jsonl`, `changes.jsonl` and `moves.jsonl` of a discovery's folder."""
    return derive(
        _read_lines(folder / "items.jsonl"),
        _read_lines(folder / "changes.jsonl"),
        _read_lines(folder / "moves.jsonl"),
    )
