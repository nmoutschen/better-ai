"""Pass when the run built nothing past its questions: no Python file added, changed or deleted, and no decision
record added or changed in docs/adr/. Whether a design.json shows a designed After, rather than marking a new part
"after" only to show its absence in Before, is for the judge."""

import os
import subprocess
import sys


def git_lines(*args: str) -> list[str]:
    """Return the lines a git command prints."""
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.splitlines()


start = os.environ["START_COMMIT"]
touched = set(git_lines("diff", "--name-only", start)) | set(git_lines("ls-files", "--others", "--exclude-standard"))
touched = {path for path in touched if not path.startswith(".code/")}
problems = [f"Python file written: {path}" for path in sorted(touched) if path.endswith(".py")]
problems += [f"decision record written: {path}" for path in sorted(touched) if path.startswith("docs/adr/")]
if problems:
    sys.exit("built past the open question: " + "; ".join(problems))
print("no code, no decision record")
