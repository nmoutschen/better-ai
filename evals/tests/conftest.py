"""Shared fixtures: a planted Git repository in a local Inspect sandbox, wrapped as a Checkout."""

import sys
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path

import pytest
from inspect_ai.util._sandbox.local import LocalSandboxEnvironment

from skill_evals.agent import IGNORED_PATHS, START_SCRIPT
from skill_evals.grading.files import Checkout

Plant = Callable[[dict[str, str]], Awaitable[Checkout]]


@pytest.fixture
def python_on_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Make `python` in sandbox commands run this interpreter."""
    directory = tmp_path / "bin"
    directory.mkdir()
    (directory / "python").symlink_to(sys.executable)
    monkeypatch.setenv("PATH", f"{directory}:{Path(sys.executable).parent}:/usr/bin:/bin")


@pytest.fixture
async def plant(python_on_path: None) -> AsyncIterator[Plant]:
    """Return a function that commits the given files as the planted repository and returns its Checkout."""
    sandbox_envs: list[LocalSandboxEnvironment] = []

    async def make(files: dict[str, str]) -> Checkout:
        sandbox_env = LocalSandboxEnvironment()
        sandbox_envs.append(sandbox_env)
        for path, content in files.items():
            await sandbox_env.write_file(path, content)
        started = await sandbox_env.exec(["bash", "-ec", START_SCRIPT, "bash", *IGNORED_PATHS])
        assert started.success, started.stderr
        return Checkout(sandbox_env, started.stdout.split()[-1], sandbox_env.directory.name)

    yield make
    for sandbox_env in sandbox_envs:
        sandbox_env.directory.cleanup()
