"""Hidden check: the app now has the shift swap flow, however it was built.

Looks at the app's HTML and JavaScript files, outside the design notes in .design/ and .code/, for words a swap
flow needs: offering a shift, and, with the argument `approve`, approving a swap. The untouched app has neither.
"""

import pathlib
import re
import sys

SKIP = {".design", ".code", ".git", "node_modules"}
NEEDED = {"offer": re.compile(r"\boffer", re.IGNORECASE), "approve": re.compile(r"\bapprov", re.IGNORECASE)}


def app_text() -> str:
    """Return the text of every HTML and JavaScript file of the app."""
    parts = []
    for path in pathlib.Path(".").rglob("*"):
        if path.suffix in {".html", ".js", ".mjs"} and not SKIP & set(path.parts) and path.is_file():
            parts.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


wanted = ["offer"] + (["approve"] if "approve" in sys.argv[1:] else [])
text = app_text()
missing = [name for name in wanted if not NEEDED[name].search(text)]
if missing:
    print("The app has no sign of: " + ", ".join(missing))
    sys.exit(1)
print("The app has: " + ", ".join(wanted))
