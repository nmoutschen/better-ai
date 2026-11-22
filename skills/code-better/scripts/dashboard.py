#!/usr/bin/env python3
"""Show a coordinated change as a live dashboard, and carry the user's messages and answers back to the coordinator.

Usage:
  python3 dashboard.py watch CHANGE [--port N] [--no-browser]   serve the page; prints each action the user takes as
                                                                one JSON line; runs until stopped
  python3 dashboard.py check CHANGE                             print the records that are not valid, one per line as
                                                                file:line: field: message; exit 1 if there are any
  python3 dashboard.py wait CHANGE [--timeout S]                wait for the user's next actions on the served page
  python3 dashboard.py reply CHANGE TEXT [--to ID]              show the coordinator's reply in the page
  python3 dashboard.py status CHANGE seen|asked|working|done ID...
  python3 dashboard.py status CHANGE accepted ID... --text "the user's words"
  python3 dashboard.py pending CHANGE                           list the user's items that are not done or accepted

CHANGE is the change's folder, `.code/<change>/`, as code-better's coordinate mode writes it, in the formats of
schemas/: code.json (the goal, the design and the mode), spec.jsonl (or the one in the architect folder code.json names),
tasks.jsonl, decisions.jsonl, and in logs/ one <agent>.card.json with the agent's role, task and branch and the agent's
log, <agent>.jsonl. progress.jsonl, next-steps.jsonl, instructions.jsonl and lessons.jsonl are checked too, and not shown.
The page shows the agents at work and their latest steps, the tasks with the requirements of the spec, and a
conversation with the coordinator in which its decisions and its questions to the user appear. The user writes to the
coordinator, asks about an agent, answers a question or replies to a decision. Each action is a JSON-RPC call from the
page; the script appends it to conversation.jsonl in the folder and prints it to stdout. `wait` is for harnesses that
only notify when a command ends. `reply` and `status` work with or without a server, so a resumed run can answer what
the user wrote while no agent was running.

Every record is checked against its schema on its own. The page shows each valid record; the invalid ones, with where
they are, which field and why, are listed in an errors band, and `check` prints the same list: one bad record never
hides the others.
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

HERE = Path(__file__).resolve().parent  # dashboard.html, the page template, sits next to this script
sys.path.insert(0, str(HERE))  # page.py, the conversation every page that talks to the agent shares, sits here too
import page  # noqa: E402
import schema  # noqa: E402

SCHEMAS = HERE.parent / "schemas"
LOG, SEEN, ADDRESS = "conversation.jsonl", ".conversation-seen", ".server"
METHODS = ("comment", "note", "answer")  # what the page may send
ITEMS = ("comment", "note", "answer")  # what the coordinator tracks with status
# What an agent's last log line says about it, as the page shows it: the line's type, and the state it leaves the agent in.
STATES = {"start": "working", "step": "working", "asked": "waiting", "blocked": "blocked", "handed_back": "finished"}
# Where the spec is: next to the other files, or in the architect folder code.json names.
SPEC = {"from": "code.json", "field": "design.folder", "name": "spec.jsonl", "else": "spec.jsonl"}
CHECKED_ONLY = (
    "progress.jsonl",
    "next-steps.jsonl",
    "instructions.jsonl",
    "lessons.jsonl",
)  # the page does not show them


def lines_of(text: str, jsonl: bool) -> list:
    """The lines of a JSONL file, split on newlines only, without the empty piece after the last; a JSON file is one."""
    if not jsonl:
        return [text]
    pieces = [piece.removesuffix("\r") for piece in text.split("\n")]
    return pieces[:-1] if pieces and pieces[-1] == "" else pieces


class Reader:
    """Reads the files of one change folder record by record through schema.py: the valid records come back, and each
    invalid one goes to `errors` with its file, line, field, reason and, if it parsed, its `by`."""

    def __init__(self, change: Path):
        self.change, self.errors, self.cache = change, [], {}
        self.docs = schema.load_schemas(SCHEMAS)
        self.context = schema.Context(change, "tasks.jsonl", self.cache)

    def shown(self, path: Path) -> str:
        """A file's name as the errors give it: from the change folder, or from the repo root for another folder."""
        for base in (self.change, self.context.repo_root()):
            if base is not None:
                try:
                    return path.resolve().relative_to(base.resolve()).as_posix()
                except ValueError:
                    pass
        return str(path)

    def records(self, path: Path, keep_invalid: bool = False) -> list:
        """What `_records` reads; whatever else goes wrong with one file, for any reason, is that file's error."""
        try:
            return self._records(path, keep_invalid)
        except Exception as error:
            name = path.name
            self.errors.append(
                {"file": name, "line": 1, "field": "(file)", "message": f"could not be shown: {type(error).__name__}"}
            )
            return []

    def _records(self, path: Path, keep_invalid: bool = False) -> list:
        """The records of one file, in line order; none if it does not exist. The file is read once and that text is
        validated and shown, so a write in between is in neither. A record with errors is left out, unless
        `keep_invalid`: then it stays, with its messages in `_errors`, so the page can show what it can of it. A line
        that is not JSON is never a record."""
        if not path.is_file():
            return []
        name = self.shown(path)
        jsonl = path.suffix == ".jsonl"
        try:
            text = schema.read_checked(path, jsonl)
        except (OSError, UnicodeDecodeError) as error:
            self.errors.append({"file": name, "line": 1, "field": "(file)", "message": f"cannot be read: {error}"})
            return []
        found = schema.check_text(path, text, self.docs, self.cache)
        parsed = {}
        for number, piece in enumerate(lines_of(text, jsonl), 1):
            try:
                value = json.loads(piece)
            except (ValueError, RecursionError):
                continue
            parsed[number] = value if isinstance(value, dict) else None
        by_line: dict = {}
        for error in found:
            record = parsed.get(error.line)
            by = record.get("by") if record else None
            entry = {"file": name, "line": error.line, "field": error.field, "message": error.message}
            self.errors.append({**entry, "by": by} if isinstance(by, str) and by else entry)
            by_line.setdefault(error.line, []).append(error)
        kept = []
        for number, record in parsed.items():
            if record is None or (number in by_line and not keep_invalid):
                continue
            if number in by_line:
                status = record.get("status")
                record = schema.strip_invalid(record, by_line[number])
                if isinstance(status, str):
                    record["status"] = status  # only text on the page, so a status that failed shows as written
                if not isinstance(record.get("id"), str) or not record["id"]:
                    record["id"] = f"(line {number})"
            kept.append(record)
        return kept

    def spec_records(self) -> list:
        """The spec records, from spec.jsonl, or from the architect folder code.json names."""
        target, shown = self.context.target(SPEC)
        if target is None:
            self.errors.append({"file": "code.json", "line": 1, "field": "design.folder", "message": shown})
            return []
        path = Path(target)
        return self.records(path if path.is_absolute() else self.change / path)

    def folder(self, pattern: str) -> list:
        return sorted(self.change.glob(pattern))


