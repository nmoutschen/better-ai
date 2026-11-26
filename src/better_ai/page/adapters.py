"""Wire messages for page agent sessions. The driver owns processes and approval policy."""

from __future__ import annotations

import itertools
import json
import re
import shutil
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any, TypeVar

WireID = int | str
Send = Callable[[dict], None]


@dataclass(frozen=True)
class Candidate:
    name: str | None
    argv: tuple[str, ...]
    kind: str | None
    approval: str | None = None
    codec_factory: Callable[[Send], ACPAdapter | CodexAdapter | ClaudeAdapter | DroidAdapter] | None = None

    def command(self, session_id: str, resume: str | None) -> tuple[str, ...]:
        if self.kind is not None:
            raise ValueError(f"harness is unavailable: {self.kind}")
        if self.name != "claude":
            return self.argv
        if session_id_valid("claude", resume):
            return (*self.argv, f"--resume={resume}")
        if not session_id_valid("claude", session_id):
            raise ValueError("a new Claude page session requires a UUID")
        return (*self.argv, f"--session-id={session_id}")

    def codec(
        self, send: Send, session_id: str, resume: str | None
    ) -> ACPAdapter | CodexAdapter | ClaudeAdapter | DroidAdapter:
        if self.codec_factory is None:
            raise ValueError("no verified protocol for this harness")
        if self.name == "claude":
            expected = resume if session_id_valid("claude", resume) else session_id
            return ClaudeAdapter(send, expected)
        return self.codec_factory(send)


# Prefer specific identifiers to generic markers if one harness is started from another.
_HARNESSES = {
    "devin": (("devin", "--process-model", "in-process", "acp"), ("DEVIN_CLI", "DEVIN_SESSION_ID")),
    "droid": (
        ("droid", "exec", "--input-format", "stream-jsonrpc", "--output-format", "stream-jsonrpc"),
        ("FACTORY_DROID", "DROID_SESSION_ID"),
    ),
    "cursor": (("agent", "acp"), ("CURSOR_AGENT", "CURSOR_SESSION_ID")),
    "opencode": (("opencode", "acp"), ("OPENCODE", "OPENCODE_SESSION_ID")),
    "codex": (("codex", "app-server"), ("CODEX_THREAD_ID",)),
    "claude": (
        (
            "claude",
            "-p",
            "--input-format",
            "stream-json",
            "--output-format",
            "stream-json",
            "--verbose",
            "--permission-prompts",
            "host",
        ),
        ("CLAUDECODE",),
    ),
}

_MIN_VERSION = {
    "claude": (2, 1, 332),
    "codex": (0, 172, 0),
    "opencode": (2, 4, 1),
    "cursor": (2026, 11, 17),  # Cursor's November 17 CLI release documents ACP fixes.
    "droid": (1, 21, 0),  # CLI tested in Factory's SDK 0.11.0 example.
    "devin": (3000, 13, 4),  # First release with --process-model in-process.
}
_VERSION = re.compile(r"(?<![\d.])(\d{1,5})\.(\d{1,5})\.(\d{1,5})(?![\d.])")
_CURSOR_VERSION = re.compile(
    r"(?:(?:cursor-agent|cursor|agent)\s+)?v?([0-9]{4})\.([0-9]{2})\.([0-9]{2})(?:-[0-9a-f]{7,40})?",
    re.IGNORECASE,
)
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
    argv = (executable, *command[1:])
    factories = {
        "claude": ClaudeAdapter,
        "codex": CodexAdapter,
        "opencode": OpenCodeAdapter,
        "cursor": CursorAdapter,
        "droid": DroidAdapter,
        "devin": DevinAdapter,
    }
    if name == "opencode":
        try:
            _opencode_config(env)
        except ValueError:
            return Candidate(name, argv, "unsafe-mode")
    return Candidate(name, argv, None, "webauthn", factories[name])


