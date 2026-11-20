#!/usr/bin/env python3
"""Show a coordinated change as a live dashboard, and carry the user's messages and answers back to the coordinator.

Usage:
  python3 dashboard.py watch CHANGE [--port N] [--no-browser]   serve the page; prints each action the user takes as
                                                                one JSON line; runs until stopped
  python3 dashboard.py wait CHANGE [--timeout S]                wait for the user's next actions on the served page
  python3 dashboard.py reply CHANGE TEXT [--to ID]              show the coordinator's reply in the page
  python3 dashboard.py status CHANGE seen|asked|working|done|accepted ID...
  python3 dashboard.py pending CHANGE                           list the user's items that are not done

CHANGE is the change's folder, `.code/<change>/`, as code-better's coordinate mode writes it: tasks.md, the agents'
logs in logs/ (their format is in agents/builder.md and agents/verifier.md) and the coordinator's decisions and
questions in decisions/ (templates/decision.md). The page shows the agents at work and their latest steps, the tasks done, and a conversation
with the coordinator in which its decisions and its questions to the user appear. The user writes to the coordinator,
asks about an agent, answers a question or replies to a decision. Each action is a JSON-RPC call from the page; the
script appends it to conversation.jsonl in the folder and prints it to stdout. `wait` is for harnesses that only
notify when a command ends. `reply` and `status` work with or without a server, so a resumed run can answer what the
user wrote while no agent was running.
"""

from __future__ import annotations

import argparse
import http.server
import re
import sys
import threading
import time
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent  # dashboard.html, the page template, sits next to this script
sys.path.insert(0, str(HERE))  # page.py, the conversation every page that talks to the agent shares, sits here too
import page  # noqa: E402

LOG, SEEN, ADDRESS = "conversation.jsonl", ".conversation-seen", ".server"
METHODS = ("comment", "note", "answer")  # what the page may send
ITEMS = ("comment", "note", "answer")  # what the coordinator tracks with status
# The first word of an agent's log line, and the state it leaves the agent in (agents/builder.md, agents/verifier.md).
STEPS = {"start": "working", "step": "working", "asked": "waiting", "blocked": "blocked", "handed back": "finished"}


def md_files(folder: Path) -> list:
    """The .md files in a folder, in name order; none if the folder does not exist yet."""
    return sorted(folder.glob("*.md")) if folder.is_dir() else []


def read_entry(path: Path) -> dict:
    entry = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() and " " not in key.strip():
            entry[key.strip()] = value.strip()
    entry.setdefault("id", path.stem)
    entry["_changed"] = path.stat().st_mtime
    return entry


def read_tasks(path: Path) -> tuple:
    """The change's name and its tasks, from the table in tasks.md (templates/tasks.md). Columns are found by their
    heading, so a table with columns added or moved still reads."""
    if not path.exists():
        return "", []
    name, head, tasks = "", None, []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("# ") and not name:
            name = re.sub(r"^#\s*Tasks:\s*", "", line).strip()
        if not line.lstrip().startswith("|"):
            head = None if tasks else head
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-+:?", c) for c in cells if c):
            continue
        if head is None:
            head = [c.lower() for c in cells]
            continue
        row = dict(zip(head, cells, strict=False))  # a short row leaves the last columns empty
        if not row.get("task") or row.get("task", "").startswith("<"):
            continue  # the template's placeholder row
        tasks.append(
            {
                "id": row.get("#", ""),
                "task": row["task"],
                "mode": row.get("mode", ""),
                "status": row.get("status", "").lower(),
            }
        )
    return name, tasks


