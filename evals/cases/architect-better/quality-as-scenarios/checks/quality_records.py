"""Pass when docs/designs/2026-11-order-export/requirements.jsonl exists, every line is JSON, and at least one record
has kind `quality`."""

import json
import sys
from pathlib import Path

path = Path("docs/designs/2026-11-order-export/requirements.jsonl")
if not path.exists():
    sys.exit(f"{path} does not exist")
kinds = []
for number, line in enumerate(path.read_text().splitlines(), 1):
    if line.strip():
        try:
            kinds.append(json.loads(line).get("kind"))
        except (json.JSONDecodeError, AttributeError) as error:
            sys.exit(f"{path} line {number} is not a JSON object: {error}")
if "quality" not in kinds:
    sys.exit(f"{path} has no record of kind quality; kinds: {kinds}")
print(kinds.count("quality"), "quality records")
