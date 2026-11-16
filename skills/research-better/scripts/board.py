#!/usr/bin/env python3
"""Show a research board as a live dashboard, and carry the user's comments and answers back to the coordinator.

Usage:
  python3 board.py watch BOARD [--port N] [--no-browser]   serve the page; prints each action the user takes as one
                                                           JSON line; exits by itself once the board is stopped
  python3 board.py snapshot BOARD --out FILE               write a static page
  python3 board.py wait BOARD [--timeout S]                wait for the user's next actions on the served page
  python3 board.py reply BOARD TEXT [--to ID]              show the coordinator's reply in the page
  python3 board.py status BOARD seen|asked|working|done|accepted ID...
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
import urllib.request
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent  # board.html, the page template, sits next to this script
KINDS = ("questions", "claims", "sources", "decisions")
FIRST_SEEN: dict = {}  # (agent, line number, text) -> time the viewer first read that log line

LOG, SEEN, ADDRESS = "conversation.jsonl", ".conversation-seen", ".server"
METHODS = ("comment", "note", "answer")  # what the page may send
ITEMS = ("comment", "note", "answer")  # what the coordinator tracks with status
STATES = ("seen", "asked", "working", "done", "accepted")
MAX_BODY = 200_000
LISTEN_GAP = 10  # seconds without a `wait` connected before the page says the coordinator is not watching


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
    data = {"brief": {}, "logs": {}, "now": time.time(), "conversation": read_log(board)}
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


def page(snapshot: dict | None) -> str:
    """The page, read on each request, so a fix to board.html or page.css shows on reload without restarting the viewer."""
    embedded = "null" if snapshot is None else json.dumps(snapshot).replace("</", "<\\/")
    shared = (HERE / "page.css").read_text(encoding="utf-8")  # the look shared with design-better's canvas
    html = (HERE / "board.html").read_text(encoding="utf-8").replace("/*__PAGE_CSS__*/", shared)
    return html.replace("__SNAPSHOT__", embedded)


def stamp_logs(board: Path, initial: bool) -> None:
    """Record when each log line first appears. Lines present before the viewer started get no time."""
    now = time.time()
    for path in md_files(board / "logs"):
        for i, line in enumerate(text_lines(path)):
            FIRST_SEEN.setdefault((path.stem, i, line), None if initial else now)


CLOSED = ("answered", "contested", "not found", "unclear")  # the statuses a worker sets when it finishes a question
ANNOUNCED: set = set()  # (question, worker, status) closes already in the log or present when the viewer started


def announce_closes(board: Path, initial: bool) -> None:
    """Post a message from the worker each time it closes a question, once its one-line answer (gist) is written.
    On a board's first viewer, questions already closed get no message, so an old board does not flood the
    conversation; a resumed viewer posts the closes it missed while it was away."""
    events = read_log(board)
    ANNOUNCED.update((e.get("q"), e.get("by"), e.get("status")) for e in events if e.get("action") == "closed")
    first = initial and not any(e.get("action") == "closed" for e in events)
    for path in md_files(board / "questions"):
        q = read_entry(path)
        status, gist = q.get("status", "").lower(), q.get("gist", "")
        key = (q["id"], q.get("owner", "none"), status)
        if status not in CLOSED or not gist or gist.lower() == "none" or key in ANNOUNCED:
            continue
        ANNOUNCED.add(key)
        if not first:
            append(
                board,
                {
                    "action": "closed",
                    "id": "c-" + str(time.time_ns()),
                    "by": key[1],
                    "q": key[0],
                    "status": status,
                    "text": gist[:500],
                },
            )


def board_stopped(board: Path) -> bool:
    brief = board / "brief.md"
    return brief.exists() and read_entry(brief).get("status") == "stopped"


# ---------- The conversation log ----------


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def log_lines(board: Path) -> list:
    """The log's lines. Only "\\n" ends a line: events are ASCII JSON, so no other character can split one."""
    log = board / LOG
    return log.read_text(encoding="utf-8").split("\n")[:-1] if log.exists() else []


def read_log(board: Path) -> list:
    events = []
    for line in log_lines(board):
        try:
            events.append(json.loads(line))
        except ValueError:
            events.append({})  # keep the position, so indexes into the log stay right
    return events


def append(board: Path, *events: dict) -> list:
    """Write events to the log as ASCII JSON, so a character such as U+2028 in a message cannot split a line."""
    lines = [json.dumps({"at": now(), **e}) for e in events]
    with (board / LOG).open("a", encoding="utf-8") as f:
        f.write("".join(line + "\n" for line in lines))
    return lines


def from_user(event: dict) -> bool:
    """An event the user made in the page, as opposed to the coordinator's replies, statuses and recorded acceptances."""
    return bool(event) and event.get("action") not in ("reply", "status", "closed") and "by" not in event


def clean(value, depth=0):
    """Keep only JSON values a page can legitimately send, with long text cut, so the log stays readable."""
    if isinstance(value, str):
        return value[:5000]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if depth < 3 and isinstance(value, dict):
        return {str(k)[:100]: clean(v, depth + 1) for k, v in list(value.items())[:20]}
    return None


