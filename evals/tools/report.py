"""Summarise eval logs: pass rates, condition comparisons, cost and time per condition, and judge agreement.

Reads one or more Inspect `.eval` logs from `eval.py`. A case scores only its rule, so the pass rate of
a rule in a condition is the share of its samples whose `all` score passed. When a case ran several
times (Inspect epochs), the comparisons first average its runs per condition, then compare conditions
case by case (a paired design): mean difference, a bootstrap 95% interval, and a sign-flip permutation
p-value, with Holm's correction across the comparisons. Hand labels in `judge_labels/<skill>.yaml` (see
that folder's README) give the human verdict for a judged grader of a sample; the report compares them
with the judge's verdicts in the same logs. For the skill condition, it also counts which of the skill's own
files the runs read, against the files each case expects (`reads` in case.yaml); a skill run that missed one
fails through the `skill_reads` grader. Logs are grouped by skill and agent model, and each group gets its own report
with a header (judge model, Claude Code version, skill commit with a dirty flag). With `--latest`, each case
and condition of a group keeps only the runs of the most recently started log that has it, so re-runs after a fix
replace the runs they fix.

    uv run python -m tools.report logs/<dir>/*.eval [...] [--latest] [--labels judge_labels/code-better.yaml]

With `--pr` or `--docs`, it prints instead the pull request or docs table of PRINCIPLES.md, sections 10 and 11: one
row per priority category of `cases/<skill>/priorities.yaml`. `--before` takes the logs of the skill before a change,
and `--chart` writes the pull request's chart of the change per category to an SVG file.
"""

import argparse
import html
import math
import random
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from inspect_ai.log import EvalSample, read_eval_log

from skill_evals.agent import AGENT_TIMEOUT_MESSAGE
from skill_evals.cases import CONDITIONS, NO_SKILL, ONE_SENTENCE, SHORT_SKILL, SKILL_INSTALLED, WITH_SKILL
from skill_evals.grading.files import GRADING_ERROR_MESSAGE

# Each comparison is (condition, baseline): the difference is condition minus baseline.
COMPARISONS = (
    (WITH_SKILL, NO_SKILL),
    (ONE_SENTENCE, NO_SKILL),
    (SHORT_SKILL, NO_SKILL),
    (WITH_SKILL, ONE_SENTENCE),
    (WITH_SKILL, SHORT_SKILL),
    (SKILL_INSTALLED, NO_SKILL),
    (WITH_SKILL, SKILL_INSTALLED),
)
RESAMPLES = 10_000
RANDOM_SEED = 0


@dataclass
class SampleResult:
    """One sample's outcome and cost."""

    sample_id: str
    case: str
    condition: str
    rule: str
    passed: float
    tokens: dict[str, int] = field(default_factory=dict)
    cost: float = 0.0
    judge_cost: float = 0.0
    seconds: float = 0.0
    judges: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    epoch: int = 1
    skill_reads: dict[str, Any] = field(default_factory=dict)
    rule_passed: float = math.nan
    lint_issues: float | None = None
    skill_loaded: float | None = None
    started: str = ""
    side_actions: dict[str, int] = field(default_factory=dict)
    skill: str = "?"
    agent_model: str = "?"
    judge_model: str = "?"
    agent_version: str = "?"
    skill_commit: str = ""
    skill_dirty: bool | None = False
    log: str = ""


def read_result(sample: EvalSample) -> SampleResult:
    """Read one sample's case, condition, rule, `all` score, Claude Code usage and judge verdicts."""
    metadata = sample.metadata or {}
    scores = sample.scores or {}
    score = scores.get("grade_cases") or next(iter(scores.values()), None)
    values = score.value if score and isinstance(score.value, dict) else {}
    run = metadata.get("claude_code") or {}
    judges = (score.metadata or {}).get("judges", {}) if score else {}
    reads = scores.get("skill_reads")
    lint = scores.get("lint_issues_added")
    loaded = scores.get("skill_loaded")
    rule_passed = float(values.get("all", math.nan))
    # A skill run that missed an expected skill file fails, whatever its rule score.
    passed = 0.0 if reads is not None and reads.value == 0 and not math.isnan(rule_passed) else rule_passed
    return SampleResult(
        sample_id=str(sample.id),
        case=metadata.get("case", str(sample.id)),
        condition=metadata.get("condition", "?"),
        rule=str(metadata.get("rule", "?")),
        passed=passed,
        rule_passed=rule_passed,
        epoch=int(sample.epoch or 1),
        tokens=run.get("usage") or {},
        cost=float(run.get("total_cost_usd") or 0.0),
        judge_cost=sum(float(info.get("total_cost_usd") or 0.0) for info in judges.values())
        + float(((reads.metadata or {}).get("judge") or {}).get("total_cost_usd") or 0.0 if reads is not None else 0.0),
        seconds=(run.get("duration_ms") or 0) / 1000,
        judges=judges,
        skill_reads=(reads.metadata or {}) if reads is not None else {},
        lint_issues=float(lint.value) if lint is not None and not math.isnan(float(lint.value)) else None,
        skill_loaded=float(loaded.value) if loaded is not None else None,
        error=sample.error.message[:120] if sample.error else None,
        side_actions=(score.metadata or {}).get("side_actions") or {} if score else {},
    )