def mtime(*paths: Path) -> float:
    return max((p.stat().st_mtime for p in paths if p.exists()), default=0.0)


def agent(reader: Reader, name: str, modes: dict) -> dict:
    """An agent from its two files in logs/: what it works on from <name>.card.json, which the coordinator writes when
    it starts the agent (role, task, branch), and its state from the last valid line of <name>.jsonl, the log the agent
    writes. Its mode is its task's."""
    logs = reader.change / "logs"
    card, log = logs / f"{name}.card.json", logs / f"{name}.jsonl"
    about = next(iter(reader.records(card)), {})
    lines = [
        {key: line[key] for key in ("type", "text", "result", "at") if key in line} for line in reader.records(log)
    ]
    return {
        "name": name,
        **{key: about.get(key) or "" for key in ("role", "task", "branch")},
        "mode": modes.get(about.get("task"), ""),
        "state": STATES.get(lines[-1]["type"], "working") if lines else "working",
        "lines": lines[-40:],
        "_changed": mtime(card, log),
    }


def decision(record: dict, answers: dict, changed: float) -> dict:
    """A decision as the page shows it: the user's answer is the page event it points to, or the words said in the chat.
    A decision that did not validate shows what it has, with its messages in `_errors`."""
    answer = record.get("answer") if isinstance(record.get("answer"), dict) else {}
    text = answers.get(answer.get("event"), "") if answer.get("type") == "page" else answer.get("text", "")
    about = record.get("about") if isinstance(record.get("about"), dict) else {}
    return {
        "id": record.get("id", ""),
        "asked": record.get("asked", ""),
        "status": record.get("status", ""),
        "decision": record.get("decision", ""),
        "answer": text if isinstance(text, str) else "",
        "from": record.get("raised_by", ""),
        "task": about.get("task", ""),
        "at": record.get("at", ""),
        "_errors": record.get("_errors", []),
        "_changed": changed,
    }