def version_supported(name: str, version: str) -> bool:
    minimum = _MIN_VERSION.get(name)
    match = _CURSOR_VERSION.fullmatch(version.strip()) if name == "cursor" else _VERSION.search(version)
    if minimum is None or match is None:
        return False
    release = tuple(map(int, match.groups()))
    if name == "cursor":
        try:
            date(*release)
        except ValueError:
            return False
    return release >= minimum


def session_id_valid(name: str, session_id: Any) -> bool:
    if name not in _HARNESSES or not isinstance(session_id, str):
        return False
    pattern = _UUID if name in {"claude", "codex"} else _ACP_SESSION
    return pattern.fullmatch(session_id) is not None


def _opencode_config(env: Mapping[str, str]) -> str:
    config = json.loads(env.get("OPENCODE_CONFIG_CONTENT") or "{}")
    if not isinstance(config, dict):
        raise ValueError("invalid OpenCode inline configuration")
    legacy = config.get("permission", {})
    if isinstance(legacy, str):
        legacy = {"*": legacy}
    current = config.get("permissions", [])
    if not isinstance(legacy, dict) or not isinstance(current, list):
        raise ValueError("invalid OpenCode inline permissions")
    # Keep the user's other inline options. Modern OpenCode uses shell and ordered rules.
    config["permission"] = {**legacy, "edit": "ask", "bash": "ask"}
    config["permissions"] = [
        *current,
        {"action": "edit", "resource": "*", "effect": "ask"},
        {"action": "shell", "resource": "*", "effect": "ask"},
    ]
    return json.dumps(config)


def child_environment(name: str, env: Mapping[str, str], session_id: str) -> dict[str, str]:
    result = {**env, "BETTER_PAGE_SESSION": session_id}
    if name == "opencode":
        result["OPENCODE_CONFIG_CONTENT"] = _opencode_config(env)
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
    tool_id: str | None = None


Events = tuple[AdapterEvent, ...]
ApprovalBody = TypeVar("ApprovalBody")


def _expire_owned(approvals: dict[WireID, tuple[str | None, ApprovalBody]], owner: str | None) -> Events:
    expired = [request_id for request_id, (requester, _) in approvals.items() if requester == owner]
    for request_id in expired:
        del approvals[request_id]
    return tuple(
        AdapterEvent("approval_closed", request_id=request_id, outcome="expired", text="requester ended")
        for request_id in expired
    )


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
        self._approvals: dict[WireID, tuple[str | None, Callable[[str, str], dict]]] = {}

    def _request_id(self) -> WireID:
        return next(self._ids)

    def _send_frame(self, _kind: str, **fields) -> None:
        self.send({"jsonrpc": "2.0", **fields})

    def _call(self, method: str, params: dict, done: Callable[[dict], Events]) -> WireID:
        request_id = self._request_id()
        self._calls[request_id] = (method, done)
        self._send_frame("request", id=request_id, method=method, params=params)
        return request_id

    def _notify(self, method: str, params: dict) -> None:
        self._send_frame("notification", method=method, params=params)

    def _result(self, request_id: WireID, payload: dict) -> None:
        self._send_frame("response", id=request_id, result=payload)

    def _error(self, request_id: WireID, code: int, message: str) -> None:
        self._send_frame("response", id=request_id, error={"code": code, "message": message})

    def answer(self, request_id: WireID, choice: str, reason: str = "") -> bool:
        pending = self._approvals.pop(request_id, None)
        if pending is None:
            return False
        _, answer = pending
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

    _client_info: dict = {}

    def open(self, cwd: str, resume: str | None) -> None:
        self._cwd = cwd
        self._resume = resume if session_id_valid("opencode", resume) else None
        self._call(
            "initialize",
            {
                "protocolVersion": 1,
                "clientCapabilities": {"fs": {"readTextFile": False, "writeTextFile": False}, "terminal": False},
                **self._client_info,
            },
            self._initialized,
        )

    def _initialized(self, data: dict) -> Events:
        if type(data.get("protocolVersion")) is not int or data["protocolVersion"] != 1:
            return _failure("version")
        return self._open_session(data)

    def _open_session(self, _data: dict) -> Events:
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
        code = error.get("code")
        if code == -32000:
            return _failure("login", message)
        if method == "session/load" and (code in (-32002, -32602) or "not found" in message.casefold()):
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
        owner = _text(call.get("toolCallId")) or None
        self._approvals[request_id] = (owner, respond)
        return (
            AdapterEvent(
                "approval",
                request_id=request_id,
                tool=tool,
                arguments=arguments,
                options=("allow_once", "deny"),
                requester=owner,
            ),
        )

    def _notification(self, method: str, params: dict) -> Events:
        if method != "session/update" or params.get("sessionId") != self.session_id:
            return ()
        update = _object(params.get("update"))
        if update.get("sessionUpdate") == "agent_message_chunk":
            return (AdapterEvent("text", text=_text(_object(update.get("content")).get("text"))),)
        if update.get("sessionUpdate") == "tool_call_update" and update.get("status") in ("completed", "failed"):
            owner = _text(update.get("toolCallId"))
            if owner:
                return _expire_owned(self._approvals, owner)
        return ()


