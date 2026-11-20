"""Tests for tools/report.py: the pass-rate table, the sample lines and judge agreement."""

import math
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import report


def rows() -> list[report.SampleResult]:
    """Three samples over two rules and two conditions, one of them errored."""
    return [
        report.SampleResult(
            "a-no-skill", "a", "no-skill", "1.1", 1, {"input_tokens": 5}, 0.5, 0.1, 30, {"judge": {"verdict": True}}
        ),
        report.SampleResult(
            "a-skill", "a", "skill", "1.1", 0, {"input_tokens": 7}, 0.7, 0.1, 40, {"judge": {"verdict": False}}
        ),
        report.SampleResult("b-no-skill", "b", "no-skill", "invocation", math.nan, error="RuntimeError: 429"),
    ]


def test_pass_table_skips_errors() -> None:
    """Errored samples are not counted; rules sort with invocation first."""
    table = report.pass_table(rows())
    assert table[0].split() == ["rule", "no-skill", "skill"]
    assert table[1].split()[:3] == ["1.1", "1/1", "100%"] and "0/1" in table[1]
    assert len(table) == 2


def test_case_lines_total() -> None:
    """Totals add tokens, cost, judge cost and time, and count errors."""
    total = report.case_lines(rows())[-1]
    assert "3 samples, 1 errors" in total and "12/0/0/0" in total and "1.200" in total


def test_agreement(tmp_path: Path) -> None:
    """Agreement is per rubric (case and grader) and overall; unknown samples are ignored."""
    labels = tmp_path / "labels.yaml"
    labels.write_text(
        "- {sample: a-no-skill, grader: judge, verdict: PASS}\n- {sample: a-skill, grader: judge, verdict: PASS}\n"
        "- {sample: zz, grader: judge, verdict: FAIL}\n"
    )
    lines = report.agreement(rows(), report.load_labels(labels))
    assert lines[0].split()[-2:] == ["1/2", "agree"] and "50%" in lines[-1]


def test_bad_label(tmp_path: Path) -> None:
    """A verdict other than PASS or FAIL is rejected."""
    labels = tmp_path / "labels.yaml"
    labels.write_text("- {sample: a-no-skill, grader: judge, verdict: maybe}\n")
    with pytest.raises(ValueError):
        report.load_labels(labels)


def test_holm_adjusted_keeps_order_and_is_monotone() -> None:
    """Holm's correction multiplies the smallest p-value by the number of tests and never decreases."""
    from tools.report import holm_adjusted

    assert holm_adjusted([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])


def test_sign_flip_p_value_separates_a_clear_effect_from_none() -> None:
    """Every case improving gives a small p-value; differences that cancel out give a large one."""
    import random

    from tools.report import sign_flip_p_value

    assert sign_flip_p_value([1.0] * 12, random.Random(0)) < 0.01
    assert sign_flip_p_value([1.0, -1.0] * 6, random.Random(0)) > 0.5


def test_bootstrap_interval_contains_the_mean() -> None:
    """The 95% interval of a mean difference contains that mean."""
    import random

    from tools.report import bootstrap_interval

    differences = [1.0, 0.0, 1.0, 1.0, 0.0, 0.5]
    low, high = bootstrap_interval(differences, random.Random(0))
    assert low <= sum(differences) / len(differences) <= high


def test_agreement_matches_the_labelled_run(tmp_path: Path) -> None:
    """With several runs of a sample, a label is compared with the judge verdict of its own epoch."""
    second = report.SampleResult(
        "a-skill", "a", "skill", "1.1", 1, {}, 0.7, 0.1, 40, {"judge": {"verdict": True}}, epoch=2
    )
    labels = tmp_path / "labels.yaml"
    labels.write_text("- {sample: a-skill, epoch: 1, grader: judge, verdict: FAIL}\n")
    lines = report.agreement([*rows(), second], report.load_labels(labels))
    assert lines[0].split()[-2:] == ["1/1", "agree"]


