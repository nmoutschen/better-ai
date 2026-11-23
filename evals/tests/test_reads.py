"""Tests for skill_evals/grading/reads.py: which skill files a run read, and which expected reads it missed."""

from types import SimpleNamespace
from typing import Any

import pytest
from conftest import assistant, skill_dir
from inspect_ai.model import ChatMessageTool, ChatMessageUser
from inspect_ai.tool import ToolCallError

from skill_evals.grading import reads
from skill_evals.grading.files import GradingError

SKILL_DIR = skill_dir("code-better")


def test_files_read_counts_only_read_tool_calls_that_did_not_fail() -> None:
    """A Read call counts, by the agent or a sub-agent (marked); listing, SKILL.md, a failed Read and a shell command do not."""
    messages = [
        ChatMessageUser(content=f"see {SKILL_DIR}/modes/tests.md"),
        assistant(
            ("Read", {"file_path": f"{SKILL_DIR}/modes/feature.md"}),
            ("Read", {"file_path": f"{SKILL_DIR}/SKILL.md"}),
            ("Bash", {"command": f"cat {SKILL_DIR}/formats/specs.md"}),
            ("Read", {"file_path": "/work/README.md"}),
            ("Read", {"file_path": "/home/agent/.claude/skills/other/modes/bug-fix.md"}),
            ("Read", {"file_path": f"{SKILL_DIR}/modes/refactor.md"}),
        ),
        ChatMessageTool(
            content="EACCES", tool_call_id="call-5", function="Read", error=ToolCallError("unknown", "EACCES")
        ),
        assistant(("Read", {"file_path": f"{SKILL_DIR}/agents/verifier.md"}), subagent=True),
        assistant(("Read", {"file_path": f"{SKILL_DIR}/modes/feature.md"}), subagent=True),
    ]
    assert reads.files_read(messages, "code-better") == {
        "modes/feature.md": reads.MAIN,
        "agents/verifier.md": reads.SUB_AGENT,
    }


def test_track_accepts_any_alternative() -> None:
    """An entry with alternatives is met by any one of them; missing entries are listed by label."""
    expected = [["modes/feature.md", "modes/bug-fix.md"], "agents/verifier.md", "formats/next-steps.md"]
    tracked = reads.track(expected, {"modes/bug-fix.md": reads.MAIN, "agents/verifier.md": reads.SUB_AGENT})
    assert tracked["expected"] == [
        "modes/feature.md or modes/bug-fix.md",
        "agents/verifier.md",
        "formats/next-steps.md",
    ]
    assert tracked["missing"] == ["formats/next-steps.md"]


READ_CALL = ("Read", {"file_path": f"{SKILL_DIR}/modes/bug-fix.md"})
CAT_CALL = ("Bash", {"command": "cd ~/.claude/skills/code-better\ncat modes/bug-fix.md"})


class StubJudge:
    """Stands in for the judge call: records the prompts and replies with a fixed text or fails."""

    def __init__(self, reply: str = "", error: str | None = None) -> None:
        """Reply with `reply`, or report `error` as the reason the judge could not run."""
        self.reply, self.error, self.prompts = reply, error, []

    async def __call__(self, system: str, prompt: str, model: str) -> tuple[str, dict[str, Any]]:
        """Return the reply and the judge info, as `reads.ask_judge` does."""
        self.prompts.append(prompt)
        info: dict[str, Any] = {"model": model, "reply": self.reply}
        return self.reply, info | ({"error": self.error} if self.error else {})


async def score(
    messages: list[Any],
    *,
    stub: StubJudge,
    monkeypatch: pytest.MonkeyPatch,
    condition: str = "skill",
    expected: list[str] | None = None,
    model: str = "opus",
) -> Any:  # noqa: ANN401
    """Run the scorer on a state with the given messages and a stubbed judge."""
    monkeypatch.setattr(reads, "ask_judge", stub)
    state = SimpleNamespace(
        metadata={
            "condition": condition,
            "skill": "code-better",
            "reads": ["modes/bug-fix.md"] if expected is None else expected,
        },
        messages=messages,
    )
    return await reads.skill_reads(model)(state, None)  # type: ignore[arg-type]


async def test_read_tool_read_counts_without_a_judge_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """A Read of the expected file passes by the script alone."""
    stub = StubJudge()
    result = await score([assistant(READ_CALL)], stub=stub, monkeypatch=monkeypatch)
    assert result.value == 1 and stub.prompts == []
    assert result.metadata["read"] == {"modes/bug-fix.md": reads.MAIN}
    assert result.metadata["missing"] == [] and result.metadata["decided_by"] == "script"


async def test_failed_read_is_missing_and_goes_to_the_judge(monkeypatch: pytest.MonkeyPatch) -> None:
    """A Read that failed leaves the file missing for the script, so the judge is asked about it."""
    messages = [
        assistant(READ_CALL),
        ChatMessageTool(
            content="EACCES", tool_call_id="call-0", function="Read", error=ToolCallError("unknown", "EACCES")
        ),
    ]
    stub = StubJudge("modes/bug-fix.md: NOT READ")
    result = await score(messages, stub=stub, monkeypatch=monkeypatch)
    assert len(stub.prompts) == 1 and "modes/bug-fix.md" in stub.prompts[0]
    assert result.value == 0


