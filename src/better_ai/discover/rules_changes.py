"""discover-better: the rules for decisions, risks and changes, and who may write each record.

Each rule is one function over lists of records, so the same code holds wherever it is applied:

- `add` (a guard, before the record is validated): the coordinator-only writer rule, the state rules of a change, the
  evidence a change cites, an identical change, and a question asked twice;
- the schema hook `risk-change` (named by `x-check` in change.schema.json): the risk rule, applied when a risk change is
  added and again by `check` to every risk change, because what it looks at cannot change;
- `set` (a step): changes and moves are never edited, the coordinator-only writer rule, the coordinator named
  in the head and the fields of a chosen option but its note stay, an answered decision keeps its `about` and `answer`,
  `answered_at` and `updated_at` are stamped, a risk that a decision or change cites keeps its id and text, and a test
  that is not planned keeps its `what`, `rule` and `settles`; `add` of an answered decision stamps `answered_at` too;
- `check` (a step): an item's latest state or importance change that no longer holds is a warning, "add a change",
  never an error, because the log cannot be edited.

What an item's state is comes from `derive`, never from a second reading of the changes.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from .. import cli, paths, records, schema
from ..paths import Refused, Unit, refusal
from . import SKILL
from .derive import ItemView, derive

NAME = SKILL.name
WRITTEN_BY_THE_COORDINATOR = ("item", "change", "option", "move", "brief", "decision", "test")

Problem = tuple[str, str]  # what is wrong, and the next action


# ---------------------------------------------------------------- reading the unit


def _object(text: str) -> dict | None:
    try:
        value = json.loads(text)
    except (ValueError, RecursionError):
        return None
    return value if isinstance(value, dict) else None


def _read(unit: Unit, relative: str) -> str:
    try:
        return paths.read_bytes(unit, relative).decode("utf-8", "replace")
    except (OSError, Refused):
        return ""


def _lines(unit: Unit, relative: str) -> list[dict]:
    """The records of a JSONL file of the unit, in order; a line that does not parse is skipped (`check` reports it)."""
    found = (_object(line) for line in schema._lines(_read(unit, relative)) if line.strip())
    return [r for r in found if r is not None]


def _evidence(unit: Unit) -> dict[str, dict]:
    found: dict[str, dict] = {}
    try:
        names = sorted(p.name for p in unit.target("evidence").glob("*.json"))
    except (OSError, Refused):
        return found
    for name in names:
        record = _object(_read(unit, f"evidence/{name}"))
        if record is not None and isinstance(record.get("id"), str):
            found[record["id"]] = record
    return found


def _head(unit: Unit) -> dict:
    return _object(_read(unit, unit.kind.head)) or {}


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _dict(value: Any) -> Mapping:
    return value if isinstance(value, Mapping) else {}


def _list(value: Any) -> list:
    return value if isinstance(value, list) else []


# ---------------------------------------------------------------- who writes what (the coordinator only)


def _coordinator_only(unit: Unit, kind: str, by: str | None) -> None:
    name = _text(_head(unit).get("coordinator"))
    if not name:
        raise Refused(f"{unit.label}: discover.json names no coordinator: fix discover.json, then run again")
    if by != name:
        raise Refused(
            f"{unit.label}: only {name} (discover.json coordinator) writes {kind}: use --by {name}",
        )


@records.add_guard(NAME, *WRITTEN_BY_THE_COORDINATOR)
def _add_by_the_coordinator(ctx: records.AddContext) -> None:
    _coordinator_only(ctx.unit, ctx.type, ctx.by)


# ---------------------------------------------------------------- the risk rule


def _about_risk(decision: Mapping, item: str, risk: str) -> bool:
    about = _dict(decision.get("about"))
    return about.get("type") == "risk" and about.get("item") == item and about.get("risk") == risk


def _cites_decision(change: Mapping, ident: str) -> bool:
    answer = _dict(_dict(change.get("cause")).get("answer"))
    return answer.get("type") == "decision" and answer.get("id") == ident


def risk_problems(
    change: Mapping,
    earlier: Sequence[Mapping],
    decisions: Sequence[Mapping],
    items: Sequence[Mapping],
    events: Sequence[Mapping],
) -> list[tuple[str, str]]:
    """What is wrong with a risk change, as (field, message): it must cite an answered decision about that exact risk,
    no earlier change cites it, and the answer is a page answer with the default or the user's words in the chat."""
    item, risk = _text(_dict(change.get("about")).get("item")), _text(change.get("risk"))
    answer = _dict(_dict(change.get("cause")).get("answer"))
    if answer.get("type") != "decision" or not isinstance(answer.get("id"), str):
        return [
            (
                "cause.answer",
                f"no decision is cited: ask the user about {risk} of {item} and cite the answered decision",
            )
        ]
    ident = answer["id"]
    problems: list[tuple[str, str]] = []
    known = next((i for i in items if i.get("id") == item), None)
    if known is not None and risk not in [_dict(r).get("id") for r in _list(known.get("risks"))]:
        problems.append(("risk", f"{item} has no risk {risk}: accept a risk the item lists"))
    decision = next((d for d in decisions if d.get("id") == ident), None)
    if decision is None:
        return problems  # dangling: the pointer reports it
    if not _about_risk(decision, item, risk):
        problems.append(
            ("cause.answer.id", f"{ident} is not about {risk} of {item}: ask the user about that risk and cite that")
        )
    elif decision.get("status") != "answered":
        problems.append(("cause.answer.id", f"{ident} is not answered: wait for the user's answer"))
    elif any(_cites_decision(c, ident) for c in earlier):
        problems.append(("cause.answer.id", f"{ident} was cited by an earlier change: ask the user again"))
    else:
        given = _dict(decision.get("answer"))
        event = next((e for e in reversed(events) if e.get("id") == given.get("event")), None)
        typed = given.get("type") == "page" and event is not None and event.get("type") == "answer"
        if typed and event.get("default") is not True:
            problems.append(
                (
                    "cause.answer.id",
                    f"{ident} was answered in words: confirm with the user in the chat and record their words",
                )
            )
    return problems


