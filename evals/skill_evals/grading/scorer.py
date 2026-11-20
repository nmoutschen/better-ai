"""Score one sample: run each of its case's graders and combine them into per-grader values and `all`.

Graders are deterministic file checks (`files.py`), a check on the transcript's commands (`commands.py`),
the judge (`judge.py`), or `any_of` a list of these. A case scores only its own rule, so `all` is the score for that rule; the rule, the condition, judge
replies and grader notes go into the score metadata. A grader that cannot apply in this run (a judge
when judging is off) scores NaN and is left out of `all`. A grader that could not run (the judge timed out, reported an
error or printed no reply, or a check hit a sandbox error) is not 0: the scorer raises `GradingError` naming the grader
and the cause, so the sample is an Inspect sample error that `inspect eval-retry` reruns (`inspect score` starts no
sandbox, so it cannot score it again). A hidden check that times out is a fail, not an error. Whether the agent read the skill's own files is a
separate scorer (`reads.py`), so `all` stays the rule's score.
"""

import math
from collections import Counter
from collections.abc import Iterator
from typing import Any

from inspect_ai.scorer import Metric, SampleScore, Score, Scorer, Target, metric, scorer
from inspect_ai.solver import TaskState
from inspect_ai.util import sandbox

from skill_evals.agent import WORKDIR
from skill_evals.grading import commands
from skill_evals.grading.files import GRADERS, Checkout, GradingError, commits_since_start
from skill_evals.grading.judge import NO_JUDGE, judge
from skill_evals.transcript import redact

NOT_APPLICABLE = float("nan")


def grader_keys(specs: list[dict[str, Any]]) -> Iterator[str]:
    """Name each grader by its type, numbering repeated types: judge, command_passes_1, command_passes_2."""
    counts = Counter(spec["type"] for spec in specs)
    seen: Counter[str] = Counter()
    for spec in specs:
        kind = spec["type"]
        seen[kind] += 1
        yield kind if counts[kind] == 1 else f"{kind}_{seen[kind]}"


class Grading:
    """Runs one sample's graders and collects their notes and judge replies."""

    def __init__(self, state: TaskState, repo: Checkout, judge_model: str) -> None:
        """Grade `state` against the checkout, judging with `judge_model` or not at all when it is "none"."""
        self.state, self.repo, self.judge_model = state, repo, judge_model
        self.judges: dict[str, dict[str, Any]] = {}

    async def run(self, key: str, spec: dict[str, Any]) -> float:
        """Return 1, 0, or NaN for a grader that does not apply in this run; raise GradingError when it could not run."""
        if spec["type"] == "any_of":
            return await self.run_any_of(key, spec)
        try:
            return await self.run_one(key, spec)
        except GradingError:
            raise
        except (RuntimeError, TimeoutError, OSError, UnicodeDecodeError) as error:
            raise GradingError(redact(f"{key}: {type(error).__name__}: {error}")) from error

    async def run_one(self, key: str, spec: dict[str, Any]) -> float:
        """Run one grader that is not `any_of`."""
        kind = spec["type"]
        if kind == "judge":
            if self.judge_model == NO_JUDGE:
                return NOT_APPLICABLE
            passed, info = await judge(spec, self.state, self.repo, self.judge_model)
            self.judges[key] = info
            if passed is None:
                raise GradingError(redact(f"{key}: judge could not run: {info.get('error', 'gave no verdict')}"))
            return int(passed)
        if kind == "ran_after_last_edit":
            return int(commands.ran_after_last_edit(spec, self.state.messages))
        if kind == "ran_command":
            return int(commands.ran_command(spec, self.state.messages))
        if kind not in GRADERS:
            raise ValueError(f"Unknown grader type: {kind!r}")
        return int(await GRADERS[kind](spec, self.repo))

    async def run_any_of(self, key: str, spec: dict[str, Any]) -> float:
        """Pass at the first inner grader that passes; else raise if one could not run, NaN if one did not apply, else 0."""
        # Stop at the first pass, so a judge listed after a deterministic check runs only when needed. A pass settles
        # any_of, so an inner grader that could not run before it no longer matters.
        skipped = False
        errors: list[str] = []
        for number, inner in enumerate(spec["graders"], 1):
            try:
                value = await self.run(f"{key}.{number}", inner)
            except GradingError as error:
                errors.append(error.detail)
                continue
            if value == 1:
                return 1
            skipped |= math.isnan(value)
        if errors:
            raise GradingError(f"{key}: no inner grader passed and one could not run: {'; '.join(errors)}")
        return NOT_APPLICABLE if skipped else 0


def combine(values: dict[str, float]) -> float:
    """Pass `all` when every grader that applies passes; NaN when none applies."""
    applied = [value for value in values.values() if not math.isnan(value)]
    return int(all(applied)) if applied else NOT_APPLICABLE


@metric
def applied_mean() -> Metric:
    """Mean over the samples where the grader applies, skipping NaN; NaN when it applies to none."""

    def compute(scores: list[SampleScore]) -> float:
        values = [float(sample.score.value) for sample in scores]  # type: ignore[arg-type]
        values = [value for value in values if not math.isnan(value)]
        return sum(values) / len(values) if values else NOT_APPLICABLE

    return compute


@scorer(metrics={"*": [applied_mean()]})
def grade_cases(keys: list[str], judge_model: str) -> Scorer:
    """Score each sample with its case's graders; `keys` lists every grader key in the task."""

    async def score(state: TaskState, target: Target) -> Score:
        repo = Checkout(sandbox(), state.store.get("start_commit"), WORKDIR)
        grading = Grading(state, repo, judge_model)
        values: dict[str, float] = {}
        for key, spec in zip(grader_keys(state.metadata["graders"]), state.metadata["graders"], strict=True):
            values[key] = await grading.run(key, spec)
        values["all"] = combine(values)
        # Side actions are measured on every sample but never scored: a case scores only its own rule.
        try:
            side_actions: dict[str, int] = {"commits": await commits_since_start(repo)}
        except (RuntimeError, TimeoutError, OSError, ValueError) as error:
            side_actions = {}
            repo.notes.append(redact(f"side actions: {type(error).__name__}: {error}"))
        for key in keys:
            values.setdefault(key, NOT_APPLICABLE)
        metadata: dict[str, Any] = {
            "rule": state.metadata["rule"],
            "condition": state.metadata["condition"],
            "side_actions": side_actions,
        }
        if grading.judges:
            metadata["judges"] = grading.judges
        if repo.notes:
            metadata["notes"] = repo.notes
        return Score(value=values, metadata=metadata)

    return score
