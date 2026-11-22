"""The research board: what its page reads from a board, the page itself, and `render`.

The board is a unit, `.research/<slug>/`. `serve`, `wait`, `reply`, `status`, `pending` and `check` are the shared verbs; this
module holds what only the board has:

- `scan` and `load`: every record of the board, each file read once and checked on its own, so one bad record never hides
  the rest. The page lists each problem with its file, line and field, and keeps a question, claim, source or the brief
  that is not valid on the page, marked. A record in the format before this change is counted, not listed as an error.
- the `PageSpec` of the board's page: its main section, its own CSS and JS, the decisions the user answers, the comments
  on a question or an agent, and the one-line message each time a worker closes a question (`announce_closes`);
- `render <board>`: the page as one file, `board.html` in the board, with the data embedded and no actions.
"""

from __future__ import annotations

import argparse
import contextlib
import html
import json
import os
import sys
import time
from calendar import timegm
from datetime import datetime, timezone
from pathlib import Path

from .. import cli, page, paths, resources, schema
from ..paths import Unit
from . import SKILL, checks  # noqa: F401  (checks registers the hooks the schemas name)

FOLDERS = ("questions", "claims", "sources")  # one <id>.json per entry
LINES_SHOWN = 60  # the log lines of each agent the page gets; it gets every search line, to count them per question
RENDERED = "board.html"
CLOSED = ("answered", "contested", "not found", "unclear")  # the statuses a worker sets when it finishes a question

_DOCS: dict = {}  # the schemas of a run, loaded once


def docs() -> dict:
    if not _DOCS:
        _DOCS.update(schema.load_schemas(*resources.schema_sources("research")))
    return _DOCS


def _cutoff() -> str:
    try:
        return resources.build_info().cutoff
    except LookupError:  # in-process, not run as better.pyz
        return resources.DEFAULT_CUTOFF


def at_time(record: dict) -> float:
    """When the record was first written, as seconds; 0 for a record whose `at` is missing or not a time."""
    try:
        return float(timegm(time.strptime(record["at"], "%Y-%m-%dT%H:%M:%SZ")))
    except (KeyError, ValueError, TypeError, OverflowError):
        return 0.0


def board_files(unit: Unit) -> list[str]:
    """The files that hold the board's records, as names inside the board, in name order: brief.json, decisions.jsonl,
    conversation.jsonl and the files of the questions, claims, sources and logs folders. A file of another shape, such as
    an old Markdown one, is listed so that it is reported, not skipped."""
    root = unit.path
    top = sorted(os.listdir(root))
    names = [n for start in ("brief.", "decisions.") for n in top if n.startswith(start) and (root / n).is_file()]
    names += [n for n in top if n == "conversation.jsonl" and (root / n).is_file()]
    for folder in (*FOLDERS, "logs", "decisions"):
        if (root / folder).is_dir():
            names += [
                f"{folder}/{n}"
                for n in sorted(os.listdir(root / folder))
                if not n.startswith(".") and (root / folder / n).is_file()
            ]
    return names


