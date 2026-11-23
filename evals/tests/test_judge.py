"""Tests for skill_evals/grading/judge.py: the record it builds, its output parsing and its verdicts."""

import json
from types import SimpleNamespace
from typing import Any

import pytest
from conftest import Plant
from inspect_ai.model import ChatMessageAssistant, ChatMessageTool, ChatMessageUser, ModelOutput
from inspect_ai.tool import ToolCall, ToolCallError

from skill_evals.grading import judge
from skill_evals.grading.files import GradingError


def messages() -> list[Any]:
    """A short run: the prompt, one failing Bash call, an edit, and a passing Bash call."""
    return [
        ChatMessageUser(content="Fix it"),
        ChatMessageAssistant(
            content="Checking.", tool_calls=[ToolCall(id="a", function="Bash", arguments={"command": "python t.py"})]
        ),
        ChatMessageTool(
            content="Exit code 1\nAssertionError", tool_call_id="a", function="Bash", error=ToolCallError("unknown", "")
        ),
        ChatMessageAssistant(
            content="",
            tool_calls=[
                ToolCall(
                    id="b", function="Edit", arguments={"file_path": "/work/f.py", "old_string": "1", "new_string": "2"}
                ),
                ToolCall(id="c", function="Bash", arguments={"command": "python t.py"}),
            ],
        ),
        ChatMessageTool(content="ok", tool_call_id="b", function="Edit"),
        ChatMessageTool(content="", tool_call_id="c", function="Bash"),
    ]


def test_render_transcript_numbers_steps_with_exit_codes() -> None:
    """Steps are numbered in order, with the failing exit code and the later passing run."""
    text = judge.render_transcript(messages())
    assert "[1] Agent says: Checking." in text
    assert "[2] Bash: python t.py\n  -> FAILED, exit code 1" in text
    assert "[3] Edit /work/f.py\n  old: 1\n  new: 2" in text
    assert "[4] Bash: python t.py\n  -> OK, exit code 0" in text


def test_render_transcript_marks_sub_agent_steps() -> None:
    """A sub-agent's text and tool calls are labelled as the sub-agent's."""
    sub = {"subagent_of": "a"}
    text = judge.render_transcript(
        [
            ChatMessageUser(content="Fix it"),
            ChatMessageAssistant(
                content="",
                metadata=sub,
                tool_calls=[ToolCall(id="s", function="Bash", arguments={"command": "git diff"})],
            ),
            ChatMessageTool(content="diff", tool_call_id="s", function="Bash"),
            ChatMessageAssistant(content="Verdict: passes.", metadata=sub),
            ChatMessageAssistant(content="Done."),
        ]
    )
    assert "[1] (sub-agent) Bash: git diff" in text
    assert "[2] Sub-agent says: Verdict: passes." in text
    assert "[3] Agent says: Done." in text


def test_clip_and_read_ranges() -> None:
    """Long outputs keep both ends; a Read shows whether it was partial."""
    assert "characters cut" in judge.clip("x" * 5000)
    assert len(judge.clip("x" * 5000, 600, 0)) < 700
    assert judge.describe_call("Read", {"file_path": "a.py"}) == "Read a.py (whole file)"
    assert judge.describe_call("Read", {"file_path": "a.py", "limit": 5}) == "Read a.py limit=5"


def test_long_prompt_does_not_hide_call_settings() -> None:
    """A sub-agent call's short settings, such as its model, show even when its prompt is clipped."""
    text = judge.describe_call("Agent", {"description": "Build T2", "prompt": "x" * 5000, "model": "opus"})
    assert '"model": "opus"' in text


@pytest.mark.parametrize(
    ("reply", "expected"),
    [("Reason.\nVERDICT: PASS", True), ("VERDICT: FAIL\n\n", False), ("VERDICT: PASS.", None), ("", None)],
)
def test_verdict(reply: str, expected: bool | None) -> None:
    """Only an exact last line counts."""
    assert judge.verdict(reply) is expected


def test_parse_output() -> None:
    """The JSON result gives the reply, cost and usage; anything else is an error."""
    data = {"result": "VERDICT: PASS", "total_cost_usd": 0.1, "usage": {"input_tokens": 5, "output_tokens": 6}}
    parsed = judge.parse_output("noise\n" + json.dumps(data))
    assert parsed["reply"] == "VERDICT: PASS" and parsed["usage"] == {"input_tokens": 5, "output_tokens": 6}
    assert judge.parse_output("not json")["error"]


