"""Read a skill's case folders and turn them into Inspect samples, one per case and condition.

Conditions: `no-skill` sends the request as is, `skill` installs the skill and invokes it with its slash
command, `one-sentence` appends the one-sentence instruction for the case's first source to the request,
`short-skill` installs a skill of the same name whose body is every sentence of `one_sentence.yaml` and invokes
it the same way, and `skill-installed` installs the skill and sends the request as is, so the agent must load
the skill itself.

A skill's kind, `behavioural` or `procedural`, is `metadata.kind` in its SKILL.md frontmatter. Behavioural skills
also run `skill-installed` by default, because agents are meant to load them for the work without a command.

A case folder `cases/<skill>/<case-id>/` holds `case.yaml` (id, rule, source, reads, situation, request, graders,
optional validation), `repo/` with the planted files, `checks/` with hidden files that graders reference by path, and
`replays/` with scripted runs for `tools/validate_cases.py` and the fake agent. A case about earlier work, such as
work the user asks the agent to correct, also has `earlier/`: `before/` with the files as they were before that work,
and `message.txt` with its commit message. The sandbox then starts with two commits, and the planted repository is
the last one. A case that needs a Git history, such as an audit that reads which files change together, has
`history/` instead: one folder per commit, in name order, with `files/` (the files that commit adds or changes),
`message.txt` and an optional `commit.env` that sets the author and date. `one_sentence.yaml` in
the skill folder holds the one-sentence instruction for each source, such as `SKILL.md#4` or `modes/bug-fix.md`.
"""

import copy
import re
from pathlib import Path
from typing import Any

import yaml
from inspect_ai.dataset import Sample

from skill_evals.grading.files import GRADERS

EVALS = Path(__file__).resolve().parents[1]
REPO = EVALS.parent
CASES = EVALS / "cases"
NO_SKILL = "no-skill"
WITH_SKILL = "skill"
ONE_SENTENCE = "one-sentence"
SHORT_SKILL = "short-skill"
SKILL_INSTALLED = "skill-installed"
CONDITIONS = (NO_SKILL, WITH_SKILL, ONE_SENTENCE, SHORT_SKILL, SKILL_INSTALLED)
SKILL_CONDITIONS = (WITH_SKILL, SHORT_SKILL)
INSTALLED_CONDITIONS = (WITH_SKILL, SHORT_SKILL, SKILL_INSTALLED)
BEHAVIOURAL = "behavioural"
PROCEDURAL = "procedural"
KINDS = (BEHAVIOURAL, PROCEDURAL)
# one-sentence names the tested rule, so it is a per-rule diagnostic rather than a default comparison.
DEFAULT_CONDITIONS = {
    PROCEDURAL: (NO_SKILL, WITH_SKILL, SHORT_SKILL),
    BEHAVIOURAL: (NO_SKILL, WITH_SKILL, SHORT_SKILL, SKILL_INSTALLED),
}
SKILL_NAME = re.compile(r"[a-z0-9][a-z0-9-]*")
# What a step of a planted history may set in its commit.env.
HISTORY_KEYS = ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_AUTHOR_DATE")
CASE_KEYS = ("id", "rule", "source", "reads", "situation", "request", "graders", "validation")
# The fields each grader type reads, besides `type`; a field outside the list is a typo that turns a check off.
GRADER_FIELDS: dict[str, tuple[str, ...]] = {
    "any_of": ("graders",),
    "catches_bug": ("tests", "files", "restore"),
    "command_fails": ("cmd", "files", "timeout"),
    "command_passes": ("cmd", "files", "timeout"),
    "diff_max_lines": ("max",),
    "file_contains": ("path", "pattern"),
    "file_keeps": ("path",),
    "file_not_contains": ("path", "pattern"),
    "file_unchanged": ("path",),
    "judge": ("rubric", "rubric_file", "observe"),
    "no_commit": (),
    "note_written": (),
    "notes_only": (),
    "planted_unchanged": ("except",),
    "ran_command": ("pattern",),
}
# The grader types that no function of grading/files.py implements: the scorer runs them itself.
SCORER_GRADERS = ("any_of", "judge", "ran_command")


