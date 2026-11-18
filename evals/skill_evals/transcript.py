"""Turn Claude Code's stream-json output into Inspect chat messages and run statistics.

`claude -p --output-format stream-json --verbose` prints one JSON event per line: a `system` init
event, `assistant` events holding text and tool_use blocks, `user` events holding tool results, and
a final `result` event with the reply, usage, cost and duration. `parse_stream` converts these so
Inspect View shows the run and the graders and the judge can read it. Every text passes through
`redact` first, so no Anthropic token can reach the eval log.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any

from inspect_ai.model import ChatMessage, ChatMessageAssistant, ChatMessageTool, ChatMessageUser
from inspect_ai.tool import ToolCall, ToolCallError

TOKEN_PATTERN = re.compile(r"sk-ant-[A-Za-z0-9_\-]+")
REDACTED = "[REDACTED]"
USAGE_KEYS = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


def redact(text: str, secrets: tuple[str, ...] = ()) -> str:
    """Replace Anthropic keys and tokens, and any given secret values, with a marker."""
    for secret in secrets:
        if secret:
            text = text.replace(secret, REDACTED)
    return TOKEN_PATTERN.sub(REDACTED, text)


@dataclass
class Run:
    """One Claude Code run: messages for Inspect, the final reply and what the CLI reported."""

    messages: list[ChatMessage] = field(default_factory=list)
    reply: str = ""
    model: str | None = None
    stats: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


def result_text(content: Any) -> str:
    """Flatten a tool_result's content, a string or a list of blocks, into text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, dict):
                parts.append(f"[{block.get('type', 'block')}]")
        return "\n".join(parts)
    return "" if content is None else str(content)


def usage_of(event: dict[str, Any]) -> dict[str, int]:
    """Return the token counts of a result event."""
    usage = event.get("usage") or {}
    return {key: int(usage.get(key) or 0) for key in USAGE_KEYS}


class _Builder:
    """Collects messages while walking the events; one assistant message per API message id."""

    def __init__(self) -> None:
        """Start with no messages."""
        self.run = Run()
        self.names: dict[str, str] = {}
        self.current: ChatMessageAssistant | None = None
        self.current_id: str | None = None

    def assistant(self, event: dict[str, Any]) -> None:
        """Add the event's text and tool calls to the current assistant message, or start one."""
        message = event.get("message") or {}
        if message.get("id") != self.current_id or self.current is None:
            self.current = ChatMessageAssistant(content="", tool_calls=[], model=message.get("model"))
            self.current_id = message.get("id")
            if event.get("parent_tool_use_id"):
                self.current.metadata = {"subagent_of": event["parent_tool_use_id"]}
            self.run.messages.append(self.current)
        for block in message.get("content") or []:
            if block.get("type") == "text" and block.get("text"):
                text = self.current.text
                self.current.content = f"{text}\n\n{block['text']}" if text else block["text"]
            elif block.get("type") == "tool_use":
                self.names[block["id"]] = block.get("name", "")
                call = ToolCall(id=block["id"], function=block.get("name", ""), arguments=block.get("input") or {})
                self.current.tool_calls = [*(self.current.tool_calls or []), call]

    def user(self, event: dict[str, Any]) -> None:
        """Add tool results, and any plain user text such as an expanded skill, as messages."""
        self.current = self.current_id = None
        content = (event.get("message") or {}).get("content")
        if isinstance(content, str):
            self.run.messages.append(ChatMessageUser(content=content))
            return
        for block in content or []:
            if block.get("type") == "tool_result":
                text = result_text(block.get("content"))
                error = ToolCallError("unknown", text) if block.get("is_error") else None
                call_id = block.get("tool_use_id", "")
                self.run.messages.append(
                    ChatMessageTool(content=text, tool_call_id=call_id, function=self.names.get(call_id), error=error)
                )
            elif block.get("type") == "text" and block.get("text"):
                self.run.messages.append(ChatMessageUser(content=block["text"]))

    def result(self, event: dict[str, Any]) -> None:
        """Record the final reply, usage, cost, duration and any error the CLI reported."""
        self.run.reply = event.get("result") or ""
        self.run.stats.update(
            usage=usage_of(event),
            total_cost_usd=float(event.get("total_cost_usd") or 0.0),
            duration_ms=int(event.get("duration_ms") or 0),
            num_turns=int(event.get("num_turns") or 0),
            subtype=event.get("subtype"),
        )
        if event.get("is_error") or event.get("subtype") != "success":
            self.run.error = f"{event.get('subtype')}: {self.run.reply or event.get('errors') or 'no reply'}"


def parse_stream(text: str, secrets: tuple[str, ...] = ()) -> Run:
    """Convert stream-json lines into a Run; lines that are not JSON events are ignored."""
    builder = _Builder()
    found_result = False
    for line in redact(text, secrets).splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = event.get("type") if isinstance(event, dict) else None
        if kind == "system" and event.get("subtype") == "init":
            builder.run.model = event.get("model")
            builder.run.stats["init"] = {
                key: event.get(key)
                for key in ("claude_code_version", "model", "permissionMode", "skills", "slash_commands")
            }
        elif kind == "assistant":
            builder.assistant(event)
        elif kind == "user":
            builder.user(event)
        elif kind == "result":
            found_result = True
            builder.result(event)
    if not found_result:
        builder.run.error = "Claude Code printed no result event"
    return builder.run
