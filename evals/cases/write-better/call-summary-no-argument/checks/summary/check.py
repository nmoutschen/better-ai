"""summary.md was rewritten, opens with the switch to the annual plan and its 15 December deadline, and keeps the facts."""
import re

text = open("summary.md").read()
assert text.strip() != open(__file__.replace("check.py", "planted.md")).read().strip(), "unchanged"


def date(day, short, month):
    return (rf"\b{day}(st|nd|rd|th)?\s*(of\s+)?{short}|{short}[a-z]*\.?\s*{day}(st|nd|rd|th)?\b"
            rf"|2026-{month:02d}-{day:02d}|\b{day}/{month}\b")


meta = r"\s*(#|(\*\*)?(To|From|Date|Subject|Re|For|Author|Prepared for)\b\s*:)"
body = " ".join(line for line in text.splitlines() if not re.match(meta, line, re.I))
opening = " ".join(body.split()[:60])
assert re.search(r"annual|yearly|once a year|12-month|one-year", opening, re.I), "the switch to the annual plan is not in the opening"
assert re.search(date(15, "Dec", 12), opening, re.I), "the 15 December deadline is not in the opening"

for pattern in (r"Corvina", r"\b25\b", r"\b48\b", r"14[,.\s]?400", r"\b40\b", r"12[,.\s]?000", r"2[,.\s]?400",
                r"\b(2|two)[\s-]*years?|24\s*months", date(15, "Dec", 12), r"below 25|under 25|fewer than 25|minimum|at least 25|reduce|lower",
                r"30[\s-]*day|cancel", r"order form|sign", date(20, "Nov", 11), r"Feb"):
    assert re.search(pattern, text, re.I), pattern
