"""Grade from the transcript whether the agent ran a command.

The grader `ran_command` (field `pattern`) passes when any shell command matching `pattern` ran, such as `git log`
in an audit that must read the history.
"""

import re
from typing import Any

from inspect_ai.model import ChatMessage, ChatMessageAssistant

from skill_evals.agent import SHELL_TOOL


def ran_command(spec: dict[str, Any], messages: list[ChatMessage]) -> bool:
    """Return whether a shell command matching the spec's `pattern` ran at any point."""
    pattern = re.compile(spec["pattern"])
    return any(
        pattern.search(str((call.arguments or {}).get("command", "")))
        for message in messages
        if isinstance(message, ChatMessageAssistant)
        for call in message.tool_calls or []
        if call.function == SHELL_TOOL
    )