def scan_file(unit: Unit, name: str, data: dict, cache: dict, now: datetime) -> None:
    """One file of the board into `data`: its records, and what is wrong with them."""
    try:
        path = unit.target(name)
        text = schema.read_checked(path, path.suffix == ".jsonl")
    except (OSError, UnicodeDecodeError, paths.Refused) as error:
        data["errors"].append({"file": name, "line": 1, "field": "(file)", "message": f"cannot be read: {error}"})
        return
    # What is shown below is built from this text, the text that was checked.
    old: list = []
    found = schema.check_text(path, text, docs(), cache, now=now, cutoff=_cutoff(), notices=old)
    if [(e.field, e.message) for e in found] == [("(file)", "no schema describes this file")]:
        data["errors"].append({"file": name, "line": 1, "field": "(file)", "message": found[0].message})
        return  # a file of another shape, such as an old Markdown one: listed, nothing to show from it
    data["old"] += len(old)
    old_lines = {e.line for e in old}
    pieces = [piece.removesuffix("\r") for piece in text.split("\n")]
    if path.suffix != ".jsonl":
        pieces = [text]
    elif pieces[-1] == "":
        pieces.pop()
    records = {}
    for number, piece in enumerate(pieces, 1):
        with contextlib.suppress(ValueError, RecursionError):
            records[number] = json.loads(piece)
    messages: dict = {}  # line -> its errors, the first of each field
    reported: set = set()
    for error in found:
        if (error.line, error.field) in reported:  # one error per field of a line, the first
            continue
        reported.add((error.line, error.field))
        entry = {"file": name, "line": error.line, "field": error.field, "message": error.message}
        record = records.get(error.line)
        if isinstance(record, dict) and isinstance(record.get("by"), str):
            entry["by"] = schema.plain(record["by"])
        data["errors"].append(entry)
        messages.setdefault(error.line, []).append(error)
    kept = {n: r for n, r in records.items() if isinstance(r, dict)}
    valid = [r for n, r in kept.items() if n not in messages]
    parent = path.parent.name
    if name == "brief.json":
        data["brief"] = next(iter(kept.values()), {})  # an invalid brief is kept, marked like a question
        if data["brief"] and 1 in messages:
            data["brief"] = schema.strip_invalid(data["brief"], messages[1])
    elif name == "decisions.jsonl":
        data["decisions"] += [
            {**r, "_old": True} if n in old_lines else r for n, r in kept.items() if n not in messages
        ]
    elif name == "conversation.jsonl":
        # An invalid event still shows, without the fields that failed. Without a valid `type` no branch of the
        # schema checked its other fields, so it is only listed.
        stripped = [schema.strip_invalid(r, messages[n]) if n in messages else r for n, r in kept.items()]
        data["conversation"] += [r for r in stripped if "_errors" not in r or isinstance(r.get("type"), str)]
    elif parent in FOLDERS:
        for number, record in kept.items():
            born = at_time(record)
            if number in messages:
                record = schema.strip_invalid(record, messages[number])
            record["_born"] = born
            if not isinstance(record.get("id"), str):
                record["id"] = path.stem  # the file is named for its id
            data[parent].append(record)
    elif parent == "logs":
        data["logs"][path.stem] = valid


def scan(unit: Unit) -> dict:
    """Every record of the board, each file read once and checked on its own. `decisions` and `logs` (agent -> records)
    hold the valid records. `brief`, `questions`, `claims`, `sources` and `conversation` hold every record that parsed
    as an object, each invalid one without the fields that failed and with its messages in `_errors`
    (schema.strip_invalid), so the page shows it marked and meets only well-typed fields. `errors` lists every problem as
    {file, line, field, message, by}, `by` only where the record could be read. `old` counts the records in the format
    before this change, which are kept as they are."""
    data: dict = {
        "brief": {},
        "decisions": [],
        "conversation": [],
        "questions": [],
        "claims": [],
        "sources": [],
        "logs": {},
        "errors": [],
        "old": 0,
    }
    try:
        docs()
    except schema.SchemaError as error:
        data["errors"].append({"file": "schemas", "line": 1, "field": "(schemas)", "message": str(error)})
        return data
    cache: dict = {}
    now = datetime.now(timezone.utc)
    for name in board_files(unit):
        try:
            scan_file(unit, name, data, cache, now)
        except Exception as error:  # for any reason: that file is an error entry and the rest of the board is shown
            message = f"could not be shown: {type(error).__name__}"
            data["errors"].append({"file": name, "line": 1, "field": "(file)", "message": message})
    return data


SCANS: dict = {}  # board path -> (the files' names, sizes and times when it was scanned, that scan)


def scan_cached(unit: Unit) -> dict:
    """The scan, made again only when a file of the board has changed since the last one, so a page polling every two
    seconds does not read a large board each time. Treat the result as read-only."""
    try:
        files = tuple((n, (s := os.stat(unit.path / n)).st_mtime_ns, s.st_size) for n in board_files(unit))
    except OSError:  # a file went away between listing and reading: scan again
        return scan(unit)
    last = SCANS.get(unit.path)
    if last is None or last[0] != files:
        SCANS[unit.path] = (files, scan(unit))
    return SCANS[unit.path][1]


def load(unit: Unit) -> dict:
    """The page's payload. It never raises, whatever the reason: a failure is an error entry."""
    try:
        return _load(unit)
    except Exception as error:
        message = f"could not be shown: {type(error).__name__}"
        errors = [{"file": "(board)", "line": 1, "field": "(board)", "message": message}]
        empty = {"brief": {}, "decisions": [], "conversation": [], "questions": [], "claims": [], "sources": []}
        return {**empty, "logs": {}, "errors": errors, "old": 0, "now": time.time()}


def _load(unit: Unit) -> dict:
    data = scan_cached(unit)
    logs = {}
    for agent, records in data["logs"].items():
        logs[agent] = {
            "records": records[-LINES_SHOWN:],
            # The page counts searches per question from these, so it gets every search line, not only the last 60.
            "searches": [r for r in records if r["type"] == "search"],
        }
    return {**data, "logs": logs, "now": time.time()}


