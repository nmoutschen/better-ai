"""Pass when findings.jsonl still lists F2 (Observability) and F3 (Security) as open: nothing in the wrap-up addresses
either, so marking one handled would record a fix that did not happen."""

import json
import sys
from pathlib import Path

PATH = Path("docs/designs/2026-11-order-export/findings.jsonl")

if not PATH.exists():
    sys.exit(f"{PATH} is missing")
findings = {}
for line in PATH.read_text().splitlines():
    if line.strip():
        record = json.loads(line)
        findings[record.get("id")] = record
f2, f3 = findings.get("F2"), findings.get("F3")
if f2 is None or f2.get("handled_by") is not None:
    sys.exit(f"F2 is no longer listed as open: {f2}")
if f3 is None or f3.get("handled_by") is not None:
    sys.exit(f"F3 is no longer listed as open: {f3}")
print("F2 and F3 still open")
