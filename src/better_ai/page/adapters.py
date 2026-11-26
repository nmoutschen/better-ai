"""Wire messages for page agent sessions. The driver owns processes and approval policy."""

from __future__ import annotations

import itertools
import json
import re
import shutil
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

WireID = int | str
Send = Callable[[dict], None]


@dataclass(frozen=True)
class Candidate:
    name: str | None
    argv: tuple[str, ...]
    kind: str


# Prefer specific identifiers to generic markers if one harness is started from another.
_HARNESSES = {
    "devin": (("devin", "acp"), ("DEVIN_CLI", "DEVIN_SESSION_ID")),
    "droid": (
        ("droid", "exec", "--input-format", "stream-jsonrpc", "--output-format", "stream-jsonrpc"),
        ("FACTORY_DROID", "DROID_SESSION_ID"),
    ),
    "cursor": (("agent", "acp"), ("CURSOR_AGENT", "CURSOR_SESSION_ID")),
    "opencode": (("opencode", "acp"), ("OPENCODE", "OPENCODE_SESSION_ID")),
    "codex": (("codex", "app-server"), ("CODEX_THREAD_ID",)),
    "claude": (
        ("claude", "-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose"),
        ("CLAUDECODE",),
    ),
}

_MIN_VERSION = {"claude": (2, 1, 332), "codex": (0, 172, 0), "opencode": (2, 4, 1)}
_VERSION = re.compile(r"(?<![\d.])(\d{1,5})\.(\d{1,5})\.(\d{1,5})(?![\d.])")
_UUID = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}")
_ACP_SESSION = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}")


def candidate(requested: str, env: Mapping[str, str], which: Callable[[str], str | None] = shutil.which) -> Candidate:
    """Return metadata without launching a process or reading harness settings."""
    name = requested
    if requested == "auto":
        name = next((name for name, (_, markers) in _HARNESSES.items() if any(env.get(k) for k in markers)), "")
        if not name:
            return Candidate(None, (), "none")
    if name not in _HARNESSES:
        raise ValueError(f"unknown harness: {name}")
    command, _ = _HARNESSES[name]
    executable = which(command[0])
    if executable is None:
        return Candidate(name, (), "not-installed")
    # A protocol endpoint alone does not establish isolation or trustworthy approval forwarding.
    return Candidate(name, (executable, *command[1:]), "no-approvals")


def version_supported(name: str, version: str) -> bool:
    minimum = _MIN_VERSION.get(name)
    match = _VERSION.search(version)
    return minimum is not None and match is not None and tuple(map(int, match.groups())) >= minimum


def session_id_valid(name: str, session_id: Any) -> bool:
    if name not in _HARNESSES or not isinstance(session_id, str):
        return False
    pattern = _UUID if name in {"claude", "codex", "droid"} else _ACP_SESSION
    return pattern.fullmatch(session_id) is not None


def child_environment(name: str, env: Mapping[str, str], session_id: str) -> dict[str, str]:
    result = {**env, "BETTER_PAGE_SESSION": session_id}
    if name == "opencode":
        result["OPENCODE_CONFIG_CONTENT"] = json.dumps({"permission": {"edit": "ask", "bash": "ask"}})
    return result


@dataclass(frozen=True)
class AdapterEvent:
    kind: str
    session_id: str | None = None
    turn_id: str | None = None
    outcome: str | None = None
    text: str = ""
    request_id: WireID | None = None
    tool: str = ""
    arguments: Any = None
    options: tuple[str, ...] = ()
    requester: str | None = None


Events = tuple[AdapterEvent, ...]


def _object(data: Any) -> dict:
    return data if isinstance(data, dict) else {}


def _text(data: Any) -> str:
    return data if isinstance(data, str) else ""


def _wire_id(data: Any) -> bool:
    return type(data) in (int, str)


def _failure(kind: str, text: str = "") -> Events:
    return (AdapterEvent("failed", outcome=kind, text=text),)


def _error_kind(error: dict, default: str) -> str:
    if error.get("code") in (401, -32000) and (
        error.get("code") == 401 or "auth" in _text(error.get("message")).lower()
    ):
        return "login"
    if error.get("code") in (429,):
        return "limit"
    message = _text(error.get("message")).casefold()
    if any(word in message for word in ("not logged in", "not authenticated", "authentication required")):
        return "login"
    if any(word in message for word in ("rate limit", "usage limit", "quota exceeded")):
        return "limit"
    return default


