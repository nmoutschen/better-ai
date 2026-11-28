"""discover-better: the live page, on the shared shell.

`load(unit)` is the page's data, served at `/data`: every record of the discovery, each read one by one (a record that
fails its schema stays, without the fields that failed, and its errors are listed), with what the records derive for an
item (`derive`), the words of each piece of evidence, the text of each final brief, and for each option the revision the
page puts in a `choose` event, from the same records as the displayed option and items. The page draws the board and
the shared conversation from this data and the log.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .. import page, paths, resources, schema
from ..paths import Unit
from . import SKILL, derive, rules_moves, summary

RECORD_FILES = (
    ("items.jsonl", "items"),
    ("changes.jsonl", "changes"),
    ("options.jsonl", "options"),
    ("moves.jsonl", "moves"),
    ("briefs.jsonl", "briefs"),
    ("decisions.jsonl", "decisions"),
    ("tests.jsonl", "tests"),
    ("conversation.jsonl", "conversation"),
)


def _files(unit: Unit, folder: str) -> list[str]:
    path = unit.path / folder
    return sorted(f"{folder}/{p.name}" for p in path.glob("*.json")) if path.is_dir() else []


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _evidence_text(record: dict, events: dict[str, str]) -> str:
    """The words of a piece of evidence: the quote itself, or the text of the page event that holds them."""
    words = record.get("words") if isinstance(record.get("words"), dict) else {}
    if words.get("type") == "event":
        return derive.evidence_event_text(events, words.get("event")) or ""
    return _text(words.get("text"))


def load(unit: Unit) -> dict:
    """The page's data for a unit. A bad file is in `errors`; a failure in this code is a bug, not an error."""
    docs = schema.docs_for(SKILL.package)
    cache: dict[str, Any] = {}
    now, cutoff = datetime.now(timezone.utc), resources.cutoff()
    errors: list[dict] = []

    def read(relative: str) -> list[dict]:
        done = schema.read_records(unit, relative, docs, cache, now, cutoff, keep_invalid=True)
        errors.extend(done.errors)
        return page.log_records(done) if relative == page.LOG else done.records  # the log keeps its lines

    head = read(unit.kind.head)
    found: dict[str, Any] = {attribute: read(name) for name, attribute in RECORD_FILES}
    sources = {s["id"]: s for name in _files(unit, "sources") for s in read(name) if isinstance(s.get("id"), str)}
    evidence = [r for name in _files(unit, "evidence") for r in read(name)]
    events = derive.evidence_event_texts(found["conversation"])
    view = derive.derive(found["items"], found["changes"], found["moves"])

    items = []
    for item in found["items"]:
        shown = view.items.get(item["id"]) if isinstance(item.get("id"), str) else None
        items.append(
            {
                **item,
                "state": shown.state if shown else derive.UNVERIFIED,
                "recorded_state": shown.recorded_state if shown else derive.UNVERIFIED,
                "importance": shown.importance if shown else None,
                "accepted_risks": list(shown.accepted_risks) if shown else [],
                "open_risks": list(shown.open_risks) if shown else [],
            }
        )

    shown_evidence = []
    for record in evidence:
        source = sources.get(record.get("source")) or {}
        origin = source.get("origin") if isinstance(source.get("origin"), dict) else {}
        shown_evidence.append(
            {
                **record,
                "text": _evidence_text(record, events),
                "origin": origin,
                "source_title": _text(source.get("title")),
                "said_by_role": _text(source.get("said_by_role")),
            }
        )

    briefs = []
    for brief in found["briefs"]:
        body = None
        if brief.get("status") == "final" and isinstance(brief.get("file"), str):
            try:
                body = paths.read_bytes(unit, brief["file"]).decode("utf-8", errors="replace")
            except (OSError, paths.Refused):
                body = None
        briefs.append({**brief, "text": body})

    revision_items = rules_moves.revision_items(found["items"], view.items)
    revisions = {
        option["id"]: rules_moves.revision_of(option, revision_items)
        for option in found["options"]
        if isinstance(option.get("id"), str) and not option.get("_errors")
    }

    # Each agent at work and its latest record, by summary's one rule (S56, L4): the page shows "No word from…" from it.
    known = summary.Discovery(
        unit, head=head[0] if head else {}, evidence=evidence, sources=list(sources.values()), **found
    )
    working = {r.get("checker") for r in found["items"] + found["tests"]} | {e.get("verifier") for e in evidence}
    last_word = {}
    for agent in sorted(a for a in working if isinstance(a, str) and a):
        heard = summary.last_word(known, agent)
        last_word[agent] = heard.strftime(schema.TIME) if heard else None

    return {
        "errors": errors,
        "head": head[0] if head else {},
        "items": items,
        "changes": found["changes"],
        "options": found["options"],
        "moves": found["moves"],
        "briefs": briefs,
        "decisions": found["decisions"],
        "tests": found["tests"],
        "evidence": shown_evidence,
        "conversation": found["conversation"],
        "revisions": revisions,
        "last_word": last_word,
        "chosen": view.chosen,
    }


SPEC = page.register(
    SKILL,
    page.PageSpec(
        title="Discovery",
        agent="coordinator",
        main="discover/page.html",
        aside="page/agents.html",
        load=load,
        events="discover-events.schema.json",
        assets={"/discover.css": "discover/page.css", "/discover.js": "discover/page.js"},
        css=("/discover.css",),
        js=("/discover.js",),
        capabilities=("decisions", "accept"),  # every thread can be closed and reopened
        methods=summary.PAGE_EVENTS,
        items=("note", "answer", *summary.PAGE_EVENTS),
        empty="Nothing yet. Answer a question, add evidence, or write to the coordinator below.",
    ),
)
