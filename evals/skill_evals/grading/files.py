"""Deterministic graders: check the result the agent left in the repository, never how it worked.

Each grader reads the submitted tree against the starting commit (Git diff, file contents) or runs a
hidden check on a disposable copy of it. How the agent worked (what it read, ran, asked or reported)
is left to the judge in `judge.py`. Hidden files go under `$GRADE_FILES`; `$START_COMMIT` names the
planted commit.
"""

import fnmatch
import re
from collections.abc import Awaitable, Callable
from pathlib import PurePosixPath
from typing import Any

from inspect_ai.util import ExecResult, OutputLimitExceededError, SandboxEnvironment

COMMAND_TIMEOUT = 60
TEST_FILE = re.compile(r"(?:^|/)(?:test_|check_)[^/]*\.py$|_test\.py$")
CACHE_FILE = re.compile(r"(?:^|/)__pycache__/|(?:^|/)\.pytest_cache/")
MARKDOWN_NOTE = re.compile(r"\.(?:md|markdown)$", re.IGNORECASE)
SNAPSHOT_SCRIPT = (
    'mkdir -p "$1/repo" "$1/grade" && cp -a ./. "$1/repo/"'
    ' && find "$1/repo" -name __pycache__ -type d -prune -exec rm -rf {} +'
)


class Checkout:
    """The submitted repository in the sandbox, compared with the planted commit."""

    def __init__(self, sandbox_env: SandboxEnvironment, start: str, workdir: str = "/work") -> None:
        """Wrap a sandbox whose `workdir` holds the repository planted at commit `start`."""
        self.sandbox_env, self.start, self.workdir = sandbox_env, start, workdir
        self.notes: list[str] = []
        self._planted: set[str] | None = None
        self._changed: tuple[set[str], set[str]] | None = None

    async def git(self, *args: str) -> str:
        """Run git in the repository and return its stdout."""
        result = await self.sandbox_env.exec(["git", *args], cwd=self.workdir, timeout=30)
        if not result.success:
            raise RuntimeError(f"git {' '.join(args)}: {result.stderr}")
        return result.stdout

    async def planted(self) -> set[str]:
        """Return the paths in the planted commit."""
        if self._planted is None:
            listing = await self.git("ls-tree", "-r", "--name-only", "-z", self.start)
            self._planted = set(listing.split("\0")) - {""}
        return self._planted

    async def changed(self) -> tuple[set[str], set[str]]:
        """Return changed tracked paths and untracked paths since the planted commit, without Python caches."""
        if self._changed is None:
            tracked = await self.git("diff", "--name-only", "--no-renames", "-z", self.start, "--")
            untracked = await self.git("ls-files", "--others", "--exclude-standard", "-z")
            self._changed = tuple(
                {path for path in listing.split("\0") if path and not CACHE_FILE.search(path)}
                for listing in (tracked, untracked)
            )
        return self._changed

    async def all_changed(self) -> set[str]:
        """Return every changed or new path."""
        tracked, untracked = await self.changed()
        return tracked | untracked

    async def planted_text(self, path: str) -> str | None:
        """Return a file's planted content, or None when the planted commit has no such file."""
        result = await self.sandbox_env.exec(["git", "show", f"{self.start}:{path}"], cwd=self.workdir)
        return result.stdout if result.success else None

    async def text(self, path: str) -> str | None:
        """Return a file's submitted content, or None when it is missing or not text."""
        try:
            return await self.sandbox_env.read_file(f"{self.workdir}/{path}")
        except (FileNotFoundError, IsADirectoryError, UnicodeDecodeError, PermissionError):
            return None

    async def snapshot_run(
        self,
        command: str,
        *,
        restore: tuple[str, ...] | list[str] = (),
        files: dict[str, str] | None = None,
        hidden: dict[str, str] | None = None,
        timeout: int = COMMAND_TIMEOUT,
    ) -> ExecResult[str] | None:
        """Run a Bash command on a disposable copy of the tree; None after a timeout or sandbox failure.

        `restore` puts planted files back, `files` replaces files in the copy, and `hidden` files go
        under `$GRADE_FILES`.
        """
        directory = None
        try:
            directory = (await self.sandbox_env.exec(["mktemp", "-d"])).stdout.strip()
            copy = await self.sandbox_env.exec(["bash", "-c", SNAPSHOT_SCRIPT, "bash", directory], cwd=self.workdir)
            if not directory or not copy.success:
                raise RuntimeError(f"snapshot: {copy.stderr}")
            replaced = dict(files or {})
            for path in restore:
                planted = await self.planted_text(path)
                if planted is None:
                    raise RuntimeError(f"{path} is not in the planted commit")
                replaced[path] = planted
            for path, content in replaced.items():
                await self.sandbox_env.write_file(f"{directory}/repo/{path}", content)
            for path, content in (hidden or {}).items():
                relative = PurePosixPath(path)
                if relative.is_absolute() or ".." in relative.parts:
                    raise ValueError(f"Invalid hidden file path: {path!r}")
                await self.sandbox_env.write_file(f"{directory}/grade/{relative}", content)
            env = {"GRADE_FILES": f"{directory}/grade", "START_COMMIT": self.start}
            return await self.sandbox_env.exec(
                ["bash", "-c", command], cwd=f"{directory}/repo", env=env, timeout=timeout, timeout_retry=False
            )
        except (TimeoutError, OutputLimitExceededError, RuntimeError, OSError, ValueError) as error:
            self.notes.append(f"{command[:80]}: {type(error).__name__}: {error}")
            return None
        finally:
            if directory:
                await self.sandbox_env.exec(["rm", "-rf", "--", directory])


