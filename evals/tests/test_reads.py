"""Tests for skill_evals/grading/reads.py: which skill files a run read, and which expected reads it missed."""

from types import SimpleNamespace

from inspect_ai.model import ChatMessageAssistant, ChatMessageUser
from inspect_ai.tool import ToolCall

from skill_evals.grading import reads

SKILL_DIR = "/home/agent/.claude/skills/code-better"


def assistant(*calls: tuple[str, dict[str, str]], subagent: bool = False) -> ChatMessageAssistant:
    """An assistant message making the given tool calls, from a sub-agent if asked."""
    tool_calls = [ToolCall(id=f"call-{n}", function=name, arguments=args) for n, (name, args) in enumerate(calls)]
    message = ChatMessageAssistant(content="", tool_calls=tool_calls)
    if subagent:
        message.metadata = {"subagent_of": "task-1"}
    return message


def test_files_read_by_read_tool_bash_and_sub_agent() -> None:
    """Read calls and printing commands count, listing and SKILL.md do not; a sub-agent's read is marked."""
    messages = [
        ChatMessageUser(content=f"see {SKILL_DIR}/modes/tests.md"),
        assistant(
            ("Read", {"file_path": f"{SKILL_DIR}/modes/feature.md"}),
            ("Read", {"file_path": f"{SKILL_DIR}/SKILL.md"}),
            ("Bash", {"command": f"ls {SKILL_DIR}/templates/specs.md"}),
            ("Bash", {"command": "cat ~/.claude/skills/code-better/templates/tasks.md"}),
            ("Read", {"file_path": "/work/README.md"}),
            ("Read", {"file_path": "/home/agent/.claude/skills/other/modes/bug-fix.md"}),
        ),
        assistant(("Read", {"file_path": f"{SKILL_DIR}/agents/verifier.md"}), subagent=True),
        assistant(("Read", {"file_path": f"{SKILL_DIR}/modes/feature.md"}), subagent=True),
    ]
    assert reads.files_read(messages, "code-better") == {
        "modes/feature.md": reads.MAIN,
        "templates/tasks.md": reads.MAIN,
        "agents/verifier.md": reads.SUB_AGENT,
    }


def test_track_accepts_any_alternative() -> None:
    """An entry with alternatives is met by any one of them; missing entries are listed by label."""
    expected = [["modes/feature.md", "modes/bug-fix.md"], "agents/verifier.md", "templates/next-steps.md"]
    tracked = reads.track(expected, {"modes/bug-fix.md": reads.MAIN, "agents/verifier.md": reads.SUB_AGENT})
    assert tracked["expected"] == [
        "modes/feature.md or modes/bug-fix.md",
        "agents/verifier.md",
        "templates/next-steps.md",
    ]
    assert tracked["missing"] == ["templates/next-steps.md"]


async def test_skill_reads_scorer() -> None:
    """A missed read scores 0 with an explanation; other conditions and cases without reads get no score."""
    read = ToolCall(id="1", function="Read", arguments={"file_path": f"{SKILL_DIR}/modes/bug-fix.md"})

    async def score(condition: str, expected: list[str], messages: list) -> object:  # noqa: ANN401
        state = SimpleNamespace(
            metadata={"condition": condition, "skill": "code-better", "reads": expected}, messages=messages
        )
        return await reads.skill_reads()(state, None)  # type: ignore[arg-type]

    missed = await score("skill", ["modes/bug-fix.md"], [])
    assert missed.value == 0 and missed.explanation == "Missed: modes/bug-fix.md"
    done = await score("skill", ["modes/bug-fix.md"], [ChatMessageAssistant(content="", tool_calls=[read])])
    assert done.value == 1 and done.metadata["read"] == {"modes/bug-fix.md": reads.MAIN}
    assert await score("no-skill", ["modes/bug-fix.md"], []) is None
    assert await score("skill", [], []) is None


def test_failed_read_and_relative_cat() -> None:
    """A Read that failed does not count; a cat after a cd into the skill folder does."""
    from inspect_ai.model import ChatMessageTool
    from inspect_ai.tool import ToolCallError

    messages = [
        assistant(("Read", {"file_path": "/root/.claude/skills/code-better/agents/verifier.md"})),
        ChatMessageTool(
            content="EACCES", tool_call_id="call-0", function="Read", error=ToolCallError("unknown", "EACCES")
        ),
        assistant(("Bash", {"command": "cd ~/.claude/skills/code-better; cat modes/feature.md templates/specs.md"})),
        assistant(("Bash", {"command": "cd ~/.claude/skills/code-better && ls modes/bug-fix.md"})),
        assistant(("Bash", {"command": "cd /work && cat notes.md"})),
    ]
    assert reads.files_read(messages, "code-better") == {
        "modes/feature.md": reads.MAIN,
        "templates/specs.md": reads.MAIN,
    }
