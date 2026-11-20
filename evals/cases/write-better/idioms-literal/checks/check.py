"""update.md gives the date the headcount numbers are due and keeps every fact."""
import re

text = open("update.md").read()
deadline = r"\b9\s*(th\s*)?(of\s*)?Dec(ember)?|Dec(ember)?\s*9(th)?\b|\b0?9[./-]12\b|2026-12-09"
assert re.search(deadline, text, re.I), "no due date for the headcount numbers"
facts = (
    r"headcount", r"Finance", r"2027", r"contractor", r"permanent", r"Rua do Ouro",
    r"18\s*(th\s*)?(of\s*)?Jan(uary)?|Jan(uary)?\s*18", r"40[ ,.]?000|40\s*k", r"desk", r"\b9\s*h(ou)?rs?\b|\b9 hours",
    r"\b4\s*h(ou)?rs?\b|\bfour hours", r"October", r"\b230\b", r"30 days|thirty days", r"Sofia", r"review",
)
missing = [p for p in facts if not re.search(p, text, re.I)]
assert not missing, missing
