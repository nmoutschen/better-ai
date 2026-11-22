#!/usr/bin/env python3
"""Show a research board as a live dashboard, and carry the user's comments and answers back to the coordinator.

Usage:
  python3 board.py watch BOARD [--port N] [--no-browser]   serve the page; prints each action the user takes as one
                                                           JSON line; exits by itself once the board is stopped
  python3 board.py snapshot BOARD --out FILE               write a static page
  python3 board.py check BOARD                             print each invalid record as file:line: field: message;
                                                           exit 1 if there is any
  python3 board.py wait BOARD [--timeout S]                wait for the user's next actions on the served page
  python3 board.py reply BOARD TEXT [--to ID]              show the coordinator's reply in the page
  python3 board.py status BOARD seen|asked|working|done ID...
  python3 board.py status BOARD accepted ID... --text "the user's words"
  python3 board.py pending BOARD                           list the user's items that are not done or accepted

BOARD is the board directory described in templates/board.md. Each record of its JSON files is checked against its
schema (schemas/, through schema.py) on its own: the page lists every invalid record, with the file, line and field,
in a band, so one bad record never hides the rest. Questions and the brief that are not valid stay on the page, marked,
claims and sources under the question they name, and conversation events with a valid type without the fields that failed
(schema.strip_invalid); other invalid records are only listed. The page shows one column per direction of the
research, the agents at work, the decisions taken without the user, and a conversation with the coordinator. The user
comments on any question, decision or agent, writes to the coordinator, or answers a decision. Each action is a
JSON-RPC call from the page; the script appends it to conversation.jsonl in the board and prints it to stdout, so a
harness that streams a command's output delivers it as it arrives. `wait` is for harnesses that only notify when a
command ends: once one has connected, the page tells the user whenever none has been connected for a few seconds. `reply` and `status` work with or without a server, so a resumed run can answer what the user wrote while
no agent was running.
"""

from __future__ import annotations

import argparse
import contextlib
import http.server
import json
import sys
import threading
import time
import webbrowser
from calendar import timegm
from pathlib import Path

HERE = Path(__file__).resolve().parent  # board.html, the page template, and its CSS and JS sit next to this script
sys.path.insert(0, str(HERE))  # page.py, the conversation every page that talks to the agent shares, sits here too
import page  # noqa: E402
import schema  # noqa: E402

SCHEMAS = HERE.parent / "schemas"
FOLDERS = ("questions", "claims", "sources")  # one <id>.json per entry
LINES_SHOWN = 60  # the log lines of each agent the page gets; it gets every search line, to count them per question

LOG, SEEN, ADDRESS = "conversation.jsonl", ".conversation-seen", ".server"
METHODS = ("comment", "note", "answer")  # what the page may send
ITEMS = ("comment", "note", "answer")  # what the coordinator tracks with status


def at_time(record: dict) -> float:
    """When the record was first written, as seconds; 0 for a record whose `at` is missing or not a time."""
    try:
        return float(timegm(time.strptime(record["at"], "%Y-%m-%dT%H:%M:%SZ")))
    except (KeyError, ValueError, TypeError, OverflowError):
        return 0.0


def board_files(board: Path) -> list:
    """The files that hold the board's records, in name order: brief.json, decisions.jsonl, the files of the
    questions, claims, sources and logs folders, and conversation.jsonl (checked here, read by the page's own
    code). A file of another shape, such as an old Markdown one, is listed so that it is reported, not skipped."""
    files = [p for pattern in ("brief.*", "decisions.*", LOG) for p in sorted(board.glob(pattern)) if p.is_file()]
    for folder in (*FOLDERS, "logs", "decisions"):
        if (board / folder).is_dir():
            files += [p for p in sorted((board / folder).iterdir()) if p.is_file() and not p.name.startswith(".")]
    return files


