"""The research board: what its page reads from a board, the page itself, and `render`.

The board is a unit, `.research/<slug>/`. `serve`, `wait`, `reply`, `status`, `pending` and `check` are the shared verbs; this
module holds what only the board has:

- `scan` and `load`: every record of the board, each file read once with `schema.read_records` and checked on its own, so
  one bad record never hides the rest. The page lists each problem with its file, line and field, and keeps a question,
  claim, source or the brief that is not valid on the page, marked. A record in the format before this change is counted,
  not listed as an error. A bug in this code is not a record error: it reaches the page's bug path.
- the `PageSpec` of the board's page: its main section, its own CSS and JS, the decisions the user answers, the comments
  on a question or an agent, and the one-line message each time a worker closes a question (`announce_closes`);
- `render <board>`: the page as one file, `board.html` in the board, with the data embedded and no actions.
"""

from __future__ import annotations

import os
import sys
import time
from calendar import timegm
from datetime import datetime, timezone
from pathlib import Path

from .. import page, resources, schema
from ..page import triggers
from ..paths import Unit
from . import SKILL, checks  # noqa: F401  (checks registers the hooks the schemas name)

FOLDERS = ("questions", "claims", "sources")  # one <id>.json per entry
LINES_SHOWN = 60  # the log lines of each agent the page gets; it gets every search line, to count them per question
RENDERED = "board.html"
CLOSED = ("answered", "contested", "not found", "unclear")  # the statuses a worker sets when it finishes a question


def at_time(record: dict) -> float:
    """When the record was first written, as seconds; 0 for a record whose `at` is missing or not a time."""
    try:
        return float(timegm(time.strptime(record["at"], schema.TIME)))
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
    """One file of the board into `data`: its records, and what is wrong with them. A record that is not valid stays,
    without the fields that failed, in the files whose records the page shows marked; the decisions and the logs keep
    only the valid ones."""
    folder, _, _ = name.partition("/")
    shown = name in ("brief.json", "conversation.jsonl") or folder in FOLDERS
    read = schema.read_records(
        unit, name, schema.docs_for("research"), cache, now, resources.cutoff(), keep_invalid=shown
    )
    data["errors"] += read.errors
    records = list(zip(read.lines, read.records, strict=True))
    if name == "brief.json":
        data["brief"] = records[0][1] if records else {}  # an invalid brief is kept, marked like a question
    elif name == "decisions.jsonl":
        data["decisions"] += [{**r, "_old": True} if n in read.old else r for n, r in records]
    elif name == "conversation.jsonl":
        # An invalid event still shows, without the fields that failed. Without a valid `type` no branch of the
        # schema checked its other fields, so it is only listed.
        data["conversation"] += [r for _, r in records if "_errors" not in r or isinstance(r.get("type"), str)]
    elif folder in FOLDERS:
        for number, record in records:
            record["_born"] = at_time(record)
            if record["id"] == f"(line {number})":
                record["id"] = Path(name).stem  # the file is named for its id
            data[folder].append(record)
    elif folder == "logs":
        data["logs"][Path(name).stem] = [r for _, r in records]


def scan(unit: Unit) -> dict:
    """Every record of the board, each file read once and checked on its own. `decisions` and `logs` (agent -> records)
    hold the valid records. `brief`, `questions`, `claims`, `sources` and `conversation` hold every record that parsed
    as an object, each invalid one without the fields that failed and with its messages in `_errors`
    (schema.strip_invalid), so the page shows it marked and meets only well-typed fields. `errors` lists every problem as
    {file, line, field, message, by}, `by` only where the record could be read."""
    data: dict = {
        "brief": {},
        "decisions": [],
        "conversation": [],
        "questions": [],
        "claims": [],
        "sources": [],
        "logs": {},
        "errors": [],
    }
    cache: dict = {}
    now = datetime.now(timezone.utc)
    for name in board_files(unit):
        scan_file(unit, name, data, cache, now)
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
    """The page's payload: the scan, each agent's log cut to its last lines and every search line, and each agent's last
    word (page.last_word), from which the page says an agent has gone quiet."""
    data = scan_cached(unit)
    written = [*data["questions"], *data["claims"], *data["sources"], *data["decisions"], *data["conversation"]]
    written += [r for records in data["logs"].values() for r in records]
    agents = {r.get("by") for r in written} | set(data["logs"])
    logs = {}
    for agent, records in data["logs"].items():
        logs[agent] = {
            "records": records[-LINES_SHOWN:],
            # The page counts searches per question from these, so it gets every search line, not only the last 60.
            "searches": [r for r in records if r["type"] == "search"],
        }
    last_word = page.last_words(written, sorted(a for a in agents if isinstance(a, str) and a))
    return {**data, "logs": logs, "last_word": last_word, "now": time.time()}


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
        triggers=triggers.research,
        title="Research board",
        agent="coordinator",
        main="research/board.html",
        aside="page/agents.html",
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
        rendered=RENDERED,
    ),
)
