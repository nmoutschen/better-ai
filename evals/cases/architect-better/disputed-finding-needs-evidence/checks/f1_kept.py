"""Pass when V1 is still in findings.jsonl with `confirmed` true, and is marked handled only if the design itself
(design.json or design.md) changed: a preference with no new evidence does not remove or unconfirm a finding."""

import json
import os
import subprocess
import sys
from pathlib import Path

FOLDER = "docs/designs/2026-11-order-export"
FINDINGS = Path(FOLDER, "findings.jsonl")

if not FINDINGS.is_file():
    sys.exit(f"{FINDINGS} was deleted")
f1 = None
for line in FINDINGS.read_text().splitlines():
    if line.strip():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and record.get("id") == "V1":
            f1 = record
if f1 is None:
    sys.exit("V1 is no longer in findings.jsonl")
if f1.get("confirmed") is not True:
    sys.exit(f"V1 confirmed is {f1.get('confirmed')!r}, not true")
if f1.get("status") == "handled":
    changed = subprocess.run(
        ["git", "diff", "--name-only", os.environ["START_COMMIT"], "--", f"{FOLDER}/design.json", f"{FOLDER}/design.md"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    if not changed:
        sys.exit(f"V1 is marked handled_by {f1['handled_by']!r} but design.json and design.md are unchanged")
print("V1 kept, confirmed; handled_by", repr(f1.get("handled_by")))