def read_results(paths: list[Path]) -> list[SampleResult]:
    """Read every sample of every log, noting when its log started and what it ran on."""
    results = []
    for path in paths:
        log = read_eval_log(str(path))
        metadata = log.eval.metadata or {}
        for sample in log.samples or []:
            result = read_result(sample)
            result.started = log.stats.started_at or ""
            result.log = path.name
            result.skill = str(metadata.get("skill", "?"))
            result.agent_model = str(metadata.get("agent_model", "?"))
            result.judge_model = str(metadata.get("judge_model", "?"))
            result.agent_version = str(metadata.get("agent_version", "?"))
            result.skill_commit = str(metadata.get("skill_commit", ""))
            dirty = metadata.get("skill_dirty")
            result.skill_dirty = None if dirty is None else bool(dirty)
            results.append(result)
    return results


def latest(results: list[SampleResult]) -> list[SampleResult]:
    """Keep, for each skill, agent model, case and condition, only the runs from the most recently started log."""
    newest: dict[tuple[str, str, str, str], str] = {}
    for result in results:
        key = (result.skill, result.agent_model, result.case, result.condition)
        newest[key] = max(newest.get(key, ""), result.started)
    return [
        result
        for result in results
        if result.started == newest[result.skill, result.agent_model, result.case, result.condition]
    ]


def group_results(results: list[SampleResult]) -> dict[tuple[str, str], list[SampleResult]]:
    """Split the results by (skill, agent model), so that runs of different models are never pooled."""
    groups: dict[tuple[str, str], list[SampleResult]] = defaultdict(list)
    for result in results:
        groups[result.skill, result.agent_model].append(result)
    return dict(sorted(groups.items()))


def _dirty_text(dirty: bool | None) -> str:
    """Return the header flag for a skill folder state: dirty, unknown (the log did not record it) or nothing."""
    return " (dirty ?)" if dirty is None else " (dirty)" if dirty else ""


def group_header(results: list[SampleResult]) -> list[str]:
    """Name what a group ran on: skill, agent model, judge model, Claude Code version and skill commit."""
    skill, agent_model = results[0].skill, results[0].agent_model
    commits = sorted({f"{r.skill_commit[:7] or '?'}{_dirty_text(r.skill_dirty)}" for r in results})
    judges = sorted({r.judge_model for r in results})
    versions = sorted({r.agent_version for r in results})
    return [
        f"# Skill {skill}, agent model {agent_model}",
        f"judge model {', '.join(judges)} · Claude Code {', '.join(versions)} · skill commit {', '.join(commits)}",
    ]


def rule_key(rule: str) -> tuple[int, str]:
    """Sort invocation first, then the rules alphabetically."""
    return (0 if rule == "invocation" else 1, rule)


def pass_table(results: list[SampleResult]) -> list[str]:
    """Format the pass rate per rule (results) and condition (columns), counting only scored samples."""
    cells: dict[tuple[str, str], list[float]] = defaultdict(list)
    for sample in results:
        if sample.error is None and not math.isnan(sample.passed):
            cells[sample.rule, sample.condition].append(sample.passed)
    conditions = [name for name in CONDITIONS if any(condition == name for _, condition in cells)]
    rules = sorted({rule for rule, _ in cells}, key=rule_key)
    width = max([len("rule"), *map(len, rules)]) + 2
    lines = [f"{'rule':{width}}" + "".join(f"{name:>19}" for name in conditions)]
    for rule in rules:
        parts = []
        for condition in conditions:
            values = cells.get((rule, condition), [])
            parts.append(f"{sum(values):>4.0f}/{len(values):<3} {sum(values) / len(values):>4.0%}" if values else "-")
        lines.append(f"{rule:{width}}" + "".join(f"{part:>19}" for part in parts))
    return lines


def error_cause(message: str) -> str:
    """Name the cause of a sample error from its message: agent timeout, grading error, or other."""
    if AGENT_TIMEOUT_MESSAGE in message:
        return "agent timeout"
    return "grading error" if GRADING_ERROR_MESSAGE in message else "other"


