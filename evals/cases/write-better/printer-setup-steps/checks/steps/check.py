"""printer-setup.md is a numbered list of at least 5 steps that keeps the exact network, paths, file, setting and extension."""
import re

text = open("printer-setup.md").read()
steps = re.findall(r"^\s*\d+[.)]\s+\S", text, re.M)
assert len(steps) >= 5, f"{len(steps)} numbered steps"
for pattern in (r"HARBOUR-STAFF", r"HARBOUR-GUEST", r"PRNSRV-02\\{1,4}Floor3-Colour",
                r"fs01\\{1,4}drivers\\{1,4}ricoh\\{1,4}IMC3000\\{1,4}x64", r"IMC3000\.inf", r"Have Disk",
                r"isn.t listed", r"shared printer by name", r"Black and White", r"Printing preferences", r"test page",
                r"\b4410\b"):
    assert re.search(pattern, text, re.I), pattern
