"""discover-better: the `brief` and `redact` verbs.

- `brief <unit> v<n>` writes version n of the brief from the records, as `brief/v<n>.md`, and sets the version final
  with the file's sha256. It first checks that no item it shows rests on a change that no longer holds. It renders to a
  temporary file, links that file to its name, and then sets the version final, so a run that stops at any point is
  finished by running it again.
- `redact <unit> E-<agent>-<n> --request <id>` removes a person's words from the unit: from each final brief (in
  place, by the marked block of the evidence), from a leftover draft file or temporary file of the brief folder that
  holds the block (removed), from the page event that holds them, from the source, from the result text of each test
  that cites the evidence, and from the evidence itself. It works from a state file, `.redact`, so a run that stops is finished by running it again, and
  the page does not start while that file exists.

A person's words are stored in one field of one record and everything else points to the evidence by id; the brief is
the one other place the words are copied to, and each copy sits in a block marked with the evidence id (the text of a
test result that cites only that evidence sits in the block too). Evidence from the user's files and tools is shown by
role in any discovery, never by its words.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .. import cli, page, paths, records, resources, schema
from ..paths import Refused, Unit, refusal
from . import SKILL, derive, rules_changes

BRIEF_FOLDER = "brief"
STATE = ".redact"  # the state file of a redact that has not finished
SERVER = ".server"  # where the page says it is served
REMOVED = "[removed]"
VERSION = re.compile(r"^v\d+$")
EVIDENCE_ID = re.compile(r"^E-[\w.-]+-\d+$")
POINTS = ("rendered", "linked", "recorded")  # where a `brief` run may stop; a test stops it at each
CONTINUE = "partly done: run redact again"


def _reached(point: str) -> None:
    """A seam for tests: `brief` calls it after each of POINTS."""


def _after_place(place: str) -> None:
    """A seam for tests: `redact` calls it after the plan is written and after each place is done."""


# ---------------------------------------------------------------- reading the unit


@dataclass
class Data:
    head: dict
    items: list[dict] = field(default_factory=list)
    changes: list[dict] = field(default_factory=list)
    options: list[dict] = field(default_factory=list)
    moves: list[dict] = field(default_factory=list)
    tests: list[dict] = field(default_factory=list)
    briefs: list[dict] = field(default_factory=list)
    decisions: list[dict] = field(default_factory=list)
    conversation: list[dict] = field(default_factory=list)
    evidence: dict[str, dict] = field(default_factory=dict)
    sources: dict[str, dict] = field(default_factory=dict)


def _lines(unit: Unit, relative: str) -> list[dict]:
    return derive.read_lines(unit.path, relative)


def _folder(unit: Unit, folder: str) -> dict[str, dict]:
    base = unit.target(folder)
    found: dict[str, dict] = {}
    if not base.is_dir():
        return found
    for path in sorted(base.glob("*.json")):
        relative = f"{folder}/{path.name}"
        record = derive.read_object(unit.path, relative)
        if record is None:
            raise refusal(f"{unit.label}/{relative}", "does not parse", f"fix it, then run check {unit.label}")
        if isinstance(record.get("id"), str):
            found[record["id"]] = record
    return found


def _load(unit: Unit, *, conversation: list[dict] | None = None) -> Data:
    head = derive.read_object(unit.path, unit.kind.head)
    if head is None:
        raise refusal(unit.label, f"{unit.kind.head} does not parse", f"fix it, then run check {unit.label}")
    return Data(
        head=head,
        items=_lines(unit, "items.jsonl"),
        changes=_lines(unit, "changes.jsonl"),
        options=_lines(unit, "options.jsonl"),
        moves=_lines(unit, "moves.jsonl"),
        tests=_lines(unit, "tests.jsonl"),
        briefs=_lines(unit, "briefs.jsonl"),
        decisions=_lines(unit, "decisions.jsonl"),
        conversation=_lines(unit, "conversation.jsonl") if conversation is None else conversation,
        evidence=_folder(unit, "evidence"),
        sources=_folder(unit, "sources"),
    )


def _internal(data: Data) -> bool:
    """Whether the discovery is for the user's own organisation. The head says so, or the last change of the setting
    does: either one keeps people's words out of a brief, so a change to external never reveals words by mistake."""
    last = None
    for change in data.changes:
        if change.get("field") == "setting" and (change.get("about") or {}).get("type") == "discovery":
            last = change.get("to")
    return data.head.get("setting") == "internal" or last == "internal"


