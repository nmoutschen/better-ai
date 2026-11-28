"""discover-better: the warnings `check` and `summary` share, and the `summary` verb.

`load` reads a discovery's records the way the page does (a record that fails its schema stays, without the fields that
failed, and its errors are listed), so `summary` can print what it read when a record is invalid. `warnings_of` is the
design's list of things that are wrong but cannot be refused, because the log cannot be edited or because they are about
time: `check` prints them after the records pass, `summary` prints them with the rest. Each warning names the record
and the next action.

`summary <unit>` prints typed JSON lines, one object per line: `head` (first, with the coordinator), `decision`,
`event` (each page event not done), `move`, `brief`, `item`, `evidence` (only while `checking`), `warning`, and, if a
record is invalid, a last `invalid` line naming the files; it then exits 1. An agent that lost its context reads this
to resume. Evidence words are never printed: they are outside text, and the agent reads them by id when it needs them.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .. import cli, page, paths, schema
from ..page import FINISHED, all_items
from ..paths import Unit
from . import SKILL, derive
from .brief import REMOVED
from .brief import STATE as REDACT_STATE
from .rules_moves import BRIEF_MOVES

PAGE_EVENTS = ("choose", "add_evidence", "add_result", "remove", "edit", "redact")  # discover's own events
USER_EVENTS = (*PAGE_EVENTS, "answer", "comment")  # what the user sends that the agent tracks; a note with no `to` too
SHOWN_ERRORS = 20  # how many error lines the `invalid` line carries


@dataclass
class Discovery:
    """What `load` read. Every list is in the order of its file; an item missing a field is as its record had it."""

    unit: Unit
    head: dict = field(default_factory=dict)
    items: list[dict] = field(default_factory=list)
    changes: list[dict] = field(default_factory=list)
    options: list[dict] = field(default_factory=list)
    moves: list[dict] = field(default_factory=list)
    briefs: list[dict] = field(default_factory=list)
    decisions: list[dict] = field(default_factory=list)
    tests: list[dict] = field(default_factory=list)
    conversation: list[dict] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)  # {file, line, field, message} for each record that fails

    def option_move(self, move: dict) -> str | None:
        option = next((o for o in self.options if o.get("id") == move.get("option")), None)
        return option.get("move") if option else None


def _files(unit: Unit, folder: str) -> list[str]:
    path = unit.path / folder
    return sorted(f"{folder}/{p.name}" for p in path.glob("*.json")) if path.is_dir() else []


def load(unit: Unit, run: cli.Run) -> Discovery:
    docs = schema.docs_for(run.info.package)
    cache: dict[str, Any] = {}
    now, cutoff = run.now(), run.info.cutoff
    found = Discovery(unit)

    def read(relative: str) -> list[dict]:
        done = schema.read_records(unit, relative, docs, cache, now, cutoff, keep_invalid=True)
        found.errors.extend(done.errors)
        return page.log_records(done) if relative == page.LOG else done.records  # the log keeps its lines

    head = read(unit.kind.head)
    found.head = head[0] if head else {}
    for name, attribute in (
        ("items.jsonl", "items"),
        ("changes.jsonl", "changes"),
        ("options.jsonl", "options"),
        ("moves.jsonl", "moves"),
        ("briefs.jsonl", "briefs"),
        ("decisions.jsonl", "decisions"),
        ("tests.jsonl", "tests"),
        ("conversation.jsonl", "conversation"),
    ):
        setattr(found, attribute, read(name))
    found.evidence = [r for name in _files(unit, "evidence") for r in read(name)]
    found.sources = [r for name in _files(unit, "sources") for r in read(name)]
    return found


# ---------------------------------------------------------------- what the page's log says


def _at(record: dict) -> datetime | None:
    try:
        return datetime.strptime(str(record.get("at")), schema.TIME).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


@dataclass
class Events:
    """The user's events, read once by the page's own rules (`page.all_items`), so no skill reads them a second way."""

    found: list[tuple[dict, str, dict]]  # (event, state, extra) of every item

    @property
    def open(self) -> list[tuple[dict, str, dict]]:
        return [f for f in self.found if f[1] not in FINISHED]

    @staticmethod
    def answered(extra: dict) -> bool:
        """An agent replied under the item."""
        return any(t.get("from") != "user" for t in extra.get("thread", []))


def read_events(lines: list[dict], agent: str = "coordinator") -> Events:
    return Events(all_items(lines, (*USER_EVENTS, "note"), agent))


# ---------------------------------------------------------------- the warnings


@dataclass(frozen=True)
class Warning_:
    code: str
    about: str
    text: str


def _strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for part in value.values():
            yield from _strings(part)
    elif isinstance(value, list):
        for part in value:
            yield from _strings(part)


def _norm(text: str) -> str:
    return " ".join(text.split()).casefold()


def _occurs(text: str, value: str) -> bool:
    """Whether the normalised text occurs in the value as whole words: `No` is not in `Nobody`."""
    return re.search(r"(?<!\w)" + re.escape(text) + r"(?!\w)", _norm(value)) is not None


def last_word(d: Discovery, agent: str) -> datetime | None:
    """The latest `at` among the records whose `by`, or whose evidence or source id, carries the agent's name."""
    found = (
        r
        for group in (d.items, d.changes, d.options, d.moves, d.briefs, d.decisions, d.tests, d.evidence, d.sources)
        for r in group
    )
    return page.last_word([*found, *d.conversation], agent, id_prefixes=("E-", "S-"))


