"""One page agent session, driven by durable delivery and authenticated page actions."""

from __future__ import annotations

import contextlib
import hashlib
import os
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field

from .. import paths, resources
from .driver_state import (
    ACTIVE_DELIVERY,
    LOG,
    STATE,
    encode,
    log_records,
    read_driver_state,
    recent_turn,
    store_log,
    write_private,
)
from .transport import ProcessTransport as ProcessTransport

POLL = 0.05
START_TIMEOUT = 30
STOP_TIMEOUT = 3
STALL_TIMEOUT = 600

ACTIONS = {
    "login": "Log in to the harness, then press Start.",
    "not-installed": "Install the harness, then serve again.",
    "version": "Update the harness, then serve again.",
    "limit": "After the harness limit resets, press Start.",
    "crashed": "Press Start to resume.",
    "not-handling": "Check the page agent's last reply and log, then press Start.",
    "driver": "Serve the page again.",
    "unsafe-mode": "Change the harness's approval mode, then serve again.",
    "no-approvals": "This harness can't be driven safely. The chat agent listens instead.",
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
    final_message: str = ""
    denied: list[dict] = field(default_factory=list)

    @property
    def items(self) -> frozenset[str]:
        return frozenset(self.record["items"])


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
        approvals=None,
        clock=time.monotonic,
        valid_session=None,
    ):
        self.conversation = conversation
        self.unit = conversation.unit
        self.harness = harness
        self.launch = launch
        self.cwd = str(cwd)
        self.step, self.handoff = step, handoff
        self.skill_path, self.command = str(skill_path), command
        self.triggers, self.approvals, self.clock = triggers, approvals, clock
        if valid_session is None:
            from .adapters import session_id_valid

            def valid_session(key):
                return session_id_valid(harness, key)

        self.valid_session = valid_session
        saved = read_driver_state(self.unit, harness, valid_session=valid_session)
        self.session = saved.get("session")
        tag = saved.get("tag")
        try:
            self.tag = str(uuid.UUID(tag))
        except (AttributeError, TypeError, ValueError):
            self.tag = str(uuid.uuid4())

        delivered = saved.get("delivered")
        self._delivered = delivered if type(delivered) is int and delivered >= 0 else 0
        self._fired = self._strings(saved.get("fired"))
        self._records = log_records(self.unit)
        for record in self._records:
            if record.get("type") == "approval" and "answer" not in record:
                record.update(answer="expired", reason="driver restarted")
        last = recent_turn(self._records, self.session)
        self._number = last.get("number", 0) if type(last.get("number")) is int else 0
        self._carry = frozenset()
        self._recover = frozenset()
        self._recover_turn = 0
        self._recover_kind = ""
        if last:
            items = self._strings(last.get("items"))
            if last.get("outcome") == "completed":
                self._carry = items
            else:
                self._recover, self._recover_turn = items, self._number
                self._recover_kind = last.get("outcome") or "crashed"
                if "end" not in last:
                    last.update(end=time.time(), outcome="crashed")

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
        self._published = ("starting", time.time(), clock(), False, {})
        self._thread = threading.Thread(target=self._run, name="page-agent", daemon=True)
        self._state = "starting"
        self._since = time.time()
        self._details = {}
        self._last_output = self.clock()
        self._first_prompt = True
        self._approval_records = {}

    @staticmethod
    def _strings(values) -> frozenset[str]:
        return (
            frozenset(value for value in values if isinstance(value, str)) if isinstance(values, list) else frozenset()
        )

    def start(self, timeout=START_TIMEOUT) -> str:
        self._deadline = time.monotonic() + timeout
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

    def close(self) -> None:
        self._closing.set()
        if self._thread.ident is not None:
            self._thread.join(timeout=4.75)

    def can_linger(self) -> bool:
        state, _, _, waiting, _ = self._published
        return state not in ("starting", "working", "stalled", "stopping") and not waiting and self._commands.empty()

    def snapshot(self) -> dict:
        state, since, at, waiting, details = self._published
        return {
            "state": state,
            "since": since,
            "age": max(0, self.clock() - at),
            "waiting": waiting,
            **details,
        }

    def _publish(self) -> None:
        self._published = (self._state, self._since, self.clock(), self._wake, self._details)

    def _log(self, record_type: str, **fields) -> None:
        self._records.append({"type": record_type, "at": time.time(), "session": self.session, **fields})
        self._flush_log()

    def _flush_log(self) -> None:
        self._records = store_log(self.unit, self._records)

    def _status(self, state: str, **details) -> None:
        if self._state != state or self._details != details:
            self._state, self._since, self._details = state, time.time(), details
            self._log("state", state=state, **details)
        self._publish()

    def _checkpoint(self) -> None:
        write_private(
            self.unit,
            STATE,
            encode(
                {
                    "version": 1,
                    "harness": self.harness,
                    "session": self.session,
                    "tag": self.tag,
                    "server_pid": os.getpid(),
                    "child_pid": self._peer.pid if self._peer else None,
                    "opened": time.time(),
                    "delivered": self._delivered,
                    "fired": sorted(self._fired),
                }
            ),
        )

    def _open(self, deadline: float) -> None:
        resume = self.session
        self._peer = self.launch(self.tag)
        self._peer.open(self.cwd, resume)
        while not self._closing.is_set() and time.monotonic() < deadline:
            event = self._peer.poll(POLL)
            if event is None:
                continue
            if event.kind == "ready":
                if not self.valid_session(event.session_id):
                    raise StartError("crashed", "harness returned an invalid session ID")
                if self.session != event.session_id:
                    self._first_prompt = True
                self.session = event.session_id
                self._last_output = self.clock()
                self._checkpoint()
                self._status("idle")
                return
            if event.kind == "failed":
                if resume and event.outcome == "missing-session":
                    resume = None
                    self._peer.open(self.cwd, None)
                    continue
                raise StartError(event.outcome or "crashed", event.text)
            if event.kind == "approval":
                self._peer.answer(event.request_id, "deny", "the page is starting")
        raise StartError("crashed", "harness startup timed out")

    def _run(self) -> None:
        try:
            self._open(self._deadline)
            self._started.set()
            while not self._closing.is_set():
                self._commands_once()
                drained = self._events_once()
                if self._state not in ("stopping", "failed"):
                    available = self._available_triggers()
                    if available:
                        self._wake = True
                    if self._state == "idle" and self._wake and drained:
                        self._deliver(available)
                self._publish()
            self._stop("server stopped")
        except StartError as error:
            self._start_error = error
            self._failed(error.kind, str(error))
        except Exception as error:
            self._start_error = StartError("driver", str(error))
            # An error in the state/log writer must still leave a readable status in memory.
            try:
                self._failed("driver", str(error))
            except Exception:
                self._state, self._since = "failed", time.time()
                self._details = {"kind": "driver", "action": ACTIONS["driver"], "message": str(error)}
                self._publish()
        finally:
            try:
                self._close_peer("driver closed")
            finally:
                self._started.set()

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
            if {value.get("id"), value.get("to")} & self._last_prompt_items:
                self._repeats = 0
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
        if (
            self._state == "working"
            and self.clock() - self._last_output >= STALL_TIMEOUT
            and not (self.approvals and self.approvals.waiting())
        ):
            self._status("stalled")
        return True

    def _receive(self, event) -> None:
        self._last_output = self.clock()
        if self._state == "stalled":
            self._status("working")
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
                self._end("completed")
                self._crash_retries = 0
                self._status("idle")
            else:
                self._failed(event.outcome or "crashed", event.text)
        elif event.kind == "approval":
            self._request_approval(event)
        elif event.kind == "approval_closed":
            if self.approvals:
                self.approvals.closed(event)
            self._record_approval_end(event, event.outcome or "expired", event.text)

    def _deliver(self, available: tuple[dict, ...]) -> None:
        batch = self.conversation.delivery(self._delivered, carry_ids=self._carry, recover_ids=self._recover)
        self._wake = False
        if not (batch.items or batch.events or available):
            return
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
        self._repeats = self._repeats + 1 if items and items == self._last_prompt_items else 1
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
                }
            ),
        )
        self._begin(batch.position, items, tuple(r["id"] for r in available))
        self._peer.prompt(self._prompt(batch, available))
        self._first_prompt = False

    def _prompt(self, batch, available: tuple[dict, ...]) -> str:
        parts = []
        if self._first_prompt:
            parts.extend(
                [
                    self.handoff,
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
        self._records.append(record)
        self._flush_log()
        self._last_output = self.clock()
        self._status("working")

    def _end(self, outcome: str) -> None:
        turn, self._turn = self._turn, None
        if turn is None:
            return
        if outcome == "completed" and turn.position is not None:
            self._delivered = turn.position
            self._fired |= frozenset(turn.triggers)
            self._carry = turn.items
            self._recover = frozenset()
            self._wake = self._wake or bool(turn.items)
            self._checkpoint()
        elif outcome != "completed":
            self._recover |= turn.items | self._carry
            self._carry = frozenset()
            self._recover_turn, self._recover_kind = turn.record["number"], outcome
            turn.record["items"] = sorted(self._recover)
        peer_stderr = self._peer.stderr if self._peer else ""
        turn.record.update(
            end=time.time(),
            outcome=outcome,
            denied=turn.denied,
            final_message=turn.final_message,
            stderr=peer_stderr[-2000:],
        )
        if not any(record is turn.record for record in self._records):
            self._records.append(turn.record)
        self._flush_log()
        with contextlib.suppress(FileNotFoundError):
            self.unit.target(ACTIVE_DELIVERY).unlink()

    def _failed(self, kind: str, message: str = "", **details) -> None:
        self._end(kind)
        self._close_peer(kind)
        self._log("error", kind=kind, message=message)
        self._status("failed", kind=kind, action=ACTIONS.get(kind, ACTIONS["crashed"]), message=message, **details)

    def _stop(self, reason: str) -> None:
        self._status("stopping")
        self._close_approvals(reason)
        if self._peer is not None:
            with contextlib.suppress(OSError):
                self._peer.cancel()
                deadline = time.monotonic() + STOP_TIMEOUT
                while self._turn is not None and time.monotonic() < deadline:
                    event = self._peer.poll(POLL)
                    if event is None:
                        continue
                    if event.kind in ("turn_ended", "failed"):
                        break
                    if event.kind == "approval":
                        self._peer.answer(event.request_id, "deny", reason)
        self._end(reason)
        self._close_peer(reason)
        self._status("stopped")

    def _request_approval(self, event) -> None:
        peer = self._peer

        def answer(choice: str, reason: str = "") -> None:
            values = (peer, event, choice, reason)
            if threading.current_thread() is self._thread:
                self._answer(*values)
            else:
                self._commands.put(("answer", values))

        record = {
            "type": "approval",
            "at": time.time(),
            "session": self.session,
            "request": event.request_id,
            "tool": event.tool,
            "arguments_sha256": hashlib.sha256(encode({"arguments": event.arguments})).hexdigest(),
        }
        self._approval_records[event.request_id] = record
        self._records.append(record)
        self._flush_log()
        if self.approvals is None:
            answer("deny", "no page approval controller")
        else:
            self.approvals.receive(event, answer)

    def _answer(self, peer, event, choice: str, reason: str) -> None:
        if self._peer is not peer:
            return
        self._peer.answer(event.request_id, choice, reason)
        self._last_output = self.clock()
        self._record_approval_end(event, choice, reason)
        if self._turn and choice == "deny":
            self._turn.denied.append({"tool": event.tool, "reason": reason})

    def _record_approval_end(self, event, choice: str, reason: str) -> None:
        record = self._approval_records.pop(event.request_id, None)
        if record is not None:
            record.update(answer=choice, reason=reason[:2000])
            if not any(item is record for item in self._records):
                self._records.append(record)
            self._flush_log()

    def _close_approvals(self, reason: str) -> None:
        if self.approvals:
            self.approvals.close(reason)
        if self._approval_records:
            for record in self._approval_records.values():
                record.update(answer="expired", reason=reason)
            self._approval_records.clear()
            self._flush_log()

    def _close_peer(self, reason: str) -> None:
        try:
            self._close_approvals(reason)
        finally:
            if self._peer is not None:
                peer, self._peer = self._peer, None
                peer.close()
