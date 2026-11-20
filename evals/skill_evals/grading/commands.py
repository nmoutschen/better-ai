"""Grade from the transcript whether the agent ran a command after its last edit, such as the project's linter.

The grader `ran_after_last_edit` (field `pattern`, a regex for the command) passes when a shell command matching
`pattern` ran after the agent's last edit, so on the final code. Edits are the harness's edit and write tool
calls, and shell commands that write a file in the repository: `sed -i`, a redirection to a file, `tee`, or a
Python one-liner that opens, writes or replaces a file. Several edits and commands in one shell command count
in the order they appear in it. A redirection counts only to a file with a name extension, such as `> labels.py`,
not under `/tmp`. Edits and commands by a sub-agent count like the agent's.
"""

import re
from typing import Any

from inspect_ai.model import ChatMessage, ChatMessageAssistant

from skill_evals.agent import EDIT_TOOL, SHELL_TOOL, WRITE_TOOL

SHELL_EDIT = re.compile(
    r"\bsed\s+(?:-\w*\s+)*-i"
    r"|(?<![0-9&>=-])>>?\s*(?!/tmp/|&)[\w./-]*\.[A-Za-z]\w*\b"
    r"|\btee\s+(?!/tmp/)"
    r"|open\([^)]*['\"][wa]\+?['\"]|\.write_text\(|\.write\(|\bos\.replace\(|\bshutil\.(?:copy|move)"
)

Event = tuple[int, int, str]


def events(messages: list[ChatMessage], pattern: re.Pattern[str]) -> list[Event]:
    """Return the edits and matching commands as (call number, position in the command, kind), in order."""
    found: list[Event] = []
    number = 0
    for message in messages:
        if not isinstance(message, ChatMessageAssistant):
            continue
        for call in message.tool_calls or []:
            number += 1
            if call.function in (EDIT_TOOL, WRITE_TOOL):
                found.append((number, 0, "edit"))
            elif call.function == SHELL_TOOL:
                command = str((call.arguments or {}).get("command", ""))
                found += [(number, match.start(), "edit") for match in SHELL_EDIT.finditer(command)]
                found += [(number, match.start(), "run") for match in pattern.finditer(command)]
    return sorted(found)


def ran_after_last_edit(spec: dict[str, Any], messages: list[ChatMessage]) -> bool:
    """Return whether a command matching the spec's `pattern` ran after the last edit, or at all if none."""
    found = events(messages, re.compile(spec["pattern"]))
    edits = [event for event in found if event[2] == "edit"]
    runs = [event for event in found if event[2] == "run"]
    return bool(runs) and (not edits or runs[-1] > edits[-1])