@schema.hook("risk-change")
def _risk_change(record: dict, context: schema.Context) -> list[tuple[str, str]]:
    changes = context.read_jsonl("changes.jsonl") or []
    earlier = [c for c in changes[: max(context.line - 1, 0)] if isinstance(c, dict)]
    return risk_problems(
        record,
        earlier,
        [d for d in context.read_jsonl("decisions.jsonl") or [] if isinstance(d, dict)],
        [i for i in context.read_jsonl("items.jsonl") or [] if isinstance(i, dict)],
        [e for e in context.read_jsonl("conversation.jsonl") or [] if isinstance(e, dict)],
    )


# ---------------------------------------------------------------- the state rules of a change


def _counting(evidence: Mapping[str, Mapping], item: str, direction: str) -> list[str]:
    """The ids of the evidence that counts and bears on the item in that direction."""
    found = []
    for ident, record in evidence.items():
        if record.get("status") != "counts":
            continue
        if any(
            _dict(b).get("item") == item and _dict(b).get("direction") == direction
            for b in _list(record.get("bears_on"))
        ):
            found.append(ident)
    return sorted(found)


def _asks_about(decision: Mapping, item: str) -> bool:
    about = _dict(decision.get("about"))
    return about.get("type") in ("item", "risk") and about.get("item") == item


def state_problems(
    to: str,
    item: Mapping,
    evidence: Mapping[str, Mapping],
    tests: Sequence[Mapping],
    decisions: Sequence[Mapping],
) -> list[Problem]:
    """Why an item may not be in this state now, each with its next action."""
    ident = _text(item.get("id"))
    if to == "supported":
        against = _counting(evidence, ident, "against")
        if against:
            return [
                (
                    f"{ident} cannot move to supported: {', '.join(against)} counts against it",
                    "choose contradicted, needs a test or waiting for you, or take the evidence off with its check",
                )
            ]
        if not _counting(evidence, ident, "for"):
            return [
                (
                    f"{ident} cannot move to supported: no evidence that counts is for it",
                    "wait for a verifier to confirm evidence for it, then add the change",
                )
            ]
    elif to == "contradicted":
        if not _counting(evidence, ident, "against"):
            return [
                (
                    f"{ident} cannot move to contradicted: no evidence that counts is against it",
                    "wait for a verifier to confirm evidence against it, then add the change",
                )
            ]
    elif to == "checking":
        being_checked = any(
            r.get("status") == "checking" and any(_dict(b).get("item") == ident for b in _list(r.get("bears_on")))
            for r in evidence.values()
        )
        if not item.get("checker") and not being_checked:
            return [
                (
                    f"{ident} cannot move to checking: it has no checker and none of its evidence is checking",
                    "set a checker on the item, or add the evidence being checked, then add the change",
                )
            ]
    elif to == "waiting for you":
        if not any(d.get("status") == "waiting" and _asks_about(d, ident) for d in decisions):
            return [
                (
                    f"{ident} cannot move to waiting for you: no open question is about it",
                    "ask the user a question about it, then add the change",
                )
            ]
    elif to == "needs a test":
        settled = any(t.get("status") != "removed" and ident in _list(t.get("settles")) for t in tests)
        if not settled:
            return [
                (
                    f"{ident} cannot move to needs a test: no test settles it",
                    "add a test that settles it, then add the change",
                ),
            ]
    return []


