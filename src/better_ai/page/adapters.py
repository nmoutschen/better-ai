"""Wire messages for page agent sessions. The driver owns processes and approval policy."""

from __future__ import annotations

import itertools
import json
import os
import re
import shutil
import subprocess
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
    codec_factory: Callable[..., ACPAdapter | CodexAdapter | ClaudeAdapter | DroidAdapter] | None = None
    text: str = ""
    chat: ChatMode | None = None

    @property
    def mode(self) -> str | None:
        return self.chat.mode if self.chat else None

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
            return ClaudeAdapter(send, expected, self.chat)
        return self.codec_factory(send, self.chat)


_REAL_BROWSER_TOOLS = (
    "mcp__claude-in-chrome",
    "mcp__Claude_Browser",
    "mcp__remote-devices__Claude_Browser",
    "mcp__computer-use",
    "mcp__remote-devices__computer",
)


@dataclass(frozen=True)
class Fact:
    text: str
    source: str


@dataclass(frozen=True)
class ChatFlag:
    """A flag the user's chat can start with, the mode it means, and how the page session is given it."""

    names: tuple[str, ...]
    value: str | None
    mode: str
    source: str
    argv: tuple[str, ...] = ()  # added to the page session's command line
    protocol: Any = None  # set in the protocol: an option value, or Codex thread parameters
    reported: bool = True  # whether the session reports this mode back, so it can be checked


@dataclass(frozen=True)
class ReportedMode:
    """A mode value the harness reports for its session, and the mode shown for it."""

    field: str
    value: str
    mode: str | None  # None: the value leaves the mode to another field (Codex)
    source: str


@dataclass(frozen=True)
class ConfigPath:
    """A harness configuration location: ~/ for home, / for system, otherwise relative to a project."""

    path: str
    source: str


@dataclass(frozen=True)
class Harness:
    display: str  # the name every notice uses, as the user knows the harness
    set_by: Fact
    chat_flags: tuple[ChatFlag, ...]
    reported: tuple[ReportedMode, ...]
    config: tuple[ConfigPath, ...]
    flags_at: int | None = None  # where chat flags go in the page command; None appends them


_CLAUDE_HELP = "`claude --help` (2.1.332)"
_CLAUDE_WIRE = "tests/fixtures/page_wire/claude_2_1_332.json"
_CODEX_HELP = "`codex --help` (0.172.0)"
_CODEX_SCHEMA = "`codex app-server generate-json-schema` (0.172.0)"
_CURSOR_FLAGS = "https://cursor.com/docs/cli/reference/parameters"
_CURSOR_CONFIG = "https://cursor.com/docs/cli/reference/configuration"
_DEVIN_FLAGS = "https://docs.devin.ai/cli/reference/commands"
_DEVIN_MODES = "https://docs.devin.ai/cli/reference/permissions"
_DROID_FLAGS = "https://docs.factory.com/reference/cli-reference"
_DROID_SETTINGS = "https://docs.factory.com/cli/configuration/settings"
_DROID_SDK = "https://www.npmjs.com/package/@factory/droid-sdk/v/0.11.0"
_OPENCODE_HELP = "`opencode --help` (2.4.1)"
_OPENCODE_CONFIG = "https://opencode.ai/docs/config/"


def _claude_mode(value: str, mode: str) -> ChatFlag:
    return ChatFlag(("--permission-mode",), value, mode, _CLAUDE_HELP, argv=("--permission-mode", value))


def _codex_config(value: str, mode: str, params: dict) -> ChatFlag:
    return ChatFlag(("-c", "--config"), value, mode, _CODEX_SCHEMA + " Config", protocol=params)


def _devin_mode(value: str, mode: str, canonical: str, argv: tuple[str, ...] = ()) -> ChatFlag:
    return ChatFlag(("--permission-mode",), value, mode, _DEVIN_FLAGS, argv=argv, protocol=canonical)