def scan_file(path: Path, board: Path, docs: dict, cache: dict, data: dict) -> None:
    """One file of the board into `data`: its records, and what is wrong with them."""
    shown = path.relative_to(board).as_posix()
    try:
        text = schema.read_checked(path, path.suffix == ".jsonl")
    except (OSError, UnicodeDecodeError) as error:
        data["errors"].append({"file": shown, "line": 1, "field": "(file)", "message": f"cannot be read: {error}"})
        return
    # What is shown below is built from this text, the text that was checked.
    found = schema.check_text(path, text, docs, cache)
    if [(e.field, e.message) for e in found] == [("(file)", "no schema describes this file")]:
        data["errors"].append({"file": shown, "line": 1, "field": "(file)", "message": found[0].message})
        return  # a file of another shape, such as an old Markdown one: listed, nothing to show from it
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
        entry = {"file": shown, "line": error.line, "field": error.field, "message": error.message}
        record = records.get(error.line)
        if isinstance(record, dict) and isinstance(record.get("by"), str):
            entry["by"] = schema.plain(record["by"])
        data["errors"].append(entry)
        messages.setdefault(error.line, []).append(error)
    kept = {n: r for n, r in records.items() if isinstance(r, dict)}
    valid = [r for n, r in kept.items() if n not in messages]
    parent = path.parent.name
    if path.name == "brief.json":
        data["brief"] = next(iter(kept.values()), {})  # an invalid brief is kept, marked like a question
        if data["brief"] and 1 in messages:
            data["brief"] = schema.strip_invalid(data["brief"], messages[1])
    elif path.name == "decisions.jsonl":
        data["decisions"] += valid
    elif path.name == LOG:
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


def scan(board: Path) -> dict:
    """Every record of the board, each file read once and checked on its own. `decisions` and `logs` (agent ->
    records) hold the valid records. `brief`, `questions`, `claims`, `sources` and `conversation` hold every record
    that parsed as an object, each invalid one without the fields that failed and with its messages in `_errors`
    (schema.strip_invalid), so the page shows it marked and meets only well-typed fields. `errors` lists every problem
    as {file, line, field, message, by}, `by` only where the record could be read."""
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
    try:
        docs = schema.load_schemas(SCHEMAS)
    except schema.SchemaError as error:
        data["errors"].append({"file": "schemas", "line": 1, "field": "(schemas)", "message": str(error)})
        return data
    cache: dict = {}
    for path in board_files(board):
        try:
            scan_file(path, board, docs, cache, data)
        except Exception as error:  # for any reason: that file is an error entry and the rest of the board is shown
            shown = path.relative_to(board).as_posix()
            message = f"could not be shown: {type(error).__name__}"
            data["errors"].append({"file": shown, "line": 1, "field": "(file)", "message": message})
    return data


SCANS: dict = {}  # board -> (the files' names, sizes and times when it was scanned, that scan)


def scan_cached(board: Path) -> dict:
    """The scan, made again only when a file of the board has changed since the last one, so a page polling every
    two seconds does not read a large board each time. Treat the result as read-only."""
    try:
        files = tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in board_files(board))
    except OSError:  # a file went away between listing and reading: scan again
        return scan(board)
    last = SCANS.get(board)
    if last is None or last[0] != files:
        SCANS[board] = (files, scan(board))
    return SCANS[board][1]


def load(board: Path) -> dict:
    """The page's payload. It never raises, whatever the reason: a failure is an error entry."""
    try:
        return _load(board)
    except Exception as error:
        message = f"could not be shown: {type(error).__name__}"
        errors = [{"file": "(board)", "line": 1, "field": "(board)", "message": message}]
        empty = {"brief": {}, "decisions": [], "conversation": [], "questions": [], "claims": [], "sources": []}
        return {**empty, "logs": {}, "errors": errors, "now": time.time()}


def _load(board: Path) -> dict:
    data = scan_cached(board)
    logs = {}
    for agent, records in data["logs"].items():
        logs[agent] = {
            "records": records[-LINES_SHOWN:],
            # The page counts searches per question from these, so it gets every search line, not only the last 60.
            "searches": [r for r in records if r["type"] == "search"],
        }
    return {**data, "logs": logs, "now": time.time()}