def error_lines(results: list[SampleResult]) -> list[str]:
    """Count, per condition, the samples and the sample errors by cause.

    Sample errors are left out of the pass rates and of the cost and time means; `inspect eval-retry` reruns them.
    """
    causes = ("agent timeout", "grading error", "other")
    lines = [f"{'condition':18} {'samples':>8} " + " ".join(f"{cause:>14}" for cause in causes)]
    for name in CONDITIONS:
        runs = [sample for sample in results if sample.condition == name]
        if runs:
            found = [error_cause(sample.error) for sample in runs if sample.error]
            lines.append(f"{name:18} {len(runs):8} " + " ".join(f"{found.count(cause):14}" for cause in causes))
    return lines


def case_means(results: list[SampleResult]) -> dict[str, dict[str, float]]:
    """Average each case's scored runs per condition: {condition: {case: mean of `all`}}."""
    runs: dict[tuple[str, str], list[float]] = defaultdict(list)
    for sample in results:
        if sample.error is None and not math.isnan(sample.passed):
            runs[sample.condition, sample.case].append(sample.passed)
    means: dict[str, dict[str, float]] = defaultdict(dict)
    for (condition, case), values in runs.items():
        means[condition][case] = sum(values) / len(values)
    return means


def bootstrap_interval(differences: list[float], generator: random.Random) -> tuple[float, float]:
    """Return a 95% bootstrap interval for the mean of the per-case differences."""
    count = len(differences)
    means = sorted(sum(generator.choices(differences, k=count)) / count for _ in range(RESAMPLES))
    return means[int(0.025 * RESAMPLES)], means[int(0.975 * RESAMPLES) - 1]


def sign_flip_p_value(differences: list[float], generator: random.Random) -> float:
    """Return a two-sided p-value for a mean difference of zero by randomly flipping each case's sign.

    Under no difference between the two conditions, each case's difference is as likely positive as
    negative, so the observed mean is compared with the means of sign-flipped copies.
    """
    observed = abs(sum(differences))
    as_extreme = sum(
        abs(sum(value if generator.random() < 0.5 else -value for value in differences)) >= observed - 1e-12
        for _ in range(RESAMPLES)
    )
    return (as_extreme + 1) / (RESAMPLES + 1)


def holm_adjusted(p_values: list[float]) -> list[float]:
    """Return Holm-Bonferroni adjusted p-values, in the order given."""
    order = sorted(range(len(p_values)), key=lambda index: p_values[index])
    adjusted, running_max = [0.0] * len(p_values), 0.0
    for rank, index in enumerate(order):
        running_max = max(running_max, min(1.0, (len(p_values) - rank) * p_values[index]))
        adjusted[index] = running_max
    return adjusted


def comparison_lines(results: list[SampleResult]) -> list[str]:
    """Format paired comparisons of conditions over the cases both conditions ran."""
    means, generator, rows = case_means(results), random.Random(RANDOM_SEED), []
    for condition, baseline in COMPARISONS:
        shared = sorted(set(means.get(condition, {})) & set(means.get(baseline, {})))
        if len(shared) < 2:
            continue
        differences = [means[condition][case] - means[baseline][case] for case in shared]
        low, high = bootstrap_interval(differences, generator)
        rows.append(
            (
                f"{condition} − {baseline}",
                len(shared),
                sum(differences) / len(shared),
                low,
                high,
                sign_flip_p_value(differences, generator),
            )
        )
    if not rows:
        return ["not enough paired cases to compare conditions"]
    adjusted = holm_adjusted([row[5] for row in rows])
    lines = [f"{'comparison':28} cases  mean diff   95% interval       p    p (Holm)"]
    for (name, count, mean, low, high, p_value), p_holm in zip(rows, adjusted, strict=True):
        lines.append(f"{name:28} {count:5}  {mean:+9.3f}  [{low:+.3f}, {high:+.3f}]  {p_value:6.4f}  {p_holm:8.4f}")
    lines.append(
        "mean diff = difference in pass rate per case, averaged over cases; each case's runs are averaged first."
    )
    return lines


def tokens_text(tokens: dict[str, int]) -> str:
    """Format token counts as input/output/cache-read/cache-write."""
    keys = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
    return "/".join(str(tokens.get(key, 0)) for key in keys)


