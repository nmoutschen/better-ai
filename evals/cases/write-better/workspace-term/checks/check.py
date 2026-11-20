"""help-article.md uses one term for the workspace concept and keeps every step, label and limit."""
import re

text = open("help-article.md").read()
facts = (
    r"New workspace", r"\b40\b", r"Private", r"Shared", r"Create", r"Invite", r"\b25\b", r"Team plan", r"Free plan",
    r"\b3\b|\bthree\b", r"\b14\b|fourteen", r"Workspace settings", r"trash|bin", r"owner", r"top[- ]left",
    r"email",
)
missing = [p for p in facts if not re.search(p, text, re.I)]
assert not missing, missing

# Count each term for the concept once; strip the longer terms first so "space" alone is counted only on its own.
rest = re.sub(r"\b(disk|storage|free|white|blank)\s+space", " ", text, flags=re.I)
terms = {}
for name, pattern in (("project space", r"\bproject[ -]spaces?\b"), ("team area", r"\bteam[ -]areas?\b"),
                      ("workspace", r"\bworkspaces?\b"), ("space", r"\bspaces?\b")):
    terms[name] = len(re.findall(pattern, rest, re.I))
    rest = re.sub(pattern, " ", rest, flags=re.I)
used = sorted(name for name, count in terms.items() if count)
assert len(used) <= 1, f"several terms for one concept: {used}"
