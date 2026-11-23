"""Tests for skill_evals/grading/commands.py: a command counts wherever it ran."""

from conftest import assistant

from skill_evals.grading.commands import ran_command


def test_ran_command_at_any_point() -> None:
    """A matching command passes wherever it ran, also before an edit; no matching command fails."""
    log = ("Bash", {"command": "git log --name-only --since=12.months"})
    write = ("Write", {"file_path": "/work/.code/audit/findings.md"})
    spec = {"pattern": r"\bgit\s+log\b"}
    assert ran_command(spec, [assistant(log, write)])
    assert not ran_command(spec, [assistant(("Bash", {"command": "git status"}), write)])
