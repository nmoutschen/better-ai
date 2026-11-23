"""Tests for tools/validate_cases.py: unknown names fail, and the untouched-repo rule covers any_of."""

import asyncio
from pathlib import Path

import pytest
from conftest import write_case

from tools import validate_cases


def graders_case(root: Path, graders: str) -> Path:
    """Write a one-file case whose graders are the given yaml, and return its folder."""
    text = (
        f"id: nested-check\nrule: some-behaviour\nsource: []\nsituation: A case.\nrequest: Do it.\ngraders:\n{graders}"
    )
    return write_case(root, text, "nested-check")


def test_unknown_case_id_fails(capsys: pytest.CaptureFixture[str]) -> None:
    """A case id that matches no folder is reported, and the exit code is 1."""
    assert validate_cases.main(["code-better", "invoice-half-upp"]) == 1
    captured = capsys.readouterr()
    assert "invoice-half-upp" in captured.out + captured.err


def test_unknown_skill_fails(capsys: pytest.CaptureFixture[str]) -> None:
    """A skill with no case folder is reported, and the exit code is 1."""
    assert validate_cases.main(["nonexistent-skill"]) == 1
    captured = capsys.readouterr()
    assert "nonexistent-skill" in captured.out + captured.err


def test_command_passes_inside_any_of_must_fail_untouched(tmp_path: Path) -> None:
    """A nested command_passes that passes on the untouched repo is a problem, like a top-level one."""
    graders = (
        "  - type: file_contains\n    path: main.py\n    pattern: NEVER\n"
        "  - type: any_of\n    graders:\n      - type: command_passes\n        cmd: 'true'\n"
    )
    problems = asyncio.run(validate_cases.validate(graders_case(tmp_path, graders), False))
    assert any("passes on the untouched repo" in problem and "any_of" in problem for problem in problems)


def test_nested_command_that_fails_untouched_is_fine(tmp_path: Path) -> None:
    """A nested command_passes that fails on the untouched repo raises no problem."""
    graders = (
        "  - type: file_contains\n    path: main.py\n    pattern: NEVER\n"
        "  - type: any_of\n    graders:\n      - type: command_passes\n        cmd: 'false'\n"
    )
    case = graders_case(tmp_path, graders)
    assert asyncio.run(validate_cases.validate(case, False)) == []
    # A good replay's bash action that exits nonzero is reported, unless it says `fails: true`.
    (case / "replays").mkdir()
    replay = case / "replays" / "good-1.yaml"
    replay.write_text("actions:\n  - bash: 'echo NEVER >> main.py; false'\n")
    assert any("without `fails: true`" in problem for problem in asyncio.run(validate_cases.validate(case, False)))
    replay.write_text("actions:\n  - bash: 'echo NEVER >> main.py; false'\n    fails: true\n")
    assert not any("fails: true" in problem for problem in asyncio.run(validate_cases.validate(case, False)))


def test_nested_any_of_key_equals_the_scorer_key() -> None:
    """A command_passes in an any_of inside an any_of is named as the scorer names it: any_of.2.1."""
    inner = {"type": "any_of", "graders": [{"type": "judge"}, {"type": "command_passes", "cmd": "true"}]}
    specs = [{"type": "any_of", "graders": [{"type": "judge"}, inner]}]
    assert [key for key, _ in validate_cases.nested_commands(specs)] == ["any_of.2.2"]
    flat = [{"type": "any_of", "graders": [{"type": "command_passes", "cmd": "true"}, inner]}]
    assert [key for key, _ in validate_cases.nested_commands(flat)] == ["any_of.1", "any_of.2.2"]