def cited_problems(change: Mapping, evidence: Mapping[str, Mapping]) -> list[Problem]:
    """Evidence a change cites must count, and bear on the item the change is about."""
    about = _dict(change.get("about"))
    item = _text(about.get("item")) if about.get("type") == "item" else None
    problems: list[Problem] = []
    for ident in _list(_dict(change.get("cause")).get("evidence")):
        record = evidence.get(ident)
        if record is None:
            continue  # dangling: the pointer reports it
        if record.get("status") != "counts":
            problems.append(
                (
                    f"{ident} does not count (it is {record.get('status')})",
                    "cite evidence that counts, or wait for its check",
                )
            )
        elif item is not None and not any(_dict(b).get("item") == item for b in _list(record.get("bears_on"))):
            problems.append((f"{ident} does not bear on {item}", f"cite evidence that bears on {item}"))
    return problems


def _items_by_id(items: Sequence[Mapping]) -> dict[str, Mapping]:
    return {i["id"]: i for i in items if isinstance(i.get("id"), str)}


def _is_identical(change: Mapping, items: Sequence[Mapping], changes: Sequence[Mapping]) -> bool:
    """The change repeats what the item (or the discovery) already holds for the field, as the last change says."""
    about, name, to = _dict(change.get("about")), change.get("field"), change.get("to")
    if about.get("type") == "discovery":
        last = [c for c in changes if _dict(c.get("about")).get("type") == "discovery" and c.get("field") == name]
        return bool(last) and last[-1].get("to") == to
    item = _text(about.get("item"))
    view: ItemView | None = derive(items, changes).items.get(item)
    if view is None:
        return False
    if name in ("state", "importance"):
        last = view.last_state_change if name == "state" else view.last_importance_change
        return last is not None and last["to"] == to
    if name == "risk":
        return change.get("risk") in view.accepted_risks
    return False


@records.add_guard(NAME, "change")
def _add_change(ctx: records.AddContext) -> None:
    change, unit = ctx.record, ctx.unit
    if change.get("field") == "state" and change.get("to") == "risk accepted":
        raise refusal(
            unit.label,
            "risk accepted is not a state: it is derived once every risk of an item is accepted",
            "accept each risk with a risk change citing the user's answer",
        )
    items, changes = _lines(unit, "items.jsonl"), _lines(unit, "changes.jsonl")
    if _is_identical(change, items, changes):
        raise refusal(unit.label, "already recorded: nothing to do")
    evidence = _evidence(unit)
    problems = cited_problems(change, evidence)
    item = _items_by_id(items).get(_text(_dict(change.get("about")).get("item")))
    if not problems and change.get("field") == "state" and item is not None:
        problems = state_problems(
            _text(change.get("to")), item, evidence, _lines(unit, "tests.jsonl"), _lines(unit, "decisions.jsonl")
        )
    if problems:
        raise refusal(unit.label, problems[0][0], problems[0][1])


# ---------------------------------------------------------------- one question once, until it is answered


def _same_words(text: Any) -> str:
    return re.sub(r"\s+", " ", _text(text)).strip().casefold()


