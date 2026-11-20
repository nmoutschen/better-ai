"""Tests for skill_evals/grading/scorer.py: grader keys, any_of, skipped judges and the combined score."""

import math
from types import SimpleNamespace
from typing import Any

import pytest

from skill_evals.grading import scorer
from skill_evals.grading.judge import NO_JUDGE


def test_grader_keys_number_repeats() -> None:
    """Repeated types get numbered keys; single types keep their name."""
    specs = [{"type": "judge"}, {"type": "command_passes"}, {"type": "command_passes"}]
    assert list(scorer.grader_keys(specs)) == ["judge", "command_passes_1", "command_passes_2"]


def test_combine_skips_nan() -> None:
    """`all` passes when every grader that applies passes; NaN when none applies."""
    assert scorer.combine({"a": 1, "b": math.nan}) == 1
    assert scorer.combine({"a": 1, "b": 0}) == 0
    assert math.isnan(scorer.combine({"a": math.nan}))


def test_applied_mean_ignores_nan() -> None:
    """The metric averages only samples where the grader applies."""
    scores = [SimpleNamespace(score=SimpleNamespace(value=value)) for value in (1, 0, math.nan)]
    assert scorer.applied_mean()(scores) == 0.5  # type: ignore[arg-type]


async def test_any_of_stops_at_first_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    """A passing deterministic check means the judge after it never runs."""
    calls: list[str] = []

    async def passes(spec: dict[str, Any], repo: Any) -> bool:
        calls.append("check")
        return True

    async def judge(*args: Any) -> tuple[bool, dict[str, Any]]:
        calls.append("judge")
        return False, {}

    monkeypatch.setitem(scorer.GRADERS, "check", passes)
    monkeypatch.setattr(scorer, "judge", judge)
    grading = scorer.Grading(SimpleNamespace(), SimpleNamespace(), "opus")  # type: ignore[arg-type]
    assert await grading.run("any_of", {"type": "any_of", "graders": [{"type": "check"}, {"type": "judge"}]}) == 1
    assert calls == ["check"]


async def test_skipped_judge_is_nan(monkeypatch: pytest.MonkeyPatch) -> None:
    """With judging off, a judge is NaN, and so is any_of when nothing else passed."""

    async def fails(spec: dict[str, Any], repo: Any) -> bool:
        return False

    monkeypatch.setitem(scorer.GRADERS, "check", fails)
    grading = scorer.Grading(SimpleNamespace(), SimpleNamespace(), NO_JUDGE)  # type: ignore[arg-type]
    assert math.isnan(await grading.run("judge", {"type": "judge", "rubric": "r"}))
    assert math.isnan(
        await grading.run("any_of", {"type": "any_of", "graders": [{"type": "check"}, {"type": "judge"}]})
    )
    with pytest.raises(ValueError, match="Unknown grader"):
        await grading.run("x", {"type": "nonsense"})


async def test_judge_verdict_is_recorded(monkeypatch: pytest.MonkeyPatch) -> None:
    """The judge's info is kept under its grader key."""

    async def judge(*args: Any) -> tuple[bool, dict[str, Any]]:
        return True, {"verdict": True}

    monkeypatch.setattr(scorer, "judge", judge)
    grading = scorer.Grading(SimpleNamespace(), SimpleNamespace(), "opus")  # type: ignore[arg-type]
    assert await grading.run("judge", {"type": "judge", "rubric": "r"}) == 1
    assert grading.judges == {"judge": {"verdict": True}}


async def test_judge_that_could_not_run_is_an_error_not_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """No verdict gives NaN and a recorded error, and `all` of the sample is unscored."""

    async def judge(*args: Any) -> tuple[None, dict[str, Any]]:
        return None, {"verdict": None, "error": "timed out"}

    monkeypatch.setattr(scorer, "judge", judge)
    grading = scorer.Grading(SimpleNamespace(), SimpleNamespace(), "opus")  # type: ignore[arg-type]
    assert math.isnan(await grading.run("judge", {"type": "judge", "rubric": "r"}))
    assert grading.errors == {"judge": "timed out"}


async def test_any_of_with_a_pass_ignores_an_errored_judge(monkeypatch: pytest.MonkeyPatch) -> None:
    """A later passing grader settles any_of, so an earlier judge error is not an error of the sample."""

    async def judge(*args: Any) -> tuple[None, dict[str, Any]]:
        return None, {"verdict": None, "error": "timed out"}

    async def passes(spec: dict[str, Any], repo: Any) -> bool:
        return True

    monkeypatch.setattr(scorer, "judge", judge)
    monkeypatch.setitem(scorer.GRADERS, "check", passes)
    grading = scorer.Grading(SimpleNamespace(), SimpleNamespace(), "opus")  # type: ignore[arg-type]
    spec = {"type": "any_of", "graders": [{"type": "judge", "rubric": "r"}, {"type": "check"}]}
    assert await grading.run("any_of", spec) == 1 and grading.errors == {}
    spec = {"type": "any_of", "graders": [{"type": "judge", "rubric": "r"}]}
    assert math.isnan(await grading.run("any_of", spec)) and "any_of" in grading.errors


async def test_score_marks_errors_and_leaves_all_unscored(monkeypatch: pytest.MonkeyPatch) -> None:
    """A raising grader and a judge without a verdict are not 0: `all` is NaN and metadata names each error."""

    async def raises(spec: dict[str, Any], repo: Any) -> bool:
        raise OSError("sandbox gone")

    async def judge(*args: Any) -> tuple[None, dict[str, Any]]:
        return None, {"verdict": None, "error": "timed out"}

    async def commits(repo: Any) -> int:
        return 0

    monkeypatch.setitem(scorer.GRADERS, "check", raises)
    monkeypatch.setattr(scorer, "judge", judge)
    monkeypatch.setattr(scorer, "commits_since_start", commits)
    monkeypatch.setattr(scorer, "sandbox", lambda: None)
    monkeypatch.setattr(scorer, "Checkout", lambda *args: SimpleNamespace(notes=[]))
    graders = [{"type": "check"}, {"type": "judge", "rubric": "r"}]
    state = SimpleNamespace(
        store=SimpleNamespace(get=lambda key: "abc"), metadata={"graders": graders, "rule": "1", "condition": "skill"}
    )
    result = await scorer.grade_cases(["check", "judge"], "opus")(state, None)  # type: ignore[arg-type]
    assert math.isnan(result.value["all"]) and math.isnan(result.value["check"]) and math.isnan(result.value["judge"])
    assert set(result.metadata["grading_errors"]) == {"check", "judge"}
    assert "sandbox gone" in result.metadata["grading_errors"]["check"]
