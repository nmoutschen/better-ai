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


def test_two_runs_with_the_same_key_stop_the_report() -> None:
    """Two logs with the same (sample, epoch, grader) cannot say which run a label belongs to."""
    labels = [{"sample": "a-skill", "grader": "judge", "verdict": "PASS"}]
    with pytest.raises(ValueError, match="a-skill"):
        report.resolve_labels([judged(True, "2026-01-01"), judged(False, "2026-01-02")], labels)


def test_agreement_after_latest_uses_the_newest_run() -> None:
    """`--latest` keeps one run per sample, so the label is compared with that run."""
    labels = [{"sample": "a-skill", "grader": "judge", "verdict": "PASS"}]
    newest = report.latest([judged(True, "2026-01-01"), judged(False, "2026-01-02")])
    assert report.agreement(newest, labels)[0].split()[-2:] == ["0/1", "agree"]


def test_label_matching_no_run_stops_and_is_named() -> None:
    """A label whose sample is not in the logs, such as a typo, stops the report and is named."""
    labels = [
        {"sample": "a-skill", "grader": "judge", "verdict": "PASS"},
        {"sample": "a-skil", "epoch": 2, "grader": "judge", "verdict": "FAIL"},
    ]
    with pytest.raises(ValueError, match=r"a-skil.*epoch 2.*no run") as stopped:
        report.resolve_labels([judged(True)], labels)
    assert "'a-skill'" not in str(stopped.value)
    assert [run.sample_id for _, run in report.resolve_labels([judged(True)], labels[:1])] == ["a-skill"]


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
    log.eval.metadata = {}
    assert report.read_results([Path("x.eval")])[0].skill_dirty is None


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


def two_model_runs() -> list[report.SampleResult]:
    """The same sample id judged in an opus group and a sonnet group."""
    a, b = judged(True), judged(False)
    a.agent_model, b.agent_model = "opus", "sonnet"
    return [a, b]


def test_label_matching_runs_of_two_agent_models_is_an_error() -> None:
    """A label has no agent model, so it cannot say which group's run it judged."""
    labels = [{"sample": "a-skill", "grader": "judge", "verdict": "PASS"}]
    runs = two_model_runs()
    runs[0].log, runs[1].log = "first.eval", "second.eval"
    with pytest.raises(ValueError, match=r"a-skill.*opus.*first\.eval.*sonnet.*second\.eval"):
        report.resolve_labels(runs, labels)


def test_label_with_agent_model_selects_one_group() -> None:
    """An agent_model field picks the group; agreement ignores labels for other models."""
    a, b = two_model_runs()
    labels = [{"sample": "a-skill", "grader": "judge", "verdict": "PASS", "agent_model": "opus"}]
    report.resolve_labels([a, b], labels)
    assert report.unmatched_labels([a, b], labels) == []
    assert [run.agent_model for _, run in report.resolve_labels([a, b], labels)] == ["opus"]
    assert report.agreement([a], labels)[0].split()[-2:] == ["1/1", "agree"]
    assert report.agreement([b], labels) == ["no labelled judge verdicts in these logs"]


def test_label_naming_a_model_with_no_run_stops() -> None:
    """A label for an agent model that has no such run matches no run."""
    labels = [{"sample": "a-skill", "grader": "judge", "verdict": "PASS", "agent_model": "haiku"}]
    with pytest.raises(ValueError, match=r"a-skill.*no run"):
        report.resolve_labels(two_model_runs(), labels)


