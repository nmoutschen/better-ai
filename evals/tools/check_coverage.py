"""Compare a skill's rules and files with the sources its eval cases point to.

Each case's `source` lists where its rule lives in the current skill: `SKILL.md#<section>` for a
numbered rule heading of `skills/<skill>/SKILL.md`, the slug of an unnumbered `###` heading such as
`SKILL.md#ask-the-user`, `SKILL.md#invocation`, or another file of the
skill folder, such as `modes/bug-fix.md`. Its `reads` lists the skill files the skill condition should
read. The report lists the sections and files no case points to, and cases whose sources or reads do not
exist. A case's `rule` names the behaviour it tests, independent of the skill's sections, so it is not checked
here. The keys of `cases/<skill>/one_sentence.yaml` must be sources too. Unknown sources, reads or sentence
keys exit 1; uncovered sections and files are only reported.

    uv run python -m tools.check_coverage code-better
"""

import argparse
import re
from pathlib import Path
from typing import Any

import yaml

from skill_evals import cases

HEADING = re.compile(r"^(#{2,6})\s+([0-9]+(?:\.[0-9]+)*)(?:[.:)]?\s|$)")
NAMED = re.compile(r"^###\s+([^0-9\s].*?)\s*$")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")


def rule_ids(text: str) -> set[str]:
    """Return the rule ids in a SKILL.md, skipping code blocks: numbered headings, where a section with subsections is
    not a rule, and unnumbered `###` headings by their slug, such as `ask-the-user`."""
    rules = {"invocation"}
    parent = fence = None
    for line in text.splitlines():
        if match := FENCE.match(line):
            if fence is None:
                fence = match[1]
            elif match[1].startswith(fence) and not line[match.end() :].strip():
                fence = None
            continue
        if fence is not None:
            continue
        if line.startswith("## "):
            parent = None
        if match := NAMED.match(line):
            rules.add(re.sub(r"[^a-z0-9]+", "-", match[1].lower()).strip("-"))
            continue
        if match := HEADING.match(line):
            level, rule = match.groups()
            if level == "##":
                parent = rule
            elif parent and rule.startswith(parent + "."):
                rules.discard(parent)
            rules.add(rule)
    return rules


def skill_sources(folder: Path) -> set[str]:
    """Return every valid source: `SKILL.md#<rule>` for each rule, and every other file of the skill folder."""
    sections = {f"SKILL.md#{rule}" for rule in rule_ids((folder / "SKILL.md").read_text())}
    files = {path.relative_to(folder).as_posix() for path in folder.rglob("*") if path.is_file()}
    return sections | (files - {"SKILL.md"})


def read_paths(case: dict[str, Any]) -> list[str]:
    """Flatten a case's `reads`, whose entries are a path or a list of alternative paths."""
    return [path for entry in case.get("reads") or [] for path in ([entry] if isinstance(entry, str) else entry)]


def main(argv: list[str] | None = None) -> int:
    """Print the coverage report for one skill; return 1 when a case names an unknown source or read."""
    parser = argparse.ArgumentParser(description="Compare a skill's rules and files with its eval cases.")
    parser.add_argument("skill")
    skill = cases.check_skill(parser.parse_args(argv).skill)
    sources = skill_sources(cases.REPO / "skills" / skill)
    found = [yaml.safe_load((path / "case.yaml").read_text()) for path in cases.case_dirs(skill)]
    used = {str(source) for case in found for source in case.get("source") or []}
    dangling = [
        f"{case['id']} ({path})"
        for case in found
        for path in [*map(str, case.get("source") or []), *read_paths(case)]
        if path not in sources or path == "SKILL.md"
    ]
    no_source = [case["id"] for case in found if not case.get("source")]
    dangling += [f"one_sentence.yaml ({key})" for key in cases.source_sentences(skill) if key not in sources]
    no_sentence = sorted(
        {str(case["source"][0]) for case in found if case.get("source")} - set(cases.source_sentences(skill))
    )
    print(f"Skill: {skill}")
    print("Sources:", ", ".join(sorted(sources)) or "none")
    print("Uncovered sources:", ", ".join(sorted(sources - used)) or "none")
    print("Cases without a source:", ", ".join(no_source) or "none")
    print("First sources without a sentence:", ", ".join(no_sentence) or "none")
    print("Cases with unknown sources or reads:", ", ".join(dangling) or "none")
    return int(bool(dangling or no_source))


if __name__ == "__main__":
    raise SystemExit(main())
