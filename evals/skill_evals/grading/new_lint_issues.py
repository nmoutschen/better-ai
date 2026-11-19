"""List the ruff issues in the Python files changed since the planted commit that the planted files did not have.

Run inside a copy of the submitted repository, with `$START_COMMIT` set, as a hidden check:

    python new_lint_issues.py                 # the repository's own ruff configuration
    python new_lint_issues.py --isolated --select F,B   # a fixed rule set, ignoring the repository's

An issue is new when its file, rule code and the stripped text of its line were not already flagged in
the planted version of that file, so moving a line does not make its issue new. The last line printed is
`<n> new issue(s)`, or `no Python file changed`. The exit code is 1 when there is a new issue, else 0.
Files Git ignores, such as an agent's working notes, are not checked.
"""

import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

Issue = tuple[str, str, str]


def changed_python_files(start: str) -> list[str]:
    """Return the Python files added, changed or renamed since `start`, including untracked ones."""
    subprocess.run(["git", "add", "-A"], check=True, capture_output=True)
    listing = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=AMR", start, "--", "*.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [path for path in listing.stdout.splitlines() if path]


def issues(root: Path, files: list[str], ruff_args: list[str]) -> Counter[Issue]:
    """Return ruff's issues in `files` under `root`, keyed by file, rule code and stripped line text."""
    if not files:
        return Counter()
    command = ["ruff", "check", "--no-cache", "--output-format=json", "--exit-zero", *ruff_args, *files]
    output = subprocess.run(command, cwd=root, check=True, capture_output=True, text=True).stdout
    found: Counter[Issue] = Counter()
    for issue in json.loads(output or "[]"):
        path = Path(issue["filename"]).resolve().relative_to(root.resolve()).as_posix()
        lines = (root / path).read_text(errors="replace").splitlines()
        row = issue["location"]["row"] - 1
        found[path, issue.get("code") or "syntax-error", lines[row].strip() if 0 <= row < len(lines) else ""] += 1
    return found


def main(ruff_args: list[str]) -> int:
    """Print the new issues and their count; return 1 when there is one."""
    start = os.environ["START_COMMIT"]
    changed = changed_python_files(start)
    if not changed:
        print("no Python file changed")
        return 0
    now = issues(Path.cwd(), changed, ruff_args)
    with tempfile.TemporaryDirectory() as planted:
        archive = subprocess.run(["git", "archive", start], check=True, capture_output=True).stdout
        subprocess.run(["tar", "-x", "-C", planted], input=archive, check=True)
        before = issues(Path(planted), [path for path in changed if (Path(planted) / path).exists()], ruff_args)
    new = now - before
    for (path, code, line), count in sorted(new.items()):
        print(f"{path}: {code}: {line}" + (f" (x{count})" if count > 1 else ""))
    print(f"{sum(new.values())} new issue(s)")
    return int(bool(new))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