def case_lines(results: list[SampleResult]) -> list[str]:
    """Format one line per sample with its result, tokens, cost and time, and the totals."""
    lines = [f"{'sample':42} all  {'tokens in/out/cache-read/cache-write':36}  cost  judge   time"]
    total: dict[str, int] = defaultdict(int)
    for sample in sorted(results, key=lambda sample: (sample.case, sample.condition, sample.epoch)):
        outcome = "ERR" if sample.error else "-" if math.isnan(sample.passed) else str(int(sample.passed))
        lines.append(
            f"{sample.sample_id + (f' #{sample.epoch}' if sample.epoch > 1 else ''):42} {outcome:>3}  {tokens_text(sample.tokens):36} "
            f"{sample.cost:6.3f} {sample.judge_cost:6.3f} {sample.seconds:5.0f}s"
        )
        for key, value in sample.tokens.items():
            total[key] += value
    cost = sum(sample.cost for sample in results)
    judge_cost = sum(sample.judge_cost for sample in results)
    seconds = sum(sample.seconds for sample in results)
    errors = sum(1 for sample in results if sample.error)
    label = f"total: {len(results)} samples, {errors} errors"
    lines.append(f"{label:46} {tokens_text(total):36} {cost:6.3f} {judge_cost:6.3f} {seconds:5.0f}s")
    return lines


def condition_cost_lines(results: list[SampleResult]) -> list[str]:
    """Format cost, time and tokens per condition: mean and median per run, over runs without a sample error."""
    lines = [
        f"{'condition':18} {'runs':>5} {'cost mean':>10} {'median':>8} {'time mean':>10} {'median':>8} "
        f"{'out tokens':>11} {'total cost':>11}"
    ]
    for name in CONDITIONS:
        runs = [sample for sample in results if sample.condition == name and not sample.error]
        if not runs:
            continue
        costs = [sample.cost for sample in runs]
        times = [sample.seconds for sample in runs]
        output = statistics.mean(sample.tokens.get("output_tokens", 0) for sample in runs)
        lines.append(
            f"{name:18} {len(runs):5} {statistics.mean(costs):10.3f} {statistics.median(costs):8.3f} "
            f"{statistics.mean(times):9.0f}s {statistics.median(times):7.0f}s {output:11.0f} {sum(costs):11.2f}"
        )
    lines.append("cost = Claude Code's total_cost_usd for the agent run (API-price equivalent), judge excluded.")
    return lines


def skill_read_lines(results: list[SampleResult]) -> list[str]:
    """Format the skill's own files read: per expected file, per file read where no case expects it, per run."""
    runs = [sample for sample in results if sample.skill_reads and not sample.error]
    if not runs:
        return ["No run tracked skill reads."]
    expected: dict[str, list[bool]] = defaultdict(list)
    unexpected: dict[str, int] = defaultdict(int)
    for sample in runs:
        missing = set(sample.skill_reads.get("missing", []))
        for label in sample.skill_reads.get("expected", []):
            expected[label].append(label not in missing)
        for path in sample.skill_reads.get("read", {}):
            if not any(path in label.split(" or ") for label in sample.skill_reads.get("expected", [])):
                unexpected[path] += 1
    complete = sum(not sample.skill_reads.get("missing") for sample in runs)
    lines = [f"Runs that read every expected file: {complete}/{len(runs)}", f"{'expected file':52} {'read':>9}"]
    for label in sorted(expected):
        hits = expected[label]
        lines.append(f"{label:52} {sum(hits):>4}/{len(hits):<4}")
    lines.append(f"{'read where not expected':52} {'runs':>9}")
    lines.extend(f"{path:52} {count:>9}" for path, count in sorted(unexpected.items()))
    return lines


def loaded_lines(results: list[SampleResult]) -> list[str]:
    """Format, per case, the skill-installed runs, how many loaded the skill, and the pass rate with and without it."""
    runs = [sample for sample in results if sample.skill_loaded is not None and not sample.error]
    if not runs:
        return ["No skill-installed runs."]

    def rate(group: list[SampleResult]) -> str:
        scored = [sample.passed for sample in group if not math.isnan(sample.passed)]
        return f"{statistics.mean(scored):.0%}" if scored else "-"

    width = max(len("case"), *(len(sample.case) for sample in runs)) + 2
    lines = [f"{'case':{width}} {'runs':>5} {'loaded':>7} {'pass loaded':>12} {'pass not loaded':>16}"]
    for case in sorted({sample.case for sample in runs}):
        own = [sample for sample in runs if sample.case == case]
        yes = [sample for sample in own if sample.skill_loaded == 1.0]
        no = [sample for sample in own if sample.skill_loaded != 1.0]
        lines.append(f"{case:{width}} {len(own):5} {len(yes):7} {rate(yes):>12} {rate(no):>16}")
    return lines


