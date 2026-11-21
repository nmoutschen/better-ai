"""Pass when spec.jsonl in the change folder holds at least one record, each with a non-empty `requirement` and a
non-empty `source`."""

import json
import sys
from pathlib import Path

SPEC = Path("docs/designs/2026-11-order-export/spec.jsonl")

if not SPEC.is_file():
    sys.exit(f"{SPEC} does not exist")
rows, problems = [], []
for number, line in enumerate(SPEC.read_text().splitlines(), 1):
    if not line.strip():
        continue
    try:
        row = json.loads(line)
    except json.JSONDecodeError as error:
        sys.exit(f"{SPEC} line {number} is not JSON: {error}")
    rows.append(row)
    name = row.get("id", f"line {number}") if isinstance(row, dict) else f"line {number}"
    if not isinstance(row, dict):
        problems.append(f"{name}: not a JSON object")
        continue
    for field in ("requirement", "source"):
        value = row.get(field)
        if not value or (isinstance(value, str) and not value.strip()):
            problems.append(f"{name}: {field} is empty or missing")
if not rows:
    sys.exit(f"{SPEC} holds no requirement")
if problems:
    sys.exit("\n".join(problems))
print(len(rows), "spec requirements, each with a source")