def _silent(d: Discovery, agent: str, since: Any, fallback: dict, now: datetime) -> int | None:
    """Minutes of silence if the agent has been quiet for more than the shared quiet threshold, else None."""
    started = _at({"at": since}) if isinstance(since, str) else _at(fallback)
    heard = last_word(d, agent)
    last = max((t for t in (started, heard) if t), default=None)
    if last is None or now - last <= page.QUIET_AFTER:
        return None
    return int((now - last).total_seconds() // 60)


def _evidence_texts(evidence: dict, events: dict[str, str]) -> list[str]:
    texts = []
    words = evidence.get("words") if isinstance(evidence.get("words"), dict) else {}
    if words.get("type") == "quote" and isinstance(words.get("text"), str):
        texts.append(words["text"])
    elif words.get("type") == "event":
        text = derive.evidence_event_text(events, words.get("event"))
        if text:
            texts.append(text)
    if isinstance(evidence.get("summary"), str):
        texts.append(evidence["summary"])
    return [t for t in (_norm(t) for t in texts) if t and t != _norm(REMOVED)]  # a redact's mark is not a copy


def _without_cited_text(test: dict, ident: Any) -> dict:
    """A test whose result cites the evidence keeps its text by design (D16): it is not a copy."""
    result = test.get("result")
    if isinstance(result, dict) and ident in (result.get("evidence") or []):
        return {**test, "result": {k: v for k, v in result.items() if k != "text"}}
    return test


def _without_corrected(other: dict, evidence: dict) -> dict:
    if other.get("id") == evidence.get("corrects"):
        return {k: v for k, v in other.items() if k != "page_words"}
    return other


def _holders(d: Discovery, evidence: dict) -> list[tuple[str, str, dict]]:
    """The records that must not hold the evidence's text: every record but the evidence itself, its own source (which
    keeps what the user typed) and the page's log (which keeps the user's events)."""
    held = []
    for label, group in (
        ("discover.json", [d.head] if d.head else []),
        ("items.jsonl", d.items),
        ("changes.jsonl", d.changes),
        ("options.jsonl", d.options),
        ("moves.jsonl", d.moves),
        ("briefs.jsonl", d.briefs),
        ("decisions.jsonl", d.decisions),
        ("tests.jsonl", [_without_cited_text(t, evidence.get("id")) for t in d.tests]),
        # a correction quotes the page_words of the evidence it corrects: those are not a copy of it
        ("evidence", [_without_corrected(e, evidence) for e in d.evidence if e is not evidence]),
        ("sources", [s for s in d.sources if s.get("id") != evidence.get("source")]),
    ):
        for record in group:
            held.append((label, str(record.get("id") or record.get("field") or "line"), record))
    return held


def _brief_text(d: Discovery, brief: dict) -> str | None:
    name = brief.get("file")
    if not isinstance(name, str):
        return None
    try:
        return d.unit.target(name).read_text(encoding="utf-8", errors="replace")
    except (OSError, paths.Refused):
        return None


def warnings_of(d: Discovery, now: datetime) -> list[Warning_]:
    """Everything the design says `check` and `summary` warn about, in its order."""
    found: list[Warning_] = []
    label = d.unit.label
    cited = {e for c in d.changes if isinstance(c.get("cause"), dict) for e in c["cause"].get("evidence") or []}
    for e in d.evidence:
        if e.get("status") == "counts" and e.get("id") not in cited:
            found.append(
                Warning_(
                    "uncited-evidence",
                    e.get("id", ""),
                    f"{e.get('id')} counts but no change cites it: add a change for the items it bears on",
                )
            )
    for e in d.evidence:
        if e.get("status") == "checking" and not e.get("verifier"):
            found.append(
                Warning_(
                    "evidence-without-verifier",
                    e.get("id", ""),
                    f"{e.get('id')} is checking and no verifier has it: start a quote verifier",
                )
            )
    corrected = {e.get("corrects") for e in d.evidence}
    for e in d.evidence:
        if e.get("status") == "reworded" and e.get("id") not in corrected:
            found.append(
                Warning_(
                    "reworded-without-correction",
                    e.get("id", ""),
                    f"{e.get('id')} is reworded: add the corrected quote, its page_words, as evidence that corrects it",
                )
            )
    for kind, group, status in (
        ("item", d.items, None),
        ("evidence", d.evidence, "checking"),
        ("test", d.tests, "running"),
    ):
        for record in group:
            agent = record.get("verifier" if kind == "evidence" else "checker")
            if not agent or (status and record.get("status") != status):
                continue
            minutes = _silent(d, agent, record.get("since"), record, now)
            if minutes is not None:
                found.append(
                    Warning_(
                        "no-word-from-agent",
                        record.get("id", ""),
                        f"No word from {agent} for {minutes} min on {record.get('id')}: restart it under a new name, "
                        "or clear it",
                    )
                )
    for decision in d.decisions:
        about = decision.get("about") if isinstance(decision.get("about"), dict) else {}
        if decision.get("status") == "answered" and about.get("type") == "risk":
            risk = about.get("risk")
            if not any(
                c.get("field") == "risk"
                and c.get("risk") == risk
                and isinstance(c.get("about"), dict)
                and c["about"].get("item") == about.get("item")
                and isinstance(c.get("cause"), dict)
                and isinstance(c["cause"].get("answer"), dict)
                and c["cause"]["answer"].get("id") == decision.get("id")
                for c in d.changes
            ):
                found.append(
                    Warning_(
                        "risk-answer-uncited",
                        decision.get("id", ""),
                        f"{decision.get('id')} is answered but no change accepts {about.get('item')} {risk}: add the "
                        "change",
                    )
                )
    for item in d.items:
        if item.get("kind") == "behaviour" and not item.get("ambiguity"):
            found.append(
                Warning_(
                    "behaviour-without-ambiguity",
                    item.get("id", ""),
                    f"{item.get('id')} has no ambiguity: run a behaviour verifier on it, or set ambiguity to what "
                    "it found",
                )
            )
    finals = {b.get("move") for b in d.briefs if b.get("status") == "final"}
    for move in d.moves:
        if d.option_move(move) in BRIEF_MOVES and move.get("id") not in finals:
            draft = next((b for b in d.briefs if b.get("move") == move.get("id")), None)
            then = (
                f"finish {draft.get('id')} and run `better.pyz brief {label} {draft.get('id')}`"
                if draft
                else "add a brief version for it"
            )
            found.append(
                Warning_(
                    "move-without-brief",
                    move.get("id", ""),
                    f"{move.get('id')} writes a brief and none is final: {then}",
                )
            )
    order = [m.get("id") for m in d.moves]
    for brief in d.briefs:
        if brief.get("status") == "draft" and brief.get("move") in order:
            later = order[order.index(brief["move"]) + 1 :]
            if later:
                found.append(
                    Warning_(
                        "draft-brief-older",
                        brief.get("id", ""),
                        f"{brief.get('id')} is a draft for {brief['move']}, and {later[0]} was chosen after it: "
                        f"finish it with brief, or write the brief for {later[-1]}",
                    )
                )
    if (d.unit.path / REDACT_STATE).exists():
        found.append(
            Warning_(
                "redact-unfinished",
                REDACT_STATE,
                f"a redact stopped part way: run `better.pyz redact {label}` again with the same request",
            )
        )
    removed = [e.get("id") for e in d.evidence if e.get("status") == "removed"]
    for brief in d.briefs:
        text = _brief_text(d, brief) if brief.get("status") == "final" else None
        for ident in removed:
            if text is not None and f"<!-- {ident} -->" in text:
                found.append(
                    Warning_(
                        "brief-holds-removed",
                        brief.get("id", ""),
                        f"{brief.get('id')} still holds the block of removed {ident}: run redact again",
                    )
                )
    evidence_events = derive.evidence_event_texts(d.conversation)
    for e in d.evidence:
        texts = _evidence_texts(e, evidence_events)
        for where, ident, record in _holders(d, e):
            if any(_occurs(t, s) for t in texts for s in _strings(record)):
                found.append(
                    Warning_(
                        "evidence-text-copied",
                        e.get("id", ""),
                        f"the words of {e.get('id')} also occur in {where} {ident}: remove the copy and cite "
                        f"{e.get('id')} by id",
                    )
                )
    events = read_events(d.conversation, str(d.head.get("coordinator")))
    pointed = {
        s
        for group in (d.items, d.changes, d.options, d.moves, d.briefs, d.decisions, d.tests, d.evidence, d.sources)
        for r in group
        for s in _strings(r)
    }
    for event, state, extra in events.found:
        ident = event["id"]
        if state == "done" and not extra.get("closed_by_user") and ident not in pointed and not events.answered(extra):
            found.append(
                Warning_(
                    "done-event-unanswered",
                    ident,
                    f"event {ident} is marked done, but no record points to it and no reply answers it: reply with "
                    "what was done",
                )
            )
    later_moves = [m for m in d.moves if _at(m)]
    for event, _, _ in events.open:
        when = _at(event)
        if event.get("type") not in ("choose", "answer") or when is None:
            continue
        newer = [m.get("id") for m in later_moves if _at(m) > when]
        newer += [
            e.get("id")
            for e, _, _ in events.found
            if e.get("type") == "answer" and e is not event and (_at(e) or when) > when
        ]
        if newer:
            found.append(
                Warning_(
                    "open-event-older",
                    event.get("id", ""),
                    f"{event.get('type')} event {event.get('id')} is still open, and {newer[0]} came after it: handle "
                    "it, or reply and mark it done",
                )
            )
    found += _step_problems(d, finals)
    return found


def _step_problems(d: Discovery, finals: set) -> list[Warning_]:
    step = d.head.get("step")
    if not isinstance(step, str) or not step.isdigit():
        return []
    number, found = int(step), []
    if number >= 6 and not d.moves:
        found.append(
            Warning_(
                "step-disagrees",
                "discover.json",
                f"step {step} follows a move, and none is recorded: choose one, or set the step back to 5",
            )
        )
    if number >= 9 and not finals:
        found.append(
            Warning_(
                "step-disagrees",
                "discover.json",
                f"step {step} hands a brief on, and none is final: run brief, or set the step back to 8",
            )
        )
    if number >= 10 and not d.head.get("handed"):
        found.append(
            Warning_(
                "step-disagrees",
                "discover.json",
                f"step {step} follows the hand-on, and handed is not recorded: hand the brief on, or set the step back to 9",
            )
        )
    return found


# ---------------------------------------------------------------- check


@cli.check_step(SKILL.name)
def _check_step(unit: Unit, run: cli.Run) -> int:
    """After every record passed its schemas: the warnings. They never fail the check."""
    for warning in warnings_of(load(unit, run), run.now()):
        run.err(f"warning: {warning.text}")
    return 0


# ---------------------------------------------------------------- summary


def _line(run: cli.Run, record_type: str, /, **fields: Any) -> None:
    run.out(json.dumps({"type": record_type, **fields}, ensure_ascii=True))


def _risks(view: derive.ItemView | None) -> dict:
    return {"accepted": list(view.accepted_risks), "open": list(view.open_risks)} if view else {}


def _summary_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("unit", help="the discovery, such as .discover/my-idea")


@cli.verb(
    "summary",
    help="print where a discovery stands as JSON lines, so an agent can resume it; exit 1 if a record is invalid",
    arguments=_summary_arguments,
    skills=(SKILL.name,),
)
def summary(args: argparse.Namespace, run: cli.Run) -> int:
    unit = paths.resolve_unit(args.unit, run.skill)
    d = load(unit, run)
    head = d.head
    _line(
        run,
        "head",
        coordinator=head.get("coordinator"),
        idea=head.get("idea"),
        appetite=head.get("appetite"),
        setting=head.get("setting"),
        step=head.get("step"),
        status=head.get("status"),
        handed=head.get("handed"),
    )
    for decision in d.decisions:
        _line(run, "decision", **{k: decision.get(k) for k in ("id", "about", "asked", "default", "status", "answer")})
    events = read_events(d.conversation, str(head.get("coordinator")))
    for event, state, extra in events.open:
        rest = {k: v for k, v in event.items() if k not in ("type", "at", "by", "id")}
        _line(
            run,
            "event",
            id=event.get("id"),
            event=event.get("type"),
            at=event.get("at"),
            state=state,
            fields=rest,
            **extra,
        )
    for move in d.moves:
        _line(
            run,
            "move",
            id=move.get("id"),
            option=move.get("option"),
            move=d.option_move(move),
            step=move.get("step"),
            why=move.get("why"),
            answer=move.get("answer"),
        )
    for brief in d.briefs:
        _line(
            run,
            "brief",
            **{k: brief.get(k) for k in ("id", "move", "status", "file", "sha256", "decision", "questions")},
        )
    views = derive.derive(d.items, d.changes, d.moves).items
    for item in d.items:
        view = views.get(item.get("id"))
        _line(
            run,
            "item",
            id=item.get("id"),
            kind=item.get("kind"),
            text=item.get("text"),
            state=view.state if view else None,
            importance=view.importance if view else None,
            risks=_risks(view),
            checker=item.get("checker"),
            since=item.get("since"),
        )
    for e in d.evidence:
        if e.get("status") == "checking":
            _line(
                run,
                "evidence",
                **{k: e.get(k) for k in ("id", "status", "source", "verifier", "since", "tries", "bears_on")},
            )
    for warning in warnings_of(d, run.now()):
        _line(run, "warning", code=warning.code, about=warning.about, text=warning.text)
    if d.errors:
        files = list(dict.fromkeys(e["file"] for e in d.errors))
        shown = [f"{e['file']}:{e['line']}: {e['field']}: {e['message']}" for e in d.errors[:SHOWN_ERRORS]]
        _line(run, "invalid", files=files, errors=shown)
        return cli.EXIT_REFUSED
    return cli.EXIT_DONE
