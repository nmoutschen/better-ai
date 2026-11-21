"""Pass when decisions.jsonl in the change folder holds at least one decision, each with a non-empty list of rejected
alternatives, and a new decision record docs/adr/000[3-9]-*.md exists, numbered after the last planted one (0002)."""

import json
import os
import subprocess
import sys
from pathlib import Path

DECISIONS = Path("docs/designs/2026-11-order-export/decisions.jsonl")


def planted(path: Path) -> bool:
    """Whether the path was in the planted commit."""
    found = subprocess.run(["git", "cat-file", "-e", f"{os.environ['START_COMMIT']}:{path}"], capture_output=True)
    return found.returncode == 0


records = sorted(path for path in Path("docs/adr").glob("000[3-9]-*.md") if not planted(path))
if not records:
    sys.exit(f"no new docs/adr/000[3-9]-*.md; docs/adr holds {sorted(str(p) for p in Path('docs/adr').iterdir())}")
if not DECISIONS.is_file():
    sys.exit(f"{DECISIONS} does not exist")
decisions = []
for number, line in enumerate(DECISIONS.read_text().splitlines(), 1):
    if line.strip():
        try:
            decisions.append(json.loads(line))
        except json.JSONDecodeError as error:
            sys.exit(f"{DECISIONS} line {number} is not JSON: {error}")
if not decisions:
    sys.exit(f"{DECISIONS} holds no decision")
bare = [d.get("id", "?") if isinstance(d, dict) else "?" for d in decisions
        if not (isinstance(d, dict) and isinstance(d.get("rejected"), list) and d["rejected"])]
if bare:
    sys.exit(f"decisions with no rejected alternatives: {bare}")
print("decision records:", [str(path) for path in records], "decisions:", len(decisions))
