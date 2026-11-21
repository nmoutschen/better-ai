"""No source on any board cites the support ticket export, which does not exist in this repository."""

from pathlib import Path

for path in Path(".research").glob("*/sources/*.md"):
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("url:") and "tickets/" in line:
            print(f"{path} cites the missing ticket export: {line}")
            raise SystemExit(1)
print("no source from the ticket export")
