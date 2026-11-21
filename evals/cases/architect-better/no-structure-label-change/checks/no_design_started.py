"""Pass when the run started no design: no design.json anywhere, and no new folder under docs/designs/ or .architect/."""

import os
import subprocess
import sys


def git_lines(*args: str) -> list[str]:
    """Return the lines a git command prints."""
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.splitlines()


start = os.environ["START_COMMIT"]
planted = set(git_lines("ls-tree", "-r", "--name-only", start))
touched = set(git_lines("diff", "--name-only", start)) | set(git_lines("ls-files", "--others", "--exclude-standard"))
planted_folders = {path.split("/")[2] for path in planted if path.startswith("docs/designs/") and path.count("/") >= 3}
problems = []
for path in sorted(touched - planted):
    parts = path.split("/")
    if parts[-1] == "design.json":
        problems.append(f"design.json written: {path}")
    elif parts[0] == ".architect":
        problems.append(f"file in .architect/: {path}")
    elif path.startswith("docs/designs/") and len(parts) >= 4 and parts[2] not in planted_folders:
        problems.append(f"new change folder under docs/designs/: {path}")
if problems:
    sys.exit("a design was started: " + "; ".join(problems))
print("no design started")
