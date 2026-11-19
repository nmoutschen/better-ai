"""Grade whether the agent read the skill's own files that a case expects, such as a mode file or an agent prompt.

The slash command loads SKILL.md; the skill then tells the agent to read other files of its folder,
such as `modes/feature.md` before building or `agents/verifier.md` before hand-back. A case lists the
files the skill condition should read under `reads`: each entry is one path, or a list of paths of
which one is enough. The `skill_reads` scorer, separate from the rule's scorer, passes a skill-condition run
only when every expected read happened; the files read and the missing ones go into its score metadata. It
gives no score to other conditions and to cases that expect no reads. It reads only the transcript, so
Inspect's `score()` can re-run it on a finished log without a sandbox; append mode stores that result as
`skill_reads1` beside the original.

Which file a tool call opened is an exact fact, so a script decides it. A read is a Read tool call on a file
in the skill folder that did not fail, or a Bash command that prints one (cat, head, sed...), by its path or
by a relative path after a `cd` into the skill folder. Reads by a sub-agent count, and are marked as such. The skills folder and the tool names come from the harness adapter (`agent.py`).
"""

import re
from typing import Any

from inspect_ai.model import ChatMessage, ChatMessageAssistant, ChatMessageTool
from inspect_ai.scorer import Score, Scorer, Target, mean, scorer
from inspect_ai.solver import TaskState

from skill_evals.agent import READ_TOOL, SHELL_TOOL, SKILLS_FOLDER
from skill_evals.cases import WITH_SKILL

READ_COMMAND = re.compile(r"\b(?:cat|head|tail|sed|awk|less|more|nl|grep|rg|bat)\b")
RELATIVE_FILE = re.compile(r"(?<![\w./-])((?:[\w-]+/)*[\w-]+\.md)\b")
MAIN = "main"
SUB_AGENT = "sub-agent"


def skill_path(skill: str) -> re.Pattern[str]:
    """Match a file inside the installed skill folder and capture its path relative to that folder."""
    return re.compile(rf"{re.escape(SKILLS_FOLDER)}/{re.escape(skill)}/([\w./-]+\.\w+)")


def shell_paths(command: str, skill: str) -> list[str]:
    """Return the skill files a printing command names: by their path, or relative to a `cd` into the skill folder."""
    if not READ_COMMAND.search(command):
        return []
    paths = skill_path(skill).findall(command)
    folder = re.search(rf"\bcd\s+\S*{re.escape(SKILLS_FOLDER)}/{re.escape(skill)}/?(?=[\s;&|]|$)", command)
    if folder:
        paths += RELATIVE_FILE.findall(command[folder.end() :])
    return paths


def files_read(messages: list[ChatMessage], skill: str) -> dict[str, str]:
    """Return each skill file read, other than SKILL.md, with who first read it: main or sub-agent."""
    failed = {m.tool_call_id for m in messages if isinstance(m, ChatMessageTool) and m.error}
    found: dict[str, str] = {}
    for message in messages:
        if not isinstance(message, ChatMessageAssistant):
            continue
        reader = SUB_AGENT if (message.metadata or {}).get("subagent_of") else MAIN
        for call in message.tool_calls or []:
            arguments = call.arguments or {}
            if call.function == READ_TOOL and call.id not in failed:
                paths = skill_path(skill).findall(str(arguments.get("file_path", "")))
            elif call.function == SHELL_TOOL:
                paths = shell_paths(str(arguments.get("command", "")), skill)
            else:
                paths = []
            for path in paths:
                if path != "SKILL.md":
                    found.setdefault(path, reader)
    return found


def expected_label(entry: str | list[str]) -> str:
    """Name an expected read: a path, or alternatives joined by " or "."""
    return entry if isinstance(entry, str) else " or ".join(entry)


def track(expected: list[str | list[str]], read: dict[str, str]) -> dict[str, Any]:
    """Compare the expected reads with the files read: what was read, and which expected reads are missing."""
    missing = [
        expected_label(entry)
        for entry in expected
        if not any(path in read for path in ([entry] if isinstance(entry, str) else entry))
    ]
    return {"expected": [expected_label(entry) for entry in expected], "read": read, "missing": missing}


@scorer(metrics=[mean()])
def skill_reads() -> Scorer:
    """Pass a skill-condition run that read every skill file its case expects; no score elsewhere."""

    async def score(state: TaskState, target: Target) -> Score | None:
        expected = state.metadata.get("reads") or []
        if state.metadata["condition"] != WITH_SKILL or not expected:
            return None
        tracked = track(expected, files_read(state.messages, state.metadata["skill"]))
        missing = tracked["missing"]
        explanation = f"Missed: {', '.join(missing)}" if missing else "Read every expected skill file."
        return Score(value=int(not missing), explanation=explanation, metadata=tracked)

    return score