def rpc_error(rid, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}


# ---------- watch ----------


def watch(board: Path, port: int, open_browser: bool, linger: float) -> None:
    lock = threading.Lock()
    # Whether a `wait` is listening: None until one first connects (the coordinator may stream this output instead),
    # then True while one is connected or reconnected within LISTEN_GAP seconds. The page warns the user when False.
    waiters = {"open": 0, "last": None}

    def listening():
        if waiters["last"] is None:
            return None
        return waiters["open"] > 0 or time.time() - waiters["last"] < LISTEN_GAP

    def wait_for_more(after: int, seconds: float) -> int:
        deadline = time.time() + seconds
        while len(log_lines(board)) <= after and time.time() < deadline:
            time.sleep(0.25)
        return len(log_lines(board))

    class Handler(http.server.BaseHTTPRequestHandler):
        def local(self) -> bool:
            # Only answer requests addressed to this machine, so a web page cannot reach the board via DNS rebinding.
            return (self.headers.get("Host") or "").rsplit(":", 1)[0] in ("127.0.0.1", "localhost")

        def send(self, code: int, body: bytes, kind: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, value) -> None:
            self.send(200, json.dumps(value).encode(), "application/json")

        def do_GET(self):
            if not self.local():
                return self.send_error(403)
            if self.path.startswith("/board.json"):
                stamp_logs(board, initial=False)
                return self.send_json({**load(board), "listening": listening()})
            if self.path in ("/", "/index.html"):
                return self.send(200, page(None).encode(), "text/html; charset=utf-8")
            if self.path.startswith("/wait?after="):
                # Long poll for `wait`: the number of events, as soon as there are more than `after`.
                value = self.path.split("=", 1)[1]
                with lock:
                    waiters["open"] += 1
                    waiters["last"] = time.time()
                try:
                    total = wait_for_more(int(value) if value.isdigit() else 0, 25)
                finally:
                    with lock:
                        waiters["open"] -= 1
                        waiters["last"] = time.time()
                return self.send(200, str(total).encode(), "text/plain")
            self.send_error(404)

        def do_POST(self):
            # Only this page may send: the same host and origin, and a JSON body that a cross-site form cannot send.
            origin = self.headers.get("Origin", "")
            if not self.local() or self.path != "/rpc" or origin != "http://" + (self.headers.get("Host") or ""):
                return self.send_error(403)
            if not (self.headers.get("Content-Type") or "").startswith("application/json"):
                return self.send_error(415)
            size = int(self.headers.get("Content-Length") or 0)
            if not 0 < size <= MAX_BODY:
                return self.send_error(413)
            try:
                msg = json.loads(self.rfile.read(size))
            except ValueError:
                return self.send_json(rpc_error(None, -32700, "Parse error"))
            rid = msg.get("id") if isinstance(msg, dict) else None
            if (
                not isinstance(msg, dict)
                or msg.get("jsonrpc") != "2.0"
                or msg.get("method") not in METHODS
                or not isinstance(msg.get("params"), dict)
            ):
                return self.send_json(rpc_error(rid, -32601, "Unknown method"))
            with lock:
                (line,) = append(board, {"action": msg["method"], **clean(msg["params"])})
                print(line, flush=True)
            self.send_json({"jsonrpc": "2.0", "id": rid, "result": "saved"})

        def log_message(self, *args):
            pass

    stamp_logs(board, initial=True)
    with lock:
        announce_closes(board, initial=True)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    (board / ADDRESS).write_text(url, encoding="utf-8")
    if not (board / SEEN).exists():  # a resumed run keeps its place, so it still sees what came in while it was away
        (board / SEEN).write_text("0", encoding="utf-8")
    print(f"Watching {board} at {url}. Each action the user takes is printed here as one JSON line.", flush=True)
    print("Stops by itself once the board's status is stopped (or press Ctrl+C).", flush=True)
    if open_browser and not webbrowser.open(url):
        print(
            "Could not open a browser on this machine. If the user's browser runs on another machine, "
            "this address does not reach it.",
            flush=True,
        )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    stopped_at = None
    try:
        while True:
            time.sleep(1)
            stamp_logs(board, initial=False)
            with lock:  # the page's actions append to the same log
                announce_closes(board, initial=False)
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
        (board / ADDRESS).unlink(missing_ok=True)


# ---------- wait, reply, status, pending ----------


def wait(board: Path, timeout: float) -> int:
    """Print the user's actions the coordinator has not seen yet, waiting for the served page to receive one."""
    if not (board / ADDRESS).exists():
        sys.exit(f"error: no page is served for {board}. Start it with `watch` first.")
    cursor = board / SEEN
    seen = int(cursor.read_text() or 0) if cursor.exists() else 0
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{(board / ADDRESS).read_text().strip()}wait?after={seen}", timeout=30) as r:
                total = int(r.read())
        except OSError:
            sys.exit("error: the page's server is not answering. Is it still running?")
        if total <= seen:
            continue
        lines = log_lines(board)[seen:total]
        new = [line for line, event in zip(lines, read_log(board)[seen:total], strict=True) if from_user(event)]
        cursor.write_text(str(total), encoding="utf-8")
        seen = total
        if new:
            print("\n".join(new), flush=True)
            return 0
    print("No new action before the timeout.", flush=True)
    return 2