# ---------------------------------------------------------------- what still holds


def _add_a_change(items: list[str], unit: Unit) -> str:
    return f"add a change for {' and '.join(items)}, then run brief again"


# ---------------------------------------------------------------- rendering


_ESCAPED = {"&": "&amp;", "<": "&lt;", ">": "&gt;"}
_MARKDOWN = re.compile(r"[\\`*_\[\]{}<>&~|#!]")


def inline(text: Any) -> str:
    """Text from outside as one inert line: whitespace and control characters are one space, and every character that
    markdown or HTML would act on is escaped, so it cannot end a block, open a link or forge a marker."""
    one = "".join(c if c.isprintable() else " " for c in " ".join(str(text).split()))
    one = one.replace("://", ":\\/\\/")
    return _MARKDOWN.sub(lambda m: _ESCAPED.get(m.group(), "\\" + m.group()), one)


def _url(url: str) -> str:
    return "<" + urllib.parse.quote(url, safe=":/?#[]@!$&'()*+,;=%-._~") + ">"


def _sort_key(ident: str) -> tuple:
    found = re.fullmatch(r"E-(.+)-(\d+)", ident)
    return (found.group(1), int(found.group(2))) if found else (ident, 0)


def _by_role(origin: dict, internal: bool) -> bool:
    """Whether the brief shows the evidence's summary by role in place of its words: the user's own words in an internal
    discovery, and anything from the user's files or tools in any discovery."""
    return origin.get("type") in ("file", "tool") or (internal and origin.get("type") == "you")


def _results(data: Data, ident: str, internal: bool) -> list[str]:
    """The text of each test result that cites only this evidence, as lines of its block: the one place a result's
    words are copied to, so redacting the evidence reaches them. A result that cites several evidence keeps its text
    out of the brief, and so does any result in an internal discovery."""
    lines = []
    for test in data.tests:
        result = test.get("result")
        if isinstance(result, dict) and result.get("evidence") == [ident] and not internal:
            lines.append(
                f'  - Result of {inline(test.get("id"))} ({inline(result.get("outcome"))}): "{inline(result.get("text"))}"'
            )
    return lines


def _evidence_block(ident: str, evidence: dict, data: Data, internal: bool, events: dict[str, str]) -> str:
    source = data.sources.get(evidence.get("source"), {})
    origin = source.get("origin") or {}
    about = "about your users" if evidence.get("about") == "your users" else "from elsewhere"
    bears = ", ".join(f"{b['direction']} {b['item']}" for b in evidence.get("bears_on") or []) or "bears on no item"
    facts = f"({inline(evidence.get('kind'))}, {about}; {inline(evidence.get('status'))}; {inline(bears)})"
    if _by_role(origin, internal):
        summary = inline(evidence.get("summary") or "no summary given")
        if origin.get("type") == "you":
            line = f"Reported by you, from {inline(source.get('said_by_role') or 'a person')}: {summary} {facts}."
        else:  # a file or a tool: the summary, under the source's own title
            line = f"From {inline(source.get('title') or 'your files')}: {summary} {facts}."
    else:
        words = evidence.get("words") or {}
        text = (
            (derive.evidence_event_text(events, words.get("event")) or "words not found")
            if words.get("type") == "event"
            else words.get("text")
        )
        line = f'"{inline(text)}" {facts}.'
        title = inline(source.get("title") or "no title")
        line += f" Source: {title}" + (f", {_url(origin['url'])}" if origin.get("type") == "web" else "") + "."
    return "\n".join([f"<!-- {ident} -->", f"- {line}", *_results(data, ident, internal), f"<!-- /{ident} -->"])


def _risk_line(risk: dict) -> str:
    return f"{inline(risk.get('id'))} ({inline(risk.get('kind'))}) {inline(risk.get('text'))}"