async def test_judge_record_and_verdict(plant: Plant, monkeypatch: pytest.MonkeyPatch) -> None:
    """The judge reads the plain request (not the condition's prompt), transcript, reply, diff and notes; its verdict decides."""
    repo = await plant({"f.py": "x = 1\n"})
    await repo.sandbox_env.write_file("f.py", "x = 2\n")
    await repo.sandbox_env.write_file("PLAN.md", "Step 1\n")
    state = SimpleNamespace(
        input_text="/code-better Fix it",
        metadata={"request": "Fix it"},
        messages=messages(),
        output=ModelOutput.from_content("m", "Done."),
    )
    seen: dict[str, Any] = {}

    async def fake_cli(sandbox_env: Any, user: str, args: list[str], **options: Any) -> tuple[str, str, bool]:
        seen.update(args=args, **options)
        return json.dumps({"result": "Quote.\nVERDICT: FAIL", "total_cost_usd": 0.2}), "", False

    monkeypatch.setattr(judge, "claude_cli", fake_cli)
    passed, info = await judge.judge({"rubric": "Pass if good."}, state, repo, "opus")  # type: ignore[arg-type]
    assert passed is False and info["verdict"] is False and "malformed" not in info
    prompt = seen["stdin"]
    for part in ("Pass if good.", "## Request\nFix it", "## Final reply\nDone.", "+x = 2", "--- PLAN.md\nStep 1"):
        assert part in prompt
    assert "/code-better" not in prompt
    assert "--tools" in seen["args"] and seen["args"][seen["args"].index("--tools") + 1] == ""


async def test_malformed_judge_output(plant: Plant, monkeypatch: pytest.MonkeyPatch) -> None:
    """A reply without a verdict line fails the grader and is marked malformed."""
    repo = await plant({"f.py": ""})
    state = SimpleNamespace(input_text="Do", messages=[ChatMessageUser(content="Do")], output=ModelOutput())

    async def fake_cli(*args: Any, **options: Any) -> tuple[str, str, bool]:
        return json.dumps({"result": "I think it passes."}), "", False

    monkeypatch.setattr(judge, "claude_cli", fake_cli)
    passed, info = await judge.judge({"rubric": "r"}, state, repo, "opus")  # type: ignore[arg-type]
    assert passed is False and info["malformed"] == "last line is not a verdict"


@pytest.mark.parametrize(
    ("cli", "reason"),
    [
        (("", "", True), "timed out"),
        ((json.dumps({"is_error": True, "subtype": "error_during_execution", "result": ""}), "429", False), "error"),
        ((json.dumps({"is_error": True, "result": ""}), "", False), "is_error"),
        (("", "", False), "no JSON"),
        ((json.dumps({"result": ""}), "", False), "no reply"),
    ],
)
async def test_judge_that_could_not_run_is_not_a_verdict(
    plant: Plant, monkeypatch: pytest.MonkeyPatch, cli: tuple[str, str, bool], reason: str
) -> None:
    """A timeout, a CLI error or no reply gives no verdict (None, not False) and records why."""
    repo = await plant({"f.py": ""})
    state = SimpleNamespace(input_text="Do", messages=[ChatMessageUser(content="Do")], output=ModelOutput())

    async def fake_cli(*args: Any, **options: Any) -> tuple[str, str, bool]:
        return cli

    monkeypatch.setattr(judge, "claude_cli", fake_cli)
    passed, info = await judge.judge({"rubric": "r"}, state, repo, "opus")  # type: ignore[arg-type]
    assert passed is None and info["verdict"] is None and reason in info["error"]


async def test_judge_raises_when_its_record_cannot_be_built(plant: Plant, monkeypatch: pytest.MonkeyPatch) -> None:
    """A sandbox error while taking the diff is a grading error, not a diff shown as unavailable."""
    repo = await plant({"f.py": ""})
    state = SimpleNamespace(input_text="Do", messages=[ChatMessageUser(content="Do")], output=ModelOutput())
    real = repo.sandbox_env.exec

    async def exec_fails(command: list[str], *args: Any, **options: Any) -> Any:
        if command[:2] == ["mktemp", "-d"]:
            raise OSError("docker gone")
        return await real(command, *args, **options)

    monkeypatch.setattr(repo.sandbox_env, "exec", exec_fails)
    with pytest.raises(GradingError, match="docker gone"):
        await judge.judge({"rubric": "r"}, state, repo, "opus")  # type: ignore[arg-type]