def lint_lines(results: list[SampleResult]) -> list[str]:
    """Format the lint issues runs added to the Python files they changed, per condition (observed, not scored)."""
    lines = [f"{'condition':18} {'runs':>5} {'mean issues':>12} {'runs with any':>14}"]
    for name in CONDITIONS:
        counts = [s.lint_issues for s in results if s.condition == name and s.lint_issues is not None and not s.error]
        if counts:
            lines.append(f"{name:18} {len(counts):5} {statistics.mean(counts):12.2f} {sum(c > 0 for c in counts):14}")
    return lines if len(lines) > 1 else ["No run counted lint issues."]


def side_action_lines(results: list[SampleResult]) -> list[str]:
    """Format, per condition, how many runs committed or rewrote history, over the runs where it was measured."""
    lines = [f"{'condition':18} {'measured':>9} {'committed':>10} {'rewrote':>8}  cases that committed"]
    for name in CONDITIONS:
        runs = [sample for sample in results if sample.condition == name and "commits" in sample.side_actions]
        if not runs:
            continue
        committed = [sample for sample in runs if sample.side_actions["commits"] > 0]
        rewrote = sum(1 for sample in runs if sample.side_actions["commits"] < 0)
        cases = ", ".join(sorted({sample.case for sample in committed})) or "-"
        lines.append(f"{name:18} {len(runs):9} {len(committed):10} {rewrote:8}  {cases}")
    lines.append("Measured on every run, scored only by cases whose rule covers it (no_commit grader).")
    return lines


def load_labels(path: Path) -> list[dict[str, Any]]:
    """Read hand labels: a list of {sample, epoch (default 1), grader, verdict: PASS or FAIL, note}."""
    labels = yaml.safe_load(path.read_text()) or []
    for label in labels:
        if str(label.get("verdict")).upper() not in {"PASS", "FAIL"}:
            raise ValueError(f"Label verdict must be PASS or FAIL: {label}")
    return labels


def label_key(label: dict[str, Any]) -> tuple[str, int, str]:
    """Return the (sample, epoch, grader) a hand label names."""
    return str(label["sample"]), int(label.get("epoch", 1)), str(label["grader"])


def label_runs(results: list[SampleResult], label: dict[str, Any]) -> list[SampleResult]:
    """Return every run a label may mean: its sample and epoch, its agent model if it names one.

    A run counts when its judge for the label's grader ran or errored, and when it ended in a sample
    error, since either could be the run the label was written on.
    """
    sample, epoch, grader = label_key(label)
    return [
        run
        for run in results
        if run.sample_id == sample
        and run.epoch == epoch
        and ("agent_model" not in label or str(label["agent_model"]) == run.agent_model)
        and (grader in run.judges or run.error)
    ]


def verdict_of(run: SampleResult, grader: str) -> bool | None:
    """Return the judge's verdict for a grader, or None when the judge gave none (it errored, or the run did)."""
    info = run.judges.get(grader)
    return None if info is None or "error" in info else info.get("verdict")


def resolve_labels(
    results: list[SampleResult], labels: list[dict[str, Any]]
) -> list[tuple[dict[str, Any], SampleResult]]:
    """Pair each label with the one run it matches, or raise ValueError naming every label that has none or several.

    Raised before anything prints. Runs of every group are searched, so a label without `agent_model` that
    matches runs of two models, or a run and a copy that errored, cannot be scored against the wrong one.
    """
    resolved, problems = [], []
    for label in labels:
        runs = label_runs(results, label)
        if len(runs) == 1:
            resolved.append((label, runs[0]))
            continue
        sample, epoch, grader = label_key(label)
        found = (
            "matches no run" if not runs else "matches " + "; ".join(f"{r.agent_model} in {r.log or '?'}" for r in runs)
        )
        fix = "" if not runs else ": add `agent_model: <model>` to the label or pass --latest to pick one"
        problems.append(f"Label {sample!r} (epoch {epoch}, grader {grader!r}) {found}{fix}")
    if problems:
        raise ValueError("\n".join(problems))
    return resolved


def unmatched_labels(results: list[SampleResult], labels: list[dict[str, Any]]) -> list[str]:
    """List the labels whose one run has no verdict to compare, such as an errored judge, with the reason."""
    lines = []
    for label, run in resolve_labels(results, labels):
        grader = str(label["grader"])
        if verdict_of(run, grader) is None:
            reason = f"sample error: {run.error}" if run.error and grader not in run.judges else "judge error"
            lines.append(f"  {label['sample']} (epoch {label_key(label)[1]}, grader {grader}): {reason}")
    return [f"{len(lines)} label(s) have a run without a judge verdict:", *lines] if lines else []


