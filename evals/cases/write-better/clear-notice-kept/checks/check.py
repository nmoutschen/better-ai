"""notice.md keeps every fact, about the same length (75% to 130% of the original words) and at most one heading."""
import re

text = open("notice.md").read()
planted = open(__file__.replace("check.py", "planted.md")).read()
FACTS = (
    r"8\s*December|December\s*8|8\s*Dec\b|Dec\s*8|8/12|2026-12-08",
    r"Tuesday|\bTue\b",
    r"0?9[:.]00|9\s*(a\.?m)",
    r"13[:.]00|1\s*(p\.?m)",
    r"valve",
    r"basement",
    r"bottle|kettle",
    r"flush",
    r"brown|discolou?r",
    r"cold tap",
    r"12[:.]30|12\.30|half past twelve",
    r"notice\s*board",
    r"0612\s*448\s*903",
    r"jortega@lindenhof-residences\.example",
    r"Joaqu[ií]n",
)
missing = [p for p in FACTS if not re.search(p, text, re.I)]
assert not missing, f"missing facts: {missing}"
words, planted_words = len(text.split()), len(planted.split())
assert 0.75 * planted_words <= words <= 1.3 * planted_words, f"{words} words against {planted_words} in the original"
headings = len(re.findall(r"^\s{0,3}#", text, re.M))
assert headings <= 1, f"{headings} headings"