def test_main_stops_before_printing_when_a_label_spans_groups(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """The ambiguity is found before the first section prints."""
    labels = tmp_path / "labels.yaml"
    labels.write_text("- {sample: a-skill, grader: judge, verdict: PASS}\n")
    monkeypatch.setattr(report, "read_results", lambda paths: two_model_runs())
    with pytest.raises(SystemExit, match="a-skill"):
        report.main(["x.eval", "--labels", str(labels)])
    assert capsys.readouterr().out == ""


def test_duplicate_run_in_a_later_group_stops_before_printing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """A label made ambiguous by a copy in the second group does not leave the first group printed."""
    runs = two_model_runs()
    twin = judged(False)
    twin.agent_model = "sonnet"
    labels = tmp_path / "labels.yaml"
    labels.write_text("- {sample: a-skill, grader: judge, verdict: PASS, agent_model: sonnet}\n")
    monkeypatch.setattr(report, "read_results", lambda paths: [*runs, twin])
    with pytest.raises(SystemExit):
        report.main(["x.eval", "--labels", str(labels)])
    assert capsys.readouterr().out == ""


def test_log_without_skill_dirty_shows_unknown() -> None:
    """Only a log that says the skill folder was clean is shown clean."""
    result = grouped("code-better", "opus", 1)
    result.skill_commit = "abc1234def"
    result.skill_dirty = None
    assert "abc1234 (dirty ?)" in "\n".join(report.group_header([result]))


def installed(case: str, loaded: float | None, passed: float) -> report.SampleResult:
    """One skill-installed run of a case that did or did not load the skill."""
    return report.SampleResult(f"{case}-skill-installed", case, "skill-installed", "r", passed, skill_loaded=loaded)


def test_loaded_lines_per_case() -> None:
    """One row per case: runs, runs that loaded the skill, pass rate when loaded and when not."""
    results = [
        installed("a", 1.0, 1),
        installed("a", 1.0, 0),
        installed("a", 0.0, 0),
        installed("b", 0.0, 1),
        installed("c", None, 1),  # not a skill-installed run
        report.SampleResult("d-skill-installed", "d", "skill-installed", "r", math.nan, skill_loaded=1.0, error="x"),
    ]
    lines = report.loaded_lines(results)
    assert lines[0].split() == ["case", "runs", "loaded", "pass", "loaded", "pass", "not", "loaded"]
    rows_ = {line.split()[0]: line.split()[1:] for line in lines[1:]}
    assert rows_["a"] == ["3", "2", "50%", "0%"]
    assert rows_["b"] == ["1", "0", "-", "100%"]
    assert "c" not in rows_ and "d" not in rows_
    assert report.loaded_lines(rows()) == ["No skill-installed runs."]


def test_every_comparison_names_known_conditions() -> None:
    """A renamed condition cannot leave a comparison that silently never runs."""
    from skill_evals.cases import CONDITIONS

    assert report.COMPARISONS
    assert all(name in CONDITIONS for pair in report.COMPARISONS for name in pair)


def test_comparisons_pinned() -> None:
    """The comparisons stay as they are."""
    assert report.COMPARISONS == (
        ("skill", "no-skill"),
        ("one-sentence", "no-skill"),
        ("short-skill", "no-skill"),
        ("skill", "one-sentence"),
        ("skill", "short-skill"),
        ("skill-installed", "no-skill"),
        ("skill", "skill-installed"),
    )


def errored_judge(started: str = "") -> report.SampleResult:
    """One run of sample a-skill whose judge could not run."""
    run = judged(True, started)
    run.judges = {"judge": {"verdict": None, "error": "timed out"}}
    return run


def sample_error(started: str = "") -> report.SampleResult:
    """One run of sample a-skill that failed before any grader ran."""
    return report.SampleResult("a-skill", "a", "skill", "1.1", math.nan, error="RuntimeError: 429", started=started)


def test_duplicate_with_one_errored_judge_stops() -> None:
    """The label cannot say which run it means, even when one copy's judge gave no verdict."""
    labels = [{"sample": "a-skill", "grader": "judge", "verdict": "PASS"}]
    with pytest.raises(ValueError, match="a-skill"):
        report.resolve_labels([judged(True, "t1"), errored_judge("t2")], labels)


def test_duplicate_with_a_sample_error_stops() -> None:
    """A copy that errored before grading still makes the label ambiguous."""
    labels = [{"sample": "a-skill", "grader": "judge", "verdict": "PASS"}]
    with pytest.raises(ValueError, match="a-skill"):
        report.resolve_labels([judged(True, "t1"), sample_error("t2")], labels)


def test_sample_error_copy_of_another_sample_does_not_stop() -> None:
    """Only a sample a label names makes a duplicate matter."""
    labels = [{"sample": "other", "grader": "judge", "verdict": "PASS"}]
    labelled = judged(True)
    labelled.sample_id = "other"
    report.resolve_labels([labelled, judged(True, "t1"), sample_error("t2")], labels)


def test_latest_resolves_duplicates_with_errors() -> None:
    """After `--latest` one run per sample is left, so the labels validate."""
    labels = [{"sample": "a-skill", "grader": "judge", "verdict": "PASS"}]
    for other in (errored_judge("t2"), sample_error("t2")):
        report.resolve_labels(report.latest([judged(True, "t1"), other]), labels)


def test_single_errored_judge_with_a_label_is_unmatched() -> None:
    """A judge that could not run gives no verdict, so its label is listed, not compared."""
    labels = [{"sample": "a-skill", "grader": "judge", "verdict": "PASS"}]
    report.resolve_labels([errored_judge()], labels)
    assert len(report.unmatched_labels([errored_judge()], labels)) == 2


def model_run(model: str, kind: str) -> report.SampleResult:
    """One run of sample a-skill by `model`: judged (True), `errored judge` or `sample error`."""
    run = {"judged": judged(True), "errored judge": errored_judge(), "sample error": sample_error()}[kind]
    run.agent_model = model
    return run


@pytest.mark.parametrize("kind", ["errored judge", "sample error"])
def test_label_with_one_copy_errored_in_another_model_stops(kind: str) -> None:
    """A copy with no verdict still counts as a match, so the label cannot be scored against the other model."""
    labels = [{"sample": "a-skill", "grader": "judge", "verdict": "PASS"}]
    with pytest.raises(ValueError, match=r"a-skill.*opus.*sonnet"):
        report.resolve_labels([model_run("opus", kind), model_run("sonnet", "judged")], labels)
    labels[0]["agent_model"] = "sonnet"
    assert [
        run.agent_model
        for _, run in report.resolve_labels([model_run("opus", kind), model_run("sonnet", "judged")], labels)
    ] == ["sonnet"]


@pytest.mark.parametrize(("kind", "reason"), [("errored judge", "judge error"), ("sample error", "sample error")])
def test_single_run_without_a_verdict_is_listed_with_its_reason(kind: str, reason: str) -> None:
    """One matching run with no verdict is not compared; it is listed with why."""
    labels = [{"sample": "a-skill", "grader": "judge", "verdict": "PASS"}]
    lines = report.unmatched_labels([model_run("opus", kind)], labels)
    assert len(lines) == 2 and reason in lines[1] and "a-skill" in lines[1]
    assert report.agreement([model_run("opus", kind)], labels) == ["no labelled judge verdicts in these logs"]


def test_duplicate_of_an_unlabelled_sample_does_not_stop() -> None:
    """Only the samples labels name matter: a duplicate elsewhere, in any model, is ignored."""
    other = judged(False, "t2")
    other.sample_id = "b-skill"
    twin = judged(True, "t1")
    twin.sample_id = "b-skill"
    labels = [{"sample": "a-skill", "grader": "judge", "verdict": "PASS"}]
    assert len(report.resolve_labels([judged(True), twin, other], labels)) == 1


def test_several_epochs_and_graders_do_not_stop() -> None:
    """Runs of other epochs, and other graders of the same run, are not matches."""
    first = judged(True)
    first.judges = {"judge": {"verdict": True}, "judge_2": {"verdict": False}}
    second = judged(False)
    second.epoch = 2
    second.judges = dict(first.judges)
    labels = [
        {"sample": "a-skill", "grader": "judge", "verdict": "PASS", "epoch": 2},
        {"sample": "a-skill", "grader": "judge_2", "verdict": "FAIL"},
    ]
    resolved = report.resolve_labels([first, second], labels)
    assert [run.epoch for _, run in resolved] == [2, 1]
    assert report.agreement([first, second], labels)[-1].split()[-3:] == ["2/2", "agree", "(100%)"]


def test_duplicate_within_a_model_stops_unless_latest() -> None:
    """Two copies in one model make the label ambiguous; `--latest` leaves the newest."""
    labels = [{"sample": "a-skill", "grader": "judge", "verdict": "PASS", "agent_model": "opus"}]
    copies = [model_run("opus", "judged"), model_run("opus", "errored judge")]
    copies[0].started, copies[1].started = "t1", "t2"
    with pytest.raises(ValueError, match="a-skill"):
        report.resolve_labels(copies, labels)
    assert len(report.resolve_labels(report.latest(copies), labels)) == 1


def test_resolution_across_groups_uses_the_one_resolved_run() -> None:
    """A label without agent_model resolves to the one run, wherever it is; other groups see no label."""
    opus, sonnet = model_run("opus", "judged"), model_run("sonnet", "judged")
    sonnet.sample_id = "b-skill"
    labels = [{"sample": "b-skill", "grader": "judge", "verdict": "FAIL"}]
    report.resolve_labels([opus, sonnet], labels)
    assert report.agreement([sonnet], labels)[-1].split()[-3:] == ["0/1", "agree", "(0%)"]
    assert report.agreement([opus], labels) == ["no labelled judge verdicts in these logs"]


def test_main_prints_labels_without_a_verdict_and_stops_on_an_unmatched_label(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """A lone errored judge is listed after the sections; a label with no run stops before any section."""
    labels = tmp_path / "labels.yaml"
    labels.write_text("- {sample: a-skill, grader: judge, verdict: PASS}\n")
    monkeypatch.setattr(report, "read_results", lambda paths: [errored_judge()])
    assert report.main(["x.eval", "--labels", str(labels)]) == 0
    assert "## Labels without a verdict" in capsys.readouterr().out
    labels.write_text("- {sample: typo, grader: judge, verdict: PASS}\n")
    with pytest.raises(SystemExit, match="typo"):
        report.main(["x.eval", "--labels", str(labels)])
    assert capsys.readouterr().out == ""


def test_judge_cost_includes_the_skill_reads_judge() -> None:
    """The judge cost adds the reads judge's cost to the rule judges' cost."""
    rule = SimpleNamespace(value={"judge": 1, "all": 1}, metadata={"judges": {"judge": {"total_cost_usd": 0.25}}})
    reads = SimpleNamespace(value=1, metadata={"judge": {"total_cost_usd": 0.5}})
    sample = SimpleNamespace(
        id="a-skill",
        epoch=1,
        error=None,
        scores={"grade_cases": rule, "skill_reads": reads},
        metadata={"case": "a", "condition": "skill", "rule": "5.1"},
    )
    assert report.read_result(sample).judge_cost == pytest.approx(0.75)  # type: ignore[arg-type]


def run(case: str, condition: str, passed: float) -> report.SampleResult:
    """One scored run of a case, on Sonnet, from a log started on 2026-11-21."""
    return report.SampleResult(
        f"{case}-{condition}", case, condition, "r", passed, started="2026-11-21T10:00:00", agent_model="sonnet"
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
    other = [report.SampleResult("a1-skill", "a1", "skill", "r", 1, agent_model="opus")]
    monkeypatch.setattr(report, "read_results", lambda paths: scored() if paths == [Path("x.eval")] else other)
    monkeypatch.setattr(report, "load_priorities", lambda skill: CATEGORIES)
    with pytest.raises(SystemExit, match="no runs"):
        report.main(["x.eval", "--pr", "--before", "old.eval"])


def test_tested_on_counts_only_cases_with_scored_runs() -> None:
    """A case whose every run errored is not counted as tested."""
    runs = [*scored(), report.SampleResult("z-skill", "z", "skill", "r", math.nan, error="429", started="2026")]
    assert report.tested_on(runs)[0] == 4
