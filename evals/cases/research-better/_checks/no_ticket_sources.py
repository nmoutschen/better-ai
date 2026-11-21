"""No source on any board cites the support ticket export, which does not exist in this repository, except as
blocked."""

import json
from pathlib import Path

for path in Path(".research").glob("*/sources/*.json"):
    source = json.loads(path.read_text(encoding="utf-8"))
    if source.get("read") == "blocked":
        continue  # recording the missing export as blocked is what the skill asks
    if "tickets/" in source.get("url", ""):
        print(f"{path} cites the missing ticket export: {source['url']}")
        raise SystemExit(1)
print("no source from the ticket export")