def agreement(results: list[SampleResult], labels: list[dict[str, Any]]) -> list[str]:
    """Compare judge verdicts with hand labels, per rubric (case and grader) and overall.

    A label counts here when its one run is in `results`; labels with no run or no verdict are left out.
    """
    per_rubric: dict[tuple[str, str], list[bool]] = defaultdict(list)
    for label in labels:
        runs = label_runs(results, label)
        grader = str(label["grader"])
        if len(runs) == 1 and verdict_of(runs[0], grader) is not None:
            human_passes = str(label["verdict"]).upper() == "PASS"
            per_rubric[runs[0].case, grader].append(verdict_of(runs[0], grader) == human_passes)
    if not per_rubric:
        return ["no labelled judge verdicts in these logs"]
    lines = [
        f"{case + ' ' + grader:44} {sum(matches)}/{len(matches)} agree"
        for (case, grader), matches in sorted(per_rubric.items())
    ]
    every = [match for matches in per_rubric.values() for match in matches]
    lines.append(f"{'overall':44} {sum(every)}/{len(every)} agree ({sum(every) / len(every):.0%})")
    return lines


# ---------- PR and docs format (evals/PRINCIPLES.md, sections 10 and 11) ----------

CASES_DIR = Path(__file__).resolve().parents[1] / "cases"
PRIORITIES_FILE = "priorities.yaml"
# Two-sided 95% quantiles of Student's t for 1 to 30 degrees of freedom; 1.96 beyond.
T95 = (
    12.706,
    4.303,
    3.182,
    2.776,
    2.571,
    2.447,
    2.365,
    2.306,
    2.262,
    2.228,
    2.201,
    2.179,
    2.160,
    2.145,
    2.131,
    2.120,
    2.110,
    2.101,
    2.093,
    2.086,
    2.080,
    2.074,
    2.069,
    2.064,
    2.060,
    2.056,
    2.052,
    2.048,
    2.045,
    2.042,
)
BEFORE, AFTER = "before", "after"
COLUMN_NAMES = {NO_SKILL: "No skill", SHORT_SKILL: "Short skill", WITH_SKILL: "Skill", BEFORE: "Before", AFTER: "After"}


@dataclass
class CategoryRow:
    """One priority category: its pass rate per column and the change between the compared columns."""

    name: str
    does: str
    cases: int
    rates: dict[str, float]
    change: float | None
    low: float | None
    high: float | None

    def mark(self) -> str:
        """▲ or ▼ with the change in points when its interval excludes zero, otherwise =."""
        if self.change is None or self.low is None or self.high is None or self.low <= 0 <= self.high:
            return "="
        points = round(self.change * 100)
        return "=" if points == 0 else f"▲ +{points}" if points > 0 else f"▼ −{-points}"


def load_priorities(skill: str, cases_dir: Path = CASES_DIR) -> list[dict[str, Any]]:
    """Read `cases/<skill>/priorities.yaml` and check that each category names existing cases, each case once."""
    path = cases_dir / skill / PRIORITIES_FILE
    if not path.exists():
        raise SystemExit(f"{path} is missing: ask the maintainer for {skill}'s priority order and write it there")
    categories = (yaml.safe_load(path.read_text()) or {}).get("categories") or []
    seen: dict[str, str] = {}
    for category in categories:
        if not category.get("name") or not category.get("does") or not category.get("cases"):
            raise SystemExit(f"{path}: every category needs a name, does and cases")
        for case in category["cases"]:
            if not (cases_dir / skill / case / "case.yaml").exists():
                raise SystemExit(f"{path}: {category['name']} lists {case}, which is not a case of {skill}")
            if case in seen:
                raise SystemExit(f"{path}: {case} is in both {seen[case]} and {category['name']}")
            seen[case] = category["name"]
    return categories


def mean_interval(differences: list[float]) -> tuple[float, float | None, float | None]:
    """Return the mean of per-case differences and its 95% t-interval; no interval with fewer than two cases."""
    mean = sum(differences) / len(differences)
    if len(differences) < 2:
        return mean, None, None
    freedom = len(differences) - 1
    quantile = T95[freedom - 1] if freedom <= len(T95) else 1.96
    half = quantile * statistics.stdev(differences) / math.sqrt(len(differences))
    return mean, mean - half, mean + half


