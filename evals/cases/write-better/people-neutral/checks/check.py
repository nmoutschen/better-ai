"""job-ad.md has no gendered or ableist words from the original and keeps every fact."""
import re

text = open("job-ad.md").read()
banned = (r"\bchair(wo)?m[ae]n\b", r"\bhe\b", r"\bhis\b", r"\bhim\b", r"\bhimself\b", r"manpower", r"\bcrazy\b",
          r"\bguys\b")
found = [p for p in banned if re.search(p, text, re.I)]
assert not found, f"found: {found}"
facts = (
    r"\b60\b", r"Rotterdam", r"cargo bike", r"\b14\b", r"\bchair", r"board", r"once a month|monthly|every month",
    r"31\s*(st\s*)?Dec(ember)?|Dec(ember)?\s*31", r"2[,.]?400", r"\b(2|two)\s*years", r"Dutch", r"English",
    r"train", r"3[,.]?150", r"3[,.]?600", r"\b8\s*(%|per\s*cent)", r"\b32\s*hours", r"0?6[:.]30",
    r"Monday", r"Friday", r"jobs@veloverde\.example", r"15\s*(th\s*)?Jan(uary)?|Jan(uary)?\s*15",
    r"25\s*(th\s*)?Jan(uary)?|Jan(uary)?\s*25",
)
missing = [p for p in facts if not re.search(p, text, re.I)]
assert not missing, missing