def test_condition_cost_lines() -> None:
    """One line per condition with runs, mean and median cost and time; errored runs are left out."""
    lines = report.condition_cost_lines(rows())
    assert lines[1].split()[:3] == ["no-skill", "1", "0.500"]
    assert lines[2].split()[:3] == ["skill", "1", "0.700"]


def test_latest_keeps_the_newest_log_per_case_and_condition() -> None:
    """A re-run replaces the earlier runs of the same case and condition and leaves the others."""
    old = report.SampleResult("a-skill", "a", "skill", "1.1", 0, started="2026-01-01")
    new = report.SampleResult("a-skill", "a", "skill", "1.1", 1, started="2026-01-02")
    other = report.SampleResult("a-no-skill", "a", "no-skill", "1.1", 1, started="2026-01-01")
    assert report.latest([old, new, other]) == [new, other]


def test_skill_read_lines() -> None:
    """Expected files count per run where expected; files no case expected are listed separately."""
    tracked = [
        {
            "expected": ["modes/feature.md or modes/bug-fix.md", "agents/verifier.md"],
            "missing": [],
            "read": {"modes/bug-fix.md": "main", "agents/verifier.md": "sub-agent"},
        },
        {
            "expected": ["modes/feature.md or modes/bug-fix.md", "agents/verifier.md"],
            "missing": ["agents/verifier.md"],
            "read": {"modes/feature.md": "main", "modes/coordinate.md": "main"},
        },
    ]
    results = [
        report.SampleResult(f"{case}-skill", case, "skill", "1.1", 1, skill_reads=reads)
        for case, reads in zip("ab", tracked, strict=True)
    ]
    lines = report.skill_read_lines([*results, *rows()])
    assert lines[0] == "Runs that read every expected file: 1/2"
    assert any(line.split()[:2] == ["agents/verifier.md", "1/2"] for line in lines)
    assert any(line.split()[-1] == "2/2" and line.startswith("modes/feature.md or") for line in lines)
    assert lines[-1].split() == ["modes/coordinate.md", "1"]
    assert report.skill_read_lines(rows()) == ["No run tracked skill reads."]


def test_missed_read_keeps_the_rule_only_score() -> None:
    """A skill run that missed a read fails, but keeps the rule scorer's `all` as its rule-only score."""
    rule = SimpleNamespace(value={"judge": 1, "all": 1}, metadata={})
    reads = SimpleNamespace(
        value=0, metadata={"expected": ["modes/bug-fix.md"], "read": {}, "missing": ["modes/bug-fix.md"]}
    )
    sample = SimpleNamespace(
        id="a-skill",
        epoch=1,
        error=None,
        scores={"grade_cases": rule, "skill_reads": reads},
        metadata={"case": "a", "condition": "skill", "rule": "5.1"},
    )
    result = report.read_result(sample)  # type: ignore[arg-type]
    assert result.passed == 0 and result.rule_passed == 1
    assert result.skill_reads["missing"] == ["modes/bug-fix.md"]
    reads.value = 1
    assert report.read_result(sample).passed == 1  # type: ignore[arg-type]


def test_lint_lines() -> None:
    """Lint counts are averaged per condition over runs that changed Python; others are left out."""
    results = [
        report.SampleResult("a-skill", "a", "skill", "1.1", 1, lint_issues=2),
        report.SampleResult("b-skill", "b", "skill", "1.1", 1, lint_issues=0),
        report.SampleResult("c-skill", "c", "skill", "1.1", 1),
    ]
    lines = report.lint_lines(results)
    assert lines[1].split() == ["skill", "2", "1.00", "1"]
    assert report.lint_lines(rows()) == ["No run counted lint issues."]


def test_rule_key_orders_invocation_then_names() -> None:
    """Invocation first, then named rules alphabetically."""
    rules = ["report-accurately", "ask-or-proceed", "invocation"]
    assert sorted(rules, key=report.rule_key) == ["invocation", "ask-or-proceed", "report-accurately"]