def board_page(snapshot: dict | None) -> str:
    """The page as one file, read on each request, so a fix to the page's files shows on reload without restarting the
    viewer. board.html is the template; page.css and page.js are shared with the other pages that talk to the agent;
    board.css and board.js are what only the board has."""
    embedded = "null" if snapshot is None else json.dumps(snapshot).replace("</", "<\\/")
    html = (HERE / "board.html").read_text(encoding="utf-8")
    for marker, name in (
        ("/*__PAGE_CSS__*/", "page.css"),
        ("/*__BOARD_CSS__*/", "board.css"),
        ("/*__PAGE_JS__*/", "page.js"),
        ("/*__BOARD_JS__*/", "board.js"),
    ):
        text = (HERE / name).read_text(encoding="utf-8")
        if name.startswith("board."):  # the template ends the line after this marker
            text = text.removesuffix("\n")
        html = html.replace(marker, text, 1)
    return html.replace("__SNAPSHOT__", embedded)


CLOSED = ("answered", "contested", "not found", "unclear")  # the statuses a worker sets when it finishes a question
ANNOUNCED: set = set()  # (question, worker, status) closes already in the log or present when the viewer started


def announce_closes(conv: page.Conversation, initial: bool, data: dict | None = None) -> None:
    """Post a message from the worker each time it closes a question, once its one-line answer (gist) is written.
    On a board's first viewer, questions already closed get no message, so an old board does not flood the
    conversation; a resumed viewer posts the closes it missed while it was away."""
    events = conv.events()
    ANNOUNCED.update((e.get("question"), e.get("by"), e.get("status")) for e in events if e.get("type") == "closed")
    first = initial and not any(e.get("type") == "closed" for e in events)
    for q in (scan_cached(conv.folder) if data is None else data)["questions"]:
        if "_errors" in q:  # an invalid question is listed in the band; it is not announced
            continue
        status, gist = q["status"], q.get("gist", "")
        key = (q["id"], q.get("owner"), status)
        if status not in CLOSED or not gist or key in ANNOUNCED:
            continue
        ANNOUNCED.add(key)
        if not first:
            try:
                conv.append(
                    {
                        "type": "closed",
                        "by": key[1],
                        "id": "c-" + str(time.time_ns()),
                        "question": key[0],
                        "status": status,
                    },
                )
            except page.EventError as error:  # the line is not written; the viewer goes on
                print(f"error: closing message for {key[0]} not written: {error}", file=sys.stderr, flush=True)


def board_stopped(board: Path, data: dict | None = None) -> bool:
    return (scan_cached(board) if data is None else data)["brief"].get("status") == "stopped"


# ---------- The conversation: conversation.jsonl in the board, one JSON event per line ----------


def conversation(board: Path) -> page.Conversation:
    return page.Conversation(
        board,
        LOG,
        SEEN,
        ADDRESS,
        ITEMS,
        "coordinator",
        "watch BOARD",
        schemas=HERE.parent / "schemas",
        events="board-events.schema.json",
    )


# ---------- watch ----------