# Every harness fact the adapters rely on, each with where it comes from. chat_mode, the mode maps and
# _CONFIG_PATH are generated from this table only. Modes without one of the four common names (manual,
# accept edits, auto, skip approvals) are shown by their own name.
HARNESS_FACTS: dict[str, Harness] = {
    "claude": Harness(
        display="Claude Code",
        set_by=Fact("the command line: the chat's own permission flag, passed on as it is", _CLAUDE_HELP),
        chat_flags=(
            _claude_mode("manual", "manual"),
            _claude_mode("acceptEdits", "accept edits"),
            _claude_mode("auto", "auto"),
            _claude_mode("bypassPermissions", "skip approvals"),
            _claude_mode("dontAsk", "don't ask"),
            _claude_mode("plan", "plan"),
            ChatFlag(
                ("--dangerously-skip-permissions",),
                None,
                "skip approvals",
                _CLAUDE_HELP,
                argv=("--dangerously-skip-permissions",),
            ),
        ),
        reported=(
            ReportedMode("permission mode", "default", "manual", _CLAUDE_WIRE + " initialize_default"),
            ReportedMode("permission mode", "manual", "manual", _CLAUDE_HELP),
            ReportedMode("permission mode", "acceptEdits", "accept edits", _CLAUDE_HELP),
            ReportedMode("permission mode", "auto", "auto", _CLAUDE_WIRE + " initialize_auto"),
            ReportedMode("permission mode", "bypassPermissions", "skip approvals", _CLAUDE_HELP),
            ReportedMode("permission mode", "dontAsk", "don't ask", _CLAUDE_HELP),
            ReportedMode("permission mode", "plan", "plan", _CLAUDE_HELP),
        ),
        config=(
            ConfigPath("~/.claude/", "https://code.claude.com/docs/en/settings"),
            ConfigPath("~/.claude.json", "https://code.claude.com/docs/en/settings"),
            ConfigPath(".claude/", "https://code.claude.com/docs/en/settings"),
            ConfigPath(".mcp.json", "https://code.claude.com/docs/en/mcp"),
            ConfigPath("/Library/Application Support/ClaudeCode/", "https://code.claude.com/docs/en/managed-settings"),
            ConfigPath("/etc/claude-code/", "https://code.claude.com/docs/en/managed-settings"),
        ),
    ),
    "codex": Harness(
        display="Codex",
        set_by=Fact(
            "the protocol: thread/start approvalPolicy and approvalsReviewer", _CODEX_SCHEMA + " ThreadStartParams"
        ),
        chat_flags=(
            ChatFlag(("--approve-for-me",), None, "auto", _CODEX_HELP, protocol={"approvalsReviewer": "auto_review"}),
            ChatFlag(
                ("--dangerously-bypass-approvals-and-sandbox",),
                None,
                "skip approvals",
                _CODEX_HELP,
                protocol={"approvalPolicy": "never"},
            ),
            ChatFlag(
                ("-a", "--ask-for-approval"),
                "on-request",
                "manual",
                _CODEX_HELP,
                protocol={"approvalPolicy": "on-request"},
            ),
            ChatFlag(
                ("-a", "--ask-for-approval"),
                "never",
                "skip approvals",
                _CODEX_HELP,
                protocol={"approvalPolicy": "never"},
            ),
            _codex_config("approval_policy=untrusted", "manual", {"approvalPolicy": "untrusted"}),
            _codex_config("approval_policy=on-request", "manual", {"approvalPolicy": "on-request"}),
            _codex_config("approval_policy=never", "skip approvals", {"approvalPolicy": "never"}),
            _codex_config("approvals_reviewer=user", "manual", {"approvalsReviewer": "user"}),
            _codex_config("approvals_reviewer=auto_review", "auto", {"approvalsReviewer": "auto_review"}),
            _codex_config("approvals_reviewer=guardian_subagent", "auto", {"approvalsReviewer": "guardian_subagent"}),
        ),
        reported=(
            ReportedMode("approvalPolicy", "untrusted", None, _CODEX_SCHEMA + " AskForApproval"),
            ReportedMode("approvalPolicy", "on-request", None, _CODEX_SCHEMA + " AskForApproval"),
            ReportedMode("approvalPolicy", "never", "skip approvals", _CODEX_HELP),
            ReportedMode("approvalsReviewer", "user", "manual", _CODEX_SCHEMA + " ApprovalsReviewer"),
            ReportedMode("approvalsReviewer", "auto_review", "auto", _CODEX_SCHEMA + " ApprovalsReviewer"),
            ReportedMode("approvalsReviewer", "guardian_subagent", "auto", _CODEX_SCHEMA + " ApprovalsReviewer"),
        ),
        config=(
            ConfigPath("~/.codex/", _CODEX_HELP),
            ConfigPath(".codex/", "https://learn.chatgpt.com/docs/hooks"),
        ),
    ),
    "cursor": Harness(
        display="Cursor",
        set_by=Fact(
            "the command line: --force, a global option; approvalMode is only reported (unverified: no recorded ACP session; an unknown value fails closed)",
            _CURSOR_FLAGS,
        ),
        chat_flags=(
            ChatFlag(
                ("-f", "--force", "--yolo"), None, "skip approvals", _CURSOR_FLAGS, argv=("--force",), reported=False
            ),
        ),
        reported=(
            ReportedMode("approvalMode", "allowlist", "manual", _CURSOR_CONFIG),
            ReportedMode("approvalMode", "auto-review", "auto", _CURSOR_CONFIG),
            ReportedMode("approvalMode", "unrestricted", "unrestricted", _CURSOR_CONFIG),
        ),
        config=(
            ConfigPath("~/.cursor/", _CURSOR_CONFIG),
            ConfigPath(".cursor/", _CURSOR_CONFIG),
        ),
        flags_at=1,
    ),
    "devin": Harness(
        display="Devin",
        set_by=Fact(
            "the protocol: session/set_config_option permission_mode (unverified: the docs do not describe ACP; an unknown value fails closed)",
            _DEVIN_MODES,
        ),
        chat_flags=(
            _devin_mode("normal", "manual", "normal"),
            _devin_mode("auto", "manual", "normal"),
            _devin_mode("accept-edits", "accept edits", "accept-edits"),
            _devin_mode("smart", "auto", "smart"),
            _devin_mode("dangerous", "skip approvals", "dangerous"),
            _devin_mode("yolo", "skip approvals", "dangerous"),
            _devin_mode("bypass", "skip approvals", "dangerous"),
            # autonomous requires --sandbox, so the page session gets it too.
            _devin_mode("autonomous", "autonomous", "autonomous", argv=("--sandbox",)),
        ),
        reported=(
            ReportedMode("permission_mode", "normal", "manual", _DEVIN_FLAGS),
            ReportedMode("permission_mode", "auto", "manual", _DEVIN_FLAGS),
            ReportedMode("permission_mode", "accept-edits", "accept edits", _DEVIN_FLAGS),
            ReportedMode("permission_mode", "smart", "auto", _DEVIN_FLAGS),
            ReportedMode("permission_mode", "dangerous", "skip approvals", _DEVIN_FLAGS),
            ReportedMode("permission_mode", "yolo", "skip approvals", _DEVIN_FLAGS),
            ReportedMode("permission_mode", "bypass", "skip approvals", _DEVIN_FLAGS),
            ReportedMode("permission_mode", "autonomous", "autonomous", _DEVIN_FLAGS),
        ),
        config=(
            ConfigPath("~/.config/devin/config.json", _DEVIN_MODES),
            ConfigPath(".devin/", _DEVIN_MODES),
        ),
        flags_at=1,
    ),
    "droid": Harness(
        display="Droid",
        set_by=Fact(
            "the protocol: droid.initialize_session autonomyLevel; --skip-permissions-unsafe on the command line",
            _DROID_SDK,
        ),
        chat_flags=(
            *(ChatFlag(("--auto",), level, level, _DROID_FLAGS, protocol=level) for level in ("low", "medium", "high")),
            ChatFlag(
                ("--skip-permissions-unsafe",),
                None,
                "skip approvals",
                _DROID_FLAGS,
                argv=("--skip-permissions-unsafe",),
                reported=False,
            ),
        ),
        reported=tuple(
            ReportedMode("autonomyLevel", level, "manual" if level == "off" else level, _DROID_SETTINGS)
            for level in ("off", "low", "medium", "high")
        ),
        config=(
            ConfigPath("~/.factory/", _DROID_SETTINGS),
            ConfigPath(".factory/", _DROID_SETTINGS),
        ),
    ),
    "opencode": Harness(
        display="OpenCode",
        set_by=Fact("no documented way: opencode acp takes no --auto; the page asks for edit and bash", _OPENCODE_HELP),
        chat_flags=(ChatFlag(("--auto",), None, "skip approvals", _OPENCODE_HELP),),
        reported=(),
        config=(
            ConfigPath("~/.config/opencode/", _OPENCODE_CONFIG),
            ConfigPath("opencode.json", _OPENCODE_CONFIG),
            ConfigPath("opencode.jsonc", _OPENCODE_CONFIG),
            ConfigPath(".opencode/", _OPENCODE_CONFIG),
            ConfigPath("/etc/opencode/", _OPENCODE_CONFIG),
            ConfigPath("/Library/Application Support/opencode/", _OPENCODE_CONFIG),
            ConfigPath("ai.opencode.managed.plist", _OPENCODE_CONFIG),
        ),
    ),
}