def error_rows() -> list[report.SampleResult]:
    """One scored sample and one sample error of each cause, in two conditions."""
    return [
        report.SampleResult("a-skill", "a", "skill", "1.1", 1, {"input_tokens": 5}, 0.5, 0.1, 30),
        report.SampleResult(
            "b-skill", "b", "skill", "1.1", math.nan, error="Grading error: judge: timed out after 600 seconds"
        ),
        report.SampleResult(
            "c-no-skill",
            "c",
            "no-skill",
            "1.1",
            math.nan,
            error="RuntimeError: Claude Code timed out after 1800 seconds",
        ),
        report.SampleResult("d-no-skill", "d", "no-skill", "1.1", math.nan, error="RuntimeError: 429"),
    ]


def test_sample_errors_are_counted_per_condition_and_cause() -> None:
    """Per condition: samples, then errors by cause (agent timeout, grading error, other)."""
    lines = report.error_lines(error_rows())
    skill = next(line for line in lines if line.startswith("skill "))
    no_skill = next(line for line in lines if line.startswith("no-skill"))
    assert skill.split()[1:] == ["2", "0", "1", "0"] and no_skill.split()[1:] == ["2", "1", "0", "1"]


def test_sample_errors_are_left_out_of_rates_and_means_but_finished_runs_keep_cost() -> None:
    """Pass rates and cost and time means use finished runs only, with their real cost; the total line counts errors."""
    assert "1/1" in report.pass_table(error_rows())[1]
    skill = next(line for line in report.condition_cost_lines(error_rows()) if line.startswith("skill "))
    assert skill.split()[1:3] == ["1", "0.500"]
    assert "4 samples, 3 errors" in report.case_lines(error_rows())[-1]


def test_read_result_keeps_the_error_text() -> None:
    """A sample error's message reaches the result, which the cause count reads."""
    sample = SimpleNamespace(
        id="x",
        epoch=1,
        error=SimpleNamespace(message="Grading error: judge: 429"),
        scores={},
        metadata={"case": "x", "condition": "skill"},
    )
    assert report.read_result(sample).error == "Grading error: judge: 429"  # type: ignore[arg-type]


def test_agreement_skips_a_judge_that_errored() -> None:
    """A judge with no verdict because it could not run is not a disagreement."""
    errored = report.SampleResult(
        "a-skill", "a", "skill", "1.1", 0, judges={"judge": {"verdict": None, "error": "timed out"}}
    )
    lines = report.agreement([errored], [{"sample": "a-skill", "grader": "judge", "verdict": "PASS"}])
    assert lines == ["no labelled judge verdicts in these logs"]


def judged(passed: bool, started: str = "") -> report.SampleResult:
    """One run of sample a-skill whose judge gave the verdict `passed`."""
    return report.SampleResult(
        "a-skill", "a", "skill", "1.1", 1, judges={"judge": {"verdict": passed}}, started=started
    )


def test_agreement_errors_on_two_runs_with_the_same_key() -> None:
    """Two logs with the same (sample, epoch, grader) cannot say which run a label belongs to."""
    labels = [{"sample": "a-skill", "grader": "judge", "verdict": "PASS"}]
    with pytest.raises(ValueError, match="a-skill"):
        report.agreement([judged(True, "2026-01-01"), judged(False, "2026-01-02")], labels)


def test_agreement_after_latest_uses_the_newest_run() -> None:
    """`--latest` keeps one run per sample, so the label is compared with that run."""
    labels = [{"sample": "a-skill", "grader": "judge", "verdict": "PASS"}]
    newest = report.latest([judged(True, "2026-01-01"), judged(False, "2026-01-02")])
    assert report.agreement(newest, labels)[0].split()[-2:] == ["0/1", "agree"]