async def file_unchanged(spec: dict[str, Any], repo: Checkout) -> bool:
    """The file is in the planted commit and has no change."""
    return spec["path"] in await repo.planted() and spec["path"] not in await repo.all_changed()


async def file_keeps(spec: dict[str, Any], repo: Checkout) -> bool:
    """Every non-blank planted line is still there, in order, ignoring indentation; additions are allowed."""
    original, current = await repo.planted_text(spec["path"]), await repo.text(spec["path"])
    if original is None or current is None:
        return False
    remaining = iter(line.strip() for line in current.splitlines())
    return all(line.strip() in remaining for line in original.splitlines() if line.strip())


async def file_contains(spec: dict[str, Any], repo: Checkout) -> bool:
    """The file exists and matches the regex."""
    text = await repo.text(spec["path"])
    return text is not None and re.search(spec["pattern"], text) is not None


async def file_not_contains(spec: dict[str, Any], repo: Checkout) -> bool:
    """The file exists and does not match the regex."""
    text = await repo.text(spec["path"])
    return text is not None and re.search(spec["pattern"], text) is None


async def planted_unchanged(spec: dict[str, Any], repo: Checkout) -> bool:
    """No planted file changed except those matching `except`; new files are always allowed."""
    tracked, _ = await repo.changed()
    allowed = spec.get("except", [])
    changed = tracked & await repo.planted()
    return all(any(fnmatch.fnmatch(path, pattern) for pattern in allowed) for path in changed)


async def notes_only(spec: dict[str, Any], repo: Checkout) -> bool:
    """Every changed or new file is a Markdown note: no code or data changed."""
    return all(MARKDOWN_NOTE.search(path) for path in await repo.all_changed())


async def diff_max_lines(spec: dict[str, Any], repo: Checkout) -> bool:
    """Added plus removed lines in planted files are within `max`; new files do not count, binary changes fail."""
    planted = await repo.planted()
    stats = await repo.git("diff", "--numstat", "--no-renames", "-z", repo.start, "--")
    lines = 0
    for row in filter(None, stats.split("\0")):
        added, removed, path = row.split("\t", 2)
        if path not in planted or CACHE_FILE.search(path):
            continue
        if "-" in (added, removed):
            return False
        lines += int(added) + int(removed)
    return lines <= spec["max"]


async def command_passes(spec: dict[str, Any], repo: Checkout) -> bool:
    """The hidden command exits zero on a copy of the submitted tree."""
    timeout = spec.get("timeout", COMMAND_TIMEOUT)
    result = await repo.snapshot_run(spec["cmd"], hidden=spec.get("files"), timeout=timeout)
    return result is not None and result.success


async def command_fails(spec: dict[str, Any], repo: Checkout) -> bool:
    """The hidden command exits nonzero on a copy of the submitted tree."""
    timeout = spec.get("timeout", COMMAND_TIMEOUT)
    result = await repo.snapshot_run(spec["cmd"], hidden=spec.get("files"), timeout=timeout)
    return result is not None and not result.success


async def catches_bug(spec: dict[str, Any], repo: Checkout) -> bool:
    """A test file the agent added or changed catches the bug.

    The test must pass on the submitted code and fail on an assertion once the bug is back: the planted
    files listed in `restore`, or the replacement `files`.
    """
    changed = await repo.all_changed()
    named = [path for path in spec.get("tests", []) if path in changed]
    for test in dict.fromkeys([*named, *sorted(path for path in changed if TEST_FILE.search(path))]):
        source = await repo.text(test) or ""
        module = test.removesuffix(".py").replace("/", ".")
        command = f"PYTHONPATH=. python -m unittest {module}" if "TestCase" in source else f"PYTHONPATH=. python {test}"
        passes = await repo.snapshot_run(command)
        if passes is None or not passes.success:
            continue
        buggy = await repo.snapshot_run(command, restore=spec.get("restore", ()), files=spec.get("files"))
        if buggy is not None and not buggy.success and "AssertionError" in buggy.stdout + buggy.stderr:
            return True
    return False


GRADERS: dict[str, Callable[[dict[str, Any], Checkout], Awaitable[bool]]] = {
    "file_unchanged": file_unchanged,
    "file_keeps": file_keeps,
    "file_contains": file_contains,
    "file_not_contains": file_not_contains,
    "planted_unchanged": planted_unchanged,
    "notes_only": notes_only,
    "diff_max_lines": diff_max_lines,
    "command_passes": command_passes,
    "command_fails": command_fails,
    "catches_bug": catches_bug,
}
