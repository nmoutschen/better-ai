"""The conversation between a served page and the agent: the log, the page's server endpoints, and the agent's `wait`,
`reply`, `status` and `pending`.

Each skill whose page talks to the agent carries an identical copy of this file next to its script, as it does
page.css and page.js, and the Scripts workflow fails if the copies differ: change it in one skill, then copy it to the
others. The script that serves the page supplies what differs: the log's file names, what the page may send, which
events are items the agent tracks, what the agent is called on the page, and the page's own events schema.

Every event, whether the page sends it or the agent writes it, is checked through schema.py against
`conversation.schema.json` and the page's `<page>-events.schema.json` before it is written to the log; one that fails
is not written. A page event answers with the JSON-RPC error -32602 and the validator's message.
"""

from __future__ import annotations

import contextlib
import functools
import http.server
import importlib.util
import json
import signal
import sys
import threading
import time
import urllib.request
from pathlib import Path


def _load_schema():
    """schema.py from the folder of this file: each skill carries its own identical copy."""
    spec = importlib.util.spec_from_file_location("page_schema", Path(__file__).resolve().with_name("schema.py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules["page_schema"] = module  # the module's own typing needs to find itself by name
    spec.loader.exec_module(module)
    return module


schema = _load_schema()
COMMON = "conversation.schema.json"
VERBS = {"wait": "read", "pending": "read", "reply": "written", "status": "written"}  # what the agent's commands do
MAX_BODY = 200_000
LISTEN_GAP = 10  # seconds without a `wait` connected before the page says the agent is not watching
STATES = ("seen", "asked", "working", "done", "accepted")  # `accepted` is written as its own event, `accepted`


class EventError(ValueError):
    """An event that fails its schema: the message is the validator's, `field: message` for each problem."""


def terminal_json(value) -> str:
    """JSON for a terminal: readable, and escaped where UTF-8 cannot hold a character (a lone surrogate), so printing
    it never fails."""
    text = json.dumps(value, ensure_ascii=False)
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return json.dumps(value)
    return text


def terminal_text(text: str) -> str:
    """Text a person gave (an id on the command line) as it can be printed: bytes UTF-8 cannot hold are escaped."""
    return text.encode("utf-8", "backslashreplace").decode("utf-8")


def now() -> str:
    """The time as an event records it: UTC, with Z."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def clean(value, depth=0):
    """Keep only JSON values a page can legitimately send, with long text cut, so the log stays readable."""
    if isinstance(value, str):
        return value[:5000]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if depth < 4 and isinstance(value, dict):
        return {str(k)[:100]: clean(v, depth + 1) for k, v in list(value.items())[:50]}
    if depth < 4 and isinstance(value, list):
        return [clean(v, depth + 1) for v in value[:50]]
    return None


def from_user(event: dict) -> bool:
    """An event the user made in the page, as opposed to the agent's replies, statuses and recorded acceptances."""
    return bool(event) and event.get("by") == "user"


def stop_like_ctrl_c() -> None:
    """Stop the server on SIGTERM or SIGHUP as on Ctrl+C, so the script still removes its address file when the
    harness ends the command or the terminal closes. A SIGKILL cannot be caught: `reply` checks the server instead."""

    def stop(signum, frame):
        raise KeyboardInterrupt

    for name in ("SIGTERM", "SIGHUP"):
        if hasattr(signal, name):  # Windows has no SIGHUP
            signal.signal(getattr(signal, name), stop)


def rpc_error(rid, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}


class Conversation:
    """One page's log, LOG in FOLDER, one ASCII JSON event per line, and the files that say where it is served (ADDRESS)
    and how far the agent has read (SEEN). ITEMS are the event types the agent tracks with a status. AGENT is what the
    page calls the agent, such as "coordinator", and the `by` of what the agent writes. START says how to serve the
    page, for the error when it is not served. SCHEMAS is the folder of the skill's schemas and EVENTS the file name of
    the page's own events schema in it."""

    def __init__(
        self,
        folder: Path,
        log: str,
        seen: str,
        address: str,
        items: tuple,
        agent: str,
        start: str,
        schemas: Path,
        events: str | None = None,
    ):
        self.folder, self.items, self.agent, self.start = folder, items, agent, start
        self.schemas, self.events_schema = schemas, events
        self.log, self.seen, self.address = folder / log, folder / seen, folder / address
        self.lock = threading.Lock()
        # Whether a `wait` is listening: None until one first connects (the agent may stream the server's output
        # instead), then True while one is connected or reconnected within LISTEN_GAP seconds. The page warns the user
        # when it is False.
        self.waiters = {"open": 0, "last": None}

    # ---------- The log ----------

    def lines(self) -> list:
        """The log's lines. Only "\\n" ends a line: events are ASCII JSON, so no other character can split one."""
        try:
            return self.log.read_text(encoding="utf-8", errors="replace").split("\n")[:-1]
        except OSError:  # no log yet, or one that cannot be read
            return []

    def events(self) -> list:
        events = []
        for line in self.lines():
            try:
                event = json.loads(line)
            except (ValueError, RecursionError):
                event = None
            events.append(
                event if isinstance(event, dict) else {}
            )  # keep the position, so indexes into the log stay right
        return events

    def check(self, event: dict) -> None:
        """Raise EventError, with the validator's message, unless the event meets the shared conversation schema and
        the page's own."""
        names = [COMMON, *([self.events_schema] if self.events_schema else [])]
        problems = schema.check_record(event, names, self.schemas)
        if problems:
            raise EventError("; ".join(f"{field}: {message}" for field, message in problems))

    def append(self, *events: dict) -> list:
        """Check events, then write them to the log as ASCII JSON, so a character such as U+2028 in a message cannot
        split a line. None is written if one fails."""
        records = [{"type": e.get("type"), "at": now(), **e} for e in events]
        for record in records:
            self.check(record)
        lines = [json.dumps(record) for record in records]
        with self.log.open("a", encoding="utf-8") as f:
            f.write("".join(line + "\n" for line in lines))
        return lines

    # ---------- The server's side ----------

    def listening(self):
        if self.waiters["last"] is None:
            return None
        return self.waiters["open"] > 0 or time.time() - self.waiters["last"] < LISTEN_GAP

    def wait_for_more(self, after: int, seconds: float) -> int:
        deadline = time.time() + seconds
        while len(self.lines()) <= after and time.time() < deadline:
            time.sleep(0.25)
        return len(self.lines())

    def waited(self, after: int) -> int:
        """Long poll for `wait`: the number of events, as soon as there are more than `after`."""
        with self.lock:
            self.waiters["open"] += 1
            self.waiters["last"] = time.time()
        try:
            return self.wait_for_more(after, 25)
        finally:
            with self.lock:
                self.waiters["open"] -= 1
                self.waiters["last"] = time.time()

    def answering(self) -> bool:
        """Whether a server answers at the address file's address: the file stays when the server is killed."""
        if not self.address.exists():
            return False
        try:
            with urllib.request.urlopen(f"{self.address.read_text().strip()}listening", timeout=2):
                return True
        except OSError:
            return False

    # ---------- The agent's side: wait, reply, status, pending ----------

    def wait(self, timeout: float) -> int:
        """Print the user's actions the agent has not seen yet, waiting for the served page to receive one."""
        if not self.address.exists():
            sys.exit(f"error: no page is served from {self.folder}. Start it with `{self.start}` first.")
        seen = int(self.seen.read_text() or 0) if self.seen.exists() else 0
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f"{self.address.read_text().strip()}wait?after={seen}", timeout=30) as r:
                    total = int(r.read())
            except OSError:
                sys.exit("error: the page's server is not answering. Is it still running?")
            if total <= seen:
                continue
            lines = self.lines()[seen:total]
            new = [line for line, event in zip(lines, self.events()[seen:total], strict=True) if from_user(event)]
            self.seen.write_text(str(total), encoding="utf-8")
            seen = total
            if new:
                print("\n".join(new), flush=True)
                return 0
        print("No new action before the timeout.", flush=True)
        return 2

    def write(self, *events: dict) -> list:
        """Append the agent's own events; one that fails its schema ends the command with the validator's message."""
        try:
            return self.append(*events)
        except EventError as error:
            sys.exit(f"error: {error}")

    def reply(self, text: str, to: str | None) -> None:
        """Show the agent's reply in the page's conversation, under the item it answers. It works without a server, so
        a resumed run can answer what the user wrote while no agent was running."""
        # Each reply has an id, so the user can answer any message, the agent's own included.
        self.write({"type": "reply", "by": self.agent, "id": "r-" + str(time.time_ns()), "text": text[:5000], "to": to})
        print("Reply shown in the page." if self.answering() else "Reply saved; the page shows it when served.")

    def set_status(self, state: str, ids: list, text: str | None = None) -> None:
        """Mark the user's items as seen, asked, working or done. Accepted records an acceptance the user gave in
        words, the same as the page's Accept button, as an `accepted` event with those words in TEXT."""
        if state == "accepted" and not (text or "").strip():
            sys.exit("error: accepted needs the user's words that accept it: pass them with --text.")
        events = self.events()
        owned = {
            e.get("id") for e in events if e.get("type") in self.items and not (e.get("type") == "note" and e.get("to"))
        }
        # An answer under one of the user's items is part of it; an answer to the agent's own message is an item.
        answers = {e.get("id"): e.get("to") for e in events if e.get("type") == "note" and e.get("to") in owned}
        misplaced = [i for i in ids if i in answers]
        if misplaced:  # an answer is part of the item it answers, which carries the state
            sys.exit(
                "error: "
                + ", ".join(f"{i} answers {answers[i]}" for i in misplaced)
                + ". Mark the item it answers instead."
            )
        known = {e.get("id") for e in events if e.get("type") in self.items}
        unknown = [i for i in ids if i not in known]
        if unknown:
            sys.exit(f"error: no comment or message with id {', '.join(unknown)}. Run `pending` to see the ids.")
        self.write(
            *(
                {"type": "accepted", "by": self.agent, "to": i, "text": text}
                if state == "accepted"
                else {"type": "status", "by": self.agent, "to": i, "status": state}
                for i in ids
            ),
        )
        print(f"Marked {state}: {terminal_text(', '.join(ids))}")

    def pending(self) -> None:
        """Print each item neither done nor accepted, in its latest form, with the answers and replies under it, so
        work can resume after an interruption. Done waits for the user; an item edited after it was finished, or a
        follow-up from the user under it, is work again."""
        items, order, state, reasons, thread, closes = {}, [], {}, {}, {}, {}
        for e in self.events():
            a, i, to = e.get("type"), e.get("id"), e.get("to")
            if a == "closed":  # a worker's message: the user can reply to it, and the reply goes to the agent
                closes[i] = e
            elif a == "note" and to and to not in items:  # an answer to the agent's own message is a new item
                order.append(i)
                items[i] = e
                if to in closes:  # the worker cannot read the page: say which question the user replied about
                    c = closes[to]
                    items[i] = {**e, "about": f"{c.get('by')} closed {c.get('question')} as {c.get('status')}"}
            elif a == "note" and to:  # the user's answer belongs to the item it answers
                thread.setdefault(to, []).append({"from": "user", "at": e.get("at"), "text": e.get("text")})
                if state.get(to) == "asked":  # the answer ends the wait: the item is the agent's again
                    state[to] = "answered by the user"
                elif state.get(to) in ("done", "accepted"):  # a follow-up under a finished item is work again
                    state[to] = "follow-up from the user"
            elif a == "reply" and to:
                thread.setdefault(to, []).append({"from": self.agent, "at": e.get("at"), "text": e.get("text")})
            elif a in self.items and i:
                if i in items and state.get(i) in ("done", "accepted"):
                    state[i] = "edited"
                if i not in items:
                    order.append(i)
                items[i] = e
            elif a == "delete" and to in items:
                items[to] = None
            elif a == "status":
                state[to] = e.get("status")
            elif a in ("accept", "accepted"):
                state[to] = "accepted"
            elif a == "reopen":
                state[to], reasons[to] = "reopened", e.get("text")
        open_items = [items[i] for i in order if items.get(i) and state.get(i) not in ("done", "accepted")]
        for e in open_items:
            extra = {}
            if state.get(e["id"]) == "reopened" and reasons.get(e["id"]):
                extra["reopened_because"] = reasons[e["id"]]
            if thread.get(e["id"]):
                extra["thread"] = thread[e["id"]]
            print(terminal_json({**e, "status": state.get(e["id"], "new"), **extra}))
        print(f"{len(open_items)} not done.")


def answers_any_failure(handle):
    """A request handler that never raises: whatever the request makes it raise, the answer is one line, with the status
    500 (for a JSON-RPC request, the error object -32603), never a dropped request or a traceback in the server's log."""

    @functools.wraps(handle)
    def run(self):
        self.answer_started = False
        try:
            return handle(self)
        except Exception as error:
            if self.answer_started:  # the status line and headers are out: a second answer would corrupt the stream
                self.close_connection = True
                return None
            self._headers_buffer = []
            what = "nested too deeply" if isinstance(error, RecursionError) else f"failed: {type(error).__name__}"
            if self.path == "/rpc":
                answer = '{"jsonrpc": "2.0", "id": null, "error": {"code": -32603, "message": "internal error: %s"}}'
                body, kind, code = (answer % what).encode(), "application/json", 200
            else:
                body, kind, code = f"{what}\n".encode(), "text/plain; charset=utf-8", 500
            status = "200 OK" if code == 200 else "500 Internal Server Error"
            head = f"HTTP/1.0 {status}\r\nContent-Type: {kind}\r\nContent-Length: {len(body)}\r\n\r\n"
            # written whole, without send_response or self.send, which may be what failed; if the connection is gone
            # there is nothing more to answer
            with contextlib.suppress(Exception):
                self.wfile.write(head.encode("ascii") + body)

    return run


class Handler(http.server.BaseHTTPRequestHandler):
    """The requests every page that talks to the agent makes. A script subclasses it, sets `conversation` and
    `methods`, the events its page may send, and answers its own paths in do_GET after `conversation_get`. The
    do_GET and do_POST a subclass defines answer any failure with a 500, as the ones here do."""

    conversation: Conversation
    methods: tuple = ()

    answer_started = False

    def flush_headers(self) -> None:
        super().flush_headers()
        self.answer_started = True

    def guarded(self, step) -> None:
        """Run a step of the request's life that is outside do_GET and do_POST (setup, handle, finish). A client that
        has gone, a reset or a closed socket, is not worth a word; anything else is one line, never a traceback."""
        try:
            step()
        except OSError:
            pass
        except Exception as error:
            with contextlib.suppress(Exception):
                print(f"page server: a request failed: {type(error).__name__}", file=sys.stderr)

    def setup(self) -> None:
        self.guarded(super().setup)

    def handle(self) -> None:
        self.guarded(super().handle)

    def finish(self) -> None:
        self.guarded(super().finish)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for name in ("do_GET", "do_POST", "do_HEAD", "do_PUT", "do_DELETE"):
            if name in vars(cls):
                setattr(cls, name, answers_any_failure(vars(cls)[name]))

    def local(self) -> bool:
        # Only answer requests addressed to this machine, so a web page cannot reach it via DNS rebinding.
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

    def after(self) -> int:
        value = self.path.split("=", 1)[1]
        return int(value) if value.isdigit() else 0

    def conversation_get(self) -> bool:
        """Answer the conversation's own GET paths; False when the path is the page's. A request addressed to another
        host is refused here too, so a page cannot forget the check."""
        c = self.conversation
        if not self.local():
            self.send_error(403)
        elif self.path == "/listening":
            self.send_json(c.listening())
        elif self.path.startswith("/events?after="):
            # Long poll for the page: every event after the first `after`, the agent's included.
            after = self.after()
            total = c.wait_for_more(after, 20)
            self.send_json({"total": total, "events": c.events()[after:total]})
        elif self.path.startswith("/wait?after="):
            self.send(200, str(c.waited(self.after())).encode(), "text/plain")
        else:
            return False
        return True

    @answers_any_failure
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
            or msg.get("method") not in self.methods
            or not isinstance(msg.get("params"), dict)
        ):
            return self.send_json(rpc_error(rid, -32601, "Unknown method"))
        # The page sets only its own fields: the type is the method, the time is the server's, and "by" is the user's,
        # so a page cannot write an event as the agent's or hide one from `wait`.
        params = clean(msg["params"])
        if "by" in params:
            return self.send_json(rpc_error(rid, -32602, "by: not allowed in what a page sends; the server sets it"))
        params = {k: v for k, v in params.items() if k not in ("type", "at")}
        with self.conversation.lock:
            try:
                (line,) = self.conversation.append({"type": msg["method"], "by": "user", **params})
            except EventError as error:
                return self.send_json(rpc_error(rid, -32602, str(error)))
            print(line, flush=True)
        self.send_json({"jsonrpc": "2.0", "id": rid, "result": "saved"})

    def log_message(self, *args):
        pass
