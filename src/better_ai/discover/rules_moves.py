"""discover-better: the rules for moves and briefs.

A move is the user's choice of one option, and the answer that proves it: a `choose` event of the page, or the user's
words in the chat. Four of the seven moves write a brief (`BRIEF_MOVES`), and three of those need a second, explicit
confirmation (`CONFIRMED_MOVES`). The rules run where the design says:

- `move-rules`, a schema check (`x-check` on `move.schema.json`), runs on `add` and in `check` for every move: the event
  names the move's option and was confirmed, a chat Expand, Adopt or Stop has an answered confirmation about the same
  option, no other move rests on the same event or confirmation, and a chat move does not repeat another's words;
- the revision rule runs on `add` only (`revision_of`): what the option and the items looked like when the user chose is
  compared with what they are now. `check` cannot repeat it, because the items change after a move is recorded;
- `brief-rules`, a schema check on `brief.schema.json`, runs on `add` and in `check`: a brief belongs to a move that
  writes one, a move has one draft brief at a time (a final one may be followed by a new version), and a final brief's file is there with the recorded `sha256`;
- `set` and `add` refuse `status: final` on a brief: only the `brief` verb makes one final.

Every message names the existing record and the next action.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

from .. import paths, records
from ..schema import Context, hook
from . import SKILL, derive

BRIEF_MOVES = ("expand", "shrink", "adopt", "stop")  # the moves that write a brief
CONFIRMED_MOVES = ("expand", "adopt", "stop")  # the moves that need the second step: cost and how hard to undo


def _rows(context: Context, name: str) -> list[dict]:
    return [r for r in context.read_jsonl(name) or [] if isinstance(r, dict)]


def _by_id(rows: list[dict]) -> dict[str, dict]:
    return {r["id"]: r for r in rows if isinstance(r.get("id"), str)}


def _words(text: Any) -> str:
    return " ".join(str(text).split()).casefold()


def _latest_event(context: Context, ident: str) -> dict | None:
    """The page's event with this id, in its latest version (a conversation line may reuse an id)."""
    found = [e for e in _rows(context, "conversation.jsonl") if e.get("id") == ident]
    return found[-1] if found else None


# ---------------------------------------------------------------- the revision of an option


def revision_of(option: dict, items: list[dict], changes: list[dict]) -> str:
    """The hash the page puts in a `choose` event: of the option as it is, and of every item as the page shows it (its
    text and, for a behaviour, its testable form, with the state and importance derived from the changes). The page
    and the move rule both call this, so they cannot disagree about what the user saw."""
    view = derive.derive(items, changes).items
    shown = []
    for item in items:
        if not isinstance(item.get("id"), str):
            continue
        found = view.get(item["id"])
        shown.append(
            {
                "id": item["id"],
                "kind": item.get("kind"),
                "text": item.get("text"),
                "testable": item.get("testable"),
                "state": found.state if found else None,
                "importance": found.importance if found else None,
            }
        )
    body = {"option": {k: v for k, v in option.items() if k not in ("at", "by")}, "items": shown}
    text = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def revision_in(folder: Path, option: str) -> str | None:
    """`revision_of` for an option of a discovery's folder; None if the option is not there."""
    chosen = next((o for o in derive._read_lines(folder / "options.jsonl") if o.get("id") == option), None)
    if chosen is None:
        return None
    return revision_of(chosen, derive._read_lines(folder / "items.jsonl"), derive._read_lines(folder / "changes.jsonl"))


# ---------------------------------------------------------------- moves


