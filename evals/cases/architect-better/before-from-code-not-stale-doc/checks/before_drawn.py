"""Pass when the run drew Before: a new design.json in a change folder (docs/designs/<change>/ or the skill's fallback
.architect/<change>/) that parses as JSON and has a non-empty containers.nodes list."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Files added since the planted commit: untracked ones, and ones the agent committed.
new_files = subprocess.run(
    ["git", "ls-files", "--others", "--exclude-standard"], capture_output=True, text=True, check=True
).stdout.split() + subprocess.run(
    ["git", "diff", "--name-only", "--diff-filter=A", os.environ["START_COMMIT"], "HEAD"],
    capture_output=True,
    text=True,
    check=True,
).stdout.split()
drawn = [path for path in new_files if re.fullmatch(r"(docs/designs|\.architect)/[^/]+/design\.json", path)]
if not drawn:
    sys.exit(f"no new design.json in a change folder; new files: {new_files}")
for path in drawn:
    try:
        design = json.loads(Path(path).read_text())
    except json.JSONDecodeError as error:
        sys.exit(f"{path} is not valid JSON: {error}")
    nodes = (design.get("containers") or {}).get("nodes") if isinstance(design, dict) else None
    if not isinstance(nodes, list) or not nodes:
        sys.exit(f"{path} has no containers.nodes list with boxes")
print("Before drawn in", drawn)