def check_skill(skill: str) -> str:
    """Return the skill name, or raise when it is not a plain folder name."""
    if not SKILL_NAME.fullmatch(skill):
        raise ValueError(f"Invalid skill name: {skill!r}")
    return skill


def skill_kind(skill: str) -> str:
    """Return the skill's kind from `metadata.kind` in its SKILL.md frontmatter, or raise when it has none."""
    text = (REPO / "skills" / check_skill(skill) / "SKILL.md").read_text()
    frontmatter = yaml.safe_load(text.split("---", 2)[1]) or {}
    kind = (frontmatter.get("metadata") or {}).get("kind")
    if kind not in KINDS:
        raise ValueError(f"{skill!r} has metadata.kind {kind!r}; expected one of {', '.join(KINDS)}")
    return kind


def default_conditions(skill: str) -> list[str]:
    """Return the conditions a run of the skill uses when none are given: they depend on its kind."""
    return list(DEFAULT_CONDITIONS[skill_kind(skill)])


def case_dirs(skill: str) -> list[Path]:
    """Return the case folders of a skill, sorted by case id."""
    folder = CASES / check_skill(skill)
    if not folder.is_dir():
        raise ValueError(f"No cases for skill {skill!r}: there is no folder {folder}")
    return sorted(path.parent for path in folder.glob("*/case.yaml"))


def _resolve(specs: list[dict[str, Any]], directory: Path) -> list[dict[str, Any]]:
    """Replace the case-relative paths in each spec's `files` map with the files' contents.

    A judge's `rubric_file` is read the same way: its text comes first, then the case's own `rubric` sentences.
    """
    specs = copy.deepcopy(specs)
    for spec in specs:
        if "files" in spec:
            spec["files"] = {name: (directory / path).read_text() for name, path in spec["files"].items()}
        if "rubric_file" in spec:
            shared = (directory / spec.pop("rubric_file")).read_text().strip()
            spec["rubric"] = f"{shared}\n\n{spec.get('rubric', '')}".strip()
        if "graders" in spec:
            spec["graders"] = _resolve(spec["graders"], directory)
    return specs


def check_graders(name: str, specs: list[dict[str, Any]]) -> None:
    """Raise unless every grader, also inside any_of, has a known, implemented type and only the fields of that type."""
    for spec in specs:
        kind = spec.get("type")
        if kind not in GRADER_FIELDS:
            raise ValueError(f"{name}: unknown grader type {kind!r}")
        if kind not in GRADERS and kind not in SCORER_GRADERS:
            raise ValueError(f"{name}: grader type {kind!r} has no implementation")
        for key in spec.keys() - {"type", *GRADER_FIELDS[kind]}:
            raise ValueError(f"{name}: {kind} has an unknown field {key!r}")
        if kind == "any_of":
            check_graders(name, spec["graders"])


def check_case(directory: Path, case: dict[str, Any]) -> None:
    """Raise unless the case has only known keys, its id is its folder name, and its graders are valid."""
    name = directory.name
    for key in case.keys() - set(CASE_KEYS):
        raise ValueError(f"{name}: unknown key {key!r} in case.yaml; keys are {', '.join(CASE_KEYS)}")
    if case.get("id") != name:
        raise ValueError(f"{name}: id {case.get('id')!r} is not the folder name")
    check_graders(name, case.get("graders") or [])


