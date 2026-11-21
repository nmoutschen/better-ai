"""Read a research board in the format of skills/research-better/templates/board.md, for the hidden checks."""

import sys
from pathlib import Path


def fail(message: str) -> None:
    print(message)
    sys.exit(1)


def entry(path: Path) -> dict:
    """One board file: the first value of each `key: value` line."""
    data = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() and " " not in key.strip():
            data.setdefault(key.strip(), value.strip())
    return data


def the_board() -> Path:
    """The one board in .research/; fails unless there is exactly one."""
    found = sorted(p.parent for p in Path(".research").glob("*/brief.md"))
    if len(found) != 1:
        fail(f"expected one board with a brief.md in .research/, found {len(found)}")
    return found[0]


def entries(board: Path, kind: str) -> dict:
    """The board's files of one kind (questions, claims, sources, decisions), by id or file name."""
    out = {}
    for path in sorted((board / kind).glob("*.md")):
        data = entry(path)
        out[data.get("id") or path.stem] = data
    return out


def unquote(value: str) -> str:
    value = value.strip()
    return value[1:-1] if len(value) >= 2 and value[0] == value[-1] == '"' else value


def none(value) -> bool:
    return value is None or value.strip() in ("", "none")