# The top-level messages each protocol defines. A message outside these is reported as "unknown", so that a
# renamed message is seen (D11); a known message the adapter does not use is ignored.
# Codex: ServerNotification and ServerRequest in `codex app-server generate-json-schema` (0.172.0).
_CODEX_NOTIFICATIONS = frozenset(
    """
    account/gatewayOAuth/changed
    account/login/completed
    account/rateLimits/updated
    account/updated
    app/list/updated
    autoApprovalReview/strictReviewRequired
    command/exec/outputDelta
    configWarning
    deprecationNotice
    error
    externalAgentConfig/import/completed
    externalAgentConfig/import/progress
    fs/changed
    fuzzyFileSearch/sessionCompleted
    fuzzyFileSearch/sessionUpdated
    guardianWarning
    hook/completed
    hook/started
    item/agentMessage/delta
    item/autoApprovalReview/completed
    item/autoApprovalReview/started
    item/commandExecution/outputDelta
    item/commandExecution/terminalInteraction
    item/completed
    item/fileChange/outputDelta
    item/fileChange/patchUpdated
    item/mcpToolCall/progress
    item/plan/delta
    item/reasoning/summaryPartAdded
    item/reasoning/summaryTextDelta
    item/reasoning/textDelta
    item/started
    mcpServer/event/stream/notification
    mcpServer/oauthLogin/completed
    mcpServer/startupStatus/updated
    model/rerouted
    model/safetyBuffering/updated
    model/verification
    modelProvider/authRecoveryCompleted
    modelProvider/authRecoveryStarted
    process/exited
    process/outputDelta
    project/changed
    remoteControl/status/changed
    serverRequest/resolved
    skills/changed
    thread/archived
    thread/attachment/updated
    thread/closed
    thread/compacted
    thread/deleted
    thread/environment/connected
    thread/environment/disconnected
    thread/goal/cleared
    thread/goal/updated
    thread/name/updated
    thread/prediction/updated
    thread/project/updated
    thread/queue/changed
    thread/readState/changed
    thread/realtime/closed
    thread/realtime/error
    thread/realtime/item/completed
    thread/realtime/item/started
    thread/realtime/item/transcript/delta
    thread/realtime/itemAdded
    thread/realtime/outputAudio/delta
    thread/realtime/sdp
    thread/realtime/started
    thread/realtime/transcript/delta
    thread/realtime/transcript/done
    thread/reverted
    thread/search/partial
    thread/section/changed
    thread/settings/updated
    thread/started
    thread/status/changed
    thread/tokenUsage/updated
    thread/unarchived
    turn/completed
    turn/diff/updated
    turn/moderationMetadata
    turn/plan/updated
    turn/started
    warning
    windows/worldWritableWarning
    windowsSandbox/setupCompleted
    """.split()
)
_CODEX_REQUESTS = frozenset(
    """
    account/chatgptAuthTokens/refresh
    applyPatchApproval
    attestation/generate
    execCommandApproval
    item/commandExecution/requestApproval
    item/fileChange/requestApproval
    item/permissions/requestApproval
    item/tool/call
    item/tool/requestUserInput
    mcpServer/elicitation/request
    """.split()
)
# ACP v1 client methods (https://agentclientprotocol.com/protocol/schema); names starting with "_" are
# extensions, which ACP says to ignore (https://agentclientprotocol.com/protocol/extensibility).
_ACP_NOTIFICATIONS = frozenset({"session/update"})
_ACP_REQUESTS = frozenset(
    {
        "session/request_permission",
        "fs/read_text_file",
        "fs/write_text_file",
        "terminal/create",
        "terminal/output",
        "terminal/release",
        "terminal/wait_for_exit",
        "terminal/kill",
    }
)
# Cursor's ACP extensions (https://cursor.com/docs/cli/acp); its two requests are still refused (S33).
_CURSOR_NOTIFICATIONS = _ACP_NOTIFICATIONS | {"cursor/update_todos", "cursor/task", "cursor/generate_image"}
_CURSOR_REQUESTS = _ACP_REQUESTS | {"cursor/ask_question", "cursor/create_plan"}
# Droid: @factory/droid-sdk 0.11.0.
_DROID_NOTIFICATIONS = frozenset({"droid.session_notification"})
_DROID_REQUESTS = frozenset({"droid.request_permission", "droid.ask_user"})
# Claude Code stream-json: the SDKMessage union (https://code.claude.com/docs/en/agent-sdk/typescript) and
# the control frames of tests/fixtures/page_wire/claude_2_1_332.json.
_CLAUDE_TYPES = frozenset(
    {
        "assistant",
        "user",
        "result",
        "system",
        "conversation_reset",
        "stream_event",
        "tool_progress",
        "auth_status",
        "rate_limit_event",
        "prompt_suggestion",
        "tool_use_summary",
        "keep_alive",
        "control_request",
        "control_response",
        "control_cancel_request",
    }
)


