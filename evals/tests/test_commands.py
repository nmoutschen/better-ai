"""Tests for skill_evals/grading/commands.py: a command counts only after the last edit."""

from inspect_ai.model import ChatMessageAssistant
from inspect_ai.tool import ToolCall

from skill_evals.grading.commands import ran_after_last_edit

SPEC = {"pattern": r"\bruff\b"}


def calls(*items: tuple[str, dict[str, str]]) -> list[ChatMessageAssistant]:
    """One assistant message per tool call."""
    return [
        ChatMessageAssistant(content="", tool_calls=[ToolCall(id=str(n), function=name, arguments=args)])
        for n, (name, args) in enumerate(items)
    ]


def test_ruff_after_the_last_edit() -> None:
    """Running the linter after the last edit passes; an edit after it, by a tool or a shell write, fails."""
    edit = ("Edit", {"file_path": "/work/a.py"})
    ruff = ("Bash", {"command": "ruff check ."})
    assert ran_after_last_edit(SPEC, calls(edit, ruff))
    assert not ran_after_last_edit(SPEC, calls(ruff, edit))
    assert not ran_after_last_edit(SPEC, calls(ruff, ("Bash", {"command": "sed -i 's/a/b/' a.py"})))
    assert not ran_after_last_edit(SPEC, calls(edit))


def test_order_inside_one_command() -> None:
    """An edit and the linter in one command count in the order they appear; temp files and tests are not edits."""
    assert ran_after_last_edit(SPEC, calls(("Bash", {"command": "sed -i 's/a/b/' a.py && ruff check ."})))
    assert not ran_after_last_edit(SPEC, calls(("Bash", {"command": "ruff check . && cat > a.py <<E\nx\nE"})))
    assert ran_after_last_edit(
        SPEC, calls(("Edit", {}), ("Bash", {"command": "ruff check . > /tmp/out.txt; python -m unittest"}))
    )
