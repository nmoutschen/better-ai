"""Shared fixtures: a planted Git repository in a local Inspect sandbox, wrapped as a Checkout."""

import subprocess
import sys
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from typing import Any

import pytest
from inspect_ai.model import ChatMessageAssistant
from inspect_ai.tool import ToolCall
from inspect_ai.util._sandbox.local import LocalSandboxEnvironment

from skill_evals.agent import AGENT_USER, IGNORED_PATHS, SKILLS_FOLDER, START_SCRIPT, home
from skill_evals.grading.files import Checkout

Plant = Callable[[dict[str, str]], Awaitable[Checkout]]


def skill_dir(skill: str) -> str:
    """Where the sandbox's agent user finds an installed skill."""
    return f"{home(AGENT_USER)}/{SKILLS_FOLDER}/{skill}"


def assistant(*calls: tuple[str, dict[str, Any]], subagent: bool = False) -> ChatMessageAssistant:
    """An assistant message making the given (tool, arguments) calls, from a sub-agent if asked."""
    tool_calls = [ToolCall(id=f"call-{n}", function=name, arguments=args) for n, (name, args) in enumerate(calls)]
    message = ChatMessageAssistant(content="", tool_calls=tool_calls)
    if subagent:
        message.metadata = {"subagent_of": "task-1"}
    return message


def git(cwd: Path, *args: str) -> str:
    """Run git in a folder, as a throwaway committer, and return its stdout."""
    command = ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args]
    return subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True).stdout


def write_tree(root: Path, files: dict[str, str]) -> None:
    """Write each file under root, creating folders."""
    for path, text in files.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text)


def write_case(root: Path, text: str, folder: str = "a-case") -> Path:
    """Write a case folder holding a one-file repo and the given case.yaml text, and return the folder."""
    write_tree(root / folder, {"repo/main.py": "x = 1\n", "case.yaml": text})
    return root / folder


def plant_dir(case: dict, target: Path) -> None:
    """Copy a loaded case's files into target, as the sandbox receives them."""
    for path, source in case["files"].items():
        (target / path).parent.mkdir(parents=True, exist_ok=True)
        (target / path).write_bytes(source.read_bytes())


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
