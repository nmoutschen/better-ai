"""One page agent session, driven by durable delivery and authenticated page actions."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import queue
import threading
import time
import uuid
from collections import Counter, deque
from concurrent.futures import Future
from dataclasses import dataclass, field

from .. import paths, resources
from .driver_state import (
    ACTIVE_DELIVERY,
    LOG,
    delivered_field,
    delivered_position,
    encode,
    iso,
    load_state,
    log_records,
    recent_turn,
    save_state,
    store_log,
    with_defaults,
)
from .transport import ProcessTransport as ProcessTransport
from .transport import end_orphan, process_started

POLL = 0.05
START_TIMEOUT = 30
RESUME_TIMEOUT = 10
STOP_TIMEOUT = 3
STALL_TIMEOUT = 600
PROTOCOL_TIMEOUT = 60
IDLE_LIMIT = 30 * 60
ALIVE_LIMIT = 10
MAX_APPROVAL_TEXT = 131072
OPTIONS = ["allow_once", "allow_session", "deny"]

ACTIONS = {
    "no-harness": "Start a harness this machine can drive, then serve again.",
    "login": "Log in to the harness, then press Start.",
    "not-installed": "Install the harness, then serve again.",
    "version": "Update the harness, then serve again.",
    "limit": "After the harness limit resets, press Start.",
    "crashed": "Press Start to resume.",
    "not-handling": "Check the page agent's last reply and log, then press Start.",
    "driver": "Serve the page again.",
    "protocol": "Update better-ai, or use a harness version it was tested with.",
    "unsafe-mode": "Change the harness's approval mode, then serve again.",
    "no-approvals": "This harness can't be driven safely. The chat agent listens instead.",
}

# The sentence the page shows for a state or failed kind: fixed words with at most one inserted value.
NOTICES = {
    "login": "All agents are stopped because {} isn't logged in. Log in from a terminal, then press Start.",
    "limit": "All agents are stopped because the harness hit its limit: {}. Press Start after it resets.",
    "crashed": "All agents are stopped because the harness failed: {}. Press Start to resume.",
    "crashed-again": "The same error came back: {}. Fix it in a terminal, then press Start.",
    "not-handling": "All agents are stopped because they did not handle {}. Press Start to retry, or reword the comment.",
    "driver": "The page's agents stopped because of an error: {}. Ask the agent in your chat to serve this page again. Log: {}.",
    "protocol": "All agents are stopped because the harness protocol is unknown: {}. Update better-ai, or use a version it was tested with.",
    "stopped": "All agents are stopped. Press Start to have them read your messages.",
    "stopping": "The agents are stopping.",
    "stalled": "The agents have shown no output for 10 minutes. Press Stop to end them, or keep waiting.",
    "idle": "This page is closed after 30 minutes with no activity. Ask the agent in your chat to reopen it.",
    "closed": "This page has closed: {}.",
}

# What an approval asks for, in the words after "<who> wants".
WANTS = {
    "Read": "to read a file",
    "Write": "to write a file",
    "Edit": "to edit a file",
    "MultiEdit": "to edit a file",
    "Bash": "to run a command",
    "WebFetch": "to fetch a web page",
    "WebSearch": "to search the web",
}


class StartError(Exception):
    def __init__(self, kind: str, message: str = ""):
        super().__init__(message or kind)
        self.kind = kind


@dataclass
class Turn:
    record: dict
    position: int | None = None
    triggers: tuple[str, ...] = ()
    actions: list[dict] = field(default_factory=list)
    changed: bool = False
    final_message: str = ""
    denied: list[dict] = field(default_factory=list)

    @property
    def items(self) -> frozenset[str]:
        return frozenset(self.record["items"])


@dataclass
class Approval:
    id: str
    event: object
    peer: object
    who: str
    tool: str
    arguments: str
    since: float
    record: dict
    key: tuple
    requester: str | None
    summary: str
    options: list


def display(value) -> str:
    return value if isinstance(value, str) else json.dumps(value, sort_keys=True, indent=2, allow_nan=False)


class Driver:
    """The loop owns the transport and durable state; HTTP handlers only post commands or read a snapshot."""

    def __init__(
        self,
        conversation,
        harness: str,
        launch,
        *,
        skill_path,
        command: str,
        cwd,
        step: str = "",
        handoff: str = "",
        triggers=lambda: (),
        workers=lambda: (),
        auto_approve=None,
        version: str = "",
        tested: str = "",
        build: str = "",
        clock=time.monotonic,
        valid_session,
    ):
        self.conversation = conversation
        self.unit = conversation.unit
        self.harness = harness
        self.launch = launch
        self.cwd = str(cwd)
        self.step = step
        self.skill_path, self.command = str(skill_path), command
        self.triggers, self.workers, self.auto_approve, self.clock = triggers, workers, auto_approve, clock
        self.version, self.tested, self.build = version, tested, build
        self.valid_session = valid_session
        saved = load_state(self.unit) or with_defaults({})
        self._saved = saved
        # A session is resumed only if this driver opened it for this unit, in the same harness (S48, S131).
        opened = saved["opened"]
        resumable = (
            saved["harness"] == harness
            and isinstance(opened, (int, float))
            and opened > 0
            and isinstance(saved["session"], str)
            and valid_session(saved["session"])
        )
        self.session = saved["session"] if resumable else None
        self._opened = opened if resumable else 0
        self.tag = str(uuid.uuid4())
        self._server_started = process_started(os.getpid())

        events = conversation.events()
        self._delivered = delivered_position(saved["delivered"], events)
        self._delivered_field = delivered_field(self._delivered, events)
        self._fired = self._strings(saved["fired"])
        self._note = handoff or saved["note"] or ""
        self._handoff_delivered = False if handoff else bool(saved["handoff_delivered"])
        self._ended = dict(saved["ended"])
        if self._ended.get("build") != build:
            # A changed better.pyz is a new chance: the count of repeated driver errors starts again.
            self._ended["repeats"] = 0
        self._turn_state = None
        self._records = log_records(self.unit)
        for record in self._records:
            if record.get("type") == "approval" and "answer" not in record:
                record.update(answer="expired", reason="driver restarted")
        self._carry = frozenset()
        self._recover = frozenset()
        self._recover_turn = 0
        self._recover_kind = ""
        self._number = 0
        # A turn still set in .driver ended without the driver seeing it: it crashed (S72).
        crashed = saved["turn"] if isinstance(saved["turn"], dict) else None
        turns = [record for record in self._records if record.get("type") == "turn"]
        if crashed:
            number = crashed.get("number")
            self._number = number if type(number) is int else 0
            record = next((r for r in reversed(turns) if r.get("number") == self._number), None)
            # With no record of that turn, the delivery file names what it carried; no other turn's record will do.
            items = self._strings(record.get("items")) if record else self._delivery_items()
            self._recover, self._recover_turn, self._recover_kind = items, self._number, "crashed"
            if record is not None and "end" not in record:
                record.update(end=time.time(), outcome="crashed")
        elif turns:
            last = turns[-1]
            number = last.get("number", 0)
            self._number = number if type(number) is int else 0
            items = self._strings(last.get("items"))
            outcome = last.get("outcome") or "crashed"
            if outcome == "completed":
                self._carry = items
            else:
                self._recover, self._recover_turn, self._recover_kind = items, self._number, outcome
            if "end" not in last:
                last.update(end=time.time(), outcome=outcome)
        self._retry = False
        self._admitted_items = set()
        self._admitted_edits = set()
        self._admitted_events = []
        self._scan_after = self._delivered

        # Startup replays persisted work. During a live session only /rpc can wake for user actions.
        self._wake = True
        self._last_prompt_items = frozenset()
        self._repeats = 0
        self._crash_retries = 0
        self._turn = None
        self._peer = None
        self._closing = threading.Event()
        self._started = threading.Event()
        self._start_error = None
        self._deadline = 0.0
        self._commands = queue.Queue()
        self._answer_lock = threading.Lock()
        self._log_lock = threading.RLock()
        self._thread = threading.Thread(target=self._run, name="page-agent", daemon=True)
        self._state = "starting"
        self._since = time.time()
        self._details = {}
        self._last_output = self.clock()
        self._last_poll = self.clock()
        self._first_prompt = True
        self._open_approvals = {}
        self._grants = set()
        self._blocked = deque(maxlen=20)
        self._auto_used = False
        self._unknown_since = None
        self._unit_checked = 0.0
        self._closed = None
        self._close_reason = "server stopped"
        self._driver_failed = False
        self._failed_error = None
        self._workers_broken = False
        self._same_end = False
        # Open until this serve reaches driver: on; a driver error after that starts a new count (D11).
        self._streak_open = True
        self._last_stderr = ""
        self._published = {}
        self._publish()

    def _delivery_items(self) -> frozenset[str]:
        try:
            record = json.loads(paths.read_bytes(self.unit, ACTIVE_DELIVERY))
        except (OSError, ValueError, paths.Refused):
            return frozenset()
        return self._strings(record.get("item_ids")) if isinstance(record, dict) else frozenset()

    @staticmethod
    def _strings(values) -> frozenset[str]:
        return (
            frozenset(value for value in values if isinstance(value, str)) if isinstance(values, list) else frozenset()
        )

    def start(self, timeout=START_TIMEOUT) -> str:
        self._deadline = time.monotonic() + timeout
        if end_orphan(self._saved["child_pid"], self._saved["child_argv"]):
            self._record_end("orphan ended at start", "orphan")
        self._thread.start()
        if not self._started.wait(timeout):
            self._closing.set()
            raise StartError("crashed", "harness startup timed out")
        if self._start_error is not None:
            raise self._start_error
        return self.session

    def enqueue(self, event: dict) -> None:
        self._commands.put(("event", event))

    def request_start(self) -> None:
        self._commands.put(("start", None))

    def request_stop(self) -> None:
        self._commands.put(("stop", None))

    def close(self, kind: str = "stopped", reason: str = "server stopped") -> None:
        """A planned end: publish closed with the reason at once, cancel as Stop does, and end the process group."""
        self._closed = (kind, reason, time.time())
        self._close_reason = reason
        self._force("closed", {"kind": kind, "message": reason}, self._closed[2])
        self._closing.set()
        if self._thread.ident is not None:
            self._thread.join(timeout=4.75)

    def busy(self) -> bool:
        """Something still needs the driver: a turn, an open approval, a worker, or work waiting."""
        published = self._published
        return bool(
            published["state"] in ("starting", "working", "stalled", "stopping")
            or published["approvals"]
            or published["waiting"]
            or self._worker_list()
            or self._workers_broken
            or not self._commands.empty()
        )

    def can_linger(self) -> bool:
        return not self.busy()

    def idle_expired(self, limit: float = IDLE_LIMIT) -> bool:
        """No tab has polled /agent for `limit` seconds and nothing needs the driver (S104)."""
        return not self.busy() and self.clock() - self._last_poll >= limit

    def check_alive(self, limit: float = ALIVE_LIMIT) -> bool:
        """For the server's watchdog: False once the loop is dead or its liveness mark is older than `limit`."""
        if self._driver_failed or self._failed_error is not None:
            return False
        if self._closing.is_set() or not self._started.is_set():
            return True
        if self.clock() - self._published["at"] > limit:
            self.fail_driver("the driver loop stopped responding")
            return False
        return True

    def fail_driver(self, error: str) -> None:
        """Publish failed, kind driver, from outside the loop, and end the harness and its approvals (S62)."""
        if self._driver_failed:
            return
        self._driver_failed = True
        self._failed_error = error
        self._force("failed", {"kind": "driver", "message": error, "log": str(self.unit.target(LOG))})
        self._record_end(error, "driver")
        self._closing.set()
        try:
            self._close_peer(error)
        except Exception as problem:
            self.log("error", kind="driver", message=f"the harness's process group did not end: {problem}")

    @property
    def error(self) -> str | None:
        return self._failed_error

    def snapshot(self) -> dict:
        published = self._published
        return {
            "state": published["state"],
            "since": published["since"],
            "age": max(0, self.clock() - published["at"]),
            "waiting": published["waiting"],
            **published["details"],
        }

    def agent(self) -> dict:
        """The body of /agent (decision D1). Each call counts as a tab polling."""
        self._last_poll = self.clock()
        published = self._published
        state, details = published["state"], published["details"]
        return {
            "state": state,
            "since": iso(published["since"]),
            "kind": details.get("kind") if state in ("failed", "closed") else None,
            "text": self._text(state, details),
            "mark_age": max(0, self.clock() - published["at"]),
            "approvals": published["approvals"],
            "workers": self._worker_list(),
            "blocked": published["blocked"],
            "auto_approved_once": published["auto"],
        }

    def _worker_list(self) -> list:
        try:
            return [dict(worker) for worker in self.workers()]
        except Exception as error:
            # A callback that fails must not look like no workers: the page stays up, and the failure is logged once.
            if not self._workers_broken:
                self._workers_broken = True
                self.log("error", kind="workers", message=f"the workers callback failed: {error}")
            return []

    def _text(self, state: str, details: dict) -> str | None:
        """The finished notice for stopped, failed and closed; null for every other state (decision D7)."""
        message = str(details.get("message", ""))[:500]
        if state == "closed":
            return NOTICES["idle"] if details.get("kind") == "idle" else NOTICES["closed"].format(message)
        if state in ("stopped", "stopping", "stalled"):
            return NOTICES[state]
        if state != "failed":
            return None
        kind = details.get("kind", "crashed")
        if kind == "crashed" and details.get("again"):
            kind = "crashed-again"
        if kind == "login":
            return NOTICES[kind].format(self.harness)
        if kind == "not-handling":
            return NOTICES[kind].format(", ".join(details.get("items", ())))
        if kind == "driver":
            return NOTICES[kind].format(message, details.get("log", self.unit.target(LOG)))
        if kind in NOTICES:
            return NOTICES[kind].format(message)
        return ACTIONS.get(kind, message)

    def _force(self, state: str, details: dict, since: float | None = None) -> None:
        """Publish a state from outside the loop thread and keep the loop from replacing it."""
        self._published = {
            **self._published,
            "state": state,
            "since": since or time.time(),
            "details": details,
            "approvals": [],
            "at": self.clock(),
        }

    def _publish(self) -> None:
        if self._driver_failed or self._closed:
            return
        state, since = self._state, self._since
        approvals = [
            {
                "id": a.id,
                "who": a.who,
                "tool": a.tool,
                "arguments": a.arguments,
                "summary": a.summary,
                "since": iso(a.since),
                "options": list(a.options),
            }
            for a in self._open_approvals.values()
        ]
        if approvals and state in ("idle", "working", "stalled"):
            state, since = "waiting", min(a.since for a in self._open_approvals.values())
        self._published = {
            "state": state,
            "since": since,
            "at": self.clock(),
            "waiting": self._wake or self._retry,
            "details": self._details,
            "approvals": approvals,
            "blocked": list(self._blocked),
            "auto": self._auto_used,
        }

    def log(self, record_type: str, **fields) -> None:
        """Add one line to .driver.log; the server calls this for pairing events, refused calls and its errors."""
        with self._log_lock:
            self._records.append({"type": record_type, "at": time.time(), "session": self.session, **fields})
            self._flush_log()

    _log = log

    def _flush_log(self) -> None:
        with self._log_lock:
            self._attach_verbs()
            self._records = store_log(self.unit, self._records)

    def _attach_verbs(self) -> None:
        """Move verb lines the verbs appended to the log onto the records of their turns (D11)."""
        turns = {r.get("number"): r for r in self._records if r.get("type") == "turn"}
        for line in log_records(self.unit):
            if line.get("type") != "verb" or not turns:
                continue
            turn = turns.get(line.get("turn")) or turns[max(n for n in turns if type(n) is int)]
            turn.setdefault("verbs", []).append({k: line.get(k) for k in ("verb", "exit", "at")})

    def _status(self, state: str, **details) -> None:
        if self._state != state or self._details != details:
            self._state, self._since, self._details = state, time.time(), details
            self._log("state", state=state, **details)
        self._publish()

    def _checkpoint(self) -> None:
        peer = self._peer
        save_state(
            self.unit,
            {
                "harness": self.harness,
                "session": self.session,
                "server_pid": os.getpid(),
                "server_started": self._server_started,
                "child_pid": getattr(peer, "pid", None),
                "child_argv": list(getattr(peer, "argv", [])) if peer else [],
                "opened": self._opened,
                "delivered": self._delivered_field,
                "note": self._note,
                "fired": sorted(self._fired),
                "handoff_delivered": self._handoff_delivered,
                "turn": self._turn_state,
                "ended": self._ended,
            },
        )

    def _record_end(self, reason: str, kind: str = "stopped") -> None:
        """Note when the harness process ended and why (S98). repeats counts the same error of kind driver in a row."""
        reason = reason[:2000]
        previous = self._ended
        same = previous.get("reason") == reason and previous.get("kind") == kind
        repeats = previous.get("repeats", 0) + 1 if kind == "driver" and same and self._streak_open else 0
        self._ended = {"at": iso(time.time()), "reason": reason, "kind": kind, "build": self.build, "repeats": repeats}
        self._same_end = same
        # The record stays in memory when the write fails.
        with contextlib.suppress(OSError, ValueError, paths.Refused):
            self._checkpoint()

    def _open(self, deadline: float) -> None:
        resume = self.session
        resume_deadline = time.monotonic() + RESUME_TIMEOUT
        self._status("starting")
        self._launch(resume)
        while not self._closing.is_set() and time.monotonic() < deadline:
            if self._started.is_set():
                try:
                    command = self._commands.get_nowait()
                except queue.Empty:
                    pass
                else:
                    self._command(*command)
                    if self._state == "stopped":
                        return
                self._publish()
            if resume and time.monotonic() > resume_deadline:
                resume = self._open_fresh("the resume took more than 10 s")
            event = self._peer.poll(POLL)
            if event is None:
                continue
            if event.kind == "ready":
                if not self.valid_session(event.session_id):
                    raise StartError("crashed", "harness returned an invalid session ID")
                if self.session != event.session_id:
                    self._first_prompt = True
                    self._opened = time.time()
                self.session = event.session_id
                self._last_output = self.clock()
                self._checkpoint()
                self._status("idle")
                return
            if event.kind == "failed":
                if resume:
                    resume = self._open_fresh(event.text or event.outcome or "the resume failed")
                    continue
                raise StartError(event.outcome or "crashed", event.text)
            if event.kind == "approval":
                self._request_approval(event, deny_reason="the page is starting")
        raise StartError("crashed", "harness startup timed out")

    def _open_fresh(self, why: str) -> None:
        """A session that cannot be resumed is replaced by a new one from the records (S30, S111)."""
        self._log("error", kind="resume", message=why)
        self._close_peer("session could not be resumed")
        self.session = None
        self._launch(None)

    def _launch(self, resume: str | None) -> None:
        try:
            self._peer = self.launch(self.tag, resume)
            self._peer.open(self.cwd, resume)
        except FileNotFoundError as error:
            raise StartError("not-installed", str(error)) from None
        except OSError as error:
            raise StartError("crashed", str(error)) from None

    def _run(self) -> None:
        try:
            # The state is written before anything is served, so a working turn left by a crash is gone (S120).
            self._flush_log()
            self._checkpoint()
            self._log("version", harness=self.harness, version=self.version, tested=self.tested)
            self._open(self._deadline)
            # On serve startup the existing log is the recovery source. Once start returns,
            # new work must enter through enqueue, including while a turn is busy or failed.
            historical = self.conversation.delivery(self._delivered, carry_ids=self._carry, recover_ids=self._recover)
            self._admitted_items.update(item["id"] for item in historical.items)
            self._admitted_edits.update((item.get("type"), item["id"]) for item in historical.items)
            self._admitted_events.extend(historical.events)
            self._last_poll = self.clock()
            self._ended["repeats"] = 0
            self._streak_open = False
            self._started.set()
            while not self._closing.is_set():
                self._check_unit()
                self._commands_once()
                drained = self._events_once()
                if self._state not in ("stopping", "failed"):
                    available = self._available_triggers()
                    if available:
                        self._wake = True
                    if self._state == "idle" and (self._wake or self._retry) and drained:
                        self._deliver(available)
                self._publish()
            if not self._driver_failed:
                self._stop(self._close_reason)
        except StartError as error:
            self._start_error = error
            self._failed(error.kind, str(error))
        except Exception as error:
            self._start_error = StartError("driver", str(error))
            self._failed_error = str(error)
            # An error in the state/log writer must still leave a readable status in memory.
            try:
                self._failed("driver", str(error))
            except Exception:
                self._state, self._since = "failed", time.time()
                self._details = {"kind": "driver", "message": str(error), "log": str(self.unit.target(LOG))}
                self._record_end(str(error), "driver")
                self._publish()
        finally:
            try:
                self._close_peer("driver closed")
            finally:
                # Synchronize the final drain with handlers enqueueing answers off-thread.
                with self._answer_lock:
                    self._closing.set()
                while True:
                    try:
                        kind, value = self._commands.get_nowait()
                    except queue.Empty:
                        break
                    if kind == "answer":
                        receipt = value[-1]
                        if receipt.set_running_or_notify_cancel():
                            receipt.set_result(False)
                self._started.set()

    def _check_unit(self) -> None:
        now = time.monotonic()
        if now - self._unit_checked >= 1:
            self._unit_checked = now
            if not os.path.isdir(self.unit.path):
                raise FileNotFoundError("the unit folder is gone")

    def _available_triggers(self) -> tuple[dict, ...]:
        return tuple(record for record in self.triggers() if record["id"] not in self._fired)

    def _commands_once(self) -> None:
        if self._peer is None:
            try:
                cmd = self._commands.get(timeout=POLL)
            except queue.Empty:
                return
            self._command(*cmd)
        for _ in range(100):
            if self._closing.is_set():
                return
            try:
                cmd = self._commands.get_nowait()
            except queue.Empty:
                break
            self._command(*cmd)

    def _command(self, kind, value) -> None:
        if kind == "event":
            self._wake = True
            targets = {value.get("id"), value.get("to")}
            self._admitted_items.update(targets)
            self._admitted_edits.add((value.get("type"), value.get("id")))
            self._admitted_events.append(value)
            if targets & self._last_prompt_items:
                self._repeats = 0
                if self._turn:
                    self._turn.changed = True
            if self._state == "failed" and self._details.get("kind") == "crashed" and self._crash_retries < 3:
                self._crash_retries += 1
                self._restart()
        elif kind == "start" and self._state in ("failed", "stopped"):
            self._crash_retries = 0
            self._repeats = 0
            self._restart()
        elif kind == "stop":
            self._stop("stopped by the user")
        elif kind == "answer":
            self._answer(*value)

    def _restart(self) -> None:
        self._wake = True
        try:
            self._open(time.monotonic() + START_TIMEOUT)
        except StartError as error:
            self._failed(error.kind, str(error))

    def _events_once(self) -> bool:
        if self._peer is not None:
            timeout = 0 if self._wake and self._state == "idle" else POLL
            for _ in range(100):
                event = self._peer.poll(timeout)
                if event is None:
                    break
                self._receive(event)
                if self._peer is None:
                    break
                timeout = 0
            else:
                # Process pending page commands before draining the next burst of harness output.
                return False
        if self._state == "working" and self.clock() - self._last_output >= STALL_TIMEOUT and not self._open_approvals:
            self._status("stalled")
        if (
            self._state in ("working", "stalled")
            and self._unknown_since is not None
            and self.clock() - self._unknown_since >= PROTOCOL_TIMEOUT
        ):
            self._failed("protocol", f"{self.harness} {self.version or 'unknown version'}; tested {self.tested}")
        return True

    def _receive(self, event) -> None:
        self._last_output = self.clock()
        if self._state == "stalled":
            self._status("working")
        # An unknown message after the last known one starts a clock; any known message ends it (S112).
        if event.kind == "unknown":
            if self._unknown_since is None:
                self._unknown_since = self.clock()
        elif event.kind != "output":
            self._unknown_since = None
        if event.kind == "failed":
            self._failed(event.outcome or "crashed", event.text)
        elif event.kind == "turn_started":
            if self._turn is None:
                self._begin(None, frozenset(), ())
            self._turn.record["turn_id"] = event.turn_id
            self._flush_log()
        elif event.kind == "text" and self._turn:
            self._turn.final_message = (self._turn.final_message + event.text)[-500:]
        elif event.kind == "turn_ended" and self._turn:
            if event.text:
                self._turn.final_message = event.text[-500:]
            if event.outcome in ("normal", "completed"):
                # Only the approvals of the agent whose turn ended close; a worker's stay open (S44).
                self._close_approvals("the turn ended", "expired", only=lambda a: a.requester is None)
                self._end("completed")
                self._crash_retries = 0
                self._status("idle")
            else:
                self._failed(event.outcome or "crashed", event.text)
        elif event.kind == "approval":
            self._request_approval(event)
        elif event.kind == "approval_closed":
            for approval in list(self._open_approvals.values()):
                if approval.event.request_id == event.request_id:
                    self._finish_approval(approval, "expired", event.text or event.outcome or "expired")
        elif event.kind == "blocked":
            entry = {
                "tool": event.tool,
                "arguments": display(event.arguments),
                "reason": event.text,
                "at": iso(time.time()),
            }
            self._blocked.append(entry)
            self._log("blocked", **entry)

    def _deliver(self, available: tuple[dict, ...]) -> None:
        # An RPC append can be visible to a previous turn before its enqueue reaches
        # this thread. Select from the session's original cursor, then admit exact
        # events and item IDs so an intervening completion cannot skip that RPC.
        parents = {}
        batch = self.conversation.delivery(
            self._scan_after,
            carry_ids=self._carry,
            recover_ids=self._recover,
            admitted_edits=self._admitted_edits,
            thread_parents=parents,
        )
        parent_ids = {parents[target] for target in self._admitted_items if target in parents}
        if parent_ids & self._last_prompt_items:
            self._repeats = 0
        admitted = self._admitted_items | self._recover | parent_ids
        batch.items[:] = [
            item
            for item in batch.items
            if item["id"] in admitted or (item["id"] in self._carry and item["status"] in ("new", "seen"))
        ]
        events = Counter(encode(event) for event in self._admitted_events)
        actions = []
        for event in batch.events:
            key = encode(event)
            if events[key]:
                actions.append(event)
                events[key] -= 1
        batch.events[:] = actions
        self._wake = self._retry = False
        items = frozenset(item["id"] for item in batch.items)
        if items and items == self._last_prompt_items and self._repeats >= 3:
            last = recent_turn(self._records, self.session)
            self._failed(
                "not-handling",
                items=sorted(items),
                final_message=last.get("final_message", ""),
                denied=last.get("denied", []),
                log=str(self.unit.target(LOG)),
            )
            return
        self._admitted_items.clear()
        self._admitted_edits.clear()
        self._admitted_events.clear()
        if not (items or actions or available):
            return
        if items != self._last_prompt_items:
            self._repeats = 0
        self._last_prompt_items = items
        paths.write_atomic(
            self.unit,
            ACTIVE_DELIVERY,
            encode(
                {
                    "session": self.tag,
                    "after": self._delivered,
                    "carry_ids": sorted(self._carry),
                    "recover_ids": sorted(self._recover),
                    "item_ids": sorted(items),
                    "position": batch.position,
                    "actions": actions,
                }
            ),
        )
        self._begin(batch.position, items, tuple(r["id"] for r in available))
        self._turn.actions = actions
        prompt = self._prompt(batch, available)
        try:
            self._peer.prompt(prompt, self._turn_state["prompt_uuid"])
        except OSError as error:
            self._failed("crashed", str(error))
        else:
            self._first_prompt = False
            if self._note and not self._handoff_delivered:
                self._handoff_delivered = True
                self._checkpoint()

    def _prompt(self, batch, available: tuple[dict, ...]) -> str:
        parts = [self._note] if self._note and not self._handoff_delivered else []
        if self._first_prompt:
            parts.extend(
                [
                    resources.read_text("page/page-agent.md"),
                    f"Skill: {self.skill_path}\nUnit: {self.unit.label}\nCurrent step: {self.step}",
                    f"Verb command: {self.command}\nWorking directory: {self.cwd}",
                ]
            )
        if self._recover:
            notes = [
                f"{item['id']}: sent before in turn {self._recover_turn}, which ended: {self._recover_kind}"
                for item in batch.items
                if item["id"] in self._recover
            ]
            if notes:
                parts.extend(notes)
                if self._recover_kind == "stopped by the user":
                    parts.append(
                        "do not resume stopped work unless the user asks; "
                        "check the records and the working tree before redoing a change"
                    )
        if len(batch.items) > 20:
            parts.append(f"For the full copy of the items, run pending {self.unit.label}.")
        parts.append(
            encode({"items": batch.prompt_items(), "user_actions": batch.events, "triggers": available}).decode()
        )
        return "\n\n".join(part for part in parts if part)

    def _begin(self, position: int | None, items: frozenset[str], triggers: tuple[str, ...]) -> None:
        self._number += 1
        record = {
            "type": "turn",
            "number": self._number,
            "session": self.session,
            "start": time.time(),
            "items": sorted(items),
        }
        self._turn = Turn(record, position, triggers)
        # The turn stays in .driver until it ends normally; a restart that finds it set treats it as crashed (S153).
        self._turn_state = {"number": self._number, "prompt_uuid": str(uuid.uuid4()), "sent_at": time.time()}
        self._checkpoint()
        self._records.append(record)
        self._flush_log()
        self._last_output = self.clock()
        self._unknown_since = None
        self._status("working")

    def _end(self, outcome: str) -> None:
        turn, self._turn = self._turn, None
        if turn is None:
            return
        if outcome == "completed" and turn.position is not None:
            self._delivered = turn.position
            self._delivered_field = delivered_field(turn.position, self.conversation.events())
            self._fired |= frozenset(turn.triggers)
            self._carry = turn.items
            self._recover = frozenset()
            self._retry = bool(turn.items)
            if not turn.changed:
                self._repeats += 1
        elif outcome != "completed":
            self._admitted_events.extend(turn.actions)
            self._recover = turn.items
            self._carry = frozenset()
            self._recover_turn, self._recover_kind = turn.record["number"], outcome
        self._turn_state = None
        peer_stderr = self._peer.stderr if self._peer else ""
        turn.record.update(
            end=time.time(),
            outcome=outcome,
            denied=turn.denied,
            final_message=turn.final_message[:500],
            stderr=peer_stderr[-2000:],
        )
        if not any(record is turn.record for record in self._records):
            self._records.append(turn.record)
        # The log says how the turn ended before the state forgets that it ran.
        self._flush_log()
        self._checkpoint()
        with contextlib.suppress(FileNotFoundError):
            self.unit.target(ACTIVE_DELIVERY).unlink()

    def _failed(self, kind: str, message: str = "", **details) -> None:
        kind = kind if kind in ACTIONS else "crashed"
        self._end(kind)
        self._record_end(message or kind, kind)
        self._close_peer(message or kind)
        self._log("error", kind=kind, message=message, stderr=self._last_stderr[-2000:])
        if kind == "driver":
            details.setdefault("log", str(self.unit.target(LOG)))
        self._status("failed", kind=kind, message=message, again=self._same_end, **details)

    def _stop(self, reason: str) -> None:
        """Show stopping, cancel, wait up to 3 s for the turn to end, then end the process group in every case."""
        self._status("stopping")
        self._close_approvals(reason, "denied")
        if self._peer is not None:
            with contextlib.suppress(OSError):
                self._peer.cancel()
                deadline = time.monotonic() + STOP_TIMEOUT
                while self._turn is not None and time.monotonic() < deadline:
                    self._publish()
                    event = self._peer.poll(POLL)
                    if event is None:
                        continue
                    if event.kind in ("turn_ended", "failed"):
                        break
                    if event.kind == "approval":
                        self._request_approval(event, deny_reason=reason)
        self._end(reason)
        if self._peer is not None:
            self._record_end(reason, "stopped" if reason == "stopped by the user" else "server")
        self._close_peer(reason)
        self._status("stopped")

    # Approvals: the driver keeps every open request in memory and relays the user's answer (decision D8).

    def _request_approval(self, event, deny_reason=None) -> None:
        try:
            arguments = display(event.arguments)
            tool = event.tool
            if not isinstance(tool, str) or not tool or len(tool) + len(arguments) > MAX_APPROVAL_TEXT:
                raise ValueError
        except (ValueError, TypeError, RecursionError):
            arguments, tool = "", str(getattr(event, "tool", ""))[:200]
            deny_reason = "Cannot display the full tool request"
        if "allow_once" not in event.options:
            deny_reason = deny_reason or "Request has no allow-once option"
        record = {
            "type": "approval",
            "at": time.time(),
            "session": self.session,
            "request": event.request_id,
            "tool": tool,
            "arguments_sha256": hashlib.sha256(encode({"arguments": event.arguments}).strip()).hexdigest(),
            "where": "turn" if self._turn else "between-turns",
        }
        approval = Approval(
            id=uuid.uuid4().hex[:16],
            event=event,
            peer=self._peer,
            who=event.requester or "page agent",
            tool=tool,
            arguments=arguments,
            since=time.time(),
            record=record,
            key=(tool, arguments),
            requester=event.requester,
            summary=WANTS.get(tool, f"to use {tool}"),
            # The page offers what the harness offers, so the harness applies its own scope to the answer (D5, D8).
            options=[option for option in OPTIONS if option in event.options],
        )
        self._open_approvals[approval.id] = approval
        self._records.append(record)
        self._flush_log()
        if approval.key in self._grants:
            # The harness asks again for a call the user allowed for the session: record it, and ask as usual.
            self._log("allowed", tool=tool, arguments_sha256=record["arguments_sha256"])
        if deny_reason:
            self._answer_open(approval, "deny", deny_reason)
        elif self.auto_approve is not None and self.auto_approve(event):
            self._auto_used = True
            self._answer_open(approval, "allow_once", "Approved page command")

    def answer_approval(self, approval_id: str, choice: str, reason: str = "") -> Future[bool]:
        """The user's answer to an open approval. The result is True once the harness was told."""
        approval = self._open_approvals.get(approval_id)
        if choice not in OPTIONS or (approval is not None and choice not in approval.options):
            raise ValueError("Invalid approval choice")
        receipt = Future()
        values = (approval_id, choice, reason, receipt)
        if threading.current_thread() is self._thread:
            self._answer(*values)
        else:
            with self._answer_lock:
                if self._closing.is_set():
                    receipt.set_result(False)
                else:
                    self._commands.put(("answer", values))
        return receipt

    def _answer(self, approval_id: str, choice: str, reason: str, receipt: Future[bool]) -> None:
        if not receipt.set_running_or_notify_cancel():
            return
        delivered = False
        try:
            approval = self._open_approvals.get(approval_id)
            # An approval is relayed only while it is still waiting; otherwise it already expired.
            if approval is None or choice not in approval.options or (self._closing.is_set() and choice != "deny"):
                return
            delivered = self._answer_open(approval, choice, reason)
        finally:
            receipt.set_result(delivered)

    def _answer_open(self, approval: Approval, choice: str, reason: str) -> bool:
        if approval.peer is not self._peer:
            self._finish_approval(approval, "expired", "the harness process ended")
            return False
        text = (
            reason
            or {
                "allow_once": "allowed once",
                "allow_session": "allowed for this session",
                "deny": "denied by the user",
            }[choice]
        )
        try:
            delivered = approval.peer.answer(approval.event.request_id, choice, text)
        except OSError:
            delivered = False
        if delivered is not True:
            self._finish_approval(approval, "expired", "approval response was not delivered")
            return False
        if choice == "allow_session":
            self._grants.add(approval.key)
        self._last_output = self.clock()
        self._finish_approval(approval, choice, text)
        if self._turn and choice == "deny":
            self._turn.denied.append({"tool": approval.tool, "reason": text})
        return True

    def _finish_approval(self, approval: Approval, answer: str, reason: str) -> None:
        if self._open_approvals.pop(approval.id, None) is None:
            return
        approval.record.update(answer=answer, reason=reason[:2000], wait=round(time.time() - approval.since, 3))
        self._flush_log()

    def _close_approvals(self, reason: str, answer: str = "expired", only=None) -> None:
        """Close open approvals with their reason, and tell the harness where its protocol carries text (S43)."""
        for approval in list(self._open_approvals.values()):
            if only is not None and not only(approval):
                continue
            if approval.peer is not None and approval.peer is self._peer:
                with contextlib.suppress(Exception):
                    approval.peer.answer(approval.event.request_id, "deny", reason)
            self._finish_approval(approval, answer, reason)

    def _close_peer(self, reason: str) -> None:
        try:
            self._close_approvals(reason)
            self._grants.clear()
        finally:
            if self._peer is not None:
                peer, self._peer = self._peer, None
                self._last_stderr = getattr(peer, "stderr", "")
                peer.close()
