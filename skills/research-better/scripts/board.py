#!/usr/bin/env python3
"""Show a research board as a live dashboard, and carry the user's comments and answers back to the coordinator.

Usage:
  python3 board.py watch BOARD [--port N] [--no-browser]   serve the page; prints each action the user takes as one
                                                           JSON line; exits by itself once the board is stopped
  python3 board.py snapshot BOARD --out FILE               write a static page
  python3 board.py wait BOARD [--timeout S]                wait for the user's next actions on the served page
  python3 board.py reply BOARD TEXT [--to ID]              show the coordinator's reply in the page
  python3 board.py status BOARD seen|asked|working|done ID...
  python3 board.py status BOARD accepted ID... --text "the user's words"
  python3 board.py pending BOARD                           list the user's items that are not done or accepted

BOARD is the board directory described in templates/board.md. The page shows one column per direction of the
research, the agents at work, the decisions taken without the user, and a conversation with the coordinator. The user
comments on any question, decision or agent, writes to the coordinator, or answers a decision. Each action is a
JSON-RPC call from the page; the script appends it to conversation.jsonl in the board and prints it to stdout, so a
harness that streams a command's output delivers it as it arrives. `wait` is for harnesses that only notify when a
command ends: once one has connected, the page tells the user whenever none has been connected for a few seconds. `reply` and `status` work with or without a server, so a resumed run can answer what the user wrote while
no agent was running.
"""

from __future__ import annotations

import argparse
import http.server
import json
import sys
import threading
import time
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent  # board.html, the page template, and its CSS and JS sit next to this script
sys.path.insert(0, str(HERE))  # page.py, the conversation every page that talks to the agent shares, sits here too
import page  # noqa: E402

KINDS = ("questions", "claims", "sources", "decisions")
FIRST_SEEN: dict = {}  # (agent, line number, text) -> time the viewer first read that log line

LOG, SEEN, ADDRESS = "conversation.jsonl", ".conversation-seen", ".server"
METHODS = ("comment", "note", "answer")  # what the page may send
ITEMS = ("comment", "note", "answer")  # what the coordinator tracks with status


def born(path: Path) -> float:
    """Creation time where the filesystem records it, else last modification."""
    stat = path.stat()
    return getattr(stat, "st_birthtime", stat.st_mtime)


def md_files(folder: Path) -> list:
    """The board's .md files in a folder, in name order; none if the folder does not exist yet."""
    return sorted(folder.glob("*.md")) if folder.is_dir() else []


def text_lines(path: Path) -> list:
    """The non-blank lines of an agent's log."""
    return [line for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]


def read_entry(path: Path) -> dict:
    entry = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() and " " not in key.strip():
            entry[key.strip()] = value.strip()
    entry.setdefault("id", path.stem)
    entry["_born"] = born(path)
    entry["_changed"] = path.stat().st_mtime
    return entry


def load(board: Path) -> dict:
    data = {"brief": {}, "logs": {}, "now": time.time(), "conversation": conversation(board).events()}
    if (board / "brief.md").exists():
        data["brief"] = read_entry(board / "brief.md")
    for kind in KINDS:
        data[kind] = [read_entry(path) for path in md_files(board / kind)]
    for path in md_files(board / "logs"):
        lines = text_lines(path)
        stamped = [[FIRST_SEEN.get((path.stem, i, line)), line] for i, line in enumerate(lines)]
        data["logs"][path.stem] = {
            "last": lines[-1] if lines else "",
            "lines": stamped[-60:],
            # The page counts searches per question from these, so it gets every search line, not only the last 60.
            "searches": [line for line in lines if line.startswith("search ")],
            "_changed": path.stat().st_mtime,
        }
    return data


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


def stamp_logs(board: Path, initial: bool) -> None:
    """Record when each log line first appears. Lines present before the viewer started get no time."""
    now = time.time()
    for path in md_files(board / "logs"):
        for i, line in enumerate(text_lines(path)):
            FIRST_SEEN.setdefault((path.stem, i, line), None if initial else now)


CLOSED = ("answered", "contested", "not found", "unclear")  # the statuses a worker sets when it finishes a question
ANNOUNCED: set = set()  # (question, worker, status) closes already in the log or present when the viewer started


def announce_closes(conv: page.Conversation, initial: bool) -> None:
    """Post a message from the worker each time it closes a question, once its one-line answer (gist) is written.
    On a board's first viewer, questions already closed get no message, so an old board does not flood the
    conversation; a resumed viewer posts the closes it missed while it was away."""
    events = conv.events()
    ANNOUNCED.update((e.get("question"), e.get("by"), e.get("status")) for e in events if e.get("type") == "closed")
    first = initial and not any(e.get("type") == "closed" for e in events)
    for path in md_files(conv.folder / "questions"):
        q = read_entry(path)
        status, gist = q.get("status", "").lower(), q.get("gist", "")
        key = (q["id"], q.get("owner", "none"), status)
        if status not in CLOSED or not gist or gist.lower() == "none" or key in ANNOUNCED:
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


def board_stopped(board: Path) -> bool:
    brief = board / "brief.md"
    return brief.exists() and read_entry(brief).get("status") == "stopped"


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
                stamp_logs(board, initial=False)
                return self.send_json({**load(board), "listening": conv.listening()})
            if self.conversation_get():
                return None
            if self.path in ("/", "/index.html"):
                return self.send(200, board_page(None).encode(), "text/html; charset=utf-8")
            self.send_error(404)

    stamp_logs(board, initial=True)
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
            stamp_logs(board, initial=False)
            with conv.lock:  # the page's actions append to the same log
                announce_closes(conv, initial=False)
            if stopped_at is None and board_stopped(board):
                stopped_at = time.time()
            if stopped_at is not None and not board_stopped(board):
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


# ---------- Command line ----------


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
    elif args.command == "wait":
        sys.exit(conversation(board).wait(args.timeout))
    elif args.command == "reply":
        conversation(board).reply(args.text, args.to)
    elif args.command == "status":
        conversation(board).set_status(args.state, args.ids, args.text)
    else:
        conversation(board).pending()


if __name__ == "__main__":
    main()