@records.add_guard(NAME, "decision")
def _add_decision(ctx: records.AddContext) -> None:
    record = ctx.record
    if record.get("status") == "answered":  # as in set, the time of the answer is the tool's, never the agent's
        record["answered_at"] = ctx.run.now().strftime(schema.TIME)
    if record.get("status") != "waiting":
        return
    for other in _lines(ctx.unit, "decisions.jsonl"):
        if (
            other.get("status") == "waiting"
            and other.get("about") == record.get("about")
            and _same_words(other.get("asked")) == _same_words(record.get("asked"))
        ):
            raise refusal(
                ctx.unit.label,
                f"{other.get('id')} already asks this and is waiting for the user",
                f"wait for the answer to {other.get('id')}, or ask something different",
            )


# ---------------------------------------------------------------- set


def _now(ctx: records.SetContext) -> str:
    return ctx.run.now().strftime(schema.TIME)


def _cited_risks(unit: Unit, item: str) -> set[str]:
    """The risks of an item that a decision or a change names."""
    cited = set()
    for decision in _lines(unit, "decisions.jsonl"):
        about = _dict(decision.get("about"))
        if about.get("type") == "risk" and about.get("item") == item and isinstance(about.get("risk"), str):
            cited.add(about["risk"])
    for change in _lines(unit, "changes.jsonl"):
        if (
            change.get("field") == "risk"
            and _dict(change.get("about")).get("item") == item
            and isinstance(change.get("risk"), str)
        ):
            cited.add(change["risk"])
    return cited


def _keep_cited_risks(ctx: records.SetContext, after: Mapping) -> None:
    """A cited risk keeps its id and text: it stays in the list once, with the words it had, whether the set changes
    the list, nulls it or unsets it."""
    item = _text(ctx.record.get("id"))
    cited = _cited_risks(ctx.unit, item)
    now = [_dict(r) for r in _list(after.get("risks"))]
    for risk in _list(ctx.record.get("risks")):
        ident, words = _dict(risk).get("id"), _dict(risk).get("text")
        if ident in cited and [r.get("text") for r in now if r.get("id") == ident] != [words]:
            raise refusal(
                ctx.unit.label,
                f"{ident} of {item} is cited by a decision or a change, so it stays once, with its id and text",
                f"keep {ident} as it is and add a new risk",
            )


OPEN_AFTER_A_MOVE = ("note", "updated_at")  # what an option that a move chose may still change


def _keep_chosen_option(ctx: records.SetContext, after: Mapping) -> None:
    """An option that a move chose keeps every field but its note: the move, its brief and the user's choice read it."""
    ident = _text(ctx.record.get("id"))
    chosen = [m.get("id") for m in _lines(ctx.unit, "moves.jsonl") if m.get("option") == ident]
    changed = [
        f
        for f in dict.fromkeys([*ctx.record, *after])
        if f not in OPEN_AFTER_A_MOVE and after.get(f) != ctx.record.get(f)
    ]
    if chosen and changed:
        raise refusal(
            ctx.unit.label,
            f"{ident} was chosen by {chosen[0]}, so its {', '.join(changed)} cannot change",
            "add a new option; only its note can change",
        )


# What a locked record may become, by the status it has now: the one table every set is held to, as the patch and the
# unsets together leave the record. A status with no row has no rule here; the schema holds the rest.
TRANSITIONS = {
    "test": {
        "planned": ("planned", "running", "done", "removed"),
        "running": ("running", "done", "removed"),
        "done": ("done", "removed"),
        "removed": ("removed",),
    },
    "decision": {"waiting": ("waiting", "answered"), "answered": ("answered",)},
}
# The fields a record keeps once it has this status: they neither change nor go.
LOCKED = {
    "test": {status: ("what", "rule", "settles") for status in ("running", "done", "removed")},
    "decision": {"answered": ("about", "answer", "answered_at", "default")},  # default: a computed result counts by it
}
WHAT_NEXT = {
    "test": lambda ident: f"add a new test and remove {ident} with a reason",
    "decision": lambda ident: "ask a new question",
}


def _after(ctx: records.SetContext) -> dict:
    """The record as the set leaves it: the patch merged (a null removes the field, as `set` may read it) and the
    fields `--unset` names removed."""
    new = dict(ctx.record)
    for name, value in ctx.patch.items():
        if value is None:
            new.pop(name, None)
        else:
            new[name] = value
    for name in ctx.unsets:
        new.pop(name, None)
    return new


