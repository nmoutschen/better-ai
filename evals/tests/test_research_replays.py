"""Tests for the research-better cases' good replays: none leaves a record pointing to one that does not exist."""

import shutil
import sys
from pathlib import Path

import pytest
import yaml
from inspect_ai.util._sandbox.local import LocalSandboxEnvironment

from skill_evals.agent import play_action

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
from better import run  # noqa: E402

CASES = ROOT / "evals" / "cases" / "research-better"
REPLAYS = sorted(CASES.glob("*/replays/good-*.yaml"))


@pytest.mark.parametrize("replay", REPLAYS, ids=lambda path: f"{path.parents[1].name}/{path.name}")
async def test_no_good_replay_leaves_a_dangling_pointer(replay: Path) -> None:
    """After a good replay's writes, `better.pyz check` passes on every board, so every ID a record names exists."""
    sandbox_env = LocalSandboxEnvironment()
    root = Path(sandbox_env.directory.name)
    try:
        shutil.copytree(replay.parents[1] / "repo", root, dirs_exist_ok=True)
        for action in yaml.safe_load(replay.read_text(encoding="utf-8")).get("actions") or []:
            if "write" in action:
                await play_action(sandbox_env, action)
        for board in sorted(root.glob(".research/*")):
            done = run("research-better", "check", str(board), cwd=root)
            assert done.returncode == 0, done.stdout + done.stderr
    finally:
        sandbox_env.directory.cleanup()


def test_there_are_good_replays() -> None:
    """The parametrized test above is not empty."""
    assert REPLAYS
