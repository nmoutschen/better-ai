"""outage-email.md follows docs/WRITING.md (ISO dates, no lists, no "!", sign-off, no internal names) and keeps the key facts."""
import re

text = open("outage-email.md").read()
months = (r"(January|February|March|April|May|June|July|August|September|October|November|December"
          r"|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\b\.?")
assert not re.search(r"\b\d{1,2}(st|nd|rd|th)?\s+(of\s+)?" + months, text), "day-month date"
assert not re.search(r"\b" + months + r"\s+\d{1,2}(st|nd|rd|th)?\b", text), "month-day date"
assert not re.search(r"\b\d{1,2}/\d{1,2}\b(?<!24/7)", text), "slash date"
assert not re.search(r"^\s*([-*+•]|\d+[.)])\s", text, re.M), "list line"
assert "!" not in text, "exclamation mark"
assert re.search(r"The Support Team", "\n".join([line for line in text.splitlines() if line.strip()][-3:])), "sign-off"
for internal in (r"INC-2291", r"\bHana\b", r"auth-mobile"):
    assert not re.search(internal, text), internal
for pattern in (r"2026-11-19", r"09[:.]12", r"11[:.]47", r"UTC", r"mobile", r"certificate", r"\b(one|1|a)\b[ -](full )?day",
                r"credit", r"\bdata\b"):
    assert re.search(pattern, text, re.I), pattern
