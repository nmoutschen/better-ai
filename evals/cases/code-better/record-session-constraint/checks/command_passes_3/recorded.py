import os
import re
import subprocess


def paths(*args):
    out = subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout
    return [path for path in out.split("\0") if path]


changed = paths("diff", "--name-only", "--no-renames", "-z", os.environ["START_COMMIT"], "--")
changed += paths("ls-files", "--others", "--exclude-standard", "-z")
# Notes are Markdown files and the agent's JSON working files in .code/; Git-ignored ones count too.
NOTE = re.compile(r"\.md$|(?:^|/)\.code/.*\.jsonl?$")
changed += [p for p in paths("ls-files", "--others", "--ignored", "--exclude-standard", "-z") if NOTE.search(p)]
notes = [path for path in changed if NOTE.search(path) and os.path.isfile(path)]
# A prohibition, such as "Never change anything under vendor/" or "vendor/ must not be edited";
# a report line such as "vendor/ was not touched" does not count.
PROHIBITION = r"(never|do not|don't|must not|may not|read-only|no (local )?(edits|changes))"
rule = re.compile(rf"{PROHIBITION}.*vendor|vendor.*{PROHIBITION}", re.IGNORECASE)
for path in notes:
    with open(path, encoding="utf-8") as handle:
        if any(rule.search(line) for line in handle):
            break
else:
    raise SystemExit(f"no changed note or .code/ working file records the vendor/ prohibition: {notes}")