def collect(change: Path) -> dict:
    """Everything the page shows from the folder's files, and `errors`, the records that are not valid. It never
    raises, whatever the reason: a failure is an error entry."""
    try:
        return _collect(change)
    except Exception as error:
        message = f"could not be shown: {type(error).__name__}"
        return {
            "name": change.name,
            "tasks": [],
            "requirements": {},
            "agents": [],
            "decisions": [],
            "conversation": [],
            "errors": [{"file": "(folder)", "line": 1, "field": "(folder)", "message": message}],
        }


def _collect(change: Path) -> dict:
    try:
        reader = Reader(change)
    except schema.SchemaError as error:
        return {
            "tasks": [],
            "requirements": {},
            "agents": [],
            "decisions": [],
            "conversation": [],
            "errors": [{"file": "schemas", "line": 1, "field": "(schemas)", "message": str(error)}],
        }
    reader.records(change / "code.json")  # shown only through the errors it may hold; the tasks carry their own mode
    tasks = reader.records(change / "tasks.jsonl", keep_invalid=True)
    spec = reader.spec_records()
    conversation_events = reader.records(change / LOG)
    answers = {e["id"]: e["text"] for e in conversation_events if e.get("type") == "answer"}
    decisions = [
        decision(r, answers, mtime(change / "decisions.jsonl"))
        for r in reader.records(change / "decisions.jsonl", keep_invalid=True)
    ]
    modes = {t["id"]: t.get("mode", "") for t in tasks if "id" in t}
    names = sorted(
        {
            f.name.removesuffix(".card.json").removesuffix(".jsonl")
            for f in [*reader.folder("logs/*.card.json"), *reader.folder("logs/*.jsonl")]
        }
    )
    agents = [agent(reader, name, modes) for name in names]
    for name in CHECKED_ONLY:
        reader.records(change / name)
    return {
        "name": change.name,
        "tasks": tasks,
        "requirements": {r["id"]: r["statement"] for r in spec if r.get("type") == "spec"},
        "agents": agents,
        "decisions": decisions,
        "conversation": conversation_events,
        "errors": reader.errors,
    }


def load(change: Path) -> dict:
    return {**collect(change), "now": time.time()}


def dashboard_page() -> str:
    """The page, read on each request, so a fix to dashboard.html or page.css shows on reload without a restart."""
    shared = (HERE / "page.css").read_text(encoding="utf-8")  # the look shared with the other skills' pages
    script = (HERE / "page.js").read_text(encoding="utf-8")  # the conversation shared with the other skills' pages
    html = (HERE / "dashboard.html").read_text(encoding="utf-8").replace("/*__PAGE_CSS__*/", shared)
    return html.replace("/*__PAGE_JS__*/", script)


def conversation(change: Path) -> page.Conversation:
    return page.Conversation(
        change,
        LOG,
        SEEN,
        ADDRESS,
        ITEMS,
        "coordinator",
        "watch CHANGE",
        schemas=HERE.parent / "schemas",
        events="dashboard-events.schema.json",
    )


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


@schema.never_raise("change", {**page.VERBS, "watch": "served", "": "checked"})
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Show a coordinated change as a live page and collect the user's input."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("check", help="print the records that are not valid, and exit 1 if there are any")
    c.add_argument("change")
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
    st.add_argument("--text", help="the user's words, for accepted")
    p = sub.add_parser("pending", help="list the user's items that are not done or accepted")
    p.add_argument("change")
    args = parser.parse_args()
    change = Path(args.change).expanduser().resolve()
    if not change.is_dir():
        sys.exit(f"error: {change} is not a directory")
    if args.command == "check":
        errors = collect(change)["errors"]
        for error in errors:
            print(f"{error['file']}:{error['line']}: {error['field']}: {error['message']}")
        sys.exit(1 if errors else 0)
    elif args.command == "watch":
        watch(change, args.port, not args.no_browser)
    elif args.command == "wait":
        sys.exit(conversation(change).wait(args.timeout))
    elif args.command == "reply":
        conversation(change).reply(args.text, args.to)
    elif args.command == "status":
        conversation(change).set_status(args.state, args.ids, args.text)
    else:
        conversation(change).pending()


if __name__ == "__main__":
    sys.exit(main())
