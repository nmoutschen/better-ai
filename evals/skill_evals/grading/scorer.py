"""Score one sample: run each of its case's graders and combine them into per-grader values and `all`.

Graders are deterministic file checks (`files.py`), the judge (`judge.py`), or `any_of` a list of
both. A case scores only its own rule, so `all` is the score for that rule; the rule, the condition, judge
replies and grader notes go into the score metadata. A grader that cannot apply in this run (a judge
when judging is off) scores NaN and is left out of `all`.
"""

import math
from collections import Counter
from collections.abc import Iterator
from typing import Any

from inspect_ai.scorer import Metric, SampleScore, Score, Scorer, Target, metric, scorer
from inspect_ai.solver import TaskState
from inspect_ai.util import sandbox

from skill_evals.agent import WORKDIR
from skill_evals.grading.files import GRADERS, Checkout, commits_since_start
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
        """Return 1, 0, or NaN for a grader that does not apply in this run."""
        kind = spec["type"]
        if kind == "any_of":
            # Stop at the first pass, so a judge listed after a deterministic check runs only when needed.
            skipped = False
            for number, inner in enumerate(spec["graders"], 1):
                value = await self.run(f"{key}.{number}", inner)
                if value == 1:
                    return 1
                skipped |= math.isnan(value)
            return NOT_APPLICABLE if skipped else 0
        if kind == "judge":
            if self.judge_model == NO_JUDGE:
                return NOT_APPLICABLE
            passed, info = await judge(spec, self.state, self.repo, self.judge_model)
            self.judges[key] = info
            return int(passed)
        if kind not in GRADERS:
            raise ValueError(f"Unknown grader type: {kind!r}")
        return int(await GRADERS[kind](spec, self.repo))


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


@scorer(metrics={})
def grade_cases(keys: list[str], judge_model: str) -> Scorer:
    """Score each sample with its case's graders; `keys` lists every grader key in the task."""

    async def score(state: TaskState, target: Target) -> Score:
        repo = Checkout(sandbox(), state.store.get("start_commit"), WORKDIR)
        grading = Grading(state, repo, judge_model)
        values: dict[str, float] = {}
        for key, spec in zip(grader_keys(state.metadata["graders"]), state.metadata["graders"], strict=True):
            try:
                values[key] = await grading.run(key, spec)
            except (RuntimeError, TimeoutError, OSError, UnicodeDecodeError) as error:
                values[key] = 0
                repo.notes.append(redact(f"{key}: {type(error).__name__}: {error}"))
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
