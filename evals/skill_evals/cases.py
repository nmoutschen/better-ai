"""Read a skill's case folders and turn them into Inspect samples, one per case and condition.

Conditions: `no-skill` sends the request as is, `skill` installs the skill and invokes it with its slash
command, `one-sentence` appends the rule's one-sentence instruction to the request, and `short-skill` installs a
skill of the same name whose body is every sentence of `one_sentence.yaml` and invokes it the same way.

A case folder `cases/<skill>/<case-id>/` holds `case.yaml` (id, rule, situation, request, graders),
`repo/` with the planted files, `checks/` with hidden files that graders reference by path, and
`replays/` with scripted runs for `tools/validate_cases.py` and the fake agent. `one_sentence.yaml` in
the skill folder holds the one-sentence instruction for each rule.
"""

import copy
import re
from pathlib import Path
from typing import Any

import yaml
from inspect_ai.dataset import Sample

EVALS = Path(__file__).resolve().parents[1]
REPO = EVALS.parent
CASES = EVALS / "cases"
NO_SKILL = "no-skill"
WITH_SKILL = "skill"
ONE_SENTENCE = "one-sentence"
SHORT_SKILL = "short-skill"
CONDITIONS = (NO_SKILL, WITH_SKILL, ONE_SENTENCE, SHORT_SKILL)
SKILL_CONDITIONS = (WITH_SKILL, SHORT_SKILL)
# one-sentence names the tested rule, so it is a per-rule diagnostic rather than a default comparison.
DEFAULT_CONDITIONS = f"{NO_SKILL},{WITH_SKILL},{SHORT_SKILL}"
SKILL_NAME = re.compile(r"[a-z0-9][a-z0-9-]*")


def check_skill(skill: str) -> str:
    """Return the skill name, or raise when it is not a plain folder name."""
    if not SKILL_NAME.fullmatch(skill):
        raise ValueError(f"Invalid skill name: {skill!r}")
    return skill


def case_dirs(skill: str) -> list[Path]:
    """Return the case folders of a skill, sorted by case id."""
    return sorted(path.parent for path in (CASES / check_skill(skill)).glob("*/case.yaml"))


def _resolve(specs: list[dict[str, Any]], directory: Path) -> list[dict[str, Any]]:
    """Replace the case-relative paths in each spec's `files` map with the files' contents."""
    specs = copy.deepcopy(specs)
    for spec in specs:
        if "files" in spec:
            spec["files"] = {name: (directory / path).read_text() for name, path in spec["files"].items()}
        if "graders" in spec:
            spec["graders"] = _resolve(spec["graders"], directory)
    return specs


def load_case(directory: Path) -> dict[str, Any]:
    """Load one case: its yaml fields, graders with file contents, and the planted files by path."""
    case = yaml.safe_load((directory / "case.yaml").read_text())
    case["rule"] = str(case["rule"])
    case["graders"] = _resolve(case["graders"], directory)
    repo = directory / "repo"
    case["files"] = {path.relative_to(repo).as_posix(): path for path in sorted(repo.rglob("*")) if path.is_file()}
    return case


def load_cases(skill: str) -> list[dict[str, Any]]:
    """Load every case of a skill."""
    return [load_case(directory) for directory in case_dirs(skill)]


def rule_sentences(skill: str) -> dict[str, str]:
    """Return the one-sentence instruction for each rule that has one, from `one_sentence.yaml`."""
    path = CASES / check_skill(skill) / "one_sentence.yaml"
    if not path.exists():
        return {}
    return {str(rule): text for rule, text in (yaml.safe_load(path.read_text()) or {}).items()}


def short_skill(skill: str) -> str:
    """Return the SKILL.md of the short skill: the real skill's frontmatter, then every rule sentence as a list."""
    original = (REPO / "skills" / check_skill(skill) / "SKILL.md").read_text()
    frontmatter = original.split("---", 2)[1]
    sentences = rule_sentences(skill)
    if not sentences:
        raise ValueError(f"No one_sentence.yaml for {skill!r}")
    body = "\n".join(f"- {text}" for text in sentences.values())
    return f"---{frontmatter}---\n\n{body}\n"


def replays(directory: Path) -> dict[str, dict[str, Any]]:
    """Return a case's replays by name, such as good-1 or bad-edits-test."""
    return {path.stem: yaml.safe_load(path.read_text()) for path in sorted((directory / "replays").glob("*.yaml"))}


def condition_prompt(request: str, condition: str, skill: str, rule_sentence: str | None = None) -> str:
    """Build the prompt for a condition.

    no-skill sends the request as is, skill and short-skill prefix the skill's slash command, and one-sentence
    appends the rule's sentence to the request.
    """
    if condition == NO_SKILL:
        return request
    if condition in SKILL_CONDITIONS:
        return f"/{skill} {request}"
    if condition == ONE_SENTENCE and rule_sentence:
        return f"{request}\n\n{rule_sentence}"
    raise ValueError(f"No prompt for condition {condition!r}")


def parse_conditions(conditions: str | list[str]) -> list[str]:
    """Accept one condition, a comma-separated list or a list, such as "skill" or "no-skill,skill"."""
    names = conditions.split(",") if isinstance(conditions, str) else conditions
    chosen = [name.strip() for name in names if name.strip()]
    unknown = [name for name in chosen if name not in CONDITIONS]
    if not chosen or unknown:
        raise ValueError(f"Conditions are {', '.join(CONDITIONS)}; got {conditions!r}")
    return chosen


def scripted_run(directory: Path) -> dict[str, Any]:
    """Return the run the fake agent plays: the case's first good replay, or an empty run."""
    runs = replays(directory)
    good = sorted(name for name in runs if name.startswith("good"))
    return runs[good[0]] if good else {"actions": [], "reply": ""}


def samples(
    skill: str,
    conditions: list[str],
    rule: str | None = None,
    case_ids: list[str] | None = None,
    scripted: bool = False,
) -> list[Sample]:
    """Build one sample per case and condition; one-sentence skips rules without a sentence.

    With `scripted`, each sample carries the run the fake agent plays.
    """
    sentences = rule_sentences(skill)
    found = []
    for directory in case_dirs(skill):
        case = load_case(directory)
        if (rule is not None and case["rule"] != rule) or (case_ids and case["id"] not in case_ids):
            continue
        for condition in conditions:
            if condition == ONE_SENTENCE and case["rule"] not in sentences:
                continue
            found.append(
                Sample(
                    id=f"{case['id']}-{condition}",
                    input=condition_prompt(case["request"], condition, skill, sentences.get(case["rule"])),
                    files={path: str(source) for path, source in case["files"].items()},
                    metadata={
                        "case": case["id"],
                        "condition": condition,
                        "rule": case["rule"],
                        "situation": case["situation"],
                        "request": case["request"],
                        "graders": case["graders"],
                        **({"scripted_run": scripted_run(directory)} if scripted else {}),
                    },
                )
            )
    return found
