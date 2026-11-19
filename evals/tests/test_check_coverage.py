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
