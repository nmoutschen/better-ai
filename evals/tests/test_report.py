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


def test_rule_key_orders_invocation_numbers_then_names() -> None:
    """Invocation first, numbered rules in numeric order, then named rules alphabetically."""
    rules = ["report-accurately", "1.10", "ask-or-proceed", "1.2", "invocation"]
    assert sorted(rules, key=report.rule_key) == ["invocation", "1.2", "1.10", "ask-or-proceed", "report-accurately"]
