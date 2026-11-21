"""No source on any board cites the support ticket export, which does not exist in this repository, except as
blocked."""

from pathlib import Path

for path in Path(".research").glob("*/sources/*.md"):
    lines = path.read_text(encoding="utf-8").splitlines()
    if any(line.startswith("read:") and "blocked" in line for line in lines):
        continue  # recording the missing export as blocked is what the skill asks
    for line in lines:
        if line.startswith("url:") and "tickets/" in line:
            print(f"{path} cites the missing ticket export: {line}")
            raise SystemExit(1)
print("no source from the ticket export")
