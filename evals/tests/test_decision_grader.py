"""The research grader decision_recorded.py accepts a decision only in a shape the shared decision schema allows."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

CHECKS = Path(__file__).resolve().parents[1] / "cases" / "research-better" / "_checks"
BASE = {
    "type": "decision",
    "at": "2026-11-21T10:00:00Z",
    "by": "coordinator",
    "id": "D1",
    "raised_by": "coordinator",
    "about": {"type": "board"},
    "asked": "x",
    "default": "y",
    "deadline": "2026-11-21T10:10:00Z",
}


def grade(tmp_path: Path, record: dict) -> int:
    """Run the grader on a board holding one decision; return its exit code."""
    board = tmp_path / ".research" / "b"
    board.mkdir(parents=True)
    (board / "brief.json").write_text("{}")
    (board / "decisions.jsonl").write_text(json.dumps(record) + "\n")
    env = {**os.environ, "GRADE_FILES": str(CHECKS)}
    return subprocess.run(
        [sys.executable, str(CHECKS / "decision_recorded.py")], cwd=tmp_path, env=env, capture_output=True
    ).returncode


@pytest.mark.parametrize("status", ["waiting", "defaulted", "answered"])
def test_a_decision_with_default_and_deadline_passes(tmp_path: Path, status: str) -> None:
    """A status that carries a default and a deadline in the shared shape passes."""
    assert grade(tmp_path, {**BASE, "status": status}) == 0


@pytest.mark.parametrize("status", ["decided", "pending", "default", "changed"])
def test_a_status_the_schema_refuses_with_default_and_deadline_fails(tmp_path: Path, status: str) -> None:
    """decided, and the old statuses, fail even with a default and a deadline."""
    assert grade(tmp_path, {**BASE, "status": status, "decision": "z"}) != 0
