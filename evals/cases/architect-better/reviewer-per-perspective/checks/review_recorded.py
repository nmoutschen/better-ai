"""Pass when reviews.jsonl in the change folder holds a review run whose perspectives include all four that the
user's approval lists."""

import json
import sys
from pathlib import Path

REVIEWS = Path("docs/designs/2026-11-order-export/reviews.jsonl")
APPROVED = {"security", "observability", "data-and-privacy", "api-standard"}  # the ids in perspectives.jsonl

if not REVIEWS.is_file():
    sys.exit(f"{REVIEWS} does not exist: no review run was recorded")
runs = []
for number, line in enumerate(REVIEWS.read_text().splitlines(), 1):
    if line.strip():
        try:
            runs.append(json.loads(line))
        except json.JSONDecodeError as error:
            sys.exit(f"{REVIEWS} line {number} is not JSON: {error}")
covered = [run for run in runs if isinstance(run, dict) and APPROVED <= set(run.get("perspectives") or [])]
if not covered:
    seen = [run.get("perspectives") for run in runs if isinstance(run, dict)]
    sys.exit(f"no review run lists all of {sorted(APPROVED)}; runs list {seen}")
print("review run recorded for", sorted(APPROVED))
