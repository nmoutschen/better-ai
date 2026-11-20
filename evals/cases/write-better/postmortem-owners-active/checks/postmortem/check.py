"""postmortem.md names each owner in the same line, list item or paragraph as their action, and keeps the facts."""
import re

text = open("postmortem.md").read()
assert text.strip() != open(__file__.replace("check.py", "planted.md")).read().strip(), "unchanged"

units, current = [], []
for line in text.splitlines():
    starts_unit = not line.strip() or re.match(r"\s*([-*+]|\d+[.)]|\||#)", line)
    if starts_unit and current:
        units.append(" ".join(current))
        current = []
    if line.strip():
        current.append(line.strip())
if current:
    units.append(" ".join(current))

owners = {
    "Ayşe Demir / runbook": (r"Ay[sş]e|Demir", r"runbook"),
    "Tomás Herrera / alert threshold": (r"Tom[aá]s|Herrera", r"alert|threshold"),
    "Mei Lin / peer review": (r"\bMei\b|\bLin\b", r"review"),
}
for name, (person, action) in owners.items():
    assert any(re.search(person, unit, re.I) and re.search(action, unit, re.I) for unit in units), name


def date(day, short):
    return rf"\b{day}(st|nd|rd|th)?\s*(of\s+)?{short}|{short}[a-z]*\.?\s*{day}(st|nd|rd|th)?\b"


for pattern in (r"0?8[:.]52", r"10[:.]20", r"11[:.]07", r"2\s*h(ours?)?\s*(and\s+)?15|2:15|135\s*min", r"\b50\s*%",
                r"\b10\s*%", r"\b180\b", r"1194", r"wiki", date(24, "Nov"), date(17, "Nov"), date(1, "Dec")):
    assert re.search(pattern, text, re.I), pattern
