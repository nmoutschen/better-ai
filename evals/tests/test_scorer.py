"""Tests for skill_evals/grading/scorer.py: grader keys, any_of, skipped judges and the combined score."""

import math
from types import SimpleNamespace
from typing import Any

import pytest

from skill_evals.grading import scorer
from skill_evals.grading.files import GradingError
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


def judge_without_verdict(error: str = "timed out") -> Any:
    """A judge stub that could not run."""

    async def judge(*args: Any) -> tuple[None, dict[str, Any]]:
        return None, {"verdict": None, "error": error}

    return judge


async def passes(spec: dict[str, Any], repo: Any) -> bool:
    """A deterministic grader that passes."""
    return True


async def fails(spec: dict[str, Any], repo: Any) -> bool:
    """A deterministic grader that fails."""
    return False


async def sandbox_error(spec: dict[str, Any], repo: Any) -> bool:
    """A deterministic grader whose sandbox broke."""
    raise OSError("sandbox gone")


def grading() -> scorer.Grading:
    """A Grading with the stubs the tests below patch in."""
    return scorer.Grading(SimpleNamespace(), SimpleNamespace(), "opus")  # type: ignore[arg-type]


async def test_judge_that_could_not_run_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """No verdict is a grading error naming the grader and the cause, not a 0."""
    monkeypatch.setattr(scorer, "judge", judge_without_verdict("timed out"))
    with pytest.raises(GradingError, match="judge.*timed out"):
        await grading().run("judge", {"type": "judge", "rubric": "r"})


async def test_judge_reply_without_verdict_line_scores_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """A reply that is there but ends in no verdict is a 0, not an error."""

    async def judge(*args: Any) -> tuple[bool, dict[str, Any]]:
        return False, {"verdict": None, "malformed": "last line is not a verdict"}

    monkeypatch.setattr(scorer, "judge", judge)
    assert await grading().run("judge", {"type": "judge", "rubric": "r"}) == 0


async def test_deterministic_grader_sandbox_error_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """An OSError from a grader is a grading error that names the grader and the cause."""
    monkeypatch.setitem(scorer.GRADERS, "check", sandbox_error)
    with pytest.raises(GradingError, match="check.*OSError.*sandbox gone"):
        await grading().run("check", {"type": "check"})


@pytest.mark.parametrize(
    ("inner", "outcome"),
    [
        (["judge", "check"], 1),
        (["check", "judge"], 1),
        (["judge", "fails"], GradingError),
        (["judge"], GradingError),
        (["fails", "fails"], 0),
    ],
)
async def test_any_of_with_errors(monkeypatch: pytest.MonkeyPatch, inner: list[str], outcome: Any) -> None:
    """A later pass settles any_of even after an inner error; with no pass, an error makes it an error."""
    monkeypatch.setattr(scorer, "judge", judge_without_verdict())
    monkeypatch.setitem(scorer.GRADERS, "check", passes)
    monkeypatch.setitem(scorer.GRADERS, "fails", fails)
    specs = [{"type": "judge", "rubric": "r"} if name == "judge" else {"type": name} for name in inner]
    spec = {"type": "any_of", "graders": specs}
    if outcome is GradingError:
        with pytest.raises(GradingError, match="any_of"):
            await grading().run("any_of", spec)
    else:
        assert await grading().run("any_of", spec) == outcome


async def test_any_of_runs_later_graders_after_a_raising_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """An exception in an inner grader does not skip the inner graders after it."""
    monkeypatch.setitem(scorer.GRADERS, "broken", sandbox_error)
    monkeypatch.setitem(scorer.GRADERS, "check", passes)
    spec = {"type": "any_of", "graders": [{"type": "broken"}, {"type": "check"}]}
    assert await grading().run("any_of", spec) == 1


async def test_score_raises_so_the_sample_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """The scorer raises instead of returning a score when a grader could not run."""
    monkeypatch.setattr(scorer, "sandbox", lambda: None)
    monkeypatch.setattr(scorer, "Checkout", lambda *args: SimpleNamespace(notes=[]))
    monkeypatch.setattr(scorer, "judge", judge_without_verdict("429"))
    graders = [{"type": "judge", "rubric": "r"}]
    state = SimpleNamespace(
        store=SimpleNamespace(get=lambda key: "abc"), metadata={"graders": graders, "rule": "1", "condition": "skill"}
    )
    with pytest.raises(GradingError, match="judge.*429"):
        await scorer.grade_cases(["judge"], "opus")(state, None)  # type: ignore[arg-type]