def _item_lines(item: dict, view: derive.ItemView) -> list[str]:
    mark = " (alternative idea)" if item.get("alternative") else ""
    head = f"- {inline(item['id'])} ({inline(item.get('kind'))}){mark}: {inline(item.get('text'))} State: {inline(view.state)}."
    if view.importance:
        head += f" Importance: {inline(view.importance)}."
    lines = [head]
    if item.get("rests_on"):
        lines.append(f"  - Rests on: {', '.join(inline(r) for r in item['rests_on'])}")
    by_id = {r.get("id"): r for r in item.get("risks") or [] if isinstance(r, dict)}
    if view.accepted_risks:
        lines.append("  - Accepted risks: " + "; ".join(_risk_line(by_id[r]) for r in view.accepted_risks))
    if view.open_risks:
        lines.append("  - Open risks: " + "; ".join(_risk_line(by_id[r]) for r in view.open_risks))
    testable = item.get("testable")
    if isinstance(testable, dict):
        lines.append(f"  - Testable ({inline(testable.get('form'))}): {inline(testable.get('text'))}")
    return lines


def _said(result: dict, cited: list) -> str:
    cited = list(dict.fromkeys(cited))  # one marker pair per evidence, even if cited twice
    """The text of a result in the tests section. A result that cites one evidence has its text in that evidence's block;
    one that cites several has it here, inside the markers of each, so redacting any one of them removes it; one that
    cites none has it plain."""
    text = f'"{inline(result.get("text"))}"'
    if not cited:
        return f" {text}"
    if len(cited) == 1 or not all(isinstance(e, str) and EVIDENCE_ID.fullmatch(e) for e in cited):
        return ""
    return " " + "".join(f"<!-- {e} -->" for e in cited) + text + "".join(f"<!-- /{e} -->" for e in reversed(cited))


def _test_lines(test: dict, internal: bool) -> list[str]:
    head = (
        f"- {inline(test.get('id'))} ({inline(test.get('kind'))}, {inline(test.get('status'))}): "
        f"{inline(test.get('what'))} Settles {', '.join(inline(s) for s in test.get('settles') or [])}. "
        f"Rule: {inline(test.get('rule'))} Cost: {inline(test.get('cost'))}. Run by: {inline(test.get('runner'))}."
    )
    lines = [head]
    result = test.get("result")
    if isinstance(result, dict):
        cited = result.get("evidence") or []
        said = "" if internal else _said(result, cited)
        ids = ", ".join(inline(e) for e in result.get("evidence") or [])
        lines.append(f"  - Result ({inline(result.get('outcome'))}):{said}" + (f" Evidence: {ids}." if ids else ""))
    if test.get("status") == "removed":
        lines.append(f"  - Removed: {inline(test.get('reason'))}")
    return lines


def _bullets(lines: list[str], empty: str) -> str:
    return "\n".join(lines) if lines else empty


