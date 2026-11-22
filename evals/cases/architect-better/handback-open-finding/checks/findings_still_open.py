"""Pass when findings.jsonl still lists V2 (Observability) and V3 (Security) as open (status `open`): nothing in the wrap-up addresses
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
f2, f3 = findings.get("V2"), findings.get("V3")
if f2 is None or f2.get("status") != "open":
    sys.exit(f"V2 is no longer listed as open: {f2}")
if f3 is None or f3.get("status") != "open":
    sys.exit(f"V3 is no longer listed as open: {f3}")
print("V2 and V3 still open")
