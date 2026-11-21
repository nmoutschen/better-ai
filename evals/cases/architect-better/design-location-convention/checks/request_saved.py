"""Pass when the request is saved word for word as request.md in a new folder under docs/designs/, the repo's design
location, and nothing was written to the skill's fallback folder .architect/."""

import os
import re
import subprocess
import sys
from pathlib import Path

REQUEST = (
    'Design a way for logged-in customers to download their own order history as a CSV file from their account page, for their own bookkeeping: one row per order with order id, date, book titles, total and status. Only their own orders, behind the session cookie as usual; nothing new is stored, the file is built when they click; if it fails, show the standard error message. No new paid services.'
    ' Decide anything else yourself and list it as an assumption.'
)


def normalise(text: str) -> str:
    """Collapse runs of whitespace, so a line wrap does not count as a change of words."""
    return re.sub(r"\s+", " ", text).strip()


# Files added since the planted commit: untracked ones, and ones the agent committed.
new_files = subprocess.run(
    ["git", "ls-files", "--others", "--exclude-standard"], capture_output=True, text=True, check=True
).stdout.split() + subprocess.run(
    ["git", "diff", "--name-only", "--diff-filter=A", os.environ["START_COMMIT"], "HEAD"],
    capture_output=True,
    text=True,
    check=True,
).stdout.split()
saved = [
    path
    for path in new_files
    if re.fullmatch(r"docs/designs/[^/]+/request\.md", path) and normalise(REQUEST) in normalise(Path(path).read_text())
]
if not saved:
    sys.exit(f"no new docs/designs/<change>/request.md holds the request word for word; new files: {new_files}")
if Path(".architect").exists():
    sys.exit(".architect/ exists although the repo has a design location")
print("request saved in", saved)