def render(unit: Unit, data: Data, version: str) -> str:
    """The text of one brief version, from the skeleton next to this module and the records."""
    record = next(b for b in data.briefs if b.get("id") == version)
    move = next((m for m in data.moves if m.get("id") == record.get("move")), None)
    if move is None:
        raise refusal(
            unit.label,
            f"{version} is for move {record.get('move')}, which is not in moves.jsonl",
            "fix the brief's move",
        )
    option = next((o for o in data.options if o.get("id") == move.get("option")), {})
    internal = _internal(data)
    derived = derive.derive(data.items, data.changes, data.moves)
    shown = [
        f"- Version: {inline(version)}",
        f"- Move: {inline(move['id'])}, {inline(option.get('move'))}",
        f"- Option: {inline(option.get('id', move.get('option')))}, {inline(option.get('text'))}",
        f"- Cost: {inline(option.get('cost'))}. Speed: {inline(option.get('speed'))}. "
        f"Upkeep: {inline(option.get('upkeep'))}. How hard to undo: {inline(option.get('undo'))}.",
    ]
    why = record.get("why") or move.get("why")
    decision = [
        f"Decision: {inline(record.get('decision') or 'none recorded')}",
        f"Why: {inline(why or 'none recorded')}",
    ]
    items = [
        line
        for item in data.items
        if item.get("id") in derived.items
        for line in _item_lines(item, derived.items[item["id"]])
    ]
    blocks = []
    events = derive.evidence_event_texts(data.conversation)
    corrected = {e.get("corrects") for e in data.evidence.values()}  # a reworded quote shows as its correction
    for ident in sorted(data.evidence, key=_sort_key):
        found = data.evidence[ident]
        if found.get("status") == "removed" or ident in corrected:
            continue
        if not EVIDENCE_ID.fullmatch(ident):
            raise refusal(unit.label, f"evidence {ident!r} has an id that is not valid", f"run check {unit.label}")
        blocks.append(_evidence_block(ident, found, data, internal, events))
    tests = [line for test in data.tests for line in _test_lines(test, internal)]
    questions = [f"- {inline(q)}" for q in record.get("questions") or []]
    values = {
        "version": inline(version),
        "move": "\n".join(shown),
        "decision": "\n\n".join(decision),
        "items": _bullets(items, "No items."),
        "evidence": "\n\n".join(blocks) if blocks else "No evidence.",
        "tests": _bullets(tests, "No tests."),
        "questions": _bullets(questions, "None recorded."),
    }
    return re.sub(r"\{\{(\w+)\}\}", lambda m: values[m.group(1)], resources.read_text("discover/brief.md"))


# ---------------------------------------------------------------- writing a line of a file in place


def _rewritten(
    unit: Unit, relative: str, edit: Callable[[dict], dict | None], *, ascii_only: bool = False
) -> tuple[list[int], Callable[[], None] | None]:
    """The lines of a JSONL file `edit` changes (it returns the new record, or None to leave a line) and a function
    that writes them, or None when nothing changes. The write is refused (busy) if the file changed since it was read."""
    text, stat = records._read(unit, relative, True)
    if text is None:
        return [], None
    pieces = text.split("\n")
    changed: list[int] = []
    for index, piece in enumerate(pieces):
        try:
            value = json.loads(piece) if piece.strip() else None
        except (ValueError, RecursionError):
            continue
        if not isinstance(value, dict):
            continue
        new = edit(value)
        if new is not None and new != value:
            pieces[index] = json.dumps(new, ensure_ascii=ascii_only) + ("\r" if piece.endswith("\r") else "")
            changed.append(index + 1)
    if not changed:
        return [], None

    def write() -> None:
        records._still(unit, relative, stat)
        paths.write_atomic(unit, relative, records._encode("\n".join(pieces)))

    return changed, write


def _valid(unit: Unit, record: dict, name: str) -> dict:
    problems = schema.check_record(record, [name])
    if problems:
        raise refusal(
            unit.label, f"the new {record.get('type')} is not valid: " + "; ".join(f"{f}: {m}" for f, m in problems)
        )
    return record


# ---------------------------------------------------------------- brief


def _brief_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("unit", help="the discovery, such as .discover/my-idea")
    parser.add_argument("version", help="the brief version to write, such as v1")


def _printed(file: str, sha256: str) -> str:
    return json.dumps({"file": file, "sha256": sha256, "status": "final"})


