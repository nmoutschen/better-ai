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
