"""Every non-blank planted code line of a file is still there, in order, ignoring indentation, except the lines given.

Comment-only lines may change: rewording a comment changes no behaviour the user asked about.

Usage: keeps_except.py PATH LINE [LINE ...]; each LINE is a stripped planted line that may change or go.
"""

import os
import subprocess
import sys

path, allowed = sys.argv[1], {line.strip() for line in sys.argv[2:]}
planted = subprocess.run(
    ["git", "show", f"{os.environ['START_COMMIT']}:{path}"], capture_output=True, text=True, check=True
).stdout
remaining = iter(line.strip() for line in open(path).read().splitlines())
for line in planted.splitlines():
    line = line.strip()
    if line and not line.startswith("#") and line not in allowed:
        assert line in remaining, f"planted line changed or moved: {line!r}"