def read_agent(path: Path) -> dict:
    """An agent's role, task and state from its log: the last `start:` line names the role and task, the last line
    the state. A line that starts with no known word counts as a step, so a slip never hides an agent."""
    lines = [line.strip() for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
    agent = {
        "name": path.stem,
        "role": "",
        "task": "",
        "branch": "",
        "state": "working",
        "lines": lines[-40:],
        "_changed": path.stat().st_mtime,
    }
    for line in lines:
        word, _, rest = line.partition(":")
        word = word.strip().lower()
        if word == "start":
            parts = [p.strip() for p in rest.split(",")]
            agent["role"] = parts[0].lower() if parts else ""
            agent["task"] = re.sub(r"^task\s*#?", "", parts[1], flags=re.I) if len(parts) > 1 else ""
            agent["branch"] = parts[2] if len(parts) > 2 else ""
        agent["state"] = STEPS.get(word, "working")
    return agent


def load(change: Path) -> dict:
    name, tasks = read_tasks(change / "tasks.md")
    return {
        "name": name or change.name,
        "tasks": tasks,
        "agents": [read_agent(path) for path in md_files(change / "logs")],
        "decisions": [read_entry(path) for path in md_files(change / "decisions")],
        "conversation": conversation(change).events(),
        "now": time.time(),
    }


def dashboard_page() -> str:
    """The page, read on each request, so a fix to dashboard.html or page.css shows on reload without a restart."""
    shared = (HERE / "page.css").read_text(encoding="utf-8")  # the look shared with the other skills' pages
    script = (HERE / "page.js").read_text(encoding="utf-8")  # the conversation shared with the other skills' pages
    html = (HERE / "dashboard.html").read_text(encoding="utf-8").replace("/*__PAGE_CSS__*/", shared)
    return html.replace("/*__PAGE_JS__*/", script)


def conversation(change: Path) -> page.Conversation:
    return page.Conversation(change, LOG, SEEN, ADDRESS, ITEMS, "coordinator", "watch CHANGE")


# ---------- watch ----------


def watch(change: Path, port: int, open_browser: bool) -> None:
    conv = conversation(change)

    class Handler(page.Handler):
        conversation = conv
        methods = METHODS

        def do_GET(self):
            if not self.local():
                return self.send_error(403)
            if self.path.startswith("/dashboard.json"):
                return self.send_json({**load(change), "listening": conv.listening()})
            if self.conversation_get():
                return None
            if self.path in ("/", "/index.html"):
                return self.send(200, dashboard_page().encode(), "text/html; charset=utf-8")
            self.send_error(404)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    conv.address.write_text(url, encoding="utf-8")
    if not conv.seen.exists():  # a resumed run keeps its place, so it still sees what came in while it was away
        conv.seen.write_text("0", encoding="utf-8")
    print(f"Watching {change} at {url}. Each action the user takes is printed here as one JSON line.", flush=True)
    print("Runs until stopped (Ctrl+C).", flush=True)
    if open_browser and not webbrowser.open(url):
        print(
            "Could not open a browser on this machine. If the user's browser runs on another machine, "
            "this address does not reach it.",
            flush=True,
        )
    page.stop_like_ctrl_c()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
        conv.address.unlink(missing_ok=True)


# ---------- Command line ----------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Show a coordinated change as a live page and collect the user's input."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    w = sub.add_parser("watch", help="serve the live page")
    w.add_argument("change")
    w.add_argument("--port", type=int, default=0, help="port to serve on (default: any free port)")
    w.add_argument("--no-browser", action="store_true", help="do not open a browser")
    t = sub.add_parser("wait", help="wait for the user's next actions on the served page, print them and exit")
    t.add_argument("change")
    t.add_argument("--timeout", type=float, default=600, help="seconds to wait (default 600)")
    r = sub.add_parser("reply", help="show a reply from the coordinator in the page")
    r.add_argument("change")
    r.add_argument("text")
    r.add_argument("--to", help="the id of the item it answers")
    st = sub.add_parser("status", help="mark the user's items seen, asked, working, done or accepted")
    st.add_argument("change")
    st.add_argument("state", choices=page.STATES)
    st.add_argument("ids", nargs="+")
    p = sub.add_parser("pending", help="list the user's items that are not done or accepted")
    p.add_argument("change")
    args = parser.parse_args()
    change = Path(args.change).expanduser().resolve()
    if not change.is_dir():
        sys.exit(f"error: {change} is not a directory")
    if args.command == "watch":
        watch(change, args.port, not args.no_browser)
    elif args.command == "wait":
        sys.exit(conversation(change).wait(args.timeout))
    elif args.command == "reply":
        conversation(change).reply(args.text, args.to)
    elif args.command == "status":
        conversation(change).set_status(args.state, args.ids)
    else:
        conversation(change).pending()


if __name__ == "__main__":
    main()
