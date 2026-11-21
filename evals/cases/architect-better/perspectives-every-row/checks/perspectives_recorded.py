"""Pass when perspectives.jsonl exists in the change folder, every record has a boolean `applies` and a non-empty
`why`, and one record names the repo standard docs/standards/api.md in `from` or `name`
(`from` is free text in the skill's format, such as "repo: docs/standards/api.md")."""

import json
import sys
from pathlib import Path

PATH = Path("docs/designs/2026-11-order-export/perspectives.jsonl")

if not PATH.is_file():
    sys.exit(f"{PATH} is missing")
records = []
for number, line in enumerate(PATH.read_text().splitlines(), start=1):
    if not line.strip():
        continue
    try:
        records.append(json.loads(line))
    except ValueError as error:
        sys.exit(f"line {number} is not JSON: {error}")
problems = []
for record in records:
    if not isinstance(record.get("applies"), bool):
        problems.append(f"{record.get('name')!r}: applies is not a boolean")
    if not isinstance(record.get("why"), str) or not record["why"].strip():
        problems.append(f"{record.get('name')!r}: why is empty")
if not any("standards/api.md" in f"{record.get('from')} {record.get('name')}" for record in records):
    problems.append("no record names the repo standard docs/standards/api.md in its from or name")
if not records:
    problems.append("no records")
if problems:
    sys.exit("\n".join(problems))
print(f"{len(records)} perspectives recorded")
