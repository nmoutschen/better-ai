"""Tests for tools/check_coverage.py: rule ids from SKILL.md headings and the coverage report."""

from pathlib import Path

import pytest

from skill_evals import cases
from tools import check_coverage


def test_code_better_coverage(capsys: pytest.CaptureFixture[str]) -> None:
    """Every code-better rule has a case, every case names a known rule, and case ids match their folders."""
    assert check_coverage.main(["code-better"]) == 0
    out = capsys.readouterr().out
    ids = [directory.name for directory in cases.case_dirs("code-better")]
    assert [case["id"] for case in cases.load_cases("code-better")] == ids
    assert "Uncovered rules: none" in out
    assert "Cases with unknown rules: none" in out


def test_dangling_rule_is_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A case whose rule is not a heading fails; headings inside code blocks and parent sections are not rules."""
    skill = tmp_path / "skills" / "another"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "## 1. Group\n### 1.1. Valid\n## 2. Standalone\n```md\n## 9. In a code block\n```\n"
    )
    case = tmp_path / "cases" / "another" / "typo"
    case.mkdir(parents=True)
    (case / "case.yaml").write_text("id: typo\nrule: '9'\nrequest: A case.\ngraders: []\n")
    monkeypatch.setattr(cases, "REPO", tmp_path)
    monkeypatch.setattr(cases, "CASES", tmp_path / "cases")
    assert check_coverage.main(["another"]) == 1
    assert "Uncovered rules: 1.1, 2, invocation" in capsys.readouterr().out