@cli.verb(
    "brief",
    help="write brief version v<n> from the records and set it final with the file's sha256",
    arguments=_brief_arguments,
    skills=(SKILL.name,),
)
def brief(args: argparse.Namespace, run: cli.Run) -> int:
    unit = paths.resolve_unit(args.unit, run.skill)
    version = args.version
    if not VERSION.fullmatch(version):
        raise refusal(unit.label, f"{version!r} is not a brief version", "name it v1, v2 and so on")
    conversation = schema.read_records(
        unit, "conversation.jsonl", schema.docs_for(SKILL.package), {}, run.now(), run.info.cutoff
    ).records
    data = _load(unit, conversation=conversation)
    record = next((b for b in data.briefs if b.get("id") == version), None)
    if record is None:
        raise refusal(unit.label, f"no brief {version} in briefs.jsonl", f"add it first: add {unit.label} brief")
    if record.get("status") == "final":
        return _again(run, unit, record)
    stale = rules_changes.stale_items(unit)
    if stale:
        reasons = "; ".join(f"{item}: {why}" for item, why in stale.items())
        raise refusal(unit.label, f"{version} cannot be rendered ({reasons})", _add_a_change(list(stale), unit))
    text = render(unit, data, version).encode("utf-8")
    paths.make_folder(unit, BRIEF_FOLDER)
    folder = unit.target(BRIEF_FOLDER)
    for orphan in folder.glob(f".{version}.md.*.tmp"):  # a run that stopped before it linked the file
        os.unlink(orphan)
    temporary = f"{BRIEF_FOLDER}/.{version}.md.{secrets.token_hex(8)}.tmp"
    paths.create_exclusive(unit, temporary, text)
    _reached("rendered")
    target = unit.target(f"{BRIEF_FOLDER}/{version}.md")
    try:
        try:
            os.link(unit.target(temporary), target)
        except FileExistsError:  # a draft: the file is an unfinished earlier run
            os.replace(unit.target(temporary), target)
    finally:
        if unit.target(temporary).exists():
            os.unlink(unit.target(temporary))
    _reached("linked")
    digest = hashlib.sha256(paths.read_bytes(unit, f"{BRIEF_FOLDER}/{version}.md")).hexdigest()
    file = f"{BRIEF_FOLDER}/{version}.md"

    def final(found: dict) -> dict | None:
        if found.get("id") != version:
            return None
        return _valid(unit, {**found, "status": "final", "file": file, "sha256": digest}, "brief.schema.json")

    _, write = _rewritten(unit, "briefs.jsonl", final)
    if write:
        write()
    _reached("recorded")
    run.out(_printed(file, digest))
    return cli.EXIT_DONE


def _again(run: cli.Run, unit: Unit, record: dict) -> int:
    version, file = record["id"], record["file"]
    next_version = f"v{int(version[1:]) + 1}"
    try:
        digest = hashlib.sha256(paths.read_bytes(unit, file)).hexdigest()
    except FileNotFoundError:
        raise refusal(unit.label, f"{version} is final but {file} is not there", f"add {next_version}") from None
    if digest != record["sha256"]:
        raise refusal(unit.label, f"{version} is final and {file} changed since", f"add {next_version}")
    run.out(_printed(file, digest))
    return cli.EXIT_DONE


# ---------------------------------------------------------------- redact


def _is_request(data: Data, evidence: str, request: str) -> bool:
    for event in data.conversation:
        if (
            event.get("id") == request
            and event.get("type") == "redact"
            and event.get("by") == "user"
            and event.get("evidence") == evidence
        ):
            return True
    for decision in data.decisions:
        if (
            decision.get("id") == request
            and decision.get("status") == "answered"
            and (decision.get("about") or {}) == {"type": "evidence", "evidence": evidence}
            and (decision.get("answer") or {}) == {"type": "chat", "text": f"remove {evidence}"}
        ):
            return True
    return False


