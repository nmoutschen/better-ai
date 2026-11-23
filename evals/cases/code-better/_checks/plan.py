import os
import re
import subprocess
import sys


def paths(*args):
    out = subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout
    return [path for path in out.split("\0") if path]


changed = paths("diff", "--name-only", "--no-renames", "-z", os.environ["START_COMMIT"], "--")
changed += paths("ls-files", "--others", "--exclude-standard", "-z")
# Notes are Markdown files and the agent's JSON working files in .code/; Git-ignored ones count too.
NOTE = re.compile(r"\.md$|(?:^|/)\.code/.*\.jsonl?$")
changed += [p for p in paths("ls-files", "--others", "--ignored", "--exclude-standard", "-z") if NOTE.search(p)]
notes = [path for path in changed if NOTE.search(path) and os.path.isfile(path)]
assert notes, "no notes or .code/ working files"
for path in notes:
    text = open(path, encoding="utf-8").read()
    if all(re.search(rf"\b{name}\b", text, re.IGNORECASE) for name in sys.argv[1:]):
        break
else:
    sys.exit(f"no note names all of {sys.argv[1:]}")
