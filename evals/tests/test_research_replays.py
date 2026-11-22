"""Tests for the research-better cases' good replays: none leaves a record pointing to one that does not exist."""

import shutil
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
from better import run  # noqa: E402

CASES = ROOT / "evals" / "cases" / "research-better"
REPLAYS = sorted(CASES.glob("*/replays/good-*.yaml"))


@pytest.mark.parametrize("replay", REPLAYS, ids=lambda path: f"{path.parents[1].name}/{path.name}")
def test_no_good_replay_leaves_a_dangling_pointer(replay: Path, tmp_path: Path) -> None:
    """After a good replay's writes, `better.pyz check` passes on every board, so every ID a record names exists."""
    shutil.copytree(replay.parents[1] / "repo", tmp_path, dirs_exist_ok=True)
    for action in yaml.safe_load(replay.read_text(encoding="utf-8")).get("actions") or []:
        if "write" in action:
            target = tmp_path / action["write"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(action["content"], encoding="utf-8")
    for board in sorted(tmp_path.glob(".research/*")):
        done = run("research-better", "check", str(board), cwd=tmp_path)
        assert done.returncode == 0, done.stdout + done.stderr


def test_there_are_good_replays() -> None:
    """The parametrized test above is not empty."""
    assert REPLAYS
