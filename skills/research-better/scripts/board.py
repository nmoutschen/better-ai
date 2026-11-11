#!/usr/bin/env python3
"""Show a research board as a live page: what agents are working on now, and the question tree.

Usage:
  python3 board.py watch BOARD [--port N]      serve a page that updates as agents write;
                                               exits by itself when the board's status is stopped
  python3 board.py snapshot BOARD --out FILE   write a static HTML page

BOARD is the board directory described in templates/board.md.
"""

from __future__ import annotations

import argparse
import http.server
import json
import os
import sys
import time
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent  # board.html, the page template, sits next to this script
KINDS = ("questions", "claims", "sources")
FIRST_SEEN: dict = {}  # (agent, line number, text) -> time the viewer first read that log line


def born(path: Path) -> float:
    """Creation time where the filesystem records it, else last modification."""
    stat = path.stat()
    return getattr(stat, "st_birthtime", stat.st_mtime)


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
    data = {"brief": {}, "logs": {}, "now": time.time()}
    if (board / "brief.md").exists():
        data["brief"] = read_entry(board / "brief.md")
    for kind in KINDS:
        folder = board / kind
        files = sorted(folder.glob("*.md")) if folder.is_dir() else []
        data[kind] = [read_entry(path) for path in files]
    if (board / "logs").is_dir():
        for path in sorted((board / "logs").glob("*.md")):
            lines = [line for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
            stamped = []
            for i, line in enumerate(lines):
                key = (path.stem, i, line)
                stamped.append([FIRST_SEEN.get(key), line])
            data["logs"][path.stem] = {"last": lines[-1] if lines else "", "lines": stamped[-60:], "count": len(lines),
                                       "_born": born(path), "_changed": path.stat().st_mtime}
    return data


PAGE = (HERE / "board.html").read_text(encoding="utf-8")


def page(snapshot: dict | None) -> str:
    embedded = "null" if snapshot is None else json.dumps(snapshot).replace("</", "<\\/")
    return PAGE.replace("__SNAPSHOT__", embedded)


def stamp_logs(board: Path, initial: bool) -> None:
    """Record when each log line first appears. Lines present before the viewer started get no time."""
    now = time.time()
    for path in sorted((board / "logs").glob("*.md")) if (board / "logs").is_dir() else []:
        lines = [line for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
        for i, line in enumerate(lines):
            FIRST_SEEN.setdefault((path.stem, i, line), None if initial else now)


def board_stopped(board: Path) -> bool:
    brief = board / "brief.md"
    return brief.exists() and read_entry(brief).get("status") == "stopped"


def watch(board: Path, port: int, open_browser: bool, linger: float) -> None:
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            # Only answer requests addressed to this machine, so a web page cannot read the board via DNS rebinding.
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
            if host not in ("127.0.0.1", "localhost"):
                self.send_error(403)
                return
            if self.path.startswith("/board.json"):
                stamp_logs(board, initial=False)
                body, kind = json.dumps(load(board)).encode(), "application/json"
            elif self.path in ("/", "/index.html"):
                body, kind = page(None).encode(), "text/html; charset=utf-8"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    stamp_logs(board, initial=True)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.timeout = 1
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"Watching {board} at {url}", flush=True)
    print("Stops by itself once the board's status is stopped (or press Ctrl+C).", flush=True)
    if open_browser and not webbrowser.open(url):
        print("Could not open a browser on this machine. If the user's browser runs on another machine, this address does not reach it.", flush=True)
    stopped_at = None
    try:
        while True:
            server.handle_request()
            stamp_logs(board, initial=False)
            if stopped_at is None and board_stopped(board):
                stopped_at = time.time()
            if stopped_at is not None and time.time() - stopped_at > linger:
                print("Board stopped; viewer exiting. The open page keeps the last state.", flush=True)
                break
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Show a research board as a web page.")
    sub = parser.add_subparsers(dest="command", required=True)
    w = sub.add_parser("watch", help="serve a live page")
    w.add_argument("board")
    w.add_argument("--port", type=int, default=0, help="port to serve on (default: any free port)")
    w.add_argument("--linger", type=float, default=10, help="seconds to keep serving after the board stops")
    w.add_argument("--no-browser", action="store_true", help="do not open a browser")
    s = sub.add_parser("snapshot", help="write a static page")
    s.add_argument("board")
    s.add_argument("--out", required=True)
    args = parser.parse_args()
    board = Path(args.board).expanduser().resolve()
    if not board.is_dir():
        sys.exit(f"error: {board} is not a directory")
    if args.command == "watch":
        watch(board, args.port, not args.no_browser, args.linger)
    else:
        Path(args.out).write_text(page(load(board)), encoding="utf-8")
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
