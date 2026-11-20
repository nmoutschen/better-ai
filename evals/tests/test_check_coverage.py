"""Tests for tools/check_coverage.py: rule ids from SKILL.md headings, case sources and reads, and the report."""

from pathlib import Path

import pytest

from skill_evals import cases
from tools import check_coverage


def test_code_better_coverage(capsys: pytest.CaptureFixture[str]) -> None:
    """Every code-better case points to existing sources and reads, and case ids match their folders."""
    assert check_coverage.main(["code-better"]) == 0
    out = capsys.readouterr().out
    ids = [directory.name for directory in cases.case_dirs("code-better")]
    assert [case["id"] for case in cases.load_cases("code-better")] == ids
    assert "Cases without a source: none" in out
    assert "Cases with unknown sources or reads: none" in out


def test_dangling_rule_is_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A source that is not a heading fails; headings inside code blocks and parent sections are not rules."""
    skill = tmp_path / "skills" / "another"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "## 1. Group\n### 1.1. Valid\n## 2. Standalone\n```md\n## 9. In a code block\n```\n"
    )
    case = tmp_path / "cases" / "another" / "typo"
    case.mkdir(parents=True)
    (skill / "modes").mkdir()
    (skill / "modes" / "fix.md").write_text("# Mode\n")
    (case / "case.yaml").write_text(
        "id: typo\nrule: '1'\nsource: ['SKILL.md#9', modes/fix.md]\nreads: [[modes/fix.md, modes/gone.md]]\n"
        "request: A case.\ngraders: []\n"
    )
    monkeypatch.setattr(cases, "REPO", tmp_path)
    monkeypatch.setattr(cases, "CASES", tmp_path / "cases")
    assert check_coverage.main(["another"]) == 1
    out = capsys.readouterr().out
    assert "Uncovered sources: SKILL.md#1.1, SKILL.md#2, SKILL.md#invocation" in out
    assert "Cases with unknown sources or reads: typo (SKILL.md#9), typo (modes/gone.md)" in out


def test_rule_ids_include_named_headings() -> None:
    """Numbered headings and unnumbered `###` headings, by slug, are rules."""
    text = "## Instructions\n\n### 1. Understand\n\n## General rules\n\n### Ask the user\n\n### Working notes\n"
    assert check_coverage.rule_ids(text) == {"invocation", "1", "ask-the-user", "working-notes"}


def test_numeric_rule_is_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A rule made only of digits and dots names a section, not a behaviour, so the coverage check fails."""
    skill = tmp_path / "skills" / "another"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("## 1. Standalone\n")
    monkeypatch.setattr(cases, "REPO", tmp_path)
    monkeypatch.setattr(cases, "CASES", tmp_path / "cases")
    for rule, expected in (("'1.1'", 1), ("5", 1), ("ask-first", 0)):
        case = tmp_path / "cases" / "another" / "a-case"
        case.mkdir(parents=True, exist_ok=True)
        (case / "case.yaml").write_text(
            f"id: a-case\nrule: {rule}\nsource: ['SKILL.md#1']\nrequest: A case.\ngraders: []\n"
        )
        assert check_coverage.main(["another"]) == expected
    assert "Cases with a numeric rule" in capsys.readouterr().out


@pytest.mark.parametrize("skill", ["code-better", "do-better", "write-better"])
def test_rules_name_behaviours(skill: str) -> None:
    """No case's rule is a section number."""
    assert [case["id"] for case in cases.load_cases(skill) if check_coverage.NUMERIC_RULE.fullmatch(case["rule"])] == []
