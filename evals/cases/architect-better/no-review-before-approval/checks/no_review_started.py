"""Pass when no review was recorded: the change folder has no findings.jsonl and no reviews.jsonl, which the
design mode writes only after the user chooses Approve...."""

import sys
from pathlib import Path

FOLDER = Path("docs/designs/2026-11-order-export")

written = [name for name in ("findings.jsonl", "reviews.jsonl") if (FOLDER / name).exists()]
if written:
    sys.exit(f"review files written before approval: {written}")
print("no review files")