async def test_judge_finds_a_read_by_cat(monkeypatch: pytest.MonkeyPatch) -> None:
    """When the judge says the file was printed by cat, it is not missed; the metadata says who found it."""
    stub = StubJudge("Step 1 prints it.\nmodes/bug-fix.md: READ")
    result = await score(
        [ChatMessageUser(content="Fix it"), assistant(CAT_CALL)],
        stub=stub,
        monkeypatch=monkeypatch,
    )
    assert result.value == 1 and "cat modes/bug-fix.md" in stub.prompts[0]
    meta = result.metadata
    assert meta["read"] == {} and meta["judge_read"] == ["modes/bug-fix.md"] and meta["missing"] == []
    assert meta["decided_by"] == "judge" and "READ" in meta["judge"]["reply"] and meta["judge"]["model"] == "opus"


async def test_judge_says_not_read(monkeypatch: pytest.MonkeyPatch) -> None:
    """A file the judge also finds unread is missed: score 0, listed as missing."""
    stub = StubJudge("modes/bug-fix.md: NOT READ")
    result = await score([], stub=stub, monkeypatch=monkeypatch)
    assert result.value == 0 and result.explanation == "Missed: modes/bug-fix.md"
    assert result.metadata["missing"] == ["modes/bug-fix.md"] and result.metadata["judge_read"] == []


async def test_judge_asked_once_for_every_alternative_of_each_missing_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    """One call per sample: it lists the alternatives of each missing entry, not the entries the script found."""
    stub = StubJudge("modes/bug-fix.md: NOT READ\nmodes/feature.md: READ\nformats/specs.md: NOT READ")
    found = assistant(("Read", {"file_path": f"{SKILL_DIR}/agents/verifier.md"}))
    result = await score(
        [found],
        stub=stub,
        monkeypatch=monkeypatch,
        expected=[["modes/bug-fix.md", "modes/feature.md"], "agents/verifier.md", "formats/specs.md"],
    )
    assert len(stub.prompts) == 1 and "agents/verifier.md" not in stub.prompts[0].split("Transcript")[0]
    assert result.metadata["missing"] == ["formats/specs.md"] and result.metadata["judge_read"] == ["modes/feature.md"]


async def test_judge_that_cannot_run_is_a_sample_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A judge that timed out or errored makes the sample a grading error, not a 0."""
    with pytest.raises(GradingError, match="timed out"):
        await score([], stub=StubJudge(error="timed out"), monkeypatch=monkeypatch)


async def test_unparsed_file_verdict_counts_as_missed(monkeypatch: pytest.MonkeyPatch) -> None:
    """A reply with no verdict line for a file leaves it missed, as a malformed judge reply fails closed elsewhere."""
    result = await score([], stub=StubJudge("It looks read to me."), monkeypatch=monkeypatch)
    assert result.value == 0 and result.metadata["judge"]["malformed"]


async def test_judging_off_keeps_the_script_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """With judge_model=none the missing file stays missed and no judge is called."""
    stub = StubJudge("modes/bug-fix.md: READ")
    result = await score([], stub=stub, monkeypatch=monkeypatch, model="none")
    assert result.value == 0 and stub.prompts == [] and result.metadata["decided_by"] == "script"


async def test_no_score_for_other_conditions_or_cases_without_reads(monkeypatch: pytest.MonkeyPatch) -> None:
    """Other conditions and cases that expect no reads get no score and no judge call."""
    stub = StubJudge()
    assert await score([], stub=stub, monkeypatch=monkeypatch, condition="no-skill") is None
    assert await score([], stub=stub, monkeypatch=monkeypatch, expected=[]) is None
    assert stub.prompts == []


class FailingJudge:
    """A judge call that fails the way a sandbox or CLI failure does: by raising."""

    def __init__(self, error: Exception) -> None:
        """Raise `error` when called."""
        self.error = error

    async def __call__(self, system: str, prompt: str, model: str) -> tuple[str, dict[str, Any]]:
        """Raise the error."""
        raise self.error


@pytest.mark.parametrize("error", [RuntimeError("sandbox gone"), TimeoutError("slow"), OSError("pipe")])
async def test_judge_that_raises_is_a_grading_error_naming_skill_reads(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    """A judge call that raises is a grading error that names the scorer, not an uncounted failure."""
    monkeypatch.setattr(reads, "ask_judge", FailingJudge(error))
    state = SimpleNamespace(
        metadata={"condition": "skill", "skill": "code-better", "reads": ["modes/bug-fix.md"]},
        messages=[ChatMessageUser(content="Fix it")],
    )
    with pytest.raises(GradingError, match="skill_reads"):
        await reads.skill_reads("opus")(state, None)  # type: ignore[arg-type]
