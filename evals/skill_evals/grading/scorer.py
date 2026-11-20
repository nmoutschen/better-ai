"""Score one sample: run each of its case's graders and combine them into per-grader values and `all`.

Graders are deterministic file checks (`files.py`), a check on the transcript's commands (`commands.py`),
the judge (`judge.py`), or `any_of` a list of these. A case scores only its own rule, so `all` is the score for that rule; the rule, the condition, judge
replies and grader notes go into the score metadata. A grader that cannot apply in this run (a judge
when judging is off) scores NaN and is left out of `all`. A grader that could not run (the judge timed out or
printed no reply, or a check raised) is not 0: it scores NaN, `all` is NaN too (unscored), and the metadata's
`grading_errors` names each such grader and why, so `inspect score` can score the run again. Whether the agent read the skill's own files is a
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
        self.errors: dict[str, str] = {}

    async def run(self, key: str, spec: dict[str, Any]) -> float:
        """Return 1, 0, or NaN for a grader that does not apply in this run or could not run (see `errors`)."""
        kind = spec["type"]
        if kind == "any_of":
            return await self.run_any_of(key, spec)
        if kind == "judge":
            if self.judge_model == NO_JUDGE:
                return NOT_APPLICABLE
            passed, info = await judge(spec, self.state, self.repo, self.judge_model)
            self.judges[key] = info
            if passed is None:
                self.errors[key] = info.get("error", "gave no verdict")
                return NOT_APPLICABLE
            return int(passed)
        if kind == "ran_after_last_edit":
            return int(commands.ran_after_last_edit(spec, self.state.messages))
        if kind == "ran_command":
            return int(commands.ran_command(spec, self.state.messages))
        if kind not in GRADERS:
            raise ValueError(f"Unknown grader type: {kind!r}")
        return int(await GRADERS[kind](spec, self.repo))

    async def run_any_of(self, key: str, spec: dict[str, Any]) -> float:
        """Pass at the first inner grader that passes; NaN when one could not run or did not apply, else 0."""
        # Stop at the first pass, so a judge listed after a deterministic check runs only when needed.
        skipped = False
        for number, inner in enumerate(spec["graders"], 1):
            value = await self.run(f"{key}.{number}", inner)
            if value == 1:
                # A pass settles any_of, so an inner grader that could not run no longer matters.
                for name in [name for name in self.errors if name.startswith(f"{key}.")]:
                    del self.errors[name]
                return 1
            skipped |= math.isnan(value)
        if any(name.startswith(f"{key}.") for name in self.errors):
            self.errors[key] = "an inner grader could not run"
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
            try:
                values[key] = await grading.run(key, spec)
            except (RuntimeError, TimeoutError, OSError, UnicodeDecodeError) as error:
                values[key] = NOT_APPLICABLE
                grading.errors[key] = redact(f"{type(error).__name__}: {error}")
                repo.notes.append(redact(f"{key}: {type(error).__name__}: {error}"))
        values["all"] = NOT_APPLICABLE if grading.errors else combine(values)
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
        if grading.errors:
            metadata["grading_errors"] = grading.errors
        if repo.notes:
            metadata["notes"] = repo.notes
        return Score(value=values, metadata=metadata)

    return score