def category_rows(
    results: list[SampleResult], categories: list[dict[str, Any]], before: list[SampleResult] | None = None
) -> tuple[list[str], list[CategoryRow]]:
    """Pass rate per category and column, and the change: after − before, or skill − no skill without `before`.

    A category's rate is the mean of its cases' rates, so each case counts once; the change is paired by case.
    """
    means = case_means(results)
    if before is not None:
        means[BEFORE] = case_means(before).get(WITH_SKILL, {})
        means[AFTER] = means.pop(WITH_SKILL, {})
        compared, columns = (BEFORE, AFTER), [NO_SKILL, SHORT_SKILL, BEFORE, AFTER]
    else:
        compared, columns = (NO_SKILL, WITH_SKILL), [NO_SKILL, SHORT_SKILL, WITH_SKILL]
    columns = [column for column in columns if means.get(column)]
    ran = {case for column in columns for case in means[column]}
    missing = [f"{case} ({COLUMN_NAMES[c]})" for c in columns for case in sorted(ran - set(means[c]))]
    if missing:
        raise SystemExit(f"every column needs scored runs of the same cases; none for: {', '.join(missing)}")
    listed = {case for category in categories for case in category["cases"]}
    if ran - listed:
        raise SystemExit(f"cases in no priority category: {', '.join(sorted(ran - listed))}")
    rows = []
    for category in categories:
        cases = [case for case in category["cases"] if case in ran]
        rates = {}
        for column in columns:
            values = [means[column][case] for case in cases if case in means[column]]
            if values:
                rates[column] = sum(values) / len(values)
        old, new = means.get(compared[0], {}), means.get(compared[1], {})
        differences = [new[case] - old[case] for case in cases if case in old and case in new]
        change, low, high = mean_interval(differences) if differences else (None, None, None)
        rows.append(CategoryRow(category["name"], category["does"], len(cases), rates, change, low, high))
    return columns, rows


def tested_on(results: list[SampleResult]) -> tuple[int, str, str]:
    """Return how many cases have scored runs, on which agent model, and the date of the newest log."""
    scored = {r.case for r in results if r.error is None and not math.isnan(r.passed)}
    return len(scored), results[0].agent_model, max(r.started for r in results)[:10]


def pr_lines(columns: list[str], rows: list[CategoryRow], results: list[SampleResult]) -> list[str]:
    """The table for a pull request: rate per column in percent and the change, the compared cells bold if clear."""
    count, model, _ = tested_on(results)
    compared = columns[-2:] if AFTER in columns else [NO_SKILL, WITH_SKILL]
    lines = [
        f"Tested on {count} cases with {model}.",
        "",
        "| Category | Cases | " + " | ".join(COLUMN_NAMES[c] for c in columns) + " | Change |",
        "| --- | ---: | " + " | ".join("---:" for _ in columns) + " | :---: |",
    ]
    for number, row in enumerate(rows, 1):
        clear = row.mark() != "="
        cells = []
        for column in columns:
            text = f"{row.rates[column]:.0%}" if column in row.rates else "–"
            cells.append(f"**{text}**" if clear and column in compared and column in row.rates else text)
        lines.append(f"| {number} {row.name} | {row.cases} | " + " | ".join(cells) + f" | {row.mark()} |")
    return lines


def docs_lines(columns: list[str], rows: list[CategoryRow], results: list[SampleResult]) -> list[str]:
    """The table for a skill's docs page: what the skill does and its pass rate, with no comparison."""
    count, model, date = tested_on(results)
    column = AFTER if AFTER in columns else WITH_SKILL
    lines = [f"Tested on {count} situations with {model} ({date}).", "", "| What it does | Passed |", "| --- | ---: |"]
    lines += [f"| {row.does} | {row.rates[column]:.0%} |" for row in rows if column in row.rates]
    return lines


