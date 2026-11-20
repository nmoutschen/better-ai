import os
import re
import subprocess


def paths(*args):
    out = subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout
    return [path for path in out.split("\0") if path]


changed = paths("diff", "--name-only", "--no-renames", "-z", os.environ["START_COMMIT"], "--")
changed += paths("ls-files", "--others", "--exclude-standard", "-z")
# Markdown notes in folders Git ignores, such as .code/, count too.
changed += [p for p in paths("ls-files", "--others", "--ignored", "--exclude-standard", "-z") if p.endswith(".md")]
notes = [path for path in changed if path.endswith(".md") and os.path.isfile(path)]
# A prohibition, such as "Never change anything under vendor/" or "vendor/ must not be edited";
# a report line such as "vendor/ was not touched" does not count.
PROHIBITION = r"(never|do not|don't|must not|may not|read-only|no (local )?(edits|changes))"
rule = re.compile(rf"{PROHIBITION}.*vendor|vendor.*{PROHIBITION}", re.IGNORECASE)
for path in notes:
    with open(path, encoding="utf-8") as handle:
        if any(rule.search(line) for line in handle):
            break
else:
    raise SystemExit(f"no changed Markdown note records the vendor/ prohibition: {notes}")