def _unknown(name: Any) -> Events:
    return (AdapterEvent("unknown", text=_text(name) or "message without a type"),)


def _reported_modes(name: str, field: str) -> dict[str, str | None]:
    return {item.value: item.mode for item in HARNESS_FACTS[name].reported if item.field == field}


@dataclass(frozen=True)
class ChatMode:
    """The chat's approval mode and how the page session is given it."""

    mode: str
    argv: tuple[str, ...] = ()
    protocol: Any = None
    reported: bool = True


def _chat_value(flag: ChatFlag, value: str) -> str:
    # Codex parses a -c value as TOML: key="value" and key = value are the same setting.
    return value.replace(" ", "").replace('"', "").replace("'", "") if "-c" in flag.names else value


def _chat_flags(name: str, argv: tuple[str, ...]) -> list[ChatFlag]:
    """The table's chat flags found in a command line, in their order."""
    found = []
    for index, arg in enumerate(argv):
        for flag in HARNESS_FACTS[name].chat_flags:
            for spelling in flag.names:
                if flag.value is None:
                    matched = arg == spelling
                elif arg == spelling:
                    matched = index + 1 < len(argv) and _chat_value(flag, argv[index + 1]) == flag.value
                else:
                    matched = (
                        arg.startswith(f"{spelling}=") and _chat_value(flag, arg[len(spelling) + 1 :]) == flag.value
                    )
                if matched:
                    found.append(flag)
    return found


def _resolve_chat(name: str, argv: tuple[str, ...] | list[str]) -> ChatMode | None:
    flags = _chat_flags(name, tuple(argv))
    if not flags:
        return None
    # The chat's own flags, in its order; the last one names the mode, as the harness reads them.
    passed = tuple(token for flag in flags for token in flag.argv)
    protocol = flags[-1].protocol
    if isinstance(protocol, dict):
        protocol = {
            key: value for flag in flags if isinstance(flag.protocol, dict) for key, value in flag.protocol.items()
        }
    return ChatMode(flags[-1].mode, passed, protocol, flags[-1].reported)


def _chat(name: str, chat: ChatMode | str | None) -> ChatMode | None:
    """A chat mode given by its shown name (as tests and older callers do) becomes the table's first entry for it."""
    if chat is None or isinstance(chat, ChatMode):
        return chat
    flag = next(flag for flag in HARNESS_FACTS[name].chat_flags if flag.mode == chat)
    return ChatMode(flag.mode, flag.argv, flag.protocol, flag.reported)


def chat_mode(name: str, argv: tuple[str, ...] | list[str]) -> str | None:
    """The approval mode the user's chat session was started in, from its own command line, or None."""
    chat = _resolve_chat(name, argv)
    return chat.mode if chat else None


def _config_pattern() -> re.Pattern:
    parts = []
    for harness in HARNESS_FACTS.values():
        for location in harness.config:
            path = location.path.removeprefix("~/")
            folder = path.endswith("/")
            body = r"[/\\]".join(
                r"(?:\\?\s)".join(re.escape(word) for word in segment.split(" "))
                for segment in path.rstrip("/").split("/")
            )
            # A folder matches itself and anything under it; a file matches only itself.
            parts.append(rf"(?<![\w.-]){body}(?:[/\\]|(?![\w.-]))" if folder else rf"(?<![\w.-]){body}(?![\w.-])")
    return re.compile("|".join(dict.fromkeys(parts)), re.IGNORECASE)


_CONFIG_PATH = _config_pattern()


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
            "--replay-user-messages",
            "--permission-prompts",
            "host",
            "--permission-prompt-tool",
            "stdio",
            # The page session never drives the user's own browser or desktop. Headless browsers stay.
            "--no-chrome",
            "--disallowed-tools",
            ",".join(_REAL_BROWSER_TOOLS),
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


