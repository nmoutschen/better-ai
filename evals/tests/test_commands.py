"""Tests for skill_evals/grading/commands.py: a command counts wherever it ran."""

from inspect_ai.model import ChatMessageAssistant
from inspect_ai.tool import ToolCall

from skill_evals.grading.commands import ran_command


def calls(*items: tuple[str, dict[str, str]]) -> list[ChatMessageAssistant]:
    """One assistant message per tool call."""
    return [
        ChatMessageAssistant(content="", tool_calls=[ToolCall(id=str(n), function=name, arguments=args)])
        for n, (name, args) in enumerate(items)
    ]


def test_ran_command_at_any_point() -> None:
    """A matching command passes wherever it ran, also before an edit; no matching command fails."""
    log = ("Bash", {"command": "git log --name-only --since=12.months"})
    write = ("Write", {"file_path": "/work/.code/audit/findings.md"})
    spec = {"pattern": r"\bgit\s+log\b"}
    assert ran_command(spec, calls(log, write))
    assert not ran_command(spec, calls(("Bash", {"command": "git status"}), write))