def load_case(directory: Path) -> dict[str, Any]:
    """Load one case: its yaml fields, graders with file contents, and the planted files by path."""
    case = yaml.safe_load((directory / "case.yaml").read_text())
    check_case(directory, case)
    case["rule"] = str(case["rule"])
    case["source"] = [str(source) for source in case.get("source") or []]
    case["reads"] = case.get("reads") or []
    case["graders"] = _resolve(case["graders"], directory)
    repo = directory / "repo"
    case["files"] = {
        path.relative_to(repo).as_posix(): path
        for path in sorted(repo.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }
    earlier, history = directory / "earlier", directory / "history"
    if earlier.is_dir() and history.is_dir():
        raise ValueError(f"{directory.name}: a case has earlier/ or history/, not both")
    if history.is_dir():
        check_history(history)
    for folder in (earlier, history):
        if folder.is_dir():
            for path in sorted(folder.rglob("*")):
                if path.is_file():
                    case["files"][f".{folder.name}/{path.relative_to(folder).as_posix()}"] = path
    return case


def check_history(history: Path) -> None:
    """Raise unless each step of a planted history has a message and sets only the author and date."""
    steps = sorted(path for path in history.iterdir() if path.is_dir())
    if not steps:
        raise ValueError(f"{history}: no commit folders")
    for step in steps:
        if not (step / "message.txt").is_file():
            raise ValueError(f"{step}: no message.txt")
        env = step / "commit.env"
        if env.is_file():
            for line in env.read_text().splitlines():
                key = line.partition("=")[0]
                if line and key not in HISTORY_KEYS:
                    raise ValueError(f"{env}: {key!r} is not one of {', '.join(HISTORY_KEYS)}")


def load_cases(skill: str) -> list[dict[str, Any]]:
    """Load every case of a skill."""
    return [load_case(directory) for directory in case_dirs(skill)]


def source_sentences(skill: str) -> dict[str, str]:
    """Return the one-sentence instruction for each source that has one, from `one_sentence.yaml`."""
    path = CASES / check_skill(skill) / "one_sentence.yaml"
    if not path.exists():
        return {}
    return {str(source): text for source, text in (yaml.safe_load(path.read_text()) or {}).items()}


def short_skill(skill: str) -> str:
    """Return the SKILL.md of the short skill: the real skill's frontmatter, then every rule sentence as a list."""
    original = (REPO / "skills" / check_skill(skill) / "SKILL.md").read_text()
    frontmatter = original.split("---", 2)[1]
    sentences = source_sentences(skill)
    if not sentences:
        raise ValueError(f"No one_sentence.yaml for {skill!r}")
    body = "\n".join(f"- {text}" for text in sentences.values())
    return f"---{frontmatter}---\n\n{body}\n"


def replays(directory: Path) -> dict[str, dict[str, Any]]:
    """Return a case's replays by name, such as good-1 or bad-edits-test."""
    return {path.stem: yaml.safe_load(path.read_text()) for path in sorted((directory / "replays").glob("*.yaml"))}


def condition_prompt(request: str, condition: str, skill: str, sentence: str | None = None) -> str:
    """Build the prompt for a condition.

    no-skill and skill-installed send the request as is, skill and short-skill prefix the skill's slash
    command, and one-sentence appends the sentence for the case's first source to the request.
    """
    if condition in (NO_SKILL, SKILL_INSTALLED):
        return request
    if condition in SKILL_CONDITIONS:
        return f"/{skill} {request}"
    if condition == ONE_SENTENCE and sentence:
        return f"{request}\n\n{sentence}"
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
    """Build one sample per case and condition; one-sentence skips cases whose first source has no sentence.

    With `scripted`, each sample carries the run the fake agent plays.
    """
    sentences = source_sentences(skill)
    found = []
    loaded = load_cases(skill)
    if unknown := sorted(set(case_ids or []) - {case["id"] for case in loaded}):
        raise ValueError(f"No case {', '.join(unknown)} in {skill!r}; cases are {', '.join(c['id'] for c in loaded)}")
    for directory, case in zip(case_dirs(skill), loaded, strict=True):
        if (rule is not None and case["rule"] != rule) or (case_ids and case["id"] not in case_ids):
            continue
        for condition in conditions:
            sentence = sentences.get(case["source"][0]) if case["source"] else None
            if condition == ONE_SENTENCE and sentence is None:
                continue
            found.append(
                Sample(
                    id=f"{case['id']}-{condition}",
                    input=condition_prompt(case["request"], condition, skill, sentence),
                    files={path: str(source) for path, source in case["files"].items()},
                    metadata={
                        "case": case["id"],
                        "condition": condition,
                        "skill": skill,
                        "rule": case["rule"],
                        "source": case["source"],
                        "reads": case["reads"],
                        "situation": case["situation"],
                        "request": case["request"],
                        "graders": case["graders"],
                        **({"scripted_run": scripted_run(directory)} if scripted else {}),
                    },
                )
            )
    return found
