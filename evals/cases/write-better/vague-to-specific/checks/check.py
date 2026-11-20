"""delivery-update.md uses the exact values from facts.md instead of the vague terms."""
import re

text = open("delivery-update.md").read()
vague = (r"\bsoon\b(?<!as soon)(?!\s+as\b)", r"\ba few weeks\b", r"\ba little before\b")
found = [p for p in vague if re.search(p, text, re.I)]
assert not found, f"vague: {found}"
facts = (
    r"12\s*(th\s*)?(of\s*)?May|May\s*12", r"\b(3|three)[ -]weeks?|\b2\s*(nd\s*)?(of\s*)?June|June\s*2\b",
    r"84\s*(%|per\s*cent)|1[,.]?512", r"\b(7|seven)\s*(of|out of|in)\s*(10|ten)\b|\b7/10\b|\b70\s*(%|per\s*cent)",
    r"\b7\s*(th\s*)?(of\s*)?May|May\s*7\b", r"Ashford Park", r"Mill Lane", r"0161\s*496\s*0732",
    r"account manager", r"address", r"order",
)
missing = [p for p in facts if not re.search(p, text, re.I)]
assert not missing, missing