def test_labels_without_a_run_are_listed() -> None:
    """A label whose sample is not in the logs, such as a typo, is printed, not dropped."""
    labels = [
        {"sample": "a-skill", "grader": "judge", "verdict": "PASS"},
        {"sample": "a-skil", "epoch": 2, "grader": "judge", "verdict": "FAIL"},
    ]
    lines = report.unmatched_labels([judged(True)], labels)
    assert len(lines) == 2 and "a-skil" in lines[1] and "epoch 2" in lines[1] and "a-skill" not in lines[1]
    assert report.unmatched_labels([judged(True)], labels[:1]) == []


def grouped(skill: str, model: str, passed: float, started: str = "") -> report.SampleResult:
    """One scored skill-condition run of case a for a (skill, agent model) group."""
    return report.SampleResult(
        f"a-skill-{model}", "a", "skill", "1.1", passed, skill=skill, agent_model=model, started=started
    )


def test_latest_keeps_runs_of_different_agent_models_apart() -> None:
    """A newer log of one agent model does not replace the runs of another agent model."""
    opus = grouped("code-better", "opus", 1, "2026-01-01")
    sonnet = grouped("code-better", "sonnet", 0, "2026-01-02")
    assert report.latest([opus, sonnet]) == [opus, sonnet]


def test_read_results_reads_the_run_description_from_the_log(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skill, agent model, judge model, Claude Code version and skill commit come from the eval metadata."""
    metadata = {
        "skill": "code-better",
        "agent_model": "opus",
        "judge_model": "sonnet",
        "agent_version": "2.1.0",
        "skill_commit": "abc1234def",
        "skill_dirty": True,
    }
    sample = SimpleNamespace(id="x", epoch=1, error=None, scores={}, metadata={"case": "x", "condition": "skill"})
    log = SimpleNamespace(
        eval=SimpleNamespace(metadata=metadata), stats=SimpleNamespace(started_at="t"), samples=[sample]
    )
    monkeypatch.setattr(report, "read_eval_log", lambda path: log)
    (result,) = report.read_results([Path("x.eval")])
    assert (result.skill, result.agent_model, result.judge_model) == ("code-better", "opus", "sonnet")
    assert (result.agent_version, result.skill_commit, result.skill_dirty) == ("2.1.0", "abc1234def", True)


def test_group_header_names_skill_models_version_and_commit_with_dirty_flag() -> None:
    """The header names what the section ran on; a dirty skill folder is flagged."""
    result = grouped("code-better", "opus", 1)
    result.judge_model, result.agent_version = "sonnet", "2.1.0"
    result.skill_commit, result.skill_dirty = "abc1234def", True
    header = "\n".join(report.group_header([result]))
    assert "code-better" in header and "agent model opus" in header and "judge model sonnet" in header
    assert "Claude Code 2.1.0" in header and "abc1234 (dirty)" in header
    result.skill_dirty = False
    assert "dirty" not in "\n".join(report.group_header([result]))


def test_two_groups_print_two_sections_without_mixing_pass_rates(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """One section per (skill, agent model), each with its own header and pass rate."""
    monkeypatch.setattr(
        report,
        "read_results",
        lambda paths: [grouped("code-better", "opus", 1), grouped("code-better", "sonnet", 0)],
    )
    assert report.main(["x.eval"]) == 0
    out = capsys.readouterr().out
    first, second = out.split("# Skill code-better, agent model sonnet")[0], out.split("agent model sonnet")[1]
    assert out.count("# Skill code-better, agent model") == 2
    assert "agent model opus" in first and "100%" in first and "0%" not in first.replace("100%", "")
    assert "0/1" in second and "100%" not in second


def test_labels_found_in_any_group_are_not_listed_as_unmatched() -> None:
    """The same sample id in two agent models' logs is not a duplicate across groups."""
    a, b = judged(True), judged(False)
    a.agent_model, b.agent_model = "opus", "sonnet"
    labels = [{"sample": "a-skill", "grader": "judge", "verdict": "PASS"}]
    assert report.unmatched_labels([a, b], labels) == []
    assert report.agreement([a], labels)[0].split()[-2:] == ["1/1", "agree"]