class _RPCAdapter:
    def __init__(self, send: Send):
        self.send = send
        self.session_id: str | None = None
        self.turn_id: str | None = None
        self._ids = itertools.count(1)
        self._calls: dict[WireID, tuple[str, Callable[[dict], Events]]] = {}
        self._approvals: dict[WireID, Callable[[str, str], dict]] = {}

    def _call(self, method: str, params: dict, done: Callable[[dict], Events]) -> int:
        request_id = next(self._ids)
        self._calls[request_id] = (method, done)
        self.send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        return request_id

    def _notify(self, method: str, params: dict) -> None:
        self.send({"jsonrpc": "2.0", "method": method, "params": params})

    def _result(self, request_id: WireID, payload: dict) -> None:
        self.send({"jsonrpc": "2.0", "id": request_id, "result": payload})

    def _error(self, request_id: WireID, code: int, message: str) -> None:
        self.send({"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}})

    def answer(self, request_id: WireID, choice: str, reason: str = "") -> bool:
        answer = self._approvals.pop(request_id, None)
        if answer is None:
            return False
        self._result(request_id, answer(choice, reason))
        return True

    def receive(self, message: dict) -> Events:
        method, request_id = message.get("method"), message.get("id")
        if isinstance(method, str):
            params = _object(message.get("params"))
            if not _wire_id(request_id):
                return self._notification(method, params) if "id" not in message else ()
            if request_id in self._approvals:
                # A second request cannot change what an open approval represents.
                self.answer(request_id, "deny", "duplicate request id")
                return (AdapterEvent("approval_closed", request_id=request_id, outcome="denied"),)
            return self._request(request_id, method, params)
        if _wire_id(request_id) and request_id in self._calls:
            called, done = self._calls.pop(request_id)
            if "error" in message:
                error = _object(message["error"])
                return self._call_failed(called, error)
            return done(_object(message.get("result")))
        return ()

    def _call_failed(self, method: str, error: dict) -> Events:
        return _failure(_error_kind(error, "crashed"), _text(error.get("message")))

    def _request(self, request_id: WireID, method: str, params: dict) -> Events:
        if any(keyword in method.casefold() for keyword in ("permission", "approval", "authorize", "consent")):
            self._error(request_id, -32601, "permission denied")
        else:
            self._error(request_id, -32601, "method not supported")
        return ()

    def _notification(self, method: str, params: dict) -> Events:
        return ()


class ACPAdapter(_RPCAdapter):
    """ACP v1 documents transport and request shapes, but leaves approval enforcement to the agent."""

    def open(self, cwd: str, resume: str | None) -> None:
        self._cwd = cwd
        self._resume = resume if session_id_valid("opencode", resume) else None
        self._call(
            "initialize",
            {
                "protocolVersion": 1,
                "clientCapabilities": {"fs": {"readTextFile": False, "writeTextFile": False}, "terminal": False},
            },
            self._initialized,
        )

    def _initialized(self, data: dict) -> Events:
        if type(data.get("protocolVersion")) is not int or data["protocolVersion"] != 1:
            return _failure("version")
        params: dict = {"cwd": self._cwd, "mcpServers": []}
        if self._resume:
            self._call("session/load", {**params, "sessionId": self._resume}, self._opened)
        else:
            self._call("session/new", params, self._opened)
        return ()

    def _opened(self, data: dict) -> Events:
        mode = _object(data.get("modes")).get("currentModeId")
        if mode in ("auto", "yolo", "bypassPermissions", "acceptEdits"):
            return _failure("unsafe-mode")
        session_id = data.get("sessionId", self._resume)
        if not session_id_valid("opencode", session_id):
            return _failure("crashed", "missing or invalid ACP session id")
        self.session_id = session_id
        return (AdapterEvent("ready", session_id=session_id),)

    def prompt(self, text: str) -> None:
        if self.session_id is None:
            raise RuntimeError("ACP session is not open")
        self._call(
            "session/prompt",
            {"sessionId": self.session_id, "prompt": [{"type": "text", "text": text}]},
            self._prompt_ended,
        )

    def cancel(self) -> None:
        if self.session_id is not None:
            self._notify("session/cancel", {"sessionId": self.session_id})

    def _prompt_ended(self, data: dict) -> Events:
        reason = data.get("stopReason")
        if reason in ("max_tokens", "max_turn_requests"):
            outcome = "limit"
        elif reason == "cancelled":
            outcome = "stopped"
        elif reason == "end_turn":
            outcome = "normal"
        else:
            outcome = "crashed"
        return (AdapterEvent("turn_ended", outcome=outcome),)

    def _call_failed(self, method: str, error: dict) -> Events:
        message = _text(error.get("message"))
        if error.get("code") == -32000 or error.get("code") == -32002:
            return _failure("login", message) if error.get("code") == -32000 else super()._call_failed(method, error)
        if method == "session/load" and (error.get("code") == -32602 or "not found" in message.casefold()):
            self._resume = None
            self._call("session/new", {"cwd": self._cwd, "mcpServers": []}, self._opened)
            return ()
        return super()._call_failed(method, error)

    def _request(self, request_id: WireID, method: str, params: dict) -> Events:
        if method != "session/request_permission":
            return super()._request(request_id, method, params)
        available = params.get("options")
        options = {}
        for option in available if isinstance(available, list) else ():
            item = _object(option)
            name = item.get("kind")
            if name in ("allow_once", "reject_once") and isinstance(item.get("optionId"), str):
                options[name] = item["optionId"]

        def respond(choice: str, _reason: str) -> dict:
            option_id = options.get("allow_once" if choice == "allow_once" else "reject_once")
            outcome = {"outcome": "selected", "optionId": option_id} if option_id else {"outcome": "cancelled"}
            return {"outcome": outcome}

        call = _object(params.get("toolCall"))
        tool = _text(call.get("name")) or _text(call.get("title"))
        arguments = call.get("rawInput")
        if (
            self.session_id is None
            or params.get("sessionId") != self.session_id
            or not tool
            or arguments is None
            or call.get("kind") == "switch_mode"
            or not options.get("allow_once")
            or options.get("allow_once") == options.get("reject_once")
        ):
            self._result(request_id, respond("deny", ""))
            return ()
        self._approvals[request_id] = respond
        return (
            AdapterEvent(
                "approval", request_id=request_id, tool=tool, arguments=arguments, options=("allow_once", "deny")
            ),
        )

    def _notification(self, method: str, params: dict) -> Events:
        if method != "session/update" or params.get("sessionId") != self.session_id:
            return ()
        update = _object(params.get("update"))
        if update.get("sessionUpdate") == "agent_message_chunk":
            return (AdapterEvent("text", text=_text(_object(update.get("content")).get("text"))),)
        return ()


class CodexAdapter(_RPCAdapter):
    """Codex app-server stdio protocol version checked against the locally shipped schema."""

    def open(self, cwd: str, resume: str | None) -> None:
        self._cwd = cwd
        self._resume = resume if session_id_valid("codex", resume) else None
        self._call("initialize", {"clientInfo": {"name": "better-ai", "version": "0.1.0"}}, self._initialized)
        self._changes: dict[tuple[str, str], list] = {}

    def _initialized(self, data: dict) -> Events:
        if not version_supported("codex", _text(data.get("userAgent"))):
            return _failure("version")
        self._notify("initialized", {})
        self._open_thread()
        return ()

    def _open_thread(self) -> None:
        params = {"cwd": self._cwd, "approvalsReviewer": "user"}
        if self._resume:
            self._call("thread/resume", {**params, "threadId": self._resume}, self._opened)
        else:
            self._call("thread/start", params, self._opened)

    def _opened(self, data: dict) -> Events:
        if data.get("approvalPolicy") not in ("untrusted", "on-request") or data.get("approvalsReviewer") != "user":
            return _failure("unsafe-mode")
        session_id = _object(data.get("thread")).get("id")
        if not session_id_valid("codex", session_id):
            return _failure("crashed", "missing or invalid Codex thread id")
        self.session_id = session_id
        return (AdapterEvent("ready", session_id=session_id),)

    def prompt(self, text: str) -> None:
        if self.session_id is None:
            raise RuntimeError("Codex thread is not open")
        self._call(
            "turn/start", {"threadId": self.session_id, "input": [{"type": "text", "text": text}]}, self._started
        )

    def cancel(self) -> None:
        if self.turn_id is not None:
            self._call("turn/interrupt", {"threadId": self.session_id, "turnId": self.turn_id}, lambda _: ())

    def _started(self, data: dict) -> Events:
        turn_id = _text(_object(data.get("turn")).get("id"))
        if not turn_id or turn_id == self.turn_id:
            return ()
        self.turn_id = turn_id
        return (AdapterEvent("turn_started", turn_id=turn_id),)

    def _notification(self, method: str, params: dict) -> Events:
        if params.get("threadId") != self.session_id:
            return ()
        if method == "turn/started":
            return self._started(params)
        if method == "turn/completed":
            turn = _object(params.get("turn"))
            turn_id = _text(turn.get("id"))
            if not turn_id or turn_id != self.turn_id:
                return ()
            self.turn_id = None
            self._changes.clear()
            status, error = turn.get("status"), _object(turn.get("error"))
            outcome = {"completed": "normal", "interrupted": "stopped"}.get(
                _text(status), _error_kind(error, "crashed")
            )
            return (AdapterEvent("turn_ended", turn_id=turn_id, outcome=outcome, text=_text(error.get("message"))),)
        if method == "item/agentMessage/delta":
            return (AdapterEvent("text", text=_text(params.get("delta"))),)
        if method == "item/started":
            item = _object(params.get("item"))
            changes = item.get("changes")
            if item.get("type") == "fileChange" and isinstance(changes, list) and changes:
                self._changes[(_text(params.get("turnId")), _text(item.get("id")))] = changes
        if method == "serverRequest/resolved" and _wire_id(params.get("requestId")):
            request_id = params["requestId"]
            if self._approvals.pop(request_id, None) is not None:
                return (AdapterEvent("approval_closed", request_id=request_id, outcome="expired"),)
        return ()

    def _request(self, request_id: WireID, method: str, params: dict) -> Events:
        if method == "item/permissions/requestApproval":
            self._result(request_id, {"permissions": {}, "scope": "turn"})
            return ()
        if method == "item/commandExecution/requestApproval":
            tool = "Command"
            complete = bool(_text(params.get("command"))) and not params.get("networkApprovalContext")
            arguments = params
        elif method == "item/fileChange/requestApproval":
            tool = "File change"
            changes = self._changes.get((_text(params.get("turnId")), _text(params.get("itemId"))))
            complete = bool(changes) and not params.get("grantRoot")
            arguments = {**params, "changes": changes}
        else:
            return super()._request(request_id, method, params)

        def respond(choice: str, _reason: str) -> dict:
            return {"decision": "accept" if choice == "allow_once" else "decline"}

        if self.session_id is None or params.get("threadId") != self.session_id or not complete:
            self._result(request_id, respond("deny", ""))
            return ()
        self._approvals[request_id] = respond
        return (
            AdapterEvent(
                "approval",
                request_id=request_id,
                tool=tool,
                arguments=arguments,
                options=("allow_once", "deny"),
                requester=_text(params.get("turnId")) or None,
            ),
        )

    def _call_failed(self, method: str, error: dict) -> Events:
        message = _text(error.get("message"))
        if method == "thread/resume" and ("not found" in message.casefold() or "no rollout" in message.casefold()):
            self._resume = None
            self._open_thread()
            return ()
        return super()._call_failed(method, error)


class ClaudeAdapter:
    """Claude Code stream-json. The MCP approval wire is handled by the separate relay."""

    def __init__(self, send: Send):
        self.send = send
        self.session_id: str | None = None
        self._ids = itertools.count(1)

    def open(self, cwd: str, resume: str | None) -> None:
        # Claude sends its authoritative session id with the stream's init event.
        self.session_id = resume if session_id_valid("claude", resume) else None

    def prompt(self, text: str) -> None:
        self.send({"type": "user", "message": {"role": "user", "content": text}})

    def cancel(self) -> None:
        self.send(
            {"type": "control_request", "request_id": f"cancel-{next(self._ids)}", "request": {"subtype": "interrupt"}}
        )

    def answer(self, request_id: WireID, choice: str, reason: str = "") -> bool:
        return False

    def receive(self, message: dict) -> Events:
        kind, subtype = message.get("type"), message.get("subtype")
        if kind == "system" and subtype == "init":
            if message.get("permissionMode") != "default":
                return _failure("unsafe-mode")
            session_id = message.get("session_id")
            if not session_id_valid("claude", session_id):
                return _failure("crashed", "missing or invalid Claude session id")
            self.session_id = session_id
            return (AdapterEvent("ready", session_id=session_id),)
        if kind == "assistant":
            content = _object(message.get("message")).get("content")
            text = (
                "".join(
                    _text(block.get("text"))
                    for block in content
                    if isinstance(block, dict) and block.get("type") == "text"
                )
                if isinstance(content, list)
                else ""
            )
            return (AdapterEvent("text", text=text),)
        if kind == "result":
            error = _text(message.get("result"))
            if subtype == "success" and message.get("is_error") is not True:
                outcome = "normal"
            elif subtype in ("interrupted", "error_interrupted"):
                outcome = "stopped"
            elif subtype in ("error_max_turns", "error_max_budget_usd"):
                outcome = "limit"
            else:
                outcome = _error_kind({"message": error}, "crashed")
            return (AdapterEvent("turn_ended", outcome=outcome, text=error),)
        if kind == "control_request" and _wire_id(message.get("request_id")):
            self.send(
                {
                    "type": "control_response",
                    "response": {"subtype": "error", "request_id": message["request_id"], "error": "permission denied"},
                }
            )
        return ()
