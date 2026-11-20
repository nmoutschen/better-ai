"""announcement.md has no hype words, stacked exclamation marks or emoji, and keeps every fact."""
import re

text = open("announcement.md").read()
assert "!!" not in text, "stacked exclamation marks"
emoji = re.findall(r"[\U0001F000-\U0001FAFF☀-➿⭐⬆⤴⤵️]", text)
assert not emoji, f"emoji: {emoji}"
hype = (r"huge news", r"insanely", r"game[- ]?changer", r"mind[- ]?blowing", r"crushing it", r"going to love",
        r"but wait", r"dying to")
found = [p for p in hype if re.search(p, text, re.I)]
assert not found, f"hype: {found}"
facts = (
    r"\b2\s*(nd\s*)?Dec(ember)?|Dec(ember)?\s*2\b", r"weekly", r"monthly", r"yearly|annually|every year|each year",
    r"\b31\b", r"\b12\b", r"hour", r"\bPro\b", r"includ|no extra|no additional|free of charge|at no cost|without (extra )?charge",
    r"Starter", r"15\s*(th\s*)?Jan(uary)?|Jan(uary)?\s*15", r"Export", r"Settings", r"\bData\b",
    r"\b1\s*(st\s*)?Dec(ember)?|Dec(ember)?\s*1\b", r"22[:.]00|10\s*pm", r"23[:.]30|11[:.]30\s*pm", r"CET",
    r"help@ledgerly\.example",
)
missing = [p for p in facts if not re.search(p, text, re.I)]
assert not missing, missing
