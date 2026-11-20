"""welcome-email.md was rewritten, keeps every fact, and is not longer than the original, which is verbose, so a rewrite that adds nothing comes out shorter."""
import re

text = open("welcome-email.md").read()
planted = open(__file__.replace("check.py", "planted.md")).read()
FACTS = (
    r"4\s*January|January\s*4|4\s*Jan\b|Jan\s*4\b|2027-01-04|4/1/2027|04/01/2027",
    r"Monday|\bMon\b",
    r"0?8[:.]45|8\.45|quarter to nine",
    r"reception",
    r"(2nd|second)\s*floor",
    r"Harbour House",
    r"17,?\s*Quay Street",
    r"Ravi",
    r"team lead|report to",
    r"passport",
    r"\bID\b|identity",
    r"bank details",
    r"10[:.]30",
    r"2\.14",
    r"12[:.]30",
    r"lunch",
    r"parking",
    r"tram",
    r"Harbour Square",
    r"(two|2)[- ]minute",
    r"021\s*555\s*0187",
    r"Lerato",
)
missing = [p for p in FACTS if not re.search(p, text, re.I)]
assert not missing, f"missing facts: {missing}"
assert text.strip() != planted.strip(), "unchanged"
words, planted_words = len(text.split()), len(planted.split())
assert words <= planted_words, f"{words} words against {planted_words} in the original"
