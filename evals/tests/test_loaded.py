"""Tests for skill_evals/grading/loaded.py: whether a run loaded the skill without a slash command."""

from conftest import assistant, skill_dir
from inspect_ai.model import ChatMessageTool

from skill_evals.grading import loaded

SKILL_DIR = skill_dir("write-better")


def test_skill_tool_with_the_name_loads_it() -> None:
    """The skill tool counts with the bare name, a leading slash or a plugin prefix, not with another skill."""
    assert loaded.loaded([assistant(("Skill", {"skill": "write-better"}))], "write-better")
    assert loaded.loaded([assistant(("Skill", {"command": "/write-better"}))], "write-better")
    assert loaded.loaded([assistant(("Skill", {"skill": "better-ai:write-better"}))], "write-better")
    assert not loaded.loaded([assistant(("Skill", {"skill": "do-better"}))], "write-better")


def test_reading_skill_md_loads_it() -> None:
    """Reading the installed SKILL.md with the read tool counts; printing it in the shell, or another file, does not."""
    assert loaded.loaded([assistant(("Read", {"file_path": f"{SKILL_DIR}/SKILL.md"}))], "write-better")
    assert not loaded.loaded([assistant(("Bash", {"command": f"cat {SKILL_DIR}/SKILL.md"}))], "write-better")
    failed = ChatMessageTool(content="", tool_call_id="call-0", error={"type": "unknown", "message": "no such file"})  # type: ignore[arg-type]
    assert not loaded.loaded([assistant(("Read", {"file_path": f"{SKILL_DIR}/SKILL.md"})), failed], "write-better")
    assert not loaded.loaded([assistant(("Read", {"file_path": f"{SKILL_DIR}/formats/x.md"}))], "write-better")
    assert not loaded.loaded([assistant(("Read", {"file_path": "/work/SKILL.md"}))], "write-better")