def _page_problems(record: dict, kind: str | None, context: Context, others: list[dict]) -> list[tuple[str, str]]:
    ident = record["answer"]["event"]
    event = _latest_event(context, ident)
    problems = []
    if event is None or event.get("type") != "choose":
        return problems  # missing or of another kind: the pointer says so
    if event.get("option") != record.get("option"):
        problems.append(
            (
                "answer.event",
                f"{ident} chose {event.get('option')}, not {record.get('option')}: record the move for "
                f"{event.get('option')}, or reply to the event and mark it done",
            )
        )
    if kind in CONFIRMED_MOVES and event.get("confirmed") is not True:
        problems.append(
            (
                "answer.event",
                f"{ident} was not confirmed, and {kind} needs the second click: reply to the event, mark it done and "
                "ask the user to choose again",
            )
        )
    for move in others:
        if isinstance(move.get("answer"), dict) and move["answer"].get("event") == ident:
            problems.append(("answer.event", f"already recorded as {move.get('id')}: mark the event done"))
    return problems


def _chat_problems(record: dict, kind: str | None, context: Context, others: list[dict]) -> list[tuple[str, str]]:
    answer = record["answer"]
    problems = []
    confirm = answer.get("confirm")
    if kind in CONFIRMED_MOVES:
        if not confirm:
            problems.append(
                (
                    "answer.confirm",
                    f"a chat {kind} needs a confirmation: ask the user about the cost of {record.get('option')} and "
                    "how hard it is to undo, record their answer as a decision, then add the move with confirm",
                )
            )
        else:
            decision = _by_id(_rows(context, "decisions.jsonl")).get(confirm)
            if decision is not None:
                about = decision.get("about") if isinstance(decision.get("about"), dict) else {}
                if about.get("type") != "option" or about.get("option") != record.get("option"):
                    problems.append(
                        (
                            "answer.confirm",
                            f"{confirm} is not about {record.get('option')}: ask the user to confirm this option",
                        )
                    )
                elif decision.get("status") != "answered":
                    problems.append(
                        ("answer.confirm", f"{confirm} is still waiting: ask the user, and add the move once answered")
                    )
    for move in others:
        theirs = move.get("answer") if isinstance(move.get("answer"), dict) else {}
        if confirm and theirs.get("confirm") == confirm:
            problems.append(("answer.confirm", f"{confirm} already confirms {move.get('id')}: ask again for this move"))
        if (
            theirs.get("type") == "chat"
            and move.get("option") == record.get("option")
            and _words(theirs.get("text")) == _words(answer.get("text"))
        ):
            problems.append(("answer.text", f"already recorded as {move.get('id')}: nothing to add"))
    return problems


@hook("move-rules")
def _move_rules(record: dict, context: Context) -> list[tuple[str, str]]:
    """The move meets the answer that proves it, and no other move rests on the same answer."""
    option = _by_id(_rows(context, "options.jsonl")).get(record.get("option"))
    kind = option.get("move") if option else None
    answer = record.get("answer")
    if not isinstance(answer, dict):
        return []
    others = [m for m in _rows(context, "moves.jsonl") if m.get("id") != record.get("id")]
    if answer.get("type") == "page" and isinstance(answer.get("event"), str):
        return _page_problems(record, kind, context, others)
    if answer.get("type") == "chat":
        return _chat_problems(record, kind, context, others)
    return []


@records.add_guard(SKILL.name, "move")
def _the_choice_is_current(ctx: records.AddContext) -> None:
    """Refuse a page move when the option or an item changed since the user chose (the revision on the event)."""
    answer = ctx.record.get("answer")
    if not isinstance(answer, dict) or answer.get("type") != "page":
        return
    events = [e for e in derive._read_lines(ctx.unit.path / "conversation.jsonl") if e.get("id") == answer.get("event")]
    event = events[-1] if events else None
    if event is None or event.get("type") != "choose" or event.get("option") != ctx.record.get("option"):
        return  # the move rule says what is wrong
    now = revision_in(ctx.unit.path, ctx.record["option"])
    if now is not None and event.get("revision") != now:
        raise paths.refusal(
            ctx.unit.label,
            f"{ctx.record['option']} or an item it rests on changed since the user chose it",
            f"reply to {answer['event']}, mark it done and ask the user to confirm again",
        )


# ---------------------------------------------------------------- briefs