def _keep_locked(ctx: records.SetContext, kind: str, after: Mapping) -> None:
    record = ctx.record
    status = record.get("status")
    ident = _text(record.get("id"))
    allowed = TRANSITIONS[kind].get(status)
    if allowed is not None and after.get("status") not in allowed:
        what = f"status cannot become {after.get('status')}"
    else:
        changed = [f for f in LOCKED[kind].get(status, ()) if after.get(f) != record.get(f)]
        if not changed:
            return
        what = f"{', '.join(changed)} cannot change"
    raise refusal(ctx.unit.label, f"{ident} is {status}, so its {what}", WHAT_NEXT[kind](ident))


@records.set_step(NAME)
def _set(ctx: records.SetContext) -> None:
    kind = ctx.record.get("type")
    ident = _text(ctx.record.get("id"))
    if kind in ("change", "move"):
        raise refusal(
            ctx.unit.label, f"a {kind} is never edited ({ident or 'it'} stays as written)", f"add a new {kind}"
        )
    if kind in WRITTEN_BY_THE_COORDINATOR:
        _coordinator_only(ctx.unit, kind, ctx.by)
    if kind == "decision" and ctx.record.get("status") == "waiting" and ctx.patch.get("status") == "answered":
        ctx.patch["answered_at"] = _now(ctx)
    after = _after(ctx)
    if kind in TRANSITIONS:
        _keep_locked(ctx, kind, after)
    elif kind == "item":
        _keep_cited_risks(ctx, after)
        ctx.patch["updated_at"] = _now(ctx)
    elif kind == "option":
        _keep_chosen_option(ctx, after)
        ctx.patch["updated_at"] = _now(ctx)
    elif kind == "discover":
        if after.get("named_sources") != ctx.record.get("named_sources"):
            _coordinator_only(ctx.unit, "named_sources", ctx.by)
            kept = after.get("named_sources")
            lost = [n for n in _list(ctx.record.get("named_sources")) if not isinstance(kept, list) or n not in kept]
            if lost:
                raise refusal(
                    ctx.unit.label,
                    "a named source stays named: sources an analyst added from it rest on it",
                    "keep every named source and add the new ones",
                )
        if after.get("coordinator") != ctx.record.get("coordinator"):
            raise refusal(
                ctx.unit.label,
                "the coordinator of a discovery cannot change: what the user's evidence says it was added by stays true",
                "start a new discovery for another coordinator",
            )


# ---------------------------------------------------------------- check: a latest change that no longer holds


def _stale(unit: Unit) -> list[tuple[str, str, Mapping, str]]:
    """Each item whose latest state or importance change no longer holds, as (item, field, the change, why): the one
    rule `check` warns by and `brief` refuses by. A cited evidence that is not in the unit does not hold either."""
    items, changes = _lines(unit, "items.jsonl"), _lines(unit, "changes.jsonl")
    evidence, tests, decisions = _evidence(unit), _lines(unit, "tests.jsonl"), _lines(unit, "decisions.jsonl")
    found = []
    views = derive(items, changes).items
    for item in items:
        ident = item.get("id")
        view = views.get(ident)
        if view is None:
            continue
        for name, change in (("state", view.last_state_change), ("importance", view.last_importance_change)):
            if change is None:
                continue
            missing = [e for e in _list(_dict(change.get("cause")).get("evidence")) if e not in evidence]
            if missing:
                found.append((ident, name, change, f"{missing[0]} is not in evidence/"))
                continue
            problems = cited_problems(change, evidence)
            if name == "state" and not problems:
                problems = state_problems(_text(change.get("to")), item, evidence, tests, decisions)
            if problems:
                found.append((ident, name, change, problems[0][0]))
    return found


def stale(unit: Unit) -> list[str]:
    """One line for each item whose latest state or importance change no longer holds."""
    return [f"{item}'s {name} is stale: add a change ({why})" for item, name, _, why in _stale(unit)]


def stale_items(unit: Unit) -> dict[str, str]:
    """The items whose latest state or importance change no longer holds, each with why (the first of its changes)."""
    found: dict[str, str] = {}
    for item, name, change, why in _stale(unit):
        found.setdefault(item, f"its latest {name} change ({change.get('to')}) no longer holds: {why}")
    return found


@cli.check_step(NAME)
def _check(unit: Unit, run: cli.Run) -> int:
    for line in stale(unit):
        run.err(f"warning: {line}")
    return 0