def chat_argv(name: str, pid: int | None = None, run: Callable = subprocess.run) -> tuple[str, ...]:
    """The command line of the harness process that runs this one, found among its ancestors; () if none."""
    pid = os.getppid() if pid is None else pid
    binary = _HARNESSES[name][0][0]
    for _ in range(12):
        try:
            shown = run(["ps", "-ww", "-o", "ppid=,command=", "-p", str(pid)], capture_output=True, text=True)
        except OSError:
            return ()
        fields = shown.stdout.strip().split(None, 1)
        if shown.returncode or len(fields) != 2 or not fields[0].isdigit():
            return ()
        argv = tuple(fields[1].split())
        # A harness run by node shows the script as the second word.
        if any(os.path.basename(word) == binary for word in argv[:2]):
            return argv
        pid = int(fields[0])
        if pid <= 1:
            return ()
    return ()


def candidate(
    requested: str,
    env: Mapping[str, str],
    which: Callable[[str], str | None] = shutil.which,
    chat_argv: tuple[str, ...] | list[str] = (),
) -> Candidate:
    """Return metadata without launching a process or reading harness settings."""
    name = requested
    if requested == "auto":
        name = next((name for name, (_, markers) in _HARNESSES.items() if any(env.get(k) for k in markers)), "")
        if not name:
            return Candidate(
                None,
                (),
                "no-harness",
                text="No supported harness found. Run serve from Claude Code, Codex, Cursor, OpenCode, Droid or Devin.",
            )
    if name not in _HARNESSES:
        raise ValueError(f"unknown harness: {name}")
    command, _ = _HARNESSES[name]
    executable = which(command[0])
    if executable is None:
        return Candidate(
            name, (), "not-installed", text=f"{display_name(name)} is not installed. Install it, then serve again."
        )
    chat = _resolve_chat(name, chat_argv)
    at = HARNESS_FACTS[name].flags_at or len(command)
    argv = (executable, *command[1:at], *(chat.argv if chat else ()), *command[at:])
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
            return Candidate(
                name,
                argv,
                "unsafe-mode",
                text="OpenCode's inline configuration is not valid. Fix OPENCODE_CONFIG_CONTENT, then serve again.",
            )
    return Candidate(name, argv, None, factories[name], chat=chat)


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


def display_name(name: str) -> str:
    """The harness's name as the user knows it (Claude Code, not claude); an unknown id as it is."""
    facts = HARNESS_FACTS.get(name)
    return facts.display if facts else name


def version_problem(name: str, reported: str) -> str:
    match = None if name == "cursor" else _VERSION.search(reported)
    found = match.group(0) if match else reported.strip()[:80] or "no version"
    needed = ".".join(str(part) for part in _MIN_VERSION[name])
    return f"{display_name(name)} reported {found}. Version {needed} or later is required."


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
    mode: str | None = None
    uuid: str | None = None


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


def _touches_config(data: Any) -> bool:
    """Whether a request names a path under a harness's own configuration folder."""
    if isinstance(data, str):
        return _CONFIG_PATH.search(data) is not None
    if isinstance(data, dict):
        return any(_touches_config(value) for value in data.values())
    if isinstance(data, list):
        return any(_touches_config(value) for value in data)
    return False


def _choices(session: bool, arguments: Any) -> tuple[str, ...]:
    """Allow for this session is offered where the harness has such a scope, never for its own config."""
    if session and not _touches_config(arguments):
        return ("allow_once", "allow_session", "deny")
    return ("allow_once", "deny")


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
    _name = "the harness"
    _harness = ""
    _notifications: frozenset[str] = frozenset()
    _requests: frozenset[str] = frozenset()

    def __init__(self, send: Send, chat_mode: ChatMode | str | None = None):
        self.send = send
        self.chat = _chat(self._harness, chat_mode)
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
                if "id" in message:
                    return ()
                return (
                    self._notification(method, params) if self._known(method, self._notifications) else _unknown(method)
                )
            if request_id in self._approvals:
                # A second request cannot change what an open approval represents.
                self.answer(request_id, "deny", "duplicate request id")
                return (AdapterEvent("approval_closed", request_id=request_id, outcome="denied"),)
            events = self._request(request_id, method, params)
            return events if self._known(method, self._requests) else (*events, *_unknown(method))
        if _wire_id(request_id) and request_id in self._calls:
            called, done = self._calls.pop(request_id)
            if "error" in message:
                error = _object(message["error"])
                return self._call_failed(called, error)
            return done(_object(message.get("result")))
        return ()

    def _call_failed(self, method: str, error: dict) -> Events:
        return _failure(_error_kind(error, "crashed"), _text(error.get("message")))

    def _known(self, method: str, known: frozenset[str]) -> bool:
        return method in known

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

    _name = "the agent"
    _mode = "manual"
    _client_info: dict = {}
    _notifications = _ACP_NOTIFICATIONS
    _requests = _ACP_REQUESTS

    def _known(self, method: str, known: frozenset[str]) -> bool:
        return method in known or method.startswith("_")

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
        return (AdapterEvent("ready", session_id=session_id, mode=self._mode),)

    def prompt(self, text: str, uuid: str | None = None) -> None:
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
            if name in ("allow_once", "allow_always", "reject_once") and isinstance(item.get("optionId"), str):
                options[name] = item["optionId"]

        def respond(choice: str, _reason: str) -> dict:
            wanted = {"allow_once": "allow_once", "allow_session": "allow_always"}.get(choice, "reject_once")
            option_id = options.get(wanted) or (options.get("allow_once") if choice == "allow_session" else None)
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
                options=_choices("allow_always" in options, arguments),
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
    _harness = "opencode"

    def _initialized(self, data: dict) -> Events:
        version = _text(_object(data.get("agentInfo")).get("version"))
        if not version_supported("opencode", version):
            return _failure("version", version_problem("opencode", version))
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
    """Read the peer's approval mode from its config option, and set it to the chat's mode."""

    _permission_option: str

    def _reported(self, data: dict) -> tuple[str | None, str | None]:
        """The reported value and the failure kind, if any."""
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
            return None, "no-approvals"
        if values[0] not in _reported_modes(self._harness, self._permission_option):
            return None, "unsafe-mode"
        return values[0], None

    def _accept(self, value: str) -> None:
        self._value = value
        modes = _reported_modes(self._harness, self._permission_option)
        # A mode set on the command line is not one the option reports, so the chat's name is shown.
        self._mode = self.chat.mode if self.chat and not self.chat.reported else modes[value]

    def _opened(self, data: dict) -> Events:
        value, failure = self._reported(data)
        if failure:
            return _failure(failure)
        session_id = data.get("sessionId", self._resume)
        wanted = self.chat.protocol if self.chat else None
        modes = _reported_modes(self._harness, self._permission_option)
        if wanted is not None and modes[value] != modes.get(wanted):
            if not session_id_valid("opencode", session_id):
                return _failure("unsafe-mode")
            self._opening = {**data, "sessionId": session_id}
            self._call(
                "session/set_config_option",
                {"sessionId": session_id, "configId": self._permission_option, "value": wanted},
                self._configured,
            )
            return ()
        self._accept(value)
        return self._finish(data)

    def _configured(self, result: dict) -> Events:
        value, failure = self._reported(result)
        modes = _reported_modes(self._harness, self._permission_option)
        if failure or modes[value] != modes.get(self.chat.protocol):
            return _failure(failure or "unsafe-mode")
        self._accept(value)
        return self._finish({**self._opening, **result})

    def _finish(self, data: dict) -> Events:
        return super()._opened(data)

    def _notification(self, method: str, params: dict) -> Events:
        if method == "session/update" and self.session_id is not None and params.get("sessionId") == self.session_id:
            update = _object(params.get("update"))
            if update.get("sessionUpdate") == "config_option_update":
                value, failure = self._reported(update)
                modes = _reported_modes(self._harness, self._permission_option)
                if failure or modes[value] != modes[self._value]:
                    self.session_id = None
                    return _failure(failure or "unsafe-mode")
        return super()._notification(method, params)