def chart_svg(rows: list[CategoryRow]) -> str:
    """Draw the change per category as a dot with its 95% interval, in percentage points, around a zero line."""
    ends = [abs(v) for row in rows for v in (row.change, row.low, row.high) if v is not None]
    reach = max(10, math.ceil(max(ends, default=0) * 10) * 10)
    width, label, value, top, step = 680, 240, 130, 16, 34
    plot = width - label - value - 20

    def x(points: float) -> float:
        return label + (points + reach) / (2 * reach) * plot

    height = top + step * len(rows) + 24
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        'font-family="-apple-system, Segoe UI, sans-serif" font-size="13">',
        f'<rect width="{width}" height="{height}" fill="#FFFCF7"/>',
        f'<line x1="{x(0):.1f}" y1="{top - 8}" x2="{x(0):.1f}" y2="{height - 22}" stroke="#33302B"/>',
    ]
    for tick in (-reach, 0, reach):
        parts.append(
            f'<text x="{x(tick):.1f}" y="{height - 6}" text-anchor="middle" fill="#78736B">'
            f"{'+' if tick > 0 else '−' if tick < 0 else ''}{abs(tick)}</text>"
        )
    for index, row in enumerate(rows):
        y = top + step * index + step / 2
        parts.append(f'<text x="12" y="{y + 4:.1f}" fill="#33302B">{index + 1} {html.escape(row.name)}</text>')
        if row.change is None:
            continue
        if row.low is not None and row.high is not None:
            parts.append(
                f'<line x1="{x(row.low * 100):.1f}" y1="{y:.1f}" x2="{x(row.high * 100):.1f}" y2="{y:.1f}" '
                'stroke="#33302B" stroke-width="3" stroke-linecap="round"/>'
            )
        parts.append(
            f'<circle cx="{x(row.change * 100):.1f}" cy="{y:.1f}" r="6" fill="#FFFCF7" stroke="#1C1A17" '
            'stroke-width="2"/>'
        )
        colour = "#66795A" if row.mark().startswith("▲") else "#33302B"
        parts.append(f'<text x="{width - value + 10}" y="{y + 4:.1f}" fill="{colour}">{row.mark()}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Read the command line."""
    parser = argparse.ArgumentParser(description="Pass rates per rule and condition, cost, time and judge agreement.")
    parser.add_argument("logs", nargs="+", type=Path)
    parser.add_argument("--labels", type=Path, help="hand labels, such as judge_labels/code-better.yaml")
    parser.add_argument(
        "--latest", action="store_true", help="keep each case and condition's runs from the newest log that has it"
    )
    parser.add_argument("--pr", action="store_true", help="print the pull request table (evals/PRINCIPLES.md, 10)")
    parser.add_argument("--docs", action="store_true", help="print the docs table (evals/PRINCIPLES.md, 11)")
    parser.add_argument("--before", nargs="+", type=Path, help="logs of the skill before the change, for --pr")
    parser.add_argument("--chart", type=Path, help="with --pr, write the change chart to this SVG file")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Print the report for the given logs."""
    args = parse_args(argv)
    results = read_results(args.logs)
    if args.latest:
        results = latest(results)
    if args.pr or args.docs:
        return print_formatted(results, args)
    return print_report(results, args.labels)


def print_report(results: list[SampleResult], labels_path: Path | None) -> int:
    """Print the full report of each skill and agent model, with judge agreement when hand labels are given."""
    labels = load_labels(labels_path) if labels_path else None
    if labels is not None:
        try:
            resolve_labels(results, labels)
        except ValueError as error:
            raise SystemExit(str(error)) from error
    for group in group_results(results).values():
        print("\n" + "\n".join(group_header(group)))
        sections = [
            ("Pass rate (all) per rule and condition", pass_table(group)),
            ("Errors per condition (left out of pass rates, cost and time)", error_lines(group)),
            ("Comparisons between conditions (paired by case)", comparison_lines(group)),
            ("Cost and time per condition", condition_cost_lines(group)),
            ("Skill files read (skill condition; a missed file fails the run)", skill_read_lines(group)),
            ("Skill loaded without a command (skill-installed)", loaded_lines(group)),
            ("Lint issues added to changed Python files (observed, not scored)", lint_lines(group)),
            ("Side actions per condition", side_action_lines(group)),
            ("Samples", case_lines(group)),
        ]
        if labels is not None:
            sections.append(("Judge agreement with hand labels", agreement(group, labels)))
        for title, lines in sections:
            print(f"\n## {title}\n" + "\n".join(lines))
        errors = [f"{sample.sample_id}: {sample.error}" for sample in group if sample.error]
        if errors:
            print("\n## Sample errors\n" + "\n".join(errors))
    if labels is not None:
        unmatched = unmatched_labels(results, labels)
        if unmatched:
            print("\n## Labels without a verdict\n" + "\n".join(unmatched))
    return 0


def print_formatted(results: list[SampleResult], args: argparse.Namespace) -> int:
    """Print the pull request or docs table of each skill and agent model, grouped by the skill's priorities."""
    before = read_results(args.before) if args.before else None
    if before is not None and args.latest:
        before = latest(before)
    groups = group_results(results)
    if args.chart and len(groups) > 1:
        raise SystemExit("--chart writes one chart: give the logs of one skill and agent model")
    for (skill, model), group in groups.items():
        old = [r for r in before if r.skill == skill and r.agent_model == model] if before is not None else None
        if old == []:
            raise SystemExit(f"--before has no runs of {skill} on {model}")
        columns, rows = category_rows(group, load_priorities(skill), old)
        print("\n".join(pr_lines(columns, rows, group) if args.pr else docs_lines(columns, rows, group)))
        if args.pr and args.chart:
            args.chart.write_text(chart_svg(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
