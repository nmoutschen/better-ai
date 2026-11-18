"""Tests for skill_evals/grading/judge.py: the record it builds, its output parsing and its verdicts."""

import json
from types import SimpleNamespace
from typing import Any

import pytest
from conftest import Plant
from inspect_ai.model import ChatMessageAssistant, ChatMessageTool, ChatMessageUser, ModelOutput
from inspect_ai.tool import ToolCall, ToolCallError

from skill_evals.grading import judge


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


def test_clip_and_read_ranges() -> None:
    """Long outputs keep both ends; a Read shows whether it was partial."""
    assert "characters cut" in judge.clip("x" * 5000)
    assert judge.describe_call("Read", {"file_path": "a.py"}) == "Read a.py (whole file)"
    assert judge.describe_call("Read", {"file_path": "a.py", "limit": 5}) == "Read a.py limit=5"


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
    """The judge reads request, transcript, reply, diff and notes, and its verdict decides the grader."""
    repo = await plant({"f.py": "x = 1\n"})
    await repo.sandbox_env.write_file("f.py", "x = 2\n")
    await repo.sandbox_env.write_file("PLAN.md", "Step 1\n")
    state = SimpleNamespace(input_text="Fix it", messages=messages(), output=ModelOutput.from_content("m", "Done."))
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