def board_stopped(unit: Unit, data: dict | None = None) -> bool:
    return (scan_cached(unit) if data is None else data)["brief"].get("status") == "stopped"


# ---------- Closed questions: a message from the worker, once its one-line answer (gist) is written ----------

ANNOUNCED: set = set()  # (board, question, worker, status) closes already in the log or present when the viewer started
STARTED: set = set()  # the boards whose first announcement has been made


def announce_closes(conv: page.Conversation, initial: bool, data: dict | None = None) -> None:
    """Post a message from the worker each time it closes a question, once its one-line answer (gist) is written. On a
    board's first viewer, questions already closed get no message, so an old board does not flood the conversation; a
    resumed viewer posts the closes it missed while it was away."""
    unit = conv.unit
    events = conv.events()
    ANNOUNCED.update(
        (unit.path, e.get("question"), e.get("by"), e.get("status")) for e in events if e.get("type") == "closed"
    )
    first = initial and not any(e.get("type") == "closed" for e in events)
    for q in (scan_cached(unit) if data is None else data)["questions"]:
        if "_errors" in q:  # an invalid question is listed in the band; it is not announced
            continue
        status, gist = q["status"], q.get("gist", "")
        key = (unit.path, q["id"], q.get("owner"), status)
        if status not in CLOSED or not gist or key in ANNOUNCED:
            continue
        ANNOUNCED.add(key)
        if not first:
            try:
                conv.append(
                    {
                        "type": "closed",
                        "by": key[2],
                        "id": "c-" + str(time.time_ns()),
                        "question": key[1],
                        "status": status,
                    },
                )
            except page.EventError as error:  # the line is not written; the viewer goes on
                print(f"error: closing message for {key[1]} not written: {error}", file=sys.stderr, flush=True)


def tick(unit: Unit, conv: page.Conversation) -> None:
    """Once a second while serving: one scan, and the closes since the last."""
    initial = unit.path not in STARTED
    STARTED.add(unit.path)
    data = scan_cached(unit)
    with conv.lock:  # the page's actions append to the same log
        announce_closes(conv, initial=initial, data=data)


def conversation(unit: Unit) -> page.Conversation:
    return page.Conversation(unit, page.spec_of(SKILL), page.load_docs(SKILL))


# ---------- The page ----------

SPEC = page.register(
    SKILL,
    page.PageSpec(
        title="Research board",
        agent="coordinator",
        main="research/board.html",
        load=load,
        events="board-events.schema.json",
        assets={"/board.css": "research/board.css", "/board.js": "research/board.js"},
        css=("/board.css",),
        js=("/board.js",),
        capabilities=("decisions",),
        methods=("comment",),
        items=("comment", "note", "answer"),
        empty="Nothing yet. Click a question or an agent to ask about it, or write to the coordinator below.",
        stopped=board_stopped,
        tick=tick,
    ),
)


# ---------- render ----------


def static_page(data: dict) -> str:
    """The page as one file: the shell with each file it links written into it, and the board's data embedded. The page
    then has no server: it shows the data, without the actions."""
    text = page.shell(SPEC)
    table = SPEC.table()
    for url in ("/page.css", *SPEC.css):
        link = f'<link href="{html.escape(url)}" rel="stylesheet">'
        text = text.replace(link, "<style>\n" + resources.read_text(table[url]).replace("</", "<\\/") + "\n</style>", 1)
    embedded = json.dumps(data).replace("</", "<\\/")
    for url in ("/page.js", *SPEC.js):
        tag = f'<script src="{html.escape(url)}"></script>'
        script = "<script>\n" + resources.read_text(table[url]).replace("</script", "<\\/script") + "\n</script>"
        if url == "/page.js":
            script = f"<script>var BOARD_SNAPSHOT = {embedded};</script>\n" + script
        text = text.replace(tag, script, 1)
    return text


def _render_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("unit", help="the board, such as .research/my-topic")


@cli.verb(
    "render",
    help=f"write the board as one static page, {RENDERED} in the board",
    arguments=_render_arguments,
    skills=("research-better",),
)
def render(args: argparse.Namespace, run: cli.Run) -> int:
    unit = paths.resolve_unit(args.unit, run.skill)
    if not unit.exists():
        raise paths.refusal(unit.label, "it holds no board", f"run create {unit.label} first")
    paths.write_atomic(unit, RENDERED, static_page(load(unit)).encode("utf-8"))
    run.out(f"wrote {Path(unit.label) / RENDERED}")
    return cli.EXIT_DONE