def watch(board: Path, port: int, open_browser: bool, linger: float) -> None:
    conv = conversation(board)

    class Handler(page.Handler):
        conversation = conv
        methods = METHODS

        def do_GET(self):
            if not self.local():
                return self.send_error(403)
            if self.path.startswith("/board.json"):
                return self.send_json({**load(board), "listening": conv.listening()})
            if self.conversation_get():
                return None
            if self.path in ("/", "/index.html"):
                return self.send(200, board_page(None).encode(), "text/html; charset=utf-8")
            self.send_error(404)

    with conv.lock:
        announce_closes(conv, initial=True)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    conv.address.write_text(url, encoding="utf-8")
    if not conv.seen.exists():  # a resumed run keeps its place, so it still sees what came in while it was away
        conv.seen.write_text("0", encoding="utf-8")
    print(f"Watching {board} at {url}. Each action the user takes is printed here as one JSON line.", flush=True)
    print("Stops by itself once the board's status is stopped (or press Ctrl+C).", flush=True)
    if open_browser and not webbrowser.open(url):
        print(
            "Could not open a browser on this machine. If the user's browser runs on another machine, "
            "this address does not reach it.",
            flush=True,
        )
    page.stop_like_ctrl_c()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    stopped_at = None
    try:
        while True:
            time.sleep(1)
            try:  # one scan a tick; a tick that fails is reported and the next one tries again
                data = scan_cached(board)
                with conv.lock:  # the page's actions append to the same log
                    announce_closes(conv, initial=False, data=data)
                stopped = board_stopped(board, data)
            except Exception as error:
                print(f"error: board tick failed: {error!r}", file=sys.stderr, flush=True)
                continue
            if stopped_at is None and stopped:
                stopped_at = time.time()
            if stopped_at is not None and not stopped:
                stopped_at = None  # reopened
            if stopped_at is not None and time.time() - stopped_at > linger:
                print("Board stopped; viewer exiting. The open page keeps the last state.", flush=True)
                break
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
        conv.address.unlink(missing_ok=True)


# ---------- check ----------


def check(board: Path) -> int:
    """Print each invalid record as `file:line: field: message`, with its author when it could be read; 1 if there
    is any, else 0. These are the errors the page lists in its band."""
    errors = scan(board)["errors"]
    for e in errors:
        print(f"{e['file']}:{e['line']}: {e['field']}: {e['message']}" + (f" (by {e['by']})" if "by" in e else ""))
    return 1 if errors else 0


# ---------- Command line ----------


@schema.never_raise("board", {**page.VERBS, "watch": "served", "snapshot": "written", "": "checked"})
def main() -> None:
    parser = argparse.ArgumentParser(description="Show a research board as a live page and collect the user's input.")
    sub = parser.add_subparsers(dest="command", required=True)
    w = sub.add_parser("watch", help="serve the live page")
    w.add_argument("board")
    w.add_argument("--port", type=int, default=0, help="port to serve on (default: any free port)")
    w.add_argument("--linger", type=float, default=10, help="seconds to keep serving after the board stops")
    w.add_argument("--no-browser", action="store_true", help="do not open a browser")
    s = sub.add_parser("snapshot", help="write a static page")
    s.add_argument("board")
    s.add_argument("--out", required=True)
    c = sub.add_parser("check", help="print each invalid record and exit 1 if there is any")
    c.add_argument("board")
    t = sub.add_parser("wait", help="wait for the user's next actions on the served page, print them and exit")
    t.add_argument("board")
    t.add_argument("--timeout", type=float, default=600, help="seconds to wait (default 600)")
    r = sub.add_parser("reply", help="show a reply from the coordinator in the page")
    r.add_argument("board")
    r.add_argument("text")
    r.add_argument("--to", help="the id of the item it answers")
    st = sub.add_parser("status", help="mark the user's items seen, asked, working, done or accepted")
    st.add_argument("board")
    st.add_argument("state", choices=page.STATES)
    st.add_argument("ids", nargs="+")
    st.add_argument("--text", help="the user's words, for accepted")
    p = sub.add_parser("pending", help="list the user's items that are not done or accepted")
    p.add_argument("board")
    args = parser.parse_args()
    board = Path(args.board).expanduser().resolve()
    if not board.is_dir():
        sys.exit(f"error: {board} is not a directory")
    if args.command == "watch":
        watch(board, args.port, not args.no_browser, args.linger)
    elif args.command == "snapshot":
        Path(args.out).write_text(board_page(load(board)), encoding="utf-8")
        print(f"wrote {args.out}")
    elif args.command == "check":
        sys.exit(check(board))
    elif args.command == "wait":
        sys.exit(conversation(board).wait(args.timeout))
    elif args.command == "reply":
        conversation(board).reply(args.text, args.to)
    elif args.command == "status":
        conversation(board).set_status(args.state, args.ids, args.text)
    else:
        conversation(board).pending()


if __name__ == "__main__":
    sys.exit(main())
