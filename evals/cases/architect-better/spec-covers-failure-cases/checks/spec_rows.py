"""Pass when spec.jsonl in the change folder holds at least one `spec` record, each with a non-empty `statement` and a
`source` that names a design section, a request sentence, a decision or a requirement. A `gap` or `unlinked` record is another kind and is not held to that; a row with no type is."""

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
    name = row.get("id", f"line {number}") if isinstance(row, dict) else f"line {number}"
    if not isinstance(row, dict):
        problems.append(f"{name}: not a JSON object")
        continue
    if row.get("type") in ("gap", "unlinked"):
        continue
    rows.append(row)
    if not isinstance(row.get("statement"), str) or not row["statement"].strip():
        problems.append(f"{name}: statement is empty or missing")
    source = row.get("source")
    kind = source.get("type") if isinstance(source, dict) else None
    field = {"design": "section", "request": "sentence"}.get(kind, kind)  # decision and requirement name their own kind
    named = source.get(field) if field else None
    if not isinstance(named, str) or not named.strip():
        problems.append(f"{name}: source is empty or names nothing")
if not rows:
    sys.exit(f"{SPEC} holds no spec requirement")
if problems:
    sys.exit("\n".join(problems))
print(len(rows), "spec requirements, each with a source")