class CursorAdapter(_ConfiguredACPAdapter):
    # The CLI documents allowlist, auto-review and unrestricted independently
    # of the agent/plan/ask profile. ACP does not require it to expose this choice.
    _harness = "cursor"
    _notifications = _CURSOR_NOTIFICATIONS
    _requests = _CURSOR_REQUESTS
    _permission_option = "approvalMode"
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
    _harness = "devin"
    _permission_option = "permission_mode"

    def __init__(self, send: Send, chat_mode: ChatMode | str | None = None):
        super().__init__(send, chat_mode)
        self._forwarded_sessions: set[str] = set()

    def _finish(self, data: dict) -> Events:
        session_id = data.get("sessionId", self._resume)
        if not isinstance(session_id, str) or session_id not in self._forwarded_sessions:
            return _failure("no-approvals")
        return super()._finish(data)

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

    _name = "codex"
    _harness = "codex"
    _notifications = _CODEX_NOTIFICATIONS
    _requests = _CODEX_REQUESTS

    def open(self, cwd: str, resume: str | None) -> None:
        self._cwd = cwd
        self._resume = resume if session_id_valid("codex", resume) else None
        self._call("initialize", {"clientInfo": {"name": "better-ai", "version": "0.1.0"}}, self._initialized)
        self._changes: dict[tuple[str, str], list] = {}

    def _initialized(self, data: dict) -> Events:
        agent = _text(data.get("userAgent"))
        if not version_supported("codex", agent):
            return _failure("version", version_problem("codex", agent))
        self._notify("initialized", {})
        self._call("account/read", {"refreshToken": False}, self._account)
        return ()

    def _account(self, data: dict) -> Events:
        if data.get("requiresOpenaiAuth") is not False and not _object(data.get("account")).get("type"):
            return _failure("login")
        self._open_thread()
        return ()

    def _open_thread(self) -> None:
        # No sandbox or network setting: the page session runs under the user's own Codex configuration.
        params = {"cwd": self._cwd, **(self.chat.protocol if self.chat else {})}
        if self._resume:
            self._call("thread/resume", {**params, "threadId": self._resume}, self._opened)
        else:
            self._call("thread/start", params, self._opened)

    def _opened(self, data: dict) -> Events:
        reviewer, policy = data.get("approvalsReviewer"), data.get("approvalPolicy")
        reviewers, policies = _reported_modes("codex", "approvalsReviewer"), _reported_modes("codex", "approvalPolicy")
        if not isinstance(reviewer, str) or not isinstance(policy, str) or reviewer not in reviewers:
            return _failure("unsafe-mode")
        if policy not in policies:
            return _failure("unsafe-mode")
        # The thread must run with every setting the chat's flags gave it.
        if self.chat and any(data.get(key) != value for key, value in self.chat.protocol.items()):
            return _failure("unsafe-mode")
        mode = policies[policy] or reviewers[reviewer]
        session_id = _object(data.get("thread")).get("id")
        if not session_id_valid("codex", session_id):
            return _failure("crashed", "missing or invalid Codex thread id")
        self.session_id = session_id
        return (AdapterEvent("ready", session_id=session_id, mode=mode),)

    def prompt(self, text: str, uuid: str | None = None) -> None:
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
        if method == "item/autoApprovalReview/completed" and _object(params.get("review")).get("status") == "denied":
            action = _object(params.get("action"))
            tool = "Command" if action.get("type") == "command" else _text(action.get("type")) or "Action"
            return (
                AdapterEvent(
                    "blocked", tool=tool, arguments=action, text=_text(_object(params.get("review")).get("rationale"))
                ),
            )
        if method == "serverRequest/resolved" and _wire_id(params.get("requestId")):
            request_id = params["requestId"]
            if self._approvals.pop(request_id, None) is not None:
                return (
                    AdapterEvent(
                        "approval_closed", request_id=request_id, outcome="expired", text="codex resolved the request"
                    ),
                )
        return ()

    def _request(self, request_id: WireID, method: str, params: dict) -> Events:
        if method == "item/permissions/requestApproval":
            self._result(request_id, {"permissions": {}, "scope": "turn"})
            return ()
        if method == "item/commandExecution/requestApproval":
            tool = "Command"
            complete = bool(_text(params.get("command"))) and not params.get("networkApprovalContext")
            arguments = params
            decisions = params.get("availableDecisions")
            session = isinstance(decisions, list) and "acceptForSession" in decisions
        elif method == "item/fileChange/requestApproval":
            tool = "File change"
            changes = self._changes.get((_text(params.get("turnId")), _text(params.get("itemId"))))
            complete = bool(changes) and not params.get("grantRoot")
            arguments = {**params, "changes": changes}
            session = True
        else:
            return super()._request(request_id, method, params)
        options = _choices(session, arguments)

        def respond(choice: str, _reason: str) -> dict:
            if choice == "allow_session" and "allow_session" in options:
                return {"decision": "acceptForSession"}
            return {"decision": "accept" if choice in ("allow_once", "allow_session") else "decline"}

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
                options=options,
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

    _name = "claude"

    def __init__(self, send: Send, expected_session: str | None = None, chat_mode: ChatMode | str | None = None):
        self.send = send
        self.expected_session = expected_session
        self.chat = _chat("claude", chat_mode)
        self.mode: str | None = None
        self._pending: list[AdapterEvent] = []
        self.session_id: str | None = None
        self._ids = itertools.count(1)
        self._initialize_id: str | None = None
        self._running = False
        self._approvals: dict[WireID, tuple[str | None, tuple[dict, list]]] = {}
        self._asked: set[str] = set()
        self._reasons: dict[str, str] = {}

    def _control(self, subtype: str) -> str:
        request_id = f"page-{next(self._ids)}"
        self.send({"type": "control_request", "request_id": request_id, "request": {"subtype": subtype}})
        return request_id

    def open(self, cwd: str, resume: str | None) -> None:
        self._initialize_id = self._control("initialize")

    def prompt(self, text: str, uuid: str | None = None) -> None:
        if self.session_id is None:
            raise RuntimeError("Claude session is not open")
        message = {
            "type": "user",
            "message": {"role": "user", "content": text},
            "parent_tool_use_id": None,
            "session_id": "default",
        }
        if uuid:
            message["uuid"] = uuid
        self.send(message)

    def cancel(self) -> None:
        self._control("interrupt")

    def _response(self, request_id: WireID, *, result: dict | None = None, error: str = "") -> None:
        payload = {"subtype": "error", "error": error} if error else {"subtype": "success", "response": result}
        self.send({"type": "control_response", "response": {"request_id": request_id, **payload}})

    def answer(self, request_id: WireID, choice: str, reason: str = "") -> bool:
        pending = self._approvals.pop(request_id, None)
        if pending is None:
            return False
        _, (arguments, scope) = pending
        if choice in ("allow_once", "allow_session"):
            result = {"behavior": "allow", "updatedInput": arguments}
            if choice == "allow_session" and scope:
                result["updatedPermissions"] = scope
                # A granted setMode changes the mode the session reports from now on.
                modes = _reported_modes("claude", "permission mode")
                for item in scope:
                    if item.get("type") == "setMode" and modes.get(item.get("mode")) not in (None, self.mode):
                        self.mode = modes[item["mode"]]
                        self._pending.append(AdapterEvent("mode", mode=self.mode))
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
        reported = _text(data.get("claude_code_version"))
        if not version_supported("claude", reported):
            return _failure("version", version_problem("claude", reported))
        mode = _reported_modes("claude", "permission mode").get(_text(data.get("current_permission_mode")))
        if mode is None or (self.chat and mode != self.chat.mode):
            return _failure("unsafe-mode")
        account = _object(data.get("account"))
        if not any(account.get(key) for key in ("subscriptionType", "apiKeySource", "tokenSource")):
            return _failure("login")
        if not session_id_valid("claude", self.expected_session):
            return _failure("crashed", "missing or invalid Claude session id")
        self.mode = mode
        self.session_id = self.expected_session
        return (AdapterEvent("ready", session_id=self.session_id, mode=mode),)

    def _request(self, request_id: WireID, request: dict) -> Events:
        if request_id in self._approvals:
            self.answer(request_id, "deny", "duplicate request id")
            return (AdapterEvent("approval_closed", request_id=request_id, outcome="denied"),)
        if request.get("subtype") != "can_use_tool":
            kind = _text(request.get("subtype")).casefold()
            denied = "permission" in kind or "approval" in kind
            self._response(request_id, error="permission denied" if denied else "method not supported")
            return ()
        tool, arguments = _text(request.get("tool_name")), request.get("input")
        if self.session_id is None or not tool or not isinstance(arguments, dict):
            self._response(request_id, result={"behavior": "deny", "message": "permission request is incomplete"})
            return ()
        owner = _text(request.get("agent_id")) or None
        # Claude's own suggestions are its "don't ask again" scopes; a grant keeps only the session ones.
        suggestions = request.get("permission_suggestions")
        scope = [
            {**item, "destination": "session"}
            for item in (suggestions if isinstance(suggestions, list) else ())
            if isinstance(item, dict)
        ]
        if request.get("suppress_always_allow_rule") is True:
            scope = []
        self._approvals[request_id] = (owner, (arguments, scope))
        if tool_use_id := _text(request.get("tool_use_id")):
            self._asked.add(tool_use_id)
        return (
            AdapterEvent(
                "approval",
                request_id=request_id,
                tool=tool,
                arguments=arguments,
                options=_choices(bool(scope), arguments),
                requester=owner,
                tool_id=tool,
            ),
        )

    def _blocked(self, message: dict) -> Events:
        denials = message.get("permission_denials")
        events = ()
        if self.mode == "auto" and isinstance(denials, list):
            events = tuple(
                AdapterEvent(
                    "blocked",
                    tool=_text(item.get("tool_name")),
                    arguments=item.get("tool_input"),
                    text=self._reasons.get(_text(item.get("tool_use_id")), ""),
                )
                for item in map(_object, denials)
                if _text(item.get("tool_use_id")) not in self._asked
            )
        self._asked.clear()
        self._reasons.clear()
        return events

    def receive(self, message: dict) -> Events:
        # A mode a grant changed is reported with the next frame from the harness.
        pending, self._pending = tuple(self._pending), []
        return (*pending, *self._receive(message))

    def _receive(self, message: dict) -> Events:
        kind, subtype = message.get("type"), message.get("subtype")
        if kind not in _CLAUDE_TYPES:
            return _unknown(kind)
        if kind == "control_response":
            response = _object(message.get("response"))
            if self._initialize_id is not None and response.get("request_id") == self._initialize_id:
                return self._initialized(response)
        if kind == "user" and message.get("isReplay") is True and _text(message.get("uuid")):
            return (AdapterEvent("prompt_echoed", uuid=message["uuid"]),)
        if kind == "system" and subtype == "permission_denied" and _text(message.get("tool_use_id")):
            self._reasons[message["tool_use_id"]] = _text(message.get("decision_reason"))
            return ()
        if kind == "system" and subtype == "init":
            if _reported_modes("claude", "permission mode").get(_text(message.get("permissionMode"))) != self.mode:
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
            return (*closed, *self._blocked(message), AdapterEvent("turn_ended", outcome=outcome, text=text))
        request_id = message.get("request_id")
        if _wire_id(request_id):
            if kind == "control_request":
                return self._request(request_id, _object(message.get("request")))
            if kind == "control_cancel_request" and self._approvals.pop(request_id, None) is not None:
                return (
                    AdapterEvent(
                        "approval_closed", request_id=request_id, outcome="expired", text="claude cancelled the request"
                    ),
                )
        return ()


