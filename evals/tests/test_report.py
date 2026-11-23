"""Tests for tools/report.py: the pass-rate table, the sample lines and judge agreement."""

import math
import random
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from tools import report


def result(**fields: Any) -> report.SampleResult:
    """One run of sample a-skill (case a, rule 1.1, passed) with the given fields changed."""
    return report.SampleResult(
        **{"sample_id": "a-skill", "case": "a", "condition": "skill", "rule": "1.1", "passed": 1.0, **fields}
    )


def verdict(passed: bool | None, **fields: Any) -> dict[str, Any]:
    """The judges field of a run whose judge gave this verdict."""
    return {"judge": {"verdict": passed, **fields}}


def rows() -> list[report.SampleResult]:
    """Three samples over two rules and two conditions, one of them errored."""
    return [
        result(
            sample_id="a-no-skill",
            condition="no-skill",
            tokens={"input_tokens": 5},
            cost=0.5,
            judge_cost=0.1,
            seconds=30,
            judges=verdict(True),
        ),
        result(passed=0, tokens={"input_tokens": 7}, cost=0.7, judge_cost=0.1, seconds=40, judges=verdict(False)),
        result(
            sample_id="b-no-skill",
            case="b",
            condition="no-skill",
            rule="invocation",
            passed=math.nan,
            error="RuntimeError: 429",
        ),
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
    assert report.holm_adjusted([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])


def test_sign_flip_p_value_separates_a_clear_effect_from_none() -> None:
    """Every case improving gives a small p-value; differences that cancel out give a large one."""
    assert report.sign_flip_p_value([1.0] * 12, random.Random(0)) < 0.01
    assert report.sign_flip_p_value([1.0, -1.0] * 6, random.Random(0)) > 0.5


def test_comparison_lines_and_category_rows_share_one_interval() -> None:
    """Differences 1, 1, 1, 0 give the same t-interval, that crosses zero, in the full report and in the PR table."""
    passed = {"skill": [1, 1, 1, 0], "no-skill": [0, 0, 0, 0]}
    runs = [
        result(sample_id=f"c{n}-{c}", case=f"c{n}", condition=c, passed=v)
        for c, vs in passed.items()
        for n, v in enumerate(vs)
    ]
    assert "[-0.045, +1.546]" in report.comparison_lines(runs)[1]
    _, found = report.category_rows(runs, [{"name": "A", "does": "a", "cases": ["c0", "c1", "c2", "c3"]}])
    assert (found[0].low, found[0].high) == pytest.approx(report.mean_interval([1, 1, 1, 0])[1:])
    assert found[0].mark() == "="


def test_condition_cost_lines() -> None:
    """One line per condition with runs, mean and median cost and time; errored runs are left out."""
    lines = report.condition_cost_lines(rows())
    assert lines[1].split()[:3] == ["no-skill", "1", "0.500"]
    assert lines[2].split()[:3] == ["skill", "1", "0.700"]


def test_latest_keeps_the_newest_log_per_case_and_condition_and_agent_model() -> None:
    """A re-run replaces the earlier runs of the same case and condition; other cases and agent models stay."""
    old, new = result(passed=0, started="2026-01-01"), result(passed=1, started="2026-01-02")
    other = result(sample_id="a-no-skill", condition="no-skill", started="2026-01-01")
    assert report.latest([old, new, other]) == [new, other]
    opus, sonnet = result(agent_model="opus", started="2026-01-01"), result(agent_model="sonnet", started="2026-01-02")
    assert report.latest([opus, sonnet]) == [opus, sonnet]


def test_skill_read_lines() -> None:
    """Expected files count per run where expected; files no case expected are listed separately."""
    expected = [["modes/feature.md", "modes/bug-fix.md"], "agents/verifier.md"]
    labels = ["modes/feature.md or modes/bug-fix.md", "agents/verifier.md"]
    results = [
        result(
            expected_reads=expected,
            skill_reads={
                "expected": labels,
                "missing": [],
                "read": {"modes/bug-fix.md": "main", "agents/verifier.md": "sub-agent"},
            },
        ),
        result(
            expected_reads=expected,
            skill_reads={
                "expected": labels,
                "missing": ["agents/verifier.md"],
                "read": {"modes/feature.md": "main", "modes/coordinate.md": "main"},
            },
        ),
    ]
    lines = report.skill_read_lines([*results, *rows()])
    assert lines[0] == "Runs that read every expected file: 1/2"
    assert any(line.split()[:2] == ["agents/verifier.md", "1/2"] for line in lines)
    assert any(line.split()[-1] == "2/2" and line.startswith("modes/feature.md or") for line in lines)
    assert lines[-1].split() == ["modes/coordinate.md", "1"]
    assert report.skill_read_lines(rows()) == ["No run tracked skill reads."]


def scores_of(**fields: Any) -> SimpleNamespace:
    """A log sample of case a in condition skill with the given scores and fields."""
    metadata = {"case": "a", "condition": "skill", "rule": "5.1", **fields.pop("metadata", {})}
    return SimpleNamespace(**{"id": "a-skill", "epoch": 1, "error": None, "scores": {}, "metadata": metadata, **fields})


def test_missed_read_keeps_the_rule_only_score() -> None:
    """A skill run that missed a read fails, but keeps the rule scorer's `all` as its rule-only score."""
    rule = SimpleNamespace(value={"judge": 1, "all": 1}, metadata={})
    reads = SimpleNamespace(
        value=0, metadata={"expected": ["modes/bug-fix.md"], "read": {}, "missing": ["modes/bug-fix.md"]}
    )
    sample = scores_of(scores={"grade_cases": rule, "skill_reads": reads})
    found = report.read_result(sample)  # type: ignore[arg-type]
    assert found.passed == 0 and found.rule_passed == 1
    assert found.skill_reads["missing"] == ["modes/bug-fix.md"]
    reads.value = 1
    assert report.read_result(sample).passed == 1  # type: ignore[arg-type]


def test_lint_lines() -> None:
    """Lint counts are averaged per condition over runs that changed Python; others are left out."""
    results = [result(lint_issues=2), result(lint_issues=0), result()]
    assert report.lint_lines(results)[1].split() == ["skill", "2", "1.00", "1"]
    assert report.lint_lines(rows()) == ["No run counted lint issues."]


def test_rule_key_orders_invocation_then_names() -> None:
    """Invocation first, then named rules alphabetically."""
    rules = ["report-accurately", "ask-or-proceed", "invocation"]
    assert sorted(rules, key=report.rule_key) == ["invocation", "ask-or-proceed", "report-accurately"]


def error_rows() -> list[report.SampleResult]:
    """One scored sample and one sample error of each cause, in two conditions."""
    return [
        result(tokens={"input_tokens": 5}, cost=0.5, judge_cost=0.1, seconds=30),
        result(case="b", passed=math.nan, error="Grading error: judge: timed out after 600 seconds"),
        result(
            case="c",
            condition="no-skill",
            passed=math.nan,
            error="RuntimeError: Claude Code timed out after 1800 seconds",
        ),
        result(case="d", condition="no-skill", passed=math.nan, error="RuntimeError: 429"),
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
    sample = scores_of(error=SimpleNamespace(message="Grading error: judge: 429"))
    assert report.read_result(sample).error == "Grading error: judge: 429"  # type: ignore[arg-type]


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
    log = SimpleNamespace(
        eval=SimpleNamespace(metadata=metadata), stats=SimpleNamespace(started_at="t"), samples=[scores_of()]
    )
    monkeypatch.setattr(report, "read_eval_log", lambda path: log)
    (found,) = report.read_results([Path("x.eval")])
    assert (found.skill, found.agent_model, found.judge_model) == ("code-better", "opus", "sonnet")
    assert (found.agent_version, found.skill_commit, found.skill_dirty) == ("2.1.0", "abc1234def", True)
    log.eval.metadata = {}
    assert report.read_results([Path("x.eval")])[0].skill_dirty is None


def test_group_header_names_skill_models_version_and_commit_with_dirty_flag() -> None:
    """The header names what the section ran on; a dirty skill folder is flagged, an unknown one is marked."""
    run = result(skill="code-better", agent_model="opus", judge_model="sonnet", agent_version="2.1.0")
    run.skill_commit, run.skill_dirty = "abc1234def", True
    header = "\n".join(report.group_header([run]))
    assert "code-better" in header and "agent model opus" in header and "judge model sonnet" in header
    assert "Claude Code 2.1.0" in header and "abc1234 (dirty)" in header
    run.skill_dirty = False
    assert "dirty" not in "\n".join(report.group_header([run]))
    run.skill_dirty = None
    assert "abc1234 (dirty ?)" in "\n".join(report.group_header([run]))


def test_two_groups_print_two_sections_without_mixing_pass_rates(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """One section per (skill, agent model), each with its own header and pass rate."""
    runs = [
        result(skill="code-better", agent_model="opus"),
        result(skill="code-better", agent_model="sonnet", passed=0),
    ]
    monkeypatch.setattr(report, "read_results", lambda paths: runs)
    assert report.main(["x.eval"]) == 0
    out = capsys.readouterr().out
    first, second = out.split("# Skill code-better, agent model sonnet")[0], out.split("agent model sonnet")[1]
    assert out.count("# Skill code-better, agent model") == 2
    assert "agent model opus" in first and "100%" in first and "0%" not in first.replace("100%", "")
    assert "0/1" in second and "100%" not in second


def test_loaded_lines_per_case() -> None:
    """One row per case: runs, runs that loaded the skill, pass rate when loaded and when not."""

    def installed(case: str, loaded: float | None, passed: float, **fields: Any) -> report.SampleResult:
        return result(case=case, condition="skill-installed", skill_loaded=loaded, passed=passed, **fields)

    results = [
        installed("a", 1.0, 1),
        installed("a", 1.0, 0),
        installed("a", 0.0, 0),
        installed("b", 0.0, 1),
        installed("c", None, 1),  # not a skill-installed run
        installed("d", 1.0, math.nan, error="x"),
    ]
    lines = report.loaded_lines(results)
    assert lines[0].split() == ["case", "runs", "loaded", "pass", "loaded", "pass", "not", "loaded"]
    by_case = {line.split()[0]: line.split()[1:] for line in lines[1:]}
    assert by_case["a"] == ["3", "2", "50%", "0%"]
    assert by_case["b"] == ["1", "0", "-", "100%"]
    assert "c" not in by_case and "d" not in by_case
    assert report.loaded_lines(rows()) == ["No skill-installed runs."]


def test_every_comparison_names_known_conditions() -> None:
    """A renamed condition cannot leave a comparison that silently never runs."""
    from skill_evals.cases import CONDITIONS

    assert report.COMPARISONS
    assert all(name in CONDITIONS for pair in report.COMPARISONS for name in pair)


def test_resolve_labels() -> None:
    """A label must match exactly one run, by sample, epoch, grader and agent model; each row says what resolves or stops."""
    label = {"sample": "a-skill", "grader": "judge", "verdict": "PASS"}
    good = verdict(True)
    broken_judge = verdict(None, error="timed out")
    failed = {"passed": math.nan, "error": "RuntimeError: 429", "judges": {}}
    two_graders = {"judge": {"verdict": True}, "judge_2": {"verdict": False}}
    other = {"sample_id": "b-skill"}

    def runs(*kinds: dict[str, Any]) -> list[report.SampleResult]:
        return [result(started=f"t{n}", **kind) for n, kind in enumerate(kinds, 1)]

    opus, sonnet = {"agent_model": "opus", "log": "first.eval"}, {"agent_model": "sonnet", "log": "second.eval"}
    table = [
        # (name, runs, labels, stops with this message or resolves to these (epoch, agent model); latest first)
        ("same key twice", runs({"judges": good}, {"judges": good}), [label], "a-skill"),
        ("a copy whose judge failed", runs({"judges": good}, {"judges": broken_judge}), [label], "a-skill"),
        ("a copy that errored", runs({"judges": good}, failed), [label], "a-skill"),
        (
            "typo",
            runs({"judges": good}),
            [label, {**label, "sample": "a-skil", "epoch": 2}],
            r"a-skil.*epoch 2.*no run",
        ),
        (
            "two agent models",
            runs({"judges": good, **opus}, {"judges": good, **sonnet}),
            [label],
            r"a-skill.*opus.*first\.eval.*sonnet.*second\.eval",
        ),
        (
            "agent model picks one",
            runs({"judges": good, **opus}, {"judges": good, **sonnet}),
            [{**label, "agent_model": "opus"}],
            [(1, "opus")],
        ),
        (
            "agent model without a run",
            runs({"judges": good, **opus}),
            [{**label, "agent_model": "haiku"}],
            r"a-skill.*no run",
        ),
        (
            "failed copy in another model",
            runs({"judges": good, **sonnet}, {**failed, **opus}),
            [label],
            r"a-skill.*(opus.*sonnet|sonnet.*opus)",
        ),
        (
            "judge-failed copy in another model",
            runs({"judges": good, **sonnet}, {"judges": broken_judge, **opus}),
            [label],
            r"a-skill.*(opus.*sonnet|sonnet.*opus)",
        ),
        (
            "model picked past a failed copy",
            runs({"judges": good, **sonnet}, {**failed, **opus}),
            [{**label, "agent_model": "sonnet"}],
            [(1, "sonnet")],
        ),
        (
            "copy of an unlabelled sample",
            runs({"judges": good}, {**other, "judges": good}, {**other, "judges": broken_judge}),
            [label],
            [(1, "?")],
        ),
        (
            "other epochs and graders",
            [result(judges=two_graders), result(judges=two_graders, epoch=2)],
            [{**label, "epoch": 2}, {**label, "grader": "judge_2"}],
            [(2, "?"), (1, "?")],
        ),
    ]
    for name, found, labels, expected in table:
        if isinstance(expected, str):
            with pytest.raises(ValueError, match=expected):
                report.resolve_labels(found, labels)
        else:
            assert [(run.epoch, run.agent_model) for _, run in report.resolve_labels(found, labels)] == expected, name
    for second in ({"judges": broken_judge}, failed):  # --latest leaves the newest copy, so the label validates again
        assert len(report.resolve_labels(report.latest(runs({"judges": good}, second)), [label])) == 1


def test_agreement_compares_each_label_with_its_own_run(tmp_path: Path) -> None:
    """The label is compared with the run of its epoch, of the newest log after --latest, and of its agent model."""
    label = {"sample": "a-skill", "grader": "judge", "verdict": "PASS"}
    first, second = result(judges=verdict(False), started="t1"), result(judges=verdict(True), epoch=2, started="t1")
    assert report.agreement([first, second], [{**label, "epoch": 1, "verdict": "FAIL"}])[0].split()[-2:] == [
        "1/1",
        "agree",
    ]
    old, new = result(judges=verdict(True), started="t1"), result(judges=verdict(False), started="t2")
    assert report.agreement(report.latest([old, new]), [label])[0].split()[-2:] == ["0/1", "agree"]
    opus, sonnet = result(judges=verdict(True), agent_model="opus"), result(judges=verdict(False), agent_model="sonnet")
    picked = [{**label, "agent_model": "opus"}]
    assert report.unmatched_labels([opus, sonnet], picked) == []
    assert report.agreement([opus], picked)[0].split()[-2:] == ["1/1", "agree"]
    assert report.agreement([sonnet], picked) == ["no labelled judge verdicts in these logs"]
    other = result(sample_id="b-skill", judges=verdict(False), agent_model="sonnet")
    elsewhere = [{**label, "sample": "b-skill", "verdict": "FAIL"}]
    report.resolve_labels([opus, other], elsewhere)
    assert report.agreement([other], elsewhere)[-1].split()[-3:] == ["1/1", "agree", "(100%)"]
    assert report.agreement([opus], elsewhere) == ["no labelled judge verdicts in these logs"]
    two = [
        result(judges={"judge": {"verdict": True}, "judge_2": {"verdict": False}}),
        result(epoch=2, judges=verdict(False)),
    ]
    both = [{**label, "epoch": 2, "verdict": "FAIL"}, {**label, "grader": "judge_2", "verdict": "FAIL"}]
    assert report.agreement(two, both)[-1].split()[-3:] == ["2/2", "agree", "(100%)"]


def test_agreement_skips_a_judge_that_errored_and_lists_its_label() -> None:
    """A judge with no verdict because it could not run, or a sample error, is listed with its reason, not compared."""
    labels = [{"sample": "a-skill", "grader": "judge", "verdict": "PASS"}]
    for run, reason in (
        (result(judges=verdict(None, error="timed out")), "judge error"),
        (result(passed=math.nan, error="RuntimeError: 429"), "sample error"),
    ):
        lines = report.unmatched_labels([run], labels)
        assert len(lines) == 2 and reason in lines[1] and "a-skill" in lines[1]
        assert report.agreement([run], labels) == ["no labelled judge verdicts in these logs"]


def test_main_checks_labels_before_printing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """A label that spans groups, or has no run, stops before any section prints; a lone failed judge is listed after."""
    labels = tmp_path / "labels.yaml"

    def run_main(text: str, found: list[report.SampleResult]) -> None:
        labels.write_text(text)
        monkeypatch.setattr(report, "read_results", lambda paths: found)
        report.main(["x.eval", "--labels", str(labels)])

    good = verdict(True)
    opus, sonnet = result(agent_model="opus", judges=good), result(agent_model="sonnet", judges=verdict(False))
    twin = result(agent_model="sonnet", judges=verdict(False))
    wrong = "- {sample: a-skill, grader: judge, verdict: PASS%s}\n"
    for text, found, message in (
        (wrong % "", [opus, sonnet], "a-skill"),
        (wrong % ", agent_model: sonnet", [opus, sonnet, twin], "a-skill"),
        (wrong.replace("a-skill", "typo") % "", [opus], "typo"),
    ):
        with pytest.raises(SystemExit, match=message):
            run_main(text, found)
        assert capsys.readouterr().out == ""
    run_main(wrong % "", [result(judges=verdict(None, error="timed out"))])
    assert "## Labels without a verdict" in capsys.readouterr().out


def test_judge_cost_includes_the_skill_reads_judge() -> None:
    """The judge cost adds the reads judge's cost to the rule judges' cost."""
    rule = SimpleNamespace(value={"judge": 1, "all": 1}, metadata={"judges": {"judge": {"total_cost_usd": 0.25}}})
    reads = SimpleNamespace(value=1, metadata={"judge": {"total_cost_usd": 0.5}})
    sample = scores_of(scores={"grade_cases": rule, "skill_reads": reads})
    assert report.read_result(sample).judge_cost == pytest.approx(0.75)  # type: ignore[arg-type]


def run(case: str, condition: str, passed: float) -> report.SampleResult:
    """One scored run of a case, on Sonnet, from a log started on 2026-11-21."""
    return result(
        sample_id=f"{case}-{condition}",
        case=case,
        condition=condition,
        rule="r",
        passed=passed,
        started="2026-11-21T10:00:00",
        agent_model="sonnet",
    )


CATEGORIES = [
    {"name": "Owns", "does": "Owns the error", "cases": ["a1", "a2", "a3"]},
    {"name": "Reads", "does": "Reads the situation", "cases": ["b1"]},
]


def scored() -> list[report.SampleResult]:
    """No skill fails category Owns, the skill passes it; category Reads has one case."""
    return [
        run("a1", "no-skill", 0),
        run("a2", "no-skill", 0),
        run("a3", "no-skill", 0.5),
        run("a1", "skill", 1),
        run("a2", "skill", 1),
        run("a3", "skill", 1),
        run("b1", "no-skill", 1),
        run("b1", "skill", 0),
    ]


def test_category_rows_pair_cases_and_mark_only_a_clear_change() -> None:
    """A change whose interval excludes zero gets ▲; a one-case category has no interval and gets =."""
    columns, rows = report.category_rows(scored(), CATEGORIES)
    assert columns == ["no-skill", "skill"]
    assert rows[0].cases == 3 and rows[0].rates == {"no-skill": pytest.approx(1 / 6), "skill": 1.0}
    assert rows[0].mark() == "▲ +83" and rows[0].low is not None and rows[0].low > 0
    assert rows[1].low is None and rows[1].mark() == "="


def test_category_rows_compare_before_and_after() -> None:
    """With logs of the skill before the change, the change is after − before."""
    before = [run("a1", "skill", 1), run("a2", "skill", 1), run("a3", "skill", 1), run("b1", "skill", 1)]
    columns, rows = report.category_rows(scored(), CATEGORIES, before)
    assert columns == ["no-skill", "before", "after"]
    assert rows[0].change == 0 and rows[0].mark() == "="
    assert rows[1].change == -1


def test_case_outside_every_category_stops() -> None:
    """A case that ran but is in no category stops the report instead of dropping out."""
    with pytest.raises(SystemExit, match="c1"):
        report.category_rows([*scored(), run("c1", "skill", 1)], CATEGORIES)


def test_pr_lines_bold_the_compared_cells_of_a_clear_change() -> None:
    """The PR table names the columns, gives percentages and bolds only a clear change's compared cells."""
    columns, rows = report.category_rows(scored(), CATEGORIES)
    lines = report.pr_lines(columns, rows, scored())
    assert lines[0] == "Tested on 4 cases with sonnet."
    assert lines[2] == "| Category | Cases | No skill | Skill | Change |"
    assert lines[4] == "| 1 Owns | 3 | **17%** | **100%** | ▲ +83 |"
    assert lines[5] == "| 2 Reads | 1 | 100% | 0% | = |"


def test_docs_lines_show_what_the_skill_does_without_a_comparison() -> None:
    """The docs table gives the skill's pass rate per category, under what it does."""
    columns, rows = report.category_rows(scored(), CATEGORIES)
    lines = report.docs_lines(columns, rows, scored())
    assert lines[0] == "Tested on 4 situations with sonnet (2026-11-21)."
    assert lines[2:] == [
        "| What it does | Passed |",
        "| --- | ---: |",
        "| Owns the error | 100% |",
        "| Reads the situation | 0% |",
    ]


def test_chart_svg_draws_one_dot_per_category_and_an_interval_where_there_is_one() -> None:
    """The chart is valid SVG with a dot per category and an interval line only for several cases."""
    import xml.etree.ElementTree as ET

    _, rows = report.category_rows(scored(), CATEGORIES)
    root = ET.fromstring(report.chart_svg(rows))
    ns = "{http://www.w3.org/2000/svg}"
    assert len(root.findall(f"{ns}circle")) == 2
    assert len([line for line in root.findall(f"{ns}line") if line.get("stroke-width") == "3"]) == 1
    assert report.CHART_NOTE == "A 95% interval crossing zero means no clear change"
    assert report.CHART_NOTE in [text.text for text in root.findall(f"{ns}text")]


def test_load_priorities_checks_names_cases_and_duplicates(tmp_path: Path) -> None:
    """A missing file, an unknown case and a case in two categories each stop with the reason."""
    with pytest.raises(SystemExit, match="missing"):
        report.load_priorities("x", tmp_path)
    for case in ("a1", "b1"):
        (tmp_path / "x" / case).mkdir(parents=True)
        (tmp_path / "x" / case / "case.yaml").write_text("id: " + case)
    path = tmp_path / "x" / "priorities.yaml"
    path.write_text("categories:\n  - {name: A, does: a, cases: [a1, zz]}\n")
    with pytest.raises(SystemExit, match="zz"):
        report.load_priorities("x", tmp_path)
    path.write_text("categories:\n  - {name: A, does: a, cases: [a1]}\n  - {name: B, does: b, cases: [a1, b1]}\n")
    with pytest.raises(SystemExit, match="both"):
        report.load_priorities("x", tmp_path)


def test_every_priorities_file_covers_each_of_its_skills_cases_once() -> None:
    """Each skill's priorities.yaml loads and lists every case folder of that skill."""
    for path in sorted(report.CASES_DIR.glob(f"*/{report.PRIORITIES_FILE}")):
        listed = {case for category in report.load_priorities(path.parent.name) for case in category["cases"]}
        folders = {folder.name for folder in path.parent.iterdir() if (folder / "case.yaml").exists()}
        assert listed == folders, path


def test_main_prints_the_pr_table_and_writes_the_chart(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """`--pr --chart` prints the table of each skill and writes its chart; the full report is not printed."""
    monkeypatch.setattr(report, "read_results", lambda paths: scored())
    monkeypatch.setattr(report, "load_priorities", lambda skill: CATEGORIES)
    chart = tmp_path / "chart.svg"
    assert report.main(["x.eval", "--pr", "--chart", str(chart)]) == 0
    printed = capsys.readouterr().out
    assert "| 1 Owns | 3 | **17%** | **100%** | ▲ +83 |" in printed and "## Pass rate" not in printed
    assert chart.read_text().startswith("<svg")


def test_column_missing_a_case_stops() -> None:
    """A case scored in one column but not another stops the report, naming the case and the column."""
    runs = [r for r in scored() if not (r.case == "a3" and r.condition == "no-skill")]
    with pytest.raises(SystemExit, match=r"a3 \(No skill\)"):
        report.category_rows(runs, CATEGORIES)


def test_change_that_rounds_to_zero_points_is_equal() -> None:
    """A change under half a point is = even when its interval excludes zero."""
    assert report.CategoryRow("A", "a", 3, {}, 0.004, 0.004, 0.004).mark() == "="
    assert report.CategoryRow("A", "a", 3, {}, -0.004, -0.004, -0.004).mark() == "="


def test_chart_escapes_category_names() -> None:
    """A category name with & or < still gives valid SVG."""
    import xml.etree.ElementTree as ET

    ET.fromstring(report.chart_svg([report.CategoryRow("a & <b>", "a", 2, {}, 0.1, 0.0, 0.2)]))


def test_before_without_runs_of_the_group_stops(monkeypatch: pytest.MonkeyPatch) -> None:
    """--before logs of another model or skill stop the report instead of showing no change."""
    other = [run("a1", "skill", 1)]
    other[0].agent_model = "opus"
    monkeypatch.setattr(report, "read_results", lambda paths: scored() if paths == [Path("x.eval")] else other)
    monkeypatch.setattr(report, "load_priorities", lambda skill: CATEGORIES)
    with pytest.raises(SystemExit, match="no runs"):
        report.main(["x.eval", "--pr", "--before", "old.eval"])


def test_tested_on_counts_only_cases_with_scored_runs() -> None:
    """A case whose every run errored is not counted as tested."""
    runs = [*scored(), result(case="z", passed=math.nan, error="429", started="2026")]
    assert report.tested_on(runs)[0] == 4
