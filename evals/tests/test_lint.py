"""Tests for skill_evals/grading/new_lint_issues.py: only issues the change added count."""

import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "skill_evals" / "grading" / "new_lint_issues.py"


def git(repo: Path, *args: str) -> str:
    """Run git in the repository and return its stdout."""
    command = ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args]
    return subprocess.run(command, cwd=repo, check=True, capture_output=True, text=True).stdout


def run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run the script in the repository against its first commit."""
    env = {**os.environ, "START_COMMIT": git(repo, "rev-list", "--max-parents=0", "HEAD").strip()}
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=repo, env=env, capture_output=True, text=True)


def test_counts_only_new_issues(tmp_path: Path) -> None:
    """An issue the planted file already had is not new; one the change adds is; ignored files are skipped."""
    (tmp_path / "pyproject.toml").write_text('[tool.ruff.lint]\nselect = ["F"]\n')
    (tmp_path / "old.py").write_text("import os\n")
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-qm", "planted")
    assert run(tmp_path).stdout.strip() == "no Python file changed"

    (tmp_path / "old.py").write_text('"""Moved."""\n\nimport os\n')
    unchanged = run(tmp_path)
    assert unchanged.returncode == 0 and unchanged.stdout.strip() == "0 new issue(s)"

    (tmp_path / "new.py").write_text("import sys\n")
    (tmp_path / ".git" / "info" / "exclude").write_text("notes/\n")
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "scratch.py").write_text("import json\n")
    added = run(tmp_path)
    assert added.returncode == 1
    assert added.stdout.splitlines() == ["new.py: F401: import sys", "1 new issue(s)"]