def _final_problems(record: dict, context: Context) -> list[tuple[str, str]]:
    name, digest = record.get("file"), record.get("sha256")
    if not isinstance(name, str) or not isinstance(digest, str):
        return []
    pure = PurePosixPath(name)
    if pure.is_absolute() or ".." in pure.parts:
        return [("file", f"{name} is not a path inside the discovery: a brief is brief/v<n>.md")]
    path = context.directory / name
    if path.is_symlink() or not path.is_file():
        return [("file", f"{name} is missing: restore the file as it was when {record.get('id')} was made final")]
    try:
        found = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        return [("file", f"{name} cannot be read ({paths.reason(error)}): restore it")]
    if found != digest:
        return [
            (
                "sha256",
                f"{name} does not have the recorded sha256: restore the file as it was when {record.get('id')} was "
                "made final",
            )
        ]
    return []


@hook("brief-rules")
def _brief_rules(record: dict, context: Context) -> list[tuple[str, str]]:
    """The brief is for a move that writes one, the move has no other draft brief, and a final one has its file."""
    problems: list[tuple[str, str]] = []
    move = _by_id(_rows(context, "moves.jsonl")).get(record.get("move"))
    option = _by_id(_rows(context, "options.jsonl")).get(move.get("option")) if move else None
    if option and option.get("move") not in BRIEF_MOVES:
        problems.append(
            (
                "move",
                f"{record.get('move')} is a {option.get('move')} move, which writes no brief: only "
                f"{', '.join(BRIEF_MOVES[:-1])} and {BRIEF_MOVES[-1]} do",
            )
        )
    mine = record.get("id")
    briefs = _rows(context, "briefs.jsonl")
    if record.get("status") == "draft":
        rivals = [b for b in briefs if b.get("id") != mine]  # a draft is held against every other brief
    else:
        rivals = briefs[: next((i for i, b in enumerate(briefs) if b.get("id") == mine), len(briefs))]  # the earlier
    for other in rivals:
        if other.get("move") == record.get("move") and other.get("status") == "draft":
            problems.append(
                ("move", f"{other.get('id')} is already the draft brief for {record.get('move')}: change it with set")
            )
    if record.get("status") == "final":
        problems += _final_problems(record, context)
    return problems


def _only_brief_makes_final(ctx: Any, what: str, field: str | None = None) -> None:
    ident = ctx.record.get("id")
    raise paths.refusal(
        ctx.unit.label,
        f"{what} cannot change {field} of {ident}" if field else f"{what} cannot make {ident} final",
        f"finish the text, then run `better.pyz brief {ctx.unit.label} {ident}`, which writes the file and sets it final",
    )


@records.add_guard(SKILL.name, "brief")
def _add_is_for_drafts(ctx: records.AddContext) -> None:
    if ctx.record.get("status") == "final":
        _only_brief_makes_final(ctx, "add")


GUARDED = ("status", "file", "sha256", "redacted")  # what `brief` and `redact` write: a draft never gains them by set


@records.set_step(SKILL.name)
def _set_leaves_moves_and_final_briefs_alone(ctx: records.SetContext) -> None:
    """A move is never changed. A final brief is never changed by set: only `redact` edits one, in place. A draft may
    change its text, but never gains `status`, `file`, `sha256` or `redacted`, whether the field is given or removed."""
    ident, kind = ctx.record.get("id"), ctx.record.get("type")
    if kind == "move":
        raise paths.refusal(
            ctx.unit.label, f"{ident} is a move, and set cannot change it", "add a new move for the user's new choice"
        )
    if kind != "brief":
        return
    if ctx.record.get("status") == "final":
        raise paths.refusal(
            ctx.unit.label,
            f"{ident} is final, and set cannot change it",
            f"add the next brief version for {ctx.record.get('move')}, or run redact to remove evidence",
        )
    touched = [f for f in GUARDED if f in ctx.patch or f in ctx.unsets]
    if ctx.patch.get("status") == "final":
        _only_brief_makes_final(ctx, "set")
    if touched:
        _only_brief_makes_final(ctx, "set", touched[0])