def _server_pid(port: str) -> int | None:
    """The process that listens on the port, as `lsof` says; None where it cannot be found out."""
    try:
        done = subprocess.run(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    first = done.stdout.split()
    return int(first[0]) if first and first[0].isdigit() else None


def _server_answering(unit: Unit) -> str | None:
    """What to tell the user when the unit's page server answers, or None. The address file stays when a server is
    killed, so the server is asked."""
    try:
        text = paths.read_bytes(unit, SERVER).decode("utf-8", errors="replace")
    except FileNotFoundError:
        return None
    address = text.strip()
    found = re.fullmatch(r"http://127\.0\.0\.1:(\d+)/", address)
    if not found:
        return None
    asker = page.Conversation(unit, page.PageSpec(title="", agent="coordinator", main="", load=lambda _: {}), {})
    if not asker.answering():
        return None
    pid = _server_pid(found.group(1))
    return f"the page server answers at {address} ({'pid ' + str(pid) if pid else 'pid not known'})"


def _read_state(unit: Unit) -> dict | None:
    try:
        raw = paths.read_bytes(unit, STATE)
    except FileNotFoundError:
        return None
    try:
        state = json.loads(raw)
        if not (
            isinstance(state, dict) and isinstance(state.get("evidence"), str) and isinstance(state.get("steps"), list)
        ):
            raise ValueError
    except ValueError:
        raise refusal(
            f"{unit.label}/{STATE}", "is not a redact state file", "fix or remove it, then run redact again"
        ) from None
    return state


def _write_state(unit: Unit, state: dict) -> None:
    paths.write_atomic(unit, STATE, (json.dumps(state, indent=2) + "\n").encode("utf-8"))


@page.serve_guard(SKILL.name)
def _no_page_while_redacting(unit: Unit) -> None:
    state = _read_state(unit)
    if state is not None:
        raise refusal(
            unit.label,
            f"a redact of {state['evidence']} is partly done, and the page would show what it is removing",
            f"run redact {unit.label} {state['evidence']} --request {state.get('request', '<id>')} again, then serve",
        )


def _block(evidence: str) -> re.Pattern:
    return re.compile(rf"<!-- {re.escape(evidence)} -->.*?<!-- /{re.escape(evidence)} -->", re.DOTALL)


def _line_of(text: str, key: str) -> int:
    for number, line in enumerate(text.split("\n"), 1):
        if line.startswith(f'  "{key}"'):
            return number
    return 1


def _linked(data: Data, evidence_id: str) -> list[str]:
    """The evidence, then the reworded quote it corrects or the corrections of it: a reworded quote and its correction
    hold the same person's words, so redact takes them together."""
    found = [evidence_id]
    for ident in found:  # grows as it goes: a correction can be reworded and corrected again, so follow every link
        corrected = data.evidence[ident].get("corrects")
        if isinstance(corrected, str) and corrected in data.evidence and corrected not in found:
            found.append(corrected)
        found += [i for i, e in data.evidence.items() if e.get("corrects") == ident and i not in found]
    return found


def _plan(unit: Unit, data: Data, evidence_id: str) -> list[dict]:
    """The places that hold the evidence's words, in the order redact works through them."""
    steps: list[dict] = []
    for ident in _linked(data, evidence_id):
        steps += [{**s, "evidence": ident} for s in _places(unit, data, ident)]
    return [{**s, "done": False} for s in steps]


def _places(unit: Unit, data: Data, evidence_id: str) -> list[dict]:
    """The places of one evidence's words."""
    evidence = data.evidence[evidence_id]
    source = data.sources.get(evidence.get("source"), {})
    steps: list[dict] = []
    for record in data.briefs:
        if record.get("status") != "final" or not isinstance(record.get("file"), str):
            continue
        try:
            text = paths.read_bytes(unit, record["file"]).decode("utf-8")
        except FileNotFoundError:
            continue
        if _block(evidence_id).search(text):
            steps += [{"do": "brief", "ref": record["id"]}, {"do": "hash", "ref": record["id"]}]
    steps += _leftovers(unit, data, evidence_id)
    given = (source.get("origin") or {}).get("given") or {}
    for event in dict.fromkeys(
        e for e in ((evidence.get("words") or {}).get("event"), given.get("event")) if isinstance(e, str)
    ):
        steps.append({"do": "event", "ref": event})
    if given.get("type") == "chat" and source.get("id"):
        steps.append({"do": "source", "ref": source["id"]})
    steps += [{"do": "test", "ref": t["id"]} for t in data.tests if evidence_id in _cited_by(t)]
    steps.append({"do": "evidence", "ref": evidence_id})
    return steps


def _cited_by(test: dict) -> list:
    result = test.get("result")
    return result.get("evidence") or [] if isinstance(result, dict) else []


def _leftovers(unit: Unit, data: Data, evidence_id: str) -> list[dict]:
    """The files of the brief folder that hold the evidence's block and are not a final brief's file: a draft's file
    that a run left, and the temporary file of a run that stopped before it linked. Each is removed."""
    final = {b.get("file") for b in data.briefs if b.get("status") == "final"}
    found = []
    folder = unit.target(BRIEF_FOLDER)
    for path in sorted(folder.glob("*")) if folder.is_dir() else []:
        relative = f"{BRIEF_FOLDER}/{path.name}"
        if relative in final or path.is_symlink() or not path.is_file():
            continue
        try:
            text = paths.read_bytes(unit, relative).decode("utf-8", errors="replace")
        except OSError:
            continue
        if _block(evidence_id).search(text):
            found.append({"do": "leftover", "ref": relative})
    return found


def _prepare(unit: Unit, data: Data, step: dict, request: str) -> tuple[list[str], Callable[[], None] | None]:
    """What one place needs: the lines to print, and the write (None when the place is already as it should be)."""
    kind, ref = step["do"], step["ref"]
    evidence_id = step["evidence"]
    if kind == "brief":
        record = next(b for b in data.briefs if b.get("id") == ref)
        text = paths.read_bytes(unit, record["file"]).decode("utf-8")
        found = list(_block(evidence_id).finditer(text))
        if not found:
            return [], None
        new = _block(evidence_id).sub(REMOVED, text)
        return (
            [
                f"{record['file']}:{text[: m.start()].count(chr(10)) + 1}: replaced the block for {evidence_id} with {REMOVED}"
                for m in found
            ],
            lambda: paths.write_atomic(unit, record["file"], new.encode("utf-8")),
        )
    if kind == "leftover":
        if not unit.target(ref).is_file():
            return [], None
        return [f"{ref}: removed, a leftover file that held the block for {evidence_id}"], lambda: os.unlink(
            unit.target(ref)
        )
    if kind == "test":

        def emptied_result(found: dict) -> dict | None:
            result = found.get("result")
            if found.get("id") != ref or not isinstance(result, dict) or result.get("text") == REMOVED:
                return None
            return _valid(unit, {**found, "result": {**result, "text": REMOVED}}, "test.schema.json")

        lines, write = _rewritten(unit, "tests.jsonl", emptied_result)
        return [f"tests.jsonl:{n}: emptied the result text of {ref}" for n in lines], write
    if kind == "hash":
        record = next(b for b in data.briefs if b.get("id") == ref)
        digest = hashlib.sha256(paths.read_bytes(unit, record["file"])).hexdigest()

        def moved(found: dict) -> dict | None:
            if found.get("id") != ref or found.get("sha256") == digest:
                return None
            kept = [*found.get("redacted", []), found["sha256"]]
            return _valid(unit, {**found, "sha256": digest, "redacted": list(dict.fromkeys(kept))}, "brief.schema.json")

        lines, write = _rewritten(unit, "briefs.jsonl", moved)
        return [
            f"briefs.jsonl:{n}: recorded the new sha256 of {record['file']}; the old one is kept under redacted"
            for n in lines
        ], write
    if kind == "event":

        def emptied(found: dict) -> dict | None:
            if found.get("id") != ref or found.get("type") not in derive.WORDS_EVENTS:
                return None
            words = {"text": REMOVED, **({"source": REMOVED} if found["type"] == "add_evidence" else {})}
            return {**found, **words}

        lines, write = _rewritten(unit, "conversation.jsonl", emptied, ascii_only=True)
        return [f"conversation.jsonl:{n}: emptied the words of event {ref}" for n in lines], write
    relative = f"sources/{ref}.json" if kind == "source" else f"evidence/{ref}.json"
    current = data.sources[ref] if kind == "source" else data.evidence[ref]
    if kind == "source":
        new = json.loads(json.dumps(current))
        new["origin"]["given"]["text"] = REMOVED
        shown = "emptied the given text"
        key = "origin"
    else:
        new = {k: v for k, v in current.items() if k not in ("checked_read", "span", "sha256", "since", "page_words")}
        words = new.get("words") or {}
        if words.get("type") == "quote":
            new["words"] = {"type": "quote", "text": REMOVED}
        if "summary" in new:
            new["summary"] = REMOVED
        new["status"] = "removed"
        new["reason"] = f"redacted on request {request}"
        shown = "emptied the words and the summary; the evidence is removed"
        key = "words"
        _valid(unit, new, "evidence.schema.json")
    if new == current:
        return [], None
    text = records._json_file(new)
    return [f"{relative}:{_line_of(text, key)}: {shown}"], lambda: paths.write_atomic(
        unit, relative, records._encode(text)
    )


def _copies(data: Data) -> list[str]:
    handed = data.head.get("handed")
    first = (
        f"- the brief recorded in handed: {handed['brief']}, handed to {handed['to']}: clean its copies by hand"
        if isinstance(handed, dict)
        else "- the briefs recorded in handed: none recorded"
    )
    return [
        "Copies may remain in:",
        first,
        "- git history",
        "- the harness's session transcripts and the model provider",
    ]


def _redact_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("unit", help="the discovery, such as .discover/my-idea")
    parser.add_argument("evidence", help="the evidence whose words are removed, such as E-coord-1")
    parser.add_argument(
        "--request", required=True, help="the id of the user's redact event, or of the answered decision 'remove E-...'"
    )


@cli.verb(
    "redact",
    help="remove a person's words from the unit, from each final brief, the page event, the source and the evidence",
    arguments=_redact_arguments,
    skills=(SKILL.name,),
)
def redact(args: argparse.Namespace, run: cli.Run) -> int:
    unit = paths.resolve_unit(args.unit, run.skill)
    evidence_id, request = args.evidence, args.request
    if not EVIDENCE_ID.fullmatch(evidence_id):
        raise refusal(
            unit.label, f"{evidence_id!r} is not an evidence id", "name it as E-<agent>-<n>, such as E-coord-1"
        )
    data = _load(unit)
    if evidence_id not in data.evidence:
        raise refusal(unit.label, f"no evidence {evidence_id}", f"see the ids in {unit.label}/evidence")
    state = _read_state(unit)
    if state is not None and state["evidence"] != evidence_id:
        raise Refused(
            f"{unit.label}: a redact of {state['evidence']} is partly done. {CONTINUE}: "
            f"redact {unit.label} {state['evidence']} --request {state.get('request', '<id>')}"
        )
    if not _is_request(data, evidence_id, request):
        raise refusal(
            unit.label,
            f"{request!r} is not a request to remove {evidence_id}",
            f"pass --request <the id of the user's redact event for {evidence_id}, or of the answered decision "
            f"whose answer is 'remove {evidence_id}'>",
        )
    answering = _server_answering(unit)
    if answering:
        raise refusal(unit.label, answering, "close the page, then run again")
    if state is None:
        before = sorted(rules_changes.stale_items(unit))
        state = {
            "evidence": evidence_id,
            "request": request,
            "stale_before": before,
            "steps": _plan(unit, data, evidence_id),
        }
        _write_state(unit, state)
    try:
        _after_place("plan")
        _work(unit, run, state, request)
    except Exception as error:
        reason = str(error) or type(error).__name__
        raise Refused(
            f"{unit.label}: {CONTINUE}: redact {unit.label} {evidence_id} --request {request} ({reason})"
        ) from None
    return cli.EXIT_DONE


def _work(unit: Unit, run: cli.Run, state: dict, request: str) -> None:
    evidence_id = state["evidence"]
    for step in state["steps"]:
        if step["done"]:
            continue
        data = _load(unit)
        lines, write = _prepare(unit, data, {"evidence": evidence_id, **step}, request)
        if (
            "lines" not in step
        ):  # what the place prints is kept first, so a run that stops after the write still prints it
            step["lines"] = lines
            _write_state(unit, state)
        if write:
            write()
        step["done"] = True
        _write_state(unit, state)
        _after_place(f"{step['do']}:{step['ref']}")
    data = _load(unit)
    caused = {k: v for k, v in rules_changes.stale_items(unit).items() if k not in state.get("stale_before", [])}
    os.unlink(unit.target(STATE))
    run.out("Changed:")
    for step in state["steps"]:
        for line in step.get("lines", []):
            run.out(line)
    if caused:
        run.out("These states are now stale:")
        for item, why in caused.items():
            run.out(f"- {item}: {why}. {_add_a_change([item], unit)}")
    else:
        run.out("No state is stale because of this.")
    for line in _copies(data):
        run.out(line)
