"""Compare a skill's numbered rules with the rules its eval cases target.

Lists the numbered rule headings of `skills/<skill>/SKILL.md` (plus `invocation`), the rules the cases
use, the rules no case covers, and cases whose rule does not exist. Unknown rules exit 1; uncovered
rules are only reported.

    uv run python -m tools.check_coverage code-better
"""

import argparse
import re

import yaml

from skill_evals import cases

HEADING = re.compile(r"^(#{2,6})\s+([0-9]+(?:\.[0-9]+)*)(?:[.:)]?\s|$)")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")


def rule_ids(text: str) -> set[str]:
    """Return the numbered rule ids in a SKILL.md, skipping code blocks; a section with subsections is not a rule."""
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
        if match := HEADING.match(line):
            level, rule = match.groups()
            if level == "##":
                parent = rule
            elif parent and rule.startswith(parent + "."):
                rules.discard(parent)
            rules.add(rule)
    return rules


def main(argv: list[str] | None = None) -> int:
    """Print the coverage report for one skill; return 1 when a case names an unknown rule."""
    parser = argparse.ArgumentParser(description="Compare a skill's numbered rules with its eval cases.")
    parser.add_argument("skill")
    skill = cases.check_skill(parser.parse_args(argv).skill)
    rules = rule_ids((cases.REPO / "skills" / skill / "SKILL.md").read_text())
    found = [yaml.safe_load((path / "case.yaml").read_text()) for path in cases.case_dirs(skill)]
    used = {str(case["rule"]) for case in found}
    dangling = [f"{case['id']} ({case['rule']})" for case in found if str(case["rule"]) not in rules]
    print(f"Skill: {skill}")
    print("Rules:", ", ".join(sorted(rules)) or "none")
    print("Rules used:", ", ".join(sorted(used)) or "none")
    print("Uncovered rules:", ", ".join(sorted(rules - used)) or "none")
    print("Cases with unknown rules:", ", ".join(dangling) or "none")
    return int(bool(dangling))


if __name__ == "__main__":
    raise SystemExit(main())
