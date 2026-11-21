"""Pass when spec.jsonl exists in the change folder and holds at least one requirement."""

import json
import sys
from pathlib import Path

SPEC = Path("docs/designs/2026-11-order-export/spec.jsonl")

if not SPEC.is_file():
    sys.exit(f"{SPEC} does not exist")
rows = [line for line in SPEC.read_text().splitlines() if line.strip()]
for number, line in enumerate(rows, 1):
    try:
        json.loads(line)
    except json.JSONDecodeError as error:
        sys.exit(f"{SPEC} record {number} is not JSON: {error}")
if not rows:
    sys.exit(f"{SPEC} is empty")
print(len(rows), "spec requirements")
