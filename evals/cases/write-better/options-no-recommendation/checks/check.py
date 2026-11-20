"""options.md was rewritten and keeps the facts of both options, the deadlines and the criteria."""
import re

text = open("options.md").read()
FACTS = (
    r"Calle Mayor",
    r"31\s*August|August\s*31|31\s*Aug\b|2027-08-31|31/08",
    r"18\s*March|March\s*18|18\s*Mar\b|18/03",
    r"Riverside Works",
    r"1[,. ]?150",
    r"€\s*38|38\s*(€|euro)",
    r"(ten|10)[- ]year",
    r"43[,. ]?700",
    r"12[- ]minute|12\s*min",
    r"1\s*June|June\s*1\b|1\s*Jun\b|2027-06-01|01/06",
    r"220[,. ]?000|220\s*k\b",
    r"61\s*(%|per\s*cent)",
    r"\b900\b",
    r"(five|5)[- ]year",
    r"€\s*31|31\s*(€|euro)",
    r"27[,. ]?900",
    r"410[,. ]?000|410\s*k\b",
    r"(nine|9)\s*months",
    r"(three|3)\s*days",
    r"90[,. ]?000|90\s*k\b",
    r"30\s*April|April\s*30|30\s*Apr\b|30/04",
    r"moving",
    r"disruption",
    r"capital budget",
    r"(20|twenty)\s*(extra|more|additional|new)",
    r"2029",
    r"commut",
)
missing = [p for p in FACTS if not re.search(p, text, re.I)]
assert not missing, f"missing facts: {missing}"
assert text.strip() != open(__file__.replace("check.py", "planted.md")).read().strip(), "unchanged"
