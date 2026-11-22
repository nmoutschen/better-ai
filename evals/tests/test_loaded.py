"""Tests for skill_evals/grading/loaded.py: whether a run loaded the skill without a slash command."""

from inspect_ai.model import ChatMessageAssistant
from inspect_ai.tool import ToolCall

from skill_evals.grading import loaded

SKILL_DIR = "/home/agent/.claude/skills/write-better"


def assistant(name: str, arguments: dict[str, str]) -> ChatMessageAssistant:
    """An assistant message making one tool call."""
    return ChatMessageAssistant(content="", tool_calls=[ToolCall(id="call-1", function=name, arguments=arguments)])


def test_skill_tool_with_the_name_loads_it() -> None:
    """The skill tool counts with the bare name, a leading slash or a plugin prefix, not with another skill."""
    assert loaded.loaded([assistant("Skill", {"skill": "write-better"})], "write-better")
    assert loaded.loaded([assistant("Skill", {"command": "/write-better"})], "write-better")
    assert loaded.loaded([assistant("Skill", {"skill": "better-ai:write-better"})], "write-better")
    assert not loaded.loaded([assistant("Skill", {"skill": "do-better"})], "write-better")


def test_reading_skill_md_loads_it() -> None:
    """Reading or printing the installed SKILL.md counts; another file of the skill or the repository does not."""
    assert loaded.loaded([assistant("Read", {"file_path": f"{SKILL_DIR}/SKILL.md"})], "write-better")
    assert loaded.loaded([assistant("Bash", {"command": f"cat {SKILL_DIR}/SKILL.md"})], "write-better")
    assert not loaded.loaded([assistant("Read", {"file_path": f"{SKILL_DIR}/formats/x.md"})], "write-better")
    assert not loaded.loaded([assistant("Read", {"file_path": "/work/SKILL.md"})], "write-better")