def reply(board: Path, text: str, to: str | None) -> None:
    """Show the coordinator's reply in the page's conversation, under the item it answers."""
    # Each reply has an id, so the user can answer any message, the agent's own included.
    append(board, {"action": "reply", "id": "r-" + str(time.time_ns()), "text": text[:5000], "to": to})
    print("Reply shown in the page." if (board / ADDRESS).exists() else "Reply saved; the page shows it when served.")


def set_status(board: Path, state: str, ids: list) -> None:
    """Mark the user's items as seen, asked, working or done. Accepted records an acceptance the user gave in words,
    the same as the page's Accept button."""
    events = read_log(board)
    owned = {
        e.get("id") for e in events if e.get("action") in ITEMS and not (e.get("action") == "note" and e.get("to"))
    }
    # An answer under one of the user's items is part of it; an answer to the agent's own message is an item itself.
    answers = {e.get("id"): e.get("to") for e in events if e.get("action") == "note" and e.get("to") in owned}
    misplaced = [i for i in ids if i in answers]
    if misplaced:  # an answer is part of the item it answers, which carries the state
        sys.exit(
            "error: "
            + ", ".join(f"{i} answers {answers[i]}" for i in misplaced)
            + ". Mark the item it answers instead."
        )
    known = {e.get("id") for e in events if e.get("action") in ITEMS}
    unknown = [i for i in ids if i not in known]
    if unknown:
        sys.exit(f"error: no comment or message with id {', '.join(unknown)}. Run `pending` to see the ids.")
    append(
        board,
        *(
            {"action": "accept", "to": i, "by": "coordinator, from the user's words"}
            if state == "accepted"
            else {"action": "status", "to": i, "status": state}
            for i in ids
        ),
    )
    print(f"Marked {state}: {', '.join(ids)}")


def pending(board: Path) -> None:
    """Print each item not yet done, with the answers and replies under it, so a resumed run can act on what the user
    wrote while no agent was running. A follow-up from the user under a done item makes it work again."""
    items, order, state, reasons, thread, closes = {}, [], {}, {}, {}, {}
    for e in read_log(board):
        a, i, to = e.get("action"), e.get("id"), e.get("to")
        if a == "closed":  # a worker's message: the user can reply to it, and the reply goes to the coordinator
            closes[i] = e
        elif (
            a == "note" and to and to not in items
        ):  # an answer to the agent's own message is a new item, about that message
            order.append(i)
            items[i] = e
            if to in closes:  # the worker cannot read the page: say which question the user replied about
                c = closes[to]
                items[i] = {**e, "about": f"{c.get('by')} closed {c.get('q')} as {c.get('status')}: {c.get('text')}"}
        elif a == "note" and to:  # the user's answer belongs to the item it answers
            thread.setdefault(to, []).append({"from": "user", "at": e.get("at"), "text": e.get("text")})
            if state.get(to) == "asked":  # the answer ends the wait: the item is the coordinator's again
                state[to] = "answered by the user"
            elif state.get(to) in ("done", "accepted"):  # a follow-up under an answered item is work again
                state[to] = "follow-up from the user"
        elif a == "reply" and to:
            thread.setdefault(to, []).append({"from": "coordinator", "at": e.get("at"), "text": e.get("text")})
        elif a in ITEMS and i:
            if i not in items:
                order.append(i)
            items[i] = e
        elif a == "status":
            state[to] = e.get("status")
        elif a == "accept":
            state[to] = "accepted"
        elif a == "reopen":
            state[to], reasons[to] = "reopened", e.get("reason")
    open_items = [items[i] for i in order if state.get(i) not in ("done", "accepted")]
    for e in open_items:
        extra = {}
        if state.get(e["id"]) == "reopened" and reasons.get(e["id"]):
            extra["reopened_because"] = reasons[e["id"]]
        if thread.get(e["id"]):
            extra["thread"] = thread[e["id"]]
        print(json.dumps({**e, "status": state.get(e["id"], "new"), **extra}, ensure_ascii=False))
    print(f"{len(open_items)} not done.")


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
    st.add_argument("state", choices=STATES)
    st.add_argument("ids", nargs="+")
    p = sub.add_parser("pending", help="list the user's items that are not done or accepted")
    p.add_argument("board")
    args = parser.parse_args()
    board = Path(args.board).expanduser().resolve()
    if not board.is_dir():
        sys.exit(f"error: {board} is not a directory")
    if args.command == "watch":
        watch(board, args.port, not args.no_browser, args.linger)
    elif args.command == "snapshot":
        Path(args.out).write_text(page(load(board)), encoding="utf-8")
        print(f"wrote {args.out}")
    elif args.command == "wait":
        sys.exit(wait(board, args.timeout))
    elif args.command == "reply":
        reply(board, args.text, args.to)
    elif args.command == "status":
        set_status(board, args.state, args.ids)
    else:
        pending(board)


if __name__ == "__main__":
    main()
