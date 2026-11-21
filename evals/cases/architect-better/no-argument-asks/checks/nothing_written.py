"""Pass when no repository file was added, changed or deleted, other than in the agent's own .code/ folder."""

import os
import subprocess
import sys


def git_lines(*args: str) -> list[str]:
    """Return the lines a git command prints."""
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.splitlines()


start = os.environ["START_COMMIT"]
touched = set(git_lines("diff", "--name-only", start)) | set(git_lines("ls-files", "--others", "--exclude-standard"))
written = sorted(path for path in touched if not path.startswith(".code/"))
if written:
    sys.exit(f"files written without a change to work on: {written}")
print("nothing written")
