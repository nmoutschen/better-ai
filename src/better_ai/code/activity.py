"""How much each task's branch changed, and when: the dashboard's measure of progress, read from git rather than from
what the agents log (design: .design/code-better-board/design.md, D3).

For a branch, `branch_activity` counts the lines added and removed per 5-minute bucket since a time (when the task's
first card was added): the commits of the branch authored since then, at their commit time, and the changes not yet
committed in the branch's worktree, at their file's modification time. A commit authored before then, as one a rebase
brought in, is not the task's work. The change folders (`.code/`) are never counted: they are the agents' records, not
their work. A branch git cannot read gives None, never an error.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

BUCKET = 300  # seconds
TIMEOUT = 5  # seconds per git call: the page asks every 2 seconds
LARGEST = 2_000_000  # bytes of an untracked file counted; a larger one counts as one line
NOT_WORK = ("--", ".", ":(exclude).code")  # pathspec: everything but the change folders


def _git(cwd: Path, *args: str) -> str | None:
    """The output of one git command, or None if it fails or git cannot be run."""
    try:
        done = subprocess.run(
            ["git", "-C", str(cwd), *args], capture_output=True, text=True, timeout=TIMEOUT, check=False
        )
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError):
        return None
    return done.stdout if done.returncode == 0 else None


def worktrees(root: Path) -> dict[str, Path]:
    """The worktree of each checked-out branch, by branch name."""
    found: dict[str, Path] = {}
    text = _git(root, "worktree", "list", "--porcelain") or ""
    path = None
    for line in text.splitlines():
        if line.startswith("worktree "):
            path = Path(line[len("worktree ") :])
        elif line.startswith("branch refs/heads/") and path is not None:
            found[line[len("branch refs/heads/") :]] = path
    return found


def _numstat(line: str) -> tuple[int, int, str] | None:
    parts = line.split("\t")
    if len(parts) < 3:
        return None
    added, removed = (int(n) if n.isdigit() else 0 for n in parts[:2])
    return added, removed, parts[-1]


def _lines_of(path: Path) -> int:
    try:
        if path.stat().st_size > LARGEST:
            return 1
        with open(path, "rb") as handle:
            data = handle.read()
    except OSError:
        return 0
    return data.count(b"\n") + (0 if data.endswith(b"\n") or not data else 1)


def branch_activity(root: Path, branch: str, since: float, trees: dict[str, Path] | None = None) -> dict | None:
    """The activity of `branch` since `since` (epoch seconds): `buckets` as [start, lines] pairs in time order, the
    `commits`, `files`, lines `added` and `removed`, and `last`, the time of the last change (or None). None when git
    cannot read the branch."""
    if (
        not branch
        or branch.startswith("-")
        or _git(root, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}") is None
    ):
        return None
    buckets: dict[int, int] = {}
    files: set[str] = set()
    added = removed = commits = 0
    last: float | None = None

    def count(when: float, plus: int, minus: int, name: str) -> None:
        nonlocal added, removed, last
        start = int(when) // BUCKET * BUCKET
        buckets[start] = buckets.get(start, 0) + plus + minus
        added, removed = added + plus, removed + minus
        files.add(name)
        last = when if last is None else max(last, when)

    log = _git(
        root,
        "log",
        f"refs/heads/{branch}",
        f"--since=@{int(since)}",
        "--first-parent",
        "--no-merges",
        "--numstat",
        "--format=@%ct %at",
        *NOT_WORK,
    )
    if log is None:
        return None
    when = None
    for line in log.splitlines():
        if line.startswith("@"):
            stamps = line[1:].split()
            if len(stamps) != 2 or not all(n.isdigit() for n in stamps):
                when = None
                continue
            committed, authored = (int(n) for n in stamps)
            when = committed if authored >= since else None
            if when is not None:
                commits += 1
                last = when if last is None else max(last, when)
        elif when is not None and (stat := _numstat(line)):
            count(when, *stat)
    tree = (trees if trees is not None else worktrees(root)).get(branch)
    if tree is not None:
        for line in (_git(tree, "diff", "--numstat", "HEAD", *NOT_WORK) or "").splitlines():
            stat = _numstat(line)
            if stat:
                _uncommitted(tree, stat, since, count)
        for name in (_git(tree, "ls-files", "--others", "--exclude-standard", *NOT_WORK) or "").splitlines():
            _uncommitted(tree, (_lines_of(tree / name), 0, name), since, count)
    return {
        "buckets": sorted([start, n] for start, n in buckets.items()),
        "commits": commits,
        "files": len(files),
        "added": added,
        "removed": removed,
        "last": last,
    }


def _uncommitted(tree: Path, stat: tuple[int, int, str], since: float, count) -> None:
    plus, minus, name = stat
    try:
        when = os.stat(tree / name).st_mtime
    except OSError:  # a deleted file has no time of its own: not counted until it is committed
        return
    if when >= since and plus + minus:
        count(when, plus, minus, name)