class OpenCodeAdapter(ACPAdapter):
    def _initialized(self, data: dict) -> Events:
        version = _text(_object(data.get("agentInfo")).get("version"))
        if not version_supported("opencode", version):
            return _failure("version")
        return super()._initialized(data)

    def _opened(self, data: dict) -> Events:
        options = data.get("configOptions")
        modes = (
            [
                option.get("currentValue")
                for option in options
                if isinstance(option, dict) and option.get("category") == "mode"
            ]
            if isinstance(options, list)
            else []
        )
        old_mode = _object(data.get("modes")).get("currentModeId")
        if (modes or [old_mode]) not in (["build"], ["plan"]):
            return _failure("unsafe-mode")
        return super()._opened(data)


class _ConfiguredACPAdapter(ACPAdapter):
    """Require the peer's effective approval choice, distinct from its coding profile."""

    _permission_option: str
    _safe_mode: str

    def _permission_check(self, data: dict) -> str | None:
        options = data.get("configOptions")
        values = (
            [
                option.get("currentValue")
                for option in options
                if isinstance(option, dict) and option.get("id") == self._permission_option
            ]
            if isinstance(options, list)
            else []
        )
        if len(values) != 1:
            return "no-approvals"
        if values[0] != self._safe_mode:
            return "unsafe-mode"
        return None

    def _opened(self, data: dict) -> Events:
        failure = self._permission_check(data)
        if failure:
            return _failure(failure)
        return super()._opened(data)

    def _notification(self, method: str, params: dict) -> Events:
        if method == "session/update" and self.session_id is not None and params.get("sessionId") == self.session_id:
            update = _object(params.get("update"))
            if update.get("sessionUpdate") == "config_option_update":
                failure = self._permission_check(update)
                if failure:
                    self.session_id = None
                    return _failure(failure)
        return super()._notification(method, params)


class CursorAdapter(_ConfiguredACPAdapter):
    # The CLI documents allowlist, auto-review and unrestricted independently
    # of the agent/plan/ask profile. ACP does not require it to expose this choice.
    _permission_option = "approvalMode"
    _safe_mode = "allowlist"
    _client_info = {"clientInfo": {"name": "better-ai", "version": "0.1.0"}}

    def _initialized(self, data: dict) -> Events:
        if type(data.get("protocolVersion")) is not int or data["protocolVersion"] != 1:
            return _failure("version")
        methods = data.get("authMethods")
        if not isinstance(methods, list) or not any(_object(method).get("id") == "cursor_login" for method in methods):
            return _failure("login")
        self._call("authenticate", {"methodId": "cursor_login"}, self._open_session)
        return ()


