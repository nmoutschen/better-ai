"""Pass when the run drew Before and stopped there: a new design.json in a change folder (docs/designs/<change>/ or
.architect/<change>/) with a non-empty containers.nodes list, and none of the
files later steps write (design.md, requirements.jsonl, perspectives.jsonl, decisions.jsonl, spec.jsonl) in that
folder. Parts marked "after" are allowed: the skill shows a new box or flow's absence in Before that way; whether the
run drew a designed After is for the judge."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

LATER_FILES = ("design.md", "requirements.jsonl", "perspectives.jsonl", "decisions.jsonl", "spec.jsonl")


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
    if not isinstance(design, dict) or not (design.get("containers") or {}).get("nodes"):
        sys.exit(f"{path} has no containers.nodes list with boxes")
    folder = Path(path).parent
    written = [name for name in LATER_FILES if (folder / name).exists()]
    if written:
        sys.exit(f"{folder} holds files of later steps before Before was confirmed: {written}")
print("Before only, in", drawn)
