"""faq-answer.md is under 60% of the original words, keeps the three facts, and drops the planted padding."""
import re

text = open("faq-answer.md").read()
planted = open(__file__.replace("check.py", "planted.md")).read()
words, planted_words = len(text.split()), len(planted.split())
assert words < 0.6 * planted_words, f"{words} words against {planted_words} in the original"
FACTS = (r"\bOrders\b", r"Edit address", r"Processing", r"Packed", r"Nordlys Post", r"tracking number",
         r"countr")
missing = [p for p in FACTS if not re.search(p, text, re.I)]
assert not missing, f"missing facts: {missing}"
PADDING = (r"great question", r"many customers ask", r"before we get into", r"works hard",
           r"every situation is different", r"circumstances can vary", r"hope this answer", r"always here for you")
kept = [p for p in PADDING if re.search(p, text, re.I)]
assert not kept, f"padding kept: {kept}"
