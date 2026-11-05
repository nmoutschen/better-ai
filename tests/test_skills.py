"""Runs every suite in tests/suites. Adding a skill means adding one suite file."""

import importlib
from pathlib import Path

import pytest

from harness import (
    Damage,
    Effect,
    Settings,
    SkillEval,
    compare,
    run_arm_once,
    score,
)


SUITES = [
    importlib.import_module(f"suites.{path.stem}").EVAL
    for path in sorted((Path(__file__).parent / "suites").glob("*.py"))
]
HOLDOUT = Settings.from_env().holdout


def _selected(items):
    return [item for item in items if HOLDOUT or not item.holdout]


EFFECTS = [
    pytest.param(suite, effect, id=f"{suite.skill}-{effect.id}")
    for suite in SUITES
    for effect in _selected(suite.effects)
]


def _damages(suite: SkillEval, effect: Effect) -> list[Damage]:
    checks = (*effect.checks, *suite.shared_checks)
    dimensions = {check.dimension for check in checks}
    return [d for d in (*effect.damages, *suite.shared_damages) if d.dimension in dimensions]


DAMAGES = [
    pytest.param(suite, effect, damage, id=f"{suite.skill}-{effect.id}-{damage.dimension}-{damage.name}")
    for suite in SUITES
    for effect in _selected(suite.effects)
    for damage in _damages(suite, effect)
]
UNDAMAGED_RUNS = {}  # One real run per effect, shared by all of its damage checks.


def _run_arm(suite: SkillEval, effect: Effect, with_skill: bool, settings: Settings) -> list[dict]:
    samples = []
    for _ in range(settings.samples):
        trace = run_arm_once(suite, effect, with_skill, settings)
        samples.append(
            {
                "scores": score((*effect.checks, *suite.shared_checks), effect.task, trace, settings),
                "metrics": trace.metrics,
                "output": trace.output,
                "steps": trace.steps,
                "source": trace.source,
            }
        )
    return samples


@pytest.mark.parametrize("suite,effect", EFFECTS)
def test_effect(suite: SkillEval, effect: Effect, settings: Settings, run_log) -> None:
    baseline = _run_arm(suite, effect, False, settings)
    skill = _run_arm(suite, effect, True, settings)
    run_log.effects.append(
        {"suite": suite.skill, "effect": effect.id, "skill": skill, "baseline": baseline}
    )
    worse = []
    for dimension in skill[0]["scores"]:
        with_skill = [sample["scores"][dimension] for sample in skill]
        without = [sample["scores"][dimension] for sample in baseline]
        verdict = compare(with_skill, without, settings)
        print(f"{dimension}: skill {with_skill}, baseline {without}: {verdict}")
        if verdict == "worse" and dimension not in suite.report_only:
            worse.append(dimension)
    assert not worse, f"The skill made these dimensions worse: {worse}"


@pytest.mark.parametrize("suite,effect,damage", DAMAGES)
def test_judge_notices_damage(
    suite: SkillEval, effect: Effect, damage: Damage, settings: Settings
) -> None:
    """Negative test: damaging a real run must lower the score of the dimension it damages."""
    key = (suite.skill, effect.id)
    if key not in UNDAMAGED_RUNS:
        # A baseline may not use its tools at all, which would leave a trajectory nothing to damage.
        UNDAMAGED_RUNS[key] = run_arm_once(suite, effect, bool(effect.tools), settings)
    trace = UNDAMAGED_RUNS[key]
    damaged = damage.apply(trace)
    if damaged == trace:
        pytest.skip("This run has nothing for the damage to change.")
    checks = tuple(
        check
        for check in (*effect.checks, *suite.shared_checks)
        if check.dimension == damage.dimension
    )
    before = score(checks, effect.task, trace, settings)[damage.dimension]
    if before < 0.4:
        pytest.skip(f"The undamaged run already scores {before:.2f}, so a drop can't be measured.")
    after = score(checks, effect.task, damaged, settings)[damage.dimension]
    print(f"{damage.dimension}/{damage.name}: {before:.2f} before damage, {after:.2f} after")
    if damage.dimension in suite.report_only:
        return
    assert before - after >= 0.2, f"{damage.dimension} only moved {before:.2f} -> {after:.2f}"
