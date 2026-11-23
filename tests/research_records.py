"""Research board fixtures shared by the board tests: the example records, and a board made by `create`."""

import copy
import json
from pathlib import Path

import better

SKILL = "research-better"
EXAMPLES = json.loads((Path(__file__).parent / "fixtures" / "research_board_examples.json").read_text())


def example(file: str, label: str) -> dict:
    return copy.deepcopy(next(e["record"] for e in EXAMPLES[file] if e["label"] == label))


def board_head() -> str:
    """The brief as an agent gives it to `create`: its own fields, as JSON on stdin."""
    brief = example("brief.json", "brief")
    for key in ("type", "at", "by"):
        brief.pop(key)
    brief["changes"] = []
    return json.dumps(brief)


def made_board(root: Path) -> Path:
    """A board made by `create`, in a folder that is not a repository."""
    done = better.call(SKILL, "create", ".research/b", "--by", "coordinator", stdin=board_head(), cwd=root)
    assert done.returncode == 0, done.stderr
    return root / ".research" / "b"
