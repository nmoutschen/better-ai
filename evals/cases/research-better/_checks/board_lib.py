"""Read a research board in the format of skills/research-better/schemas/, for the hidden checks."""

import json
import sys
from pathlib import Path


def fail(message: str) -> None:
    print(message)
    sys.exit(1)


def entry(path: Path) -> dict:
    """One board record: a whole JSON file, which may span lines, or the first line of a JSONL file."""
    if not path.is_file():
        fail(f"{path} is not on the board")
    try:
        text = path.read_text(encoding="utf-8")
        return json.loads(text if path.suffix == ".json" else text.splitlines()[0])
    except (ValueError, IndexError):
        fail(f"{path} is not a JSON record")
        return {}


def the_board() -> Path:
    """The one board in .research/; fails unless there is exactly one."""
    found = sorted(p.parent for p in Path(".research").glob("*/brief.json"))
    if len(found) != 1:
        fail(f"expected one board with a brief.json in .research/, found {len(found)}")
    return found[0]


def entries(board: Path, kind: str) -> dict:
    """The board's records of one kind (questions, claims, sources, decisions), by id."""
    out = {}
    if kind == "decisions":
        path = board / "decisions.jsonl"
        for line in path.read_text(encoding="utf-8").splitlines() if path.is_file() else []:
            if line.strip():
                record = json.loads(line)
                out[record["id"]] = record  # a later line for the same id replaces the earlier one
        return out
    for path in sorted((board / kind).glob("*.json")):
        data = entry(path)
        out[data.get("id") or path.stem] = data
    return out


def none(value) -> bool:
    """True for a missing value, null, an empty string or an empty list."""
    return value is None or value == "" or value == []
