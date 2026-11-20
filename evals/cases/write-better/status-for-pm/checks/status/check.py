"""status.md keeps the open accounts, the decision deadline, the billing run, the correction date and the long-term fix's timing."""
import re

text = open("status.md").read()


def date(day, short, month):
    return (rf"\b{day}(st|nd|rd|th)?\s*(of\s+)?{short}|{short}[a-z]*\.?\s*{day}(st|nd|rd|th)?\b"
            rf"|2026-{month:02d}-{day:02d}|\b{day}/{month}\b")


for pattern in (r"\b12\b|twelve", date(24, "Nov", 11), date(1, "Dec", 12), date(27, "Nov", 11), r"January|\bJan\b"):
    assert re.search(pattern, text, re.I), pattern
