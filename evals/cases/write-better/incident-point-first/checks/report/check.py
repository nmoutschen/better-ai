"""incident-report.md opens with the rollback and its deadline, and keeps the decision's facts."""
import re

text = open("incident-report.md").read()
assert text.strip() != open(__file__.replace("check.py", "planted.md")).read().strip(), "unchanged"
meta = r"\s*(#|(\*\*)?(To|From|Date|Subject|Author|Status|Audience|Prepared for)\b)"
body = " ".join(line for line in text.splitlines() if not re.match(meta, line, re.I))
opening = " ".join(body.split()[:70])
assert re.search(r"roll(ed|ing)?[\s-]*back|revert", opening, re.I), "rollback not in the opening"
assert re.search(r"Friday|\b20(th)?\s*(of\s+)?Nov|Nov[a-z]*\.?\s*20\b|2026-11-20", opening, re.I), "deadline not in the opening"
for pattern in (r"4\.12", r"4\.13", r"\b312\b", r"8[,.\s]?400", r"\b40\b", r"2[.,]1\s*%", r"Apple Pay",
                r"\b4(th)?\s*(of\s+)?Dec|Dec[a-z]*\.?\s*4\b|2026-12-04", r"approv"):
    assert re.search(pattern, text, re.I), pattern