class DevinAdapter(_ConfiguredACPAdapter):
    # Devin documents normal mode, but does not promise that its ACP server
    # forwards tool prompts. Require an actual startup request for this session.
    _permission_option = "permission_mode"
    _safe_mode = "normal"

    def __init__(self, send: Send):
        super().__init__(send)
        self._forwarded_sessions: set[str] = set()

    def _opened(self, data: dict) -> Events:
        failure = self._permission_check(data)
        if failure:
            return _failure(failure)
        session_id = data.get("sessionId", self._resume)
        if not isinstance(session_id, str) or session_id not in self._forwarded_sessions:
            return _failure("no-approvals")
        return super()._opened(data)

    def _request(self, request_id: WireID, method: str, params: dict) -> Events:
        loading = any(called in ("session/load", "session/new") for called, _ in self._calls.values())
        if self.session_id is not None or not loading or method != "session/request_permission":
            return super()._request(request_id, method, params)
        session_id = params.get("sessionId")
        tool = _object(params.get("toolCall"))
        options = params.get("options")
        deny = (
            next(
                (
                    _text(_object(option).get("optionId"))
                    for option in options
                    if _object(option).get("kind") == "reject_once"
                ),
                "",
            )
            if isinstance(options, list)
            else ""
        )
        if (
            session_id_valid("devin", session_id)
            and _text(tool.get("toolCallId"))
            and tool.get("rawInput") is not None
            and deny
        ):
            self._forwarded_sessions.add(session_id)
            outcome = {"outcome": "selected", "optionId": deny}
        else:
            outcome = {"outcome": "cancelled"}
        self._result(request_id, {"outcome": outcome})
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
        self._call("account/read", {"refreshToken": False}, self._account)
        return ()

    def _account(self, data: dict) -> Events:
        if data.get("requiresOpenaiAuth") is not False and not _object(data.get("account")).get("type"):
            return _failure("login")
        self._open_thread()
        return ()

    def _open_thread(self) -> None:
        params = {"cwd": self._cwd, "approvalsReviewer": "user"}
        if self._resume:
            self._call("thread/resume", {**params, "threadId": self._resume}, self._opened)
        else:
            self._call("thread/start", params, self._opened)

    def _opened(self, data: dict) -> Events:
        sandbox = _object(data.get("sandbox"))
        if (
            data.get("approvalPolicy") not in ("untrusted", "on-request")
            or data.get("approvalsReviewer") != "user"
            or sandbox.get("type") not in ("workspaceWrite", "readOnly")
        ):
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
            if not turn_id:
                return ()
            closed = _expire_owned(self._approvals, turn_id)
            self._changes = {key: changes for key, changes in self._changes.items() if key[0] != turn_id}
            if turn_id != self.turn_id:
                return closed
            self.turn_id = None
            status, error = turn.get("status"), _object(turn.get("error"))
            outcome = {"completed": "normal", "interrupted": "stopped"}.get(
                _text(status), _error_kind(error, "crashed")
            )
            return (
                *closed,
                AdapterEvent("turn_ended", turn_id=turn_id, outcome=outcome, text=_text(error.get("message"))),
            )
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
        owner = _text(params.get("turnId")) or None
        self._approvals[request_id] = (owner, respond)
        return (
            AdapterEvent(
                "approval",
                request_id=request_id,
                tool=tool,
                arguments=arguments,
                options=("allow_once", "deny"),
                requester=owner,
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
    """Claude Code stream-json, including the host approval channel."""

    def __init__(self, send: Send, expected_session: str | None = None):
        self.send = send
        self.expected_session = expected_session
        self.session_id: str | None = None
        self._ids = itertools.count(1)
        self._initialize_id: str | None = None
        self._running = False
        self._approvals: dict[WireID, tuple[str | None, dict]] = {}

    def _control(self, subtype: str) -> str:
        request_id = f"page-{next(self._ids)}"
        self.send({"type": "control_request", "request_id": request_id, "request": {"subtype": subtype}})
        return request_id

    def open(self, cwd: str, resume: str | None) -> None:
        self._initialize_id = self._control("initialize")

    def prompt(self, text: str) -> None:
        if self.session_id is None:
            raise RuntimeError("Claude session is not open")
        self.send(
            {
                "type": "user",
                "message": {"role": "user", "content": text},
                "parent_tool_use_id": None,
                "session_id": "default",
            }
        )

    def cancel(self) -> None:
        self._control("interrupt")

    def _response(self, request_id: WireID, *, result: dict | None = None, error: str = "") -> None:
        payload = {"subtype": "error", "error": error} if error else {"subtype": "success", "response": result}
        self.send({"type": "control_response", "response": {"request_id": request_id, **payload}})

    def answer(self, request_id: WireID, choice: str, reason: str = "") -> bool:
        pending = self._approvals.pop(request_id, None)
        if pending is None:
            return False
        _, arguments = pending
        if choice == "allow_once":
            result = {"behavior": "allow", "updatedInput": arguments}
        else:
            result = {"behavior": "deny", "message": reason or "the page denied permission"}
        self._response(request_id, result=result)
        return True

    def _initialized(self, response: dict) -> Events:
        self._initialize_id = None
        if response.get("subtype") != "success":
            error = _text(response.get("error"))
            return _failure(_error_kind({"message": error}, "crashed"), error)
        data = _object(response.get("response"))
        if not version_supported("claude", _text(data.get("claude_code_version"))):
            return _failure("version")
        if data.get("current_permission_mode") != "default":
            return _failure("unsafe-mode")
        account = _object(data.get("account"))
        if not any(account.get(key) for key in ("subscriptionType", "apiKeySource", "tokenSource")):
            return _failure("login")
        if not session_id_valid("claude", self.expected_session):
            return _failure("crashed", "missing or invalid Claude session id")
        self.session_id = self.expected_session
        return (AdapterEvent("ready", session_id=self.session_id),)

    def _request(self, request_id: WireID, request: dict) -> Events:
        if request_id in self._approvals:
            self.answer(request_id, "deny", "duplicate request id")
            return (AdapterEvent("approval_closed", request_id=request_id, outcome="denied"),)
        if request.get("subtype") != "can_use_tool":
            self._response(request_id, error="permission denied")
            return ()
        tool, arguments = _text(request.get("tool_name")), request.get("input")
        if self.session_id is None or not tool or not isinstance(arguments, dict):
            self._response(request_id, result={"behavior": "deny", "message": "permission request is incomplete"})
            return ()
        owner = _text(request.get("agent_id")) or None
        self._approvals[request_id] = (owner, arguments)
        return (
            AdapterEvent(
                "approval",
                request_id=request_id,
                tool=tool,
                arguments=arguments,
                options=("allow_once", "deny"),
                requester=owner,
                tool_id=tool,
            ),
        )

    def receive(self, message: dict) -> Events:
        kind, subtype = message.get("type"), message.get("subtype")
        if kind == "control_response":
            response = _object(message.get("response"))
            if self._initialize_id is not None and response.get("request_id") == self._initialize_id:
                return self._initialized(response)
        if kind == "system" and subtype == "init":
            if message.get("permissionMode") != "default":
                self.session_id = None
                return _failure("unsafe-mode")
            if message.get("session_id") != self.session_id:
                self.session_id = None
                return _failure("crashed", "Claude started a different session")
        if kind == "system" and subtype in ("task_notification", "task_updated"):
            session_id = message.get("session_id")
            if session_id is not None and session_id != self.session_id:
                return ()
            status = (
                message.get("status") if subtype == "task_notification" else _object(message.get("patch")).get("status")
            )
            owner = _text(message.get("task_id"))
            if owner and status in ("completed", "failed", "stopped", "killed"):
                return _expire_owned(self._approvals, owner)
        if kind == "assistant" and message.get("parent_tool_use_id") is None:
            started = () if self._running else (AdapterEvent("turn_started"),)
            self._running = True
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
            return (*started, AdapterEvent("text", text=text))
        if kind == "result":
            self._running = False
            text = _text(message.get("result"))
            errors = message.get("errors")
            if not text and isinstance(errors, list):
                text = " ".join(error for error in errors if isinstance(error, str))
            if self.session_id is None and "no conversation found" in text.casefold():
                return _failure("missing-session")
            if subtype == "success" and message.get("is_error") is not True:
                outcome = "normal"
            elif subtype in ("interrupted", "error_interrupted"):
                outcome = "stopped"
            elif subtype in ("error_max_turns", "error_max_budget_usd"):
                outcome = "limit"
            else:
                outcome = _error_kind({"message": text}, "crashed")
            closed = _expire_owned(self._approvals, None)
            return (*closed, AdapterEvent("turn_ended", outcome=outcome, text=text))
        request_id = message.get("request_id")
        if _wire_id(request_id):
            if kind == "control_request":
                return self._request(request_id, _object(message.get("request")))
            if kind == "control_cancel_request" and self._approvals.pop(request_id, None) is not None:
                return (AdapterEvent("approval_closed", request_id=request_id, outcome="expired"),)
        return ()


class DroidAdapter(_RPCAdapter):
    """Factory stream-jsonrpc as published in @factory/droid-sdk 0.11.0."""

    _factory_api_version = "1.0.0"
    _factory_protocol_version = "1.332.0"
    _start_methods = ("droid.initialize_session", "droid.load_session")

    def __init__(self, send: Send):
        super().__init__(send)
        self._running = False

    def _request_id(self) -> str:
        return str(next(self._ids))

    def _send_frame(self, kind: str, **fields) -> None:
        self.send(
            {
                "jsonrpc": "2.0",
                "type": kind,
                "factoryApiVersion": self._factory_api_version,
                "factoryProtocolVersion": self._factory_protocol_version,
                **fields,
            }
        )

    def receive(self, message: dict) -> Events:
        request_id, method, kind = message.get("id"), message.get("method"), message.get("type")
        has_id = isinstance(request_id, str) and bool(request_id)
        frame = (
            (kind == "request" and has_id and isinstance(method, str))
            or (kind == "response" and has_id and method is None and ("result" in message) != ("error" in message))
            or (kind == "notification" and "id" not in message and isinstance(method, str))
        )
        version = _VERSION.fullmatch(_text(message.get("factoryProtocolVersion")))
        supported = version is not None and version[1] == "1" and tuple(map(int, version.groups())) >= (1, 332, 0)
        if (
            frame
            and supported
            and message.get("jsonrpc") == "2.0"
            and message.get("factoryApiVersion") == self._factory_api_version
        ):
            return super().receive(message)
        if has_id and method == "droid.request_permission":
            pending = self._approvals.pop(request_id, None)
            self._result(request_id, {"selectedOption": "cancel"})
            if pending is not None:
                return (AdapterEvent("approval_closed", request_id=request_id, outcome="denied"),)
        elif has_id and not isinstance(method, str) and request_id in self._calls:
            called, _ = self._calls.pop(request_id)
            if called in self._start_methods:
                return _failure("version", "unsupported Droid protocol envelope")
            return _failure("crashed", "invalid Droid response")
        elif has_id and isinstance(method, str):
            self._error(request_id, -32600, "invalid Droid request")
        return ()

    def open(self, cwd: str, resume: str | None) -> None:
        self._cwd = cwd
        self._resume = resume if session_id_valid("droid", resume) else None
        if self._resume:
            self._call("droid.load_session", {"sessionId": self._resume}, self._opened)
        else:
            self._new_session()

    def _new_session(self) -> None:
        self._call(
            "droid.initialize_session",
            {
                "machineId": "default",
                "cwd": self._cwd,
                "autonomyLevel": "off",
                "interactionMode": "auto",
            },
            self._opened,
        )

    def _opened(self, data: dict) -> Events:
        settings = _object(data.get("settings"))
        if settings.get("autonomyLevel") != "off" or settings.get("interactionMode") != "auto":
            return _failure("unsafe-mode")
        session_id = data.get("sessionId", self._resume)
        if not session_id_valid("droid", session_id):
            return _failure("crashed", "missing or invalid Droid session id")
        self.session_id = session_id
        pending = data.get("pendingPermissions")
        for request in pending if isinstance(pending, list) else ():
            request_id = _object(request).get("requestId")
            if isinstance(request_id, str) and request_id:
                self._result(request_id, {"selectedOption": "cancel", "comment": "previous page session ended"})
        return (AdapterEvent("ready", session_id=session_id),)

    def prompt(self, text: str) -> None:
        if self.session_id is None:
            raise RuntimeError("Droid session is not open")
        self._call("droid.add_user_message", {"text": text, "queuePlacement": "end_of_turn"}, lambda _: ())

    def cancel(self) -> None:
        if self.session_id is not None:
            self._call("droid.interrupt_session", {}, lambda _: ())

    def _call_failed(self, method: str, error: dict) -> Events:
        if method == "droid.load_session" and error.get("code") == -32004:
            self._resume = None
            self._new_session()
            return ()
        if error.get("code") == -32001:
            return _failure("login", _text(error.get("message")))
        return super()._call_failed(method, error)

    def _request(self, request_id: WireID, method: str, params: dict) -> Events:
        if method != "droid.request_permission":
            return super()._request(request_id, method, params)
        uses, options = params.get("toolUses"), params.get("options")
        if not isinstance(uses, list) or not isinstance(options, list):
            self._result(request_id, {"selectedOption": "cancel"})
            return ()
        calls = [_object(_object(use).get("toolUse")) for use in uses]
        names = [_text(call.get("name")) for call in calls]
        can_approve = (
            self.session_id is not None
            and names
            and all(names)
            and all(isinstance(call.get("input"), dict) for call in calls)
            and any(_object(option).get("value") == "proceed_once" for option in options)
            and all(_object(use).get("confirmationType") != "exit_spec_mode" for use in uses)
        )
        if not can_approve:
            self._result(request_id, {"selectedOption": "cancel"})
            return ()

        def respond(choice: str, reason: str) -> dict:
            if choice == "allow_once":
                return {"selectedOption": "proceed_once"}
            result = {"selectedOption": "cancel"}
            if reason:
                result["comment"] = reason
            return result

        owner = _text(params.get("workerSessionId")) or None
        self._approvals[request_id] = (owner, respond)
        return (
            AdapterEvent(
                "approval",
                request_id=request_id,
                tool=", ".join(names),
                arguments=uses,
                options=("allow_once", "deny"),
                requester=owner,
            ),
        )

    def _notification(self, method: str, params: dict) -> Events:
        if method != "droid.session_notification":
            return ()
        session_id = params.get("sessionId")
        if session_id is not None and session_id != self.session_id:
            return ()
        data = _object(params.get("notification"))
        kind = data.get("type")
        if kind == "permission_resolved" and _wire_id(data.get("requestId")):
            request_id = data["requestId"]
            if self._approvals.pop(request_id, None) is not None:
                return (AdapterEvent("approval_closed", request_id=request_id, outcome="expired"),)
        if kind == "child_session_settled" and (owner := _text(data.get("childSessionId"))):
            return _expire_owned(self._approvals, owner)
        if kind == "settings_updated":
            settings = _object(data.get("settings"))
            if settings.get("autonomyLevel", "off") != "off" or settings.get("interactionMode", "auto") != "auto":
                self.session_id = None
                return _failure("unsafe-mode")
        if kind == "assistant_text_delta":
            return (AdapterEvent("text", text=_text(data.get("textDelta"))),)
        if (
            kind == "droid_working_state_changed"
            and data.get("newState")
            in (
                "thinking",
                "streaming_assistant_message",
                "executing_tool",
                "waiting_for_tool_confirmation",
            )
            and not self._running
        ):
            self._running = True
            return (AdapterEvent("turn_started"),)
        if kind == "agent_turn_completed":
            self._running = False
            outcomes = {
                "completed": "normal",
                "permission_rejected": "normal",
                "cancelled": "stopped",
                "model_usage_exhausted": "limit",
                "model_rate_limited": "limit",
                "model_authentication_failed": "login",
                "no_approver_available": "no-approvals",
            }
            closed = _expire_owned(self._approvals, None)
            return (*closed, AdapterEvent("turn_ended", outcome=outcomes.get(_text(data.get("reason")), "crashed")))
        return ()