class DroidAdapter(_RPCAdapter):
    """Factory stream-jsonrpc as published in @factory/droid-sdk 0.11.0."""

    _name = "droid"
    _harness = "droid"
    _notifications = _DROID_NOTIFICATIONS
    _requests = _DROID_REQUESTS
    _factory_api_version = "1.0.0"
    _factory_protocol_version = "1.332.0"
    _start_methods = ("droid.initialize_session", "droid.load_session")

    def __init__(self, send: Send, chat_mode: ChatMode | str | None = None):
        super().__init__(send, chat_mode)
        self._level = "off"
        self._mode = "off"
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
        params = {"machineId": "default", "cwd": self._cwd, "interactionMode": "auto"}
        if self.chat and self.chat.protocol is not None:
            params["autonomyLevel"] = self.chat.protocol
        self._call("droid.initialize_session", params, self._opened)

    def _opened(self, data: dict) -> Events:
        settings = _object(data.get("settings"))
        level = settings.get("autonomyLevel")
        levels = _reported_modes("droid", "autonomyLevel")
        if (
            level not in levels
            or settings.get("interactionMode") != "auto"
            or (self.chat and self.chat.reported and levels[level] != self.chat.mode)
        ):
            return _failure("unsafe-mode")
        self._level = level
        # --skip-permissions-unsafe is not an autonomy level, so the chat's name is shown.
        self._mode = self.chat.mode if self.chat and not self.chat.reported else levels[level]
        session_id = data.get("sessionId", self._resume)
        if not session_id_valid("droid", session_id):
            return _failure("crashed", "missing or invalid Droid session id")
        self.session_id = session_id
        pending = data.get("pendingPermissions")
        for request in pending if isinstance(pending, list) else ():
            request_id = _object(request).get("requestId")
            if isinstance(request_id, str) and request_id:
                self._result(request_id, {"selectedOption": "cancel", "comment": "previous page session ended"})
        return (AdapterEvent("ready", session_id=session_id, mode=self._mode),)

    def prompt(self, text: str, uuid: str | None = None) -> None:
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

        offered = {_object(option).get("value") for option in options}

        def respond(choice: str, reason: str) -> dict:
            if choice == "allow_session" and "proceed_always" in offered:
                return {"selectedOption": "proceed_always"}
            if choice in ("allow_once", "allow_session"):
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
                options=_choices("proceed_always" in offered, uses),
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
                return (
                    AdapterEvent(
                        "approval_closed", request_id=request_id, outcome="expired", text="droid resolved the request"
                    ),
                )
        if kind == "child_session_settled" and (owner := _text(data.get("childSessionId"))):
            return _expire_owned(self._approvals, owner)
        if kind == "settings_updated":
            settings = _object(data.get("settings"))
            if (
                settings.get("autonomyLevel", self._level) != self._level
                or settings.get("interactionMode", "auto") != "auto"
            ):
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
