"""Collects results across tests, prints the summary, and saves each run."""

import hashlib
import json
import subprocess
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, median

import pytest

import review
from harness import METRICS, SKILLS_DIR, Settings, compare


RUNS_DIR = Path(__file__).resolve().parents[1] / ".eval-runs"
LOG_KEY = pytest.StashKey["RunLog"]()


@dataclass
class RunLog:
    settings: Settings
    effects: list[dict] = field(default_factory=list)


@pytest.fixture(scope="session")
def settings() -> Settings:
    settings = Settings.from_env()
    result = subprocess.run(["ollama", "show", settings.judge_model], capture_output=True, text=True)
    if result.returncode != 0:
        pytest.exit(f"Judge model unavailable: {result.stderr.strip()}", returncode=1)
    return settings


@pytest.fixture(scope="session")
def run_log(request: pytest.FixtureRequest, settings: Settings) -> RunLog:
    log = RunLog(settings)
    request.config.stash[LOG_KEY] = log
    return log


def _print_effects(writer, log: RunLog) -> None:
    by_skill = defaultdict(lambda: defaultdict(lambda: {"skill": [], "baseline": []}))
    for entry in log.effects:
        for arm in ("skill", "baseline"):
            for sample in entry[arm]:
                for dimension, value in sample["scores"].items():
                    by_skill[entry["suite"]][dimension][arm].append(value)
    for suite, dimensions in by_skill.items():
        writer.line(f"{suite}, all cases:")
        for dimension, arms in sorted(dimensions.items()):
            verdict = compare(arms["skill"], arms["baseline"], log.settings)
            writer.line(
                f"  {dimension:<22} skill {mean(arms['skill']):.2f}  "
                f"baseline {mean(arms['baseline']):.2f}  n={len(arms['skill'])}  {verdict}"
            )
        entries = [e for e in log.effects if e["suite"] == suite]
        for metric in METRICS:
            skill = [s["metrics"][metric] for e in entries for s in e["skill"]]
            baseline = [s["metrics"][metric] for e in entries for s in e["baseline"]]
            if any(skill) or any(baseline):
                writer.line(
                    f"  {metric:<22} skill {median(skill):.2f}  baseline {median(baseline):.2f}  (median)"
                )


def _print_where_baseline_searched(writer, log: RunLog) -> None:
    """Without a search, a baseline loses every trajectory score, which says little about the skill."""
    entries = [
        entry
        for entry in log.effects
        if any(s["metrics"]["searches"] for s in entry["skill"])
        and all(s["metrics"]["searches"] for s in entry["baseline"])
    ]
    if not entries:
        return
    writer.line(f"Only cases where every baseline run searched: {[e['effect'] for e in entries]}")
    for dimension in sorted({d for e in entries for d in e["skill"][0]["scores"]}):
        skill = [s["scores"][dimension] for e in entries for s in e["skill"] if dimension in s["scores"]]
        baseline = [s["scores"][dimension] for e in entries for s in e["baseline"] if dimension in s["scores"]]
        verdict = compare(skill, baseline, log.settings)
        writer.line(
            f"  {dimension:<22} skill {mean(skill):.2f}  "
            f"baseline {mean(baseline):.2f}  n={len(skill)}  {verdict}"
        )


def _skill_hash() -> str:
    text = (SKILLS_DIR / "write-better" / "SKILL.md").read_bytes()
    return hashlib.sha256(text).hexdigest()


def _previous_version(current_hash: str, current_path: Path) -> Path | None:
    """The newest earlier run made with a different version of the skill."""
    for path in sorted(RUNS_DIR.glob("2*.json"), reverse=True):
        if path == current_path:
            continue
        saved_hash = json.loads(path.read_text(encoding="utf-8")).get("skill_hash")
        if saved_hash and saved_hash != current_hash:
            return path
    return None


def _report_review(writer, run_path: Path, skill_hash: str) -> None:
    key = RUNS_DIR / "review-key.json"
    choices = review.latest_choices()
    if key.exists() and choices and choices.stat().st_mtime > key.stat().st_mtime:
        writer.line(f"Your last review, from {choices}:")
        for line in review.tally(key, choices):
            writer.line(line)
    page = review.build(run_path, _previous_version(skill_hash, run_path))
    writer.line(f"Next review: {page}")


def pytest_terminal_summary(terminalreporter, config) -> None:
    log = config.stash.get(LOG_KEY, None)
    if log is None or not log.effects:
        return
    terminalreporter.section("Skill evals")
    _print_effects(terminalreporter, log)
    _print_where_baseline_searched(terminalreporter, log)
    RUNS_DIR.mkdir(exist_ok=True)
    path = RUNS_DIR / f"{time.strftime('%Y%m%d-%H%M%S')}.json"
    skill_hash = _skill_hash()
    path.write_text(
        json.dumps({"skill_hash": skill_hash, "effects": log.effects}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    terminalreporter.line(f"Outputs and scores saved to {path}")
    _report_review(terminalreporter, path, skill_hash)
