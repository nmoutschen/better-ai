"""discover-better: the rules for evidence and sources: the quote flow, the URL rule and the evidence statuses.

A quote becomes evidence in four steps. An analyst adds a `source` (a page it read) and an `evidence` that is
`checking`, with no verifier. The coordinator sets a `verifier` on it. The verifier reads the page itself, from the
shell, and sets the outcome with `set --by <verifier> --raw <file>`: `counts` only with the span it copied, which must
occur in that file, and a quote that occurs in the span. `better.pyz` computes the file's `sha256`; it makes no network
call and reads no page but that file.

Who may change an evidence's status:

| From | To | Who | When |
|---|---|---|---|
| `checking` | `counts`, `unverified`, `not reachable`, `not found`, `reworded` | the current `verifier` | always |
| `not reachable` | `checking` | the coordinator | `tries` holds fewer than two verifiers; it sets a new `verifier` |
| `checking` | `unverified` ("verifier did not finish") | the coordinator | `since` is older than 30 minutes |
| any | `removed` | the coordinator | the reason names the user's request (a `remove` or `redact` event, or an answered decision about the evidence) |

`not found`: the words are not on a raw read of the page. `reworded`: the page says the same in other words, which the
verifier copies into `page_words`. The coordinator then adds the corrected quote as new evidence whose `corrects`
names the reworded one and whose words are its `page_words`: it starts `checking` and goes through the same flow, and
the coordinator judges again what it bears on.

A source may also be a file or a connector item (origin `file`, `tool`); an analyst adds one only for a named source
(`named_problem`), and its quotes follow the same flow with no URL rule. Evidence of kind `data` from such a source is
a computed result: no verifier, and the coordinator sets it `counts` once the user took the default of a question about
it (`confirmation_problem`), or `unverified` with the reason "not confirmed by you".

Every other change is refused, with its next action. Evidence from the user (a source with origin `you`) counts at once:
only the coordinator adds it, with a `given` that points to the user's `add_evidence` event or holds their typed words.

Where each rule runs:

- `check`, and `add` and `set` before they write: the hooks `discover-source` and `discover-evidence` (`x-check` in the
  schemas), which look at one record and the files around it: the URL rule, the setting's `said_by_role` and
  `summary`, what `counts` needs, and what evidence from the user is;
- `add` guards: who writes (the coordinator, or the analyst that is the current `checker` of every item the evidence
  bears on), how new evidence starts, repeated evidence, and one record per page event;
- the `set` step: the statuses above, who sets `verifier` and `since`, `tries`, and the check of `--raw`.

A rule that needs the writer or the history of a record cannot run on a record at rest, so `check` holds what a
record must be to count and `add` and `set` hold how it got there.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any

from .. import cli, paths, quotes, records, schema
from ..quotes import normalise, quote_in_span
from . import derive

SKILL = "discover-better"
TIMEOUT = 30  # minutes a verifier may run before the coordinator may give up on it
TIMEOUT_REASON = "verifier did not finish"
MAX_TRIES = 2  # a `not reachable` evidence is tried again only while fewer verifiers than this were started
CHECKED = ("checked_read", "span", "sha256")  # what `counts` holds and nothing else does
SOURCE_ID = re.compile(r"S-[\w.-]+-\d+")
READ_KINDS = ("web", "file", "tool")  # origins an analyst read and a verifier reads again, as against `you`
CONFIRM = "Confirm this result"  # the default of the question that makes a computed result count
NOT_CONFIRMED = "not confirmed by you"
USER_ONLY = ("verifier", "tries", "since", *CHECKED)  # fields the user's own evidence never has
OUTCOMES = (
    "counts",
    "unverified",
    "not reachable",
    "not found",
    "reworded",
)  # what a verifier sets on checking evidence
WITH_REASON = ("unverified", "not reachable", "not found", "reworded", "removed")  # the statuses that hold a reason


# ---------------------------------------------------------------- reading the unit


def _folder(unit: paths.Unit, name: str) -> Iterator[tuple[str, dict]]:
    """Each record file of a folder of the unit, as (relative path, record), in name order."""
    try:
        base = unit.target(name)
        files = sorted(base.glob("*.json")) if base.is_dir() else []
    except paths.Refused:
        return
    for file in files:
        if file.is_symlink():
            continue
        value = derive.read_object(unit.path, f"{name}/{file.name}")
        if isinstance(value, dict):
            yield f"{name}/{file.name}", value


def _source(unit: paths.Unit, ident: Any) -> dict | None:
    if not isinstance(ident, str) or not SOURCE_ID.fullmatch(ident):
        return None
    return derive.read_object(unit.path, f"sources/{ident}.json")


def _origin(source: dict | None) -> str | None:
    origin = source.get("origin") if isinstance(source, dict) else None
    kind = origin.get("type") if isinstance(origin, dict) else None
    return kind if kind in (*READ_KINDS, "you") else None


def named_problem(head: Any, origin: dict) -> str | None:
    """Why an analyst may not add a file or tool source, or None: a file must be a named path or inside a named folder
    (by path segments), and a tool must be a named tool."""
    named = [n for n in (head.get("named_sources") if isinstance(head, dict) else None) or [] if isinstance(n, dict)]
    if origin.get("type") == "tool":
        if any(n.get("type") == "tool" and n.get("tool") == origin.get("tool") for n in named):
            return None
        return f"the tool {origin.get('tool')} is not named: ask the coordinator to name it, or add no source from it"
    path = os.path.normpath(str(origin.get("path")))
    for n in named:
        if n.get("type") == "file" and isinstance(n.get("path"), str):
            base = os.path.normpath(n["path"])
            if path == base or path.startswith(base.rstrip("/") + "/"):
                return None
    return f"{origin.get('path')} is not a named file or inside a named folder: add no source from it, and tell the coordinator"


def _computed(source: dict | None, record: dict) -> bool:
    """Evidence of kind data from a file or a tool: the user confirms it, nothing re-reads it."""
    return record.get("kind") == "data" and _origin(source) in ("file", "tool")


def confirmation_problem(decisions: list, events: list, ident: str) -> str | None:
    """Why a computed result may not count yet, or None: a question about it with the default "Confirm this result"
    that the user answered with that default (the page's default click, or those words in the chat)."""
    asked = [
        d
        for d in decisions
        if isinstance(d, dict)
        and isinstance(d.get("about"), dict)
        and d["about"].get("type") == "evidence"
        and d["about"].get("evidence") == ident
        and d.get("default") == CONFIRM
    ]
    if not asked:
        return f'no question about {ident} with the default "{CONFIRM}": ask the user, and wait for their answer'
    for d in asked:
        answer = d.get("answer") if isinstance(d.get("answer"), dict) else {}
        if d.get("status") != "answered":
            continue
        if answer.get("type") == "chat" and answer.get("text") == CONFIRM:
            return None
        event = next((e for e in reversed(events) if isinstance(e, dict) and e.get("id") == answer.get("event")), None)
        if answer.get("type") == "page" and event and event.get("type") == "answer" and event.get("default") is True:
            return None
    if all(d.get("status") != "answered" for d in asked):
        return f"the question about {ident} is not answered: wait for the user's answer"
    return f'the user did not take the default "{CONFIRM}": set {ident} unverified with the reason "{NOT_CONFIRMED}"'


# ---------------------------------------------------------------- hooks: what a record at rest must be


@schema.hook("discover-source")
def _source_at_rest(record: dict, ctx: schema.Context) -> list[tuple[str, str]]:
    """Who may name a file or tool, and the role a source from you needs where the setting is internal. The address of a
    web source is held to `x-public-url` in the schema."""
    origin = record.get("origin")
    if not isinstance(origin, dict):
        return []
    head = ctx.read_json("../discover.json")
    if origin.get("type") in ("file", "tool") and record.get("by") != (head or {}).get("coordinator"):
        why = named_problem(head, origin)
        if why:
            return [("origin", why)]
    internal = isinstance(head, dict) and head.get("setting") == "internal"
    if origin.get("type") == "you" and internal and not record.get("said_by_role"):
        return [("said_by_role", "needed for a source from you in an internal discovery: say who said it, by role")]
    return []


@schema.hook("discover-evidence")
def _evidence_at_rest(record: dict, ctx: schema.Context) -> list[tuple[str, str]]:
    """What evidence must be to be in the state it is in: what `counts` needs, and what the user's own evidence is."""
    problems: list[tuple[str, str]] = []
    head = ctx.read_json("../discover.json")
    source_id = record.get("source")
    source = (
        ctx.read_json(f"../sources/{source_id}.json")
        if isinstance(source_id, str) and SOURCE_ID.fullmatch(source_id)
        else None
    )
    kind = _origin(source)
    words = record.get("words") if isinstance(record.get("words"), dict) else {}
    status = record.get("status")
    if words.get("type") == "event":
        given = source["origin"].get("given") if kind == "you" else None
        if not isinstance(given, dict) or given.get("type") != "page" or given.get("event") != words.get("event"):
            problems.append(("words", "event words need a source from you that points to the same page event"))
    if kind == "you":
        if status not in ("counts", "removed"):
            problems.append(
                ("status", "evidence from you counts at once: its status is counts, or removed once the user asks")
            )
        for name in USER_ONLY:
            if name in record:
                problems.append((name, "evidence from you is not checked by a verifier: leave it out"))
        coordinator = head.get("coordinator") if isinstance(head, dict) else None
        if coordinator and record.get("by") != coordinator:
            problems.append(("by", f"evidence from you is added by the coordinator, {coordinator}"))
        if isinstance(head, dict) and head.get("setting") == "internal" and not record.get("summary"):
            problems.append(("summary", "needed for evidence from you in an internal discovery: the words by role"))
    elif kind in READ_KINDS:
        coordinator = head.get("coordinator") if isinstance(head, dict) else None
        if coordinator and record.get("verifier") == coordinator:
            problems.append(("verifier", "the coordinator is never the verifier: a verifier agent reads the page"))
        if "since" in record and not record.get("verifier"):
            problems.append(("since", "since is set only while a verifier runs: set a verifier"))
        if status == "counts" and _computed(source, record):
            decisions = ctx.read_jsonl("../decisions.jsonl") or []
            why = confirmation_problem(decisions, ctx.read_jsonl("../conversation.jsonl") or [], str(record.get("id")))
            if why:
                problems.append(("status", why))
        elif status == "counts":
            problems += _counting(record, words)
    return problems


def _counting(record: dict, words: dict) -> list[tuple[str, str]]:
    """Web evidence that counts: a verifier other than its analyst read the page raw and the span holds the quote."""
    problems = []
    verifier = record.get("verifier")
    if not verifier:
        problems.append(
            ("verifier", "counts only after a verifier read the page: set a verifier and have it set the outcome")
        )
    elif verifier == record.get("by"):
        problems.append(("verifier", "the analyst that added the evidence cannot be the verifier that counts it"))
    if record.get("checked_read") != "raw":
        problems.append(("checked_read", "counts needs checked_read raw: a verifier reads the page itself"))
    span = record.get("span")
    if words.get("type") != "quote" or not isinstance(words.get("text"), str):
        problems.append(("words", "web evidence counts as a quote"))
    elif isinstance(span, str) and not quote_in_span(words["text"], span):
        problems.append(("span", "the quote does not occur in the span: a verifier copies the span that holds it"))
    return problems


# ---------------------------------------------------------------- add guards


def _refuse(unit: paths.Unit, reason: str, then: str | None = None) -> paths.Refused:
    return paths.refusal(unit.label, reason, then)


@records.add_guard(SKILL, "source")
def _source_by_the_coordinator_if_from_you(ctx: records.AddContext) -> None:
    """A source from you holds the user's own words or event: only the coordinator adds it."""
    origin = ctx.record.get("origin")
    if isinstance(origin, dict) and origin.get("type") == "you":
        coordinator = records.written_by(ctx.unit, "coordinator")
        if ctx.by != coordinator:
            raise _refuse(
                ctx.unit,
                f"only the coordinator ({coordinator}) adds a source from you",
                "stop: tell the coordinator what the user gave, in your hand-back",
            )


@records.add_guard(SKILL, "evidence")
def _evidence_writer_and_start(ctx: records.AddContext) -> None:
    """Who adds evidence, how it starts, and that it is not repeated."""
    unit, record, by = ctx.unit, ctx.record, ctx.by
    coordinator = records.written_by(unit, "coordinator")
    kind = _origin(_source(unit, record.get("source")))
    if kind == "you" and by != coordinator:
        raise _refuse(
            unit,
            f"only the coordinator ({coordinator}) adds evidence from you",
            "stop: tell the coordinator what the user gave, in your hand-back",
        )
    if kind in READ_KINDS:
        started = [n for n in (*USER_ONLY, "reason") if n in record]
        if record.get("status") != "checking" or started:
            what = "status " + str(record.get("status")) if record.get("status") != "checking" else ", ".join(started)
            raise _refuse(
                unit,
                f"new evidence from a page, file or connector starts checking, with no verifier fields ({what})",
                'add it with "status": "checking" and without verifier, tries, since, checked_read, span, sha256 or '
                "reason; the coordinator starts a verifier",
            )
    if "corrects" in record:
        _corrects_reworded(unit, record, by, coordinator)
    if by != coordinator:
        _must_be_checker(unit, by, record)
    _not_repeated(unit, record)


def _corrects_reworded(unit: paths.Unit, record: dict, by: str, coordinator: str) -> None:
    """A correction: the coordinator quotes the page's words of a reworded evidence, from the same source, once."""
    target = record.get("corrects")
    if by != coordinator:
        raise _refuse(
            unit,
            f"only the coordinator ({coordinator}) adds the correction of a reworded quote",
            "stop: tell the coordinator, in your hand-back",
        )
    found = dict(_folder(unit, "evidence")).get(f"evidence/{target}.json")
    if not isinstance(found, dict) or found.get("status") != "reworded":
        raise _refuse(
            unit,
            f"{target} is not reworded: only reworded evidence is corrected",
            "correct evidence its verifier set reworded",
        )
    if record.get("source") != found.get("source"):
        raise _refuse(unit, f"the correction quotes the same source as {target} ({found.get('source')})")
    words = record.get("words") if isinstance(record.get("words"), dict) else {}
    if normalise(str(words.get("text") or "")) != normalise(str(found.get("page_words") or "")):
        raise _refuse(
            unit,
            f"the correction's words must be the page_words of {target}",
            f'quote "{found.get("page_words")}" word for word',
        )
    for _, other in _folder(unit, "evidence"):
        if other.get("corrects") == target:
            raise _refuse(unit, f"{target} is already corrected by {other.get('id')}", f"use {other.get('id')}")


def _must_be_checker(unit: paths.Unit, by: str, record: dict) -> None:
    if not record.get("bears_on"):
        raise _refuse(
            unit,
            f"evidence added by {by} must bear on an item it checks: bears_on is empty",
            "name the items it bears on, or leave the evidence to the coordinator",
        )
    items = {i.get("id"): i for i in derive.read_lines(unit.path, "items.jsonl")}
    for bears in record.get("bears_on") or []:
        item = items.get(bears.get("item")) if isinstance(bears, dict) else None
        if item is None:
            continue  # a pointer to no item is the schema's to report
        checker = item.get("checker")
        if checker != by:
            now = f"{checker} checks it" if checker else "no analyst checks it now"
            raise _refuse(
                unit,
                f"you ({by}) are not the checker of {item['id']}: {now}",
                "stop: you were replaced; add no more records, and say so in your hand-back",
            )


def _not_repeated(unit: paths.Unit, record: dict, skip: str | None = None) -> None:
    words = record.get("words")
    if not isinstance(words, dict):
        return
    mine = _comparable(words)
    for _, other in _folder(unit, "evidence"):
        if (
            other.get("id") != skip
            and other.get("source") == record.get("source")
            and mine is not None
            and _comparable(other.get("words")) == mine
        ):
            note = " (removed)" if other.get("status") == "removed" else ""
            raise _refuse(
                unit,
                f"already recorded as {other.get('id')}{note}: the same source and the same words",
                f"use {other.get('id')}, or add the evidence with other words",
            )


def _comparable(words: Any) -> tuple[str, str] | None:
    if not isinstance(words, dict):
        return None
    if words.get("type") == "quote" and isinstance(words.get("text"), str):
        return "quote", normalise(words["text"])
    if words.get("type") == "event" and isinstance(words.get("event"), str):
        return "event", words["event"]
    return None


def _page_events(value: Any) -> Iterator[str]:
    """Each page event a record points to: `{type: page or event, event: <id>}`, wherever it is in the record."""
    if isinstance(value, dict):
        if value.get("type") in ("page", "event") and isinstance(value.get("event"), str):
            yield value["event"]
        for inner in value.values():
            yield from _page_events(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from _page_events(inner)


def _unit_records(unit: paths.Unit) -> Iterator[tuple[str, int, dict]]:
    """Every record that may point to a page event: the unit's JSONL files but the conversation and the logs, and its
    source and evidence files."""
    try:
        files = sorted(p for p in unit.path.glob("*.jsonl") if p.name != "conversation.jsonl" and not p.is_symlink())
    except OSError:
        files = []
    for file in files:
        for number, record in enumerate(derive.read_lines(unit.path, file.name), 1):
            yield file.name, number, record
    for folder in ("sources", "evidence"):
        for relative, record in _folder(unit, folder):
            yield relative, 1, record


def _clash(first: dict, second: dict) -> str | None:
    """A page event both records point to, unless one is evidence and the other its source: the evidence of a source
    from the user states the same event as its source."""
    for evidence, source in ((first, second), (second, first)):
        if (
            evidence.get("type") == "evidence"
            and source.get("type") == "source"
            and source.get("id") == evidence.get("source")
        ):
            return None
    shared = set(_page_events(first)) & set(_page_events(second))
    return min(shared) if shared else None


def _clash_message(event: str, other: dict, number: int, relative: str) -> str:
    name = other.get("id") or f"line {number}"
    return f"page event {event} is already used by {name} ({relative})"


CLASH_NEXT = "a page event backs one record: use another event, or change that record"


@records.add_guard(SKILL)
def _a_page_event_backs_one_record(ctx: records.AddContext) -> None:
    """A page event is one thing the user did: one record points to it."""
    if not set(_page_events(ctx.record)):
        return
    for relative, number, other in _unit_records(ctx.unit):
        event = _clash(ctx.record, other)
        if event:
            raise _refuse(ctx.unit, _clash_message(event, other, number, relative), CLASH_NEXT)


@cli.check_step(SKILL)
def _check_page_events(unit: paths.Unit, run: cli.Run) -> int:
    """The same rule over the whole unit, as an error: the later record of two that point to one event."""
    seen = [(r, n, rec) for r, n, rec in _unit_records(unit) if set(_page_events(rec))]
    shown = os.path.relpath(unit.path)
    found = 0
    for index, (relative, number, record) in enumerate(seen):
        for earlier_relative, earlier_number, earlier in seen[:index]:
            event = _clash(record, earlier)
            if event:
                message = _clash_message(event, earlier, earlier_number, earlier_relative)
                run.out(f"{shown}/{relative}:{number}: page event: {message}: {CLASH_NEXT}")
                found = 1
    return found


# ---------------------------------------------------------------- the set step


def _since(record: dict) -> datetime | None:
    try:
        return datetime.strptime(record["since"], records.TIME).replace(tzinfo=timezone.utc)
    except (KeyError, TypeError, ValueError):
        return None


def _names_the_request(unit: paths.Unit, ident: str, reason: Any) -> bool:
    """The reason names the user's request to remove this evidence: a `remove` or `redact` event of theirs, or a
    decision about it that they answered with exactly "remove <id>"."""
    if not isinstance(reason, str):
        return False
    wanted = [
        e.get("id")
        for e in derive.read_lines(unit.path, "conversation.jsonl")
        if e.get("by") == "user"
        and (
            (e.get("type") == "remove" and e.get("record") == ident)
            or (e.get("type") == "redact" and e.get("evidence") == ident)
        )
    ]
    for decision in derive.read_lines(unit.path, "decisions.jsonl"):
        about = decision.get("about")
        answer = decision.get("answer")
        said = answer.get("text") if isinstance(answer, dict) else None
        asked = isinstance(about, dict) and about.get("type") == "evidence" and about.get("evidence") == ident
        if decision.get("status") == "answered" and asked and said == f"remove {ident}":
            wanted.append(decision.get("id"))
    return any(isinstance(w, str) and re.search(rf"(?<![\w-]){re.escape(w)}(?![\w-])", reason) for w in wanted)


def _count(ctx: records.SetContext, by: str) -> None:
    """Make the patch of a set to `counts` complete, or refuse. The verifier gives `checked_read` and `span`; the
    command adds the hash of the file."""
    record, patch, ident = ctx.record, ctx.patch, ctx.record["id"]
    if by == record.get("by"):
        raise _refuse(
            ctx.unit,
            f"you ({by}) added {ident}: a verifier cannot count the evidence it added",
            "stop: the coordinator starts another verifier",
        )
    if patch.get("checked_read") != "raw":
        raise _refuse(
            ctx.unit,
            "counts needs checked_read raw",
            'set "checked_read": "raw" with the span you copied from the page you read yourself',
        )
    span = patch.get("span")
    if not isinstance(span, str) or not span:
        raise _refuse(ctx.unit, "counts needs the span you copied from the page", 'set "span" to that text')
    words = record.get("words") if isinstance(record.get("words"), dict) else {}
    digest = quotes.check_read(
        ctx,
        [span],
        words.get("text"),
        "save the raw page to a file outside .discover/ and run again with --raw <file>",
        reworded='set "status": "reworded" with the reason "reworded" and the page\'s passage in "page_words"',
    )
    patch["sha256"] = digest


def _computed_outcome(ctx: records.SetContext, by: str, coordinator: str, new: str) -> None:
    """The outcome of a computed result: the coordinator alone sets it, `counts` once the user confirmed it, or
    `unverified` with the reason that they did not. No verifier reads it again and no --raw file is used."""
    ident = ctx.record["id"]
    if by != coordinator:
        raise _refuse(
            ctx.unit,
            f"{ident} is a computed result: only the coordinator ({coordinator}) sets it, once the user confirms it",
            "stop: tell the coordinator, in your hand-back",
        )
    if new == "counts":
        why = confirmation_problem(
            derive.read_lines(ctx.unit.path, "decisions.jsonl"),
            derive.read_lines(ctx.unit.path, "conversation.jsonl"),
            ident,
        )
        if why:
            raise _refuse(ctx.unit, f"{ident} cannot count yet: {why}")
    elif new != "unverified" or ctx.patch.get("reason") != NOT_CONFIRMED:
        raise _refuse(
            ctx.unit,
            f'a computed result is set counts, or unverified with the reason "{NOT_CONFIRMED}" (not {new})',
            "ask the user to confirm it",
        )


def _who(ctx: records.SetContext, by: str, coordinator: str, old: str, new: str) -> paths.Refused:
    """The refusal of a change of status the writer may not make."""
    record = ctx.record
    ident, verifier = record["id"], record.get("verifier")
    tries = record.get("tries") or []
    if by != coordinator and verifier and by in tries and by != verifier:
        return _refuse(ctx.unit, f"you were replaced by {verifier}: stop")
    if old == "checking" and new in OUTCOMES:
        if by == coordinator:
            how = (
                f"only the verifier {verifier} sets the outcome; after {TIMEOUT} minutes of its silence set unverified "
                f'with the reason "{TIMEOUT_REASON}"'
                if verifier
                else "no verifier is started yet: set a verifier first"
            )
            return _refuse(ctx.unit, f"{ident} is checking: {how}")
        return _refuse(
            ctx.unit,
            f"you ({by}) are not the verifier of {ident}" + (f"; {verifier} is" if verifier else ""),
            "stop: only the verifier the coordinator started sets the outcome",
        )
    allowed = {
        "checking": "its verifier sets counts, unverified, not reachable, not found or reworded",
        "not reachable": f"the coordinator may set checking again with a new verifier while fewer than {MAX_TRIES} tried",
        "counts": "nothing but removed, by the coordinator, at the user's request",
        "unverified": "nothing but removed, by the coordinator, at the user's request",
        "not found": "nothing but removed, by the coordinator, at the user's request",
        "reworded": "nothing but removed, by the coordinator, at the user's request; the coordinator adds the "
        "corrected quote as new evidence that corrects it",
        "removed": "nothing: removed evidence stays removed",
    }.get(old, "nothing")
    return _refuse(
        ctx.unit,
        f"{ident} cannot go from {old} to {new} (by {by}): from {old} {allowed}",
        "add new evidence if the words are to be checked again",
    )


UNSET = object()  # a field `set` removes, with --unset or with null
STAMPED = ("type", "at", "by", "id")
# The write table of evidence: who may change each field, and in which status. Nothing else may be changed. A field
# not here is refused. "analyst" is the analyst that added the evidence.
FIXED_AFTER_CHECKING = ("source", "words", "bears_on", "kind", "about")  # coordinator or analyst, while checking, alone
EVIDENCE_FIELDS = (
    *FIXED_AFTER_CHECKING,
    "summary",  # the coordinator, while checking or counting
    "status",  # the quote flow's table
    "verifier",  # the coordinator, as it starts a verifier, while checking
    "since",  # the coordinator, with a verifier, while checking
    "tries",  # better.pyz alone
    "reason",  # only with the change of status that holds it
    "checked_read",  # only with counts, from the verifier
    "span",  # only with counts, from the verifier
    "sha256",  # better.pyz alone, from --raw
    "page_words",  # only with reworded, from the verifier
)
SOURCE_FIELDS = ("origin", "title", "said_by_role")  # origin: never; title: coordinator or analyst; role: coordinator


def _changes(record: dict, patch: dict, unsets: tuple[str, ...]) -> dict[str, Any]:
    """The fields a set really changes, as new value or UNSET: a value the record has already is not a change, and
    neither is removing a field it does not have."""
    found: dict[str, Any] = {}
    for name, value in patch.items():
        if value is None:
            value = UNSET
        if value is UNSET:
            if name in record:
                found[name] = UNSET
        elif name not in record or record[name] != value or name == "verifier":  # a verifier is always a start
            found[name] = value
    for name in unsets:
        if name in record:
            found[name] = UNSET
    return found


def _no_unset(ctx: records.SetContext, name: str) -> paths.Refused:
    return _refuse(
        ctx.unit,
        f"{name} of {ctx.record['id']} cannot be removed",
        "leave --unset and null out: better.pyz drops the fields a change of status makes stale",
    )


def _write_table(
    ctx: records.SetContext, changes: dict[str, Any], by: str, coordinator: str, old: str, new: str
) -> None:
    """The write table of evidence, for every field the set changes but `status`: who, and in which status."""
    unit, record = ctx.unit, ctx.record
    ident, verifier = record["id"], record.get("verifier")
    tries = list(record.get("tries") or ([verifier] if verifier else []))
    for name, value in changes.items():
        if name == "status":
            continue
        if name in STAMPED or name not in EVIDENCE_FIELDS:
            raise _refuse(
                unit, f"{name} of {ident} cannot be changed", "change only the fields the evidence's format lists"
            )
        if value is UNSET:
            raise _no_unset(ctx, name)
        if name == "sha256":
            raise _refuse(unit, "sha256 is computed by better.pyz from --raw", "leave sha256 out of the fields")
        if name == "tries":
            raise _refuse(unit, "tries is kept by better.pyz", "leave tries out of the fields")
        if name in FIXED_AFTER_CHECKING:
            if old != "checking":
                raise _refuse(
                    unit,
                    f"{name} of {ident} is fixed once the evidence leaves checking (it is {old})",
                    "add new evidence with the new words, source or items",
                )
            if new != old:
                raise _refuse(
                    unit, f"{name} cannot change in the set that changes the status", f"set {name} on its own"
                )
            if by not in (coordinator, record.get("by")):
                raise _refuse(
                    unit,
                    f"only the coordinator ({coordinator}) or {record.get('by')}, who added {ident}, changes {name}",
                    "stop: tell the coordinator, in your hand-back",
                )
            merged = {**record, name: value}
            if name in ("source", "words"):
                _not_repeated(unit, merged, ident)
            if name == "bears_on" and by != coordinator:
                _must_be_checker(unit, by, merged)
        elif name == "summary":
            if by != coordinator or old not in ("checking", "counts"):
                raise _refuse(
                    unit,
                    f"only the coordinator ({coordinator}) writes summary, while {ident} is checking or counts",
                    "ask the coordinator",
                )
        elif name in ("verifier", "since"):
            if by != coordinator:
                raise _refuse(
                    unit,
                    f"only the coordinator ({coordinator}) sets verifier or since",
                    "stop: you cannot start or replace a verifier",
                )
            if new != "checking":
                raise _refuse(unit, f"{name} is set only while {ident} is checking", f"{ident} is {new}")
            if name == "since" and not (verifier or "verifier" in changes):
                raise _refuse(unit, f"since is set only while a verifier runs on {ident}", "set a verifier first")
            if name == "verifier" and value == coordinator:
                raise _refuse(
                    unit, "the coordinator is never the verifier", "start a verifier agent with a name of its own"
                )
            if name == "verifier" and value in tries:
                raise _refuse(
                    unit,
                    f"{value} is already in tries of {ident} ({', '.join(tries)})",
                    "start a verifier with a new name",
                )
        elif name == "page_words":
            if not (old == "checking" and new == "reworded"):
                raise _refuse(
                    unit,
                    f"page_words of {ident} is set only when its verifier sets it reworded",
                    'set "status": "reworded" with the reason and the page\'s words together',
                )
        elif name == "reason":
            if new == old or new not in WITH_REASON:
                raise _refuse(
                    unit,
                    f"reason of {ident} is set only with the change of status that needs it",
                    "set the status and the reason together",
                )
        elif name in ("checked_read", "span") and not (old == "checking" and new == "counts"):
            raise _refuse(
                unit,
                f"{name} is set only when a verifier counts the evidence",
                "set counts with checked_read, the span and --raw",
            )


@records.set_step(SKILL)
def evidence_status_rules(ctx: records.SetContext) -> None:
    """The write table and the status table, on every set of evidence: who changes which field in which status, how
    the status changes, `tries`, `since` and the check of `--raw`."""
    record, patch, by, unit = ctx.record, ctx.patch, ctx.by, ctx.unit
    if record.get("type") != "evidence":
        return
    ident = record["id"]
    coordinator = records.written_by(unit, "coordinator")
    if by is None:
        raise _refuse(unit, f"setting {ident} needs --by", "run again with --by <your agent name>")
    verifier = record.get("verifier")
    if by != coordinator and verifier and by in (record.get("tries") or []) and by != verifier:
        raise _refuse(unit, f"you were replaced by {verifier}: stop")
    changes = _changes(record, patch, ctx.unsets)
    if changes.get("status") is UNSET:
        raise _no_unset(ctx, "status")
    old, new = record.get("status"), patch.get("status", record.get("status"))
    tries = list(record.get("tries") or ([verifier] if verifier else []))
    now = ctx.run.now()
    computed = _computed(_source(unit, record.get("source")), record)
    _write_table(ctx, changes, by, coordinator, old, new)

    if new != old:
        if new == "removed":
            if by != coordinator:
                raise _refuse(unit, f"only the coordinator ({coordinator}) removes evidence", "ask the coordinator")
            if not _names_the_request(unit, ident, patch.get("reason")):
                raise _refuse(
                    unit,
                    f"the reason must name the user's request to remove {ident}",
                    'give a reason that holds the id of their remove or redact event, or of a decision they answered "remove '
                    + ident
                    + '"',
                )
            for name in (*CHECKED, "page_words"):
                if name in record:
                    patch[name] = None
        elif old == "checking" and new in OUTCOMES and computed:
            _computed_outcome(ctx, by, coordinator, new)
        elif old == "checking" and new in OUTCOMES:
            if by == verifier:
                pass
            elif new == "unverified" and by == coordinator and patch.get("reason") == TIMEOUT_REASON:
                if not verifier:
                    raise _refuse(unit, f"no verifier runs on {ident}: nothing to wait for", "set a verifier first")
                started = _since(record)
                if started is None or (now - started).total_seconds() < TIMEOUT * 60:
                    waited = f"{int((now - started).total_seconds() // 60)} minutes ago" if started else "not at all"
                    raise _refuse(
                        unit,
                        f"the verifier of {ident} started {waited}: give it {TIMEOUT} minutes",
                        f"run again once since is older than {TIMEOUT} minutes",
                    )
            else:
                raise _who(ctx, by, coordinator, old, new)
        elif old == "not reachable" and new == "checking":
            if by != coordinator or len(tries) >= MAX_TRIES:
                if by == coordinator:
                    raise _refuse(
                        unit,
                        f"{ident} was tried by {len(tries)} verifiers, two at most ({', '.join(tries)}): that is enough",
                        'set it unverified with a reason, such as "not reachable twice"',
                    )
                raise _who(ctx, by, coordinator, old, new)
            if "verifier" not in patch:
                raise _refuse(unit, f"a new try needs a new verifier for {ident}", 'set "verifier" to a new name')
            patch["reason"] = None
        else:
            raise _who(ctx, by, coordinator, old, new)

    if new == "reworded" and new != old and not patch.get("page_words"):
        raise _refuse(
            unit,
            f"reworded needs page_words: what the page says in place of the quote of {ident}",
            'set "page_words" to the page\'s passage, word for word, on one line',
        )
    if new == "counts" and old == "checking" and not computed:
        _count(ctx, by)
    elif ctx.raw is not None:
        raise _refuse(unit, "--raw is for setting counts", "leave --raw out")
    if "verifier" in patch:
        patch["tries"] = [*tries, patch["verifier"]]
        patch.setdefault("since", now.strftime(records.TIME))
    if old == "checking" and new != "checking" and "since" in record | patch:
        patch["since"] = None


@records.set_step(SKILL)
def source_write_table(ctx: records.SetContext) -> None:
    """The write table of a source: its origin is fixed once added; its title is the coordinator's or its analyst's;
    the role of the user's source is the coordinator's. Nothing is removed."""
    record, by, unit = ctx.record, ctx.by, ctx.unit
    if record.get("type") != "source":
        return
    ident = record["id"]
    coordinator = records.written_by(unit, "coordinator")
    if by is None:
        raise _refuse(unit, f"setting {ident} needs --by", "run again with --by <your agent name>")
    for name, value in _changes(record, ctx.patch, ctx.unsets).items():
        if name not in SOURCE_FIELDS:
            raise _refuse(
                unit, f"{name} of {ident} cannot be changed", "change only the fields the source's format lists"
            )
        if value is UNSET:
            raise _refuse(unit, f"{name} of {ident} cannot be removed", "leave --unset out")
        if name == "origin":
            raise _refuse(unit, f"the origin of {ident} is fixed once added", "add a new source for the new page")
        allowed = (coordinator,) if name == "said_by_role" else (coordinator, record.get("by"))
        if by not in allowed:
            raise _refuse(
                unit,
                f"only the coordinator ({coordinator}) changes {name} of {ident}"
                + ("" if name == "said_by_role" else f" or {record.get('by')}, who added it"),
                "stop: tell the coordinator, in your hand-back",
            )
