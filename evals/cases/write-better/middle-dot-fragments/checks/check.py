"""digest.md has no fragments joined by separators, no sentence over 40 words, and keeps every fact."""
import re

MAX_WORDS = 40  # a generous bound: the planted long sentences run to 60-70 words

text = open("digest.md").read()
for line in text.splitlines():
    assert not re.search(r"\S[ \t]*[·•∙⋅|][ \t]*\S", line) or line.lstrip().startswith("|"), f"separator: {line}"
    for sentence in re.split(r"(?<=[.!?;])\s+", line):
        words = len(re.findall(r"[\w£€$@'’-]+", sentence))
        assert words <= MAX_WORDS, f"{words} words: {sentence}"
facts = (
    r"\b42\b", r"\b3\b|\bthree\b", r"\b2\b|\btwo\b", r"Amina Diallo", r"Jonas Berg", r"Priya Raman",
    r"twenty|\b20\+?\s*years", r"lead", r"7\s*(th\s*)?Dec(ember)?|Dec(ember)?\s*7\b", r"0?8[:.]00|8\s*am",
    r"Harbour Gate", r"65\s*km", r"13\s*(th\s*)?Dec(ember)?|Dec(ember)?\s*13", r"19[:.]00|7\s*pm",
    r"Old Ropeworks", r"£\s?8(?!\d)", r"£\s?25", r"2027", r"track", r"£\s?30", r"£\s?36",
    r"1\s*(st\s*)?Jan(uary)?|Jan(uary)?\s*1\b", r"light", r"helmet", r"\b10\s*km", r"(second|next|later) group",
    r"secretary@northsidecc\.example",
)
missing = [p for p in facts if not re.search(p, text, re.I)]
assert not missing, missing
