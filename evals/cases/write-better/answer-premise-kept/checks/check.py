"""answer.md is under 70% of the original words and still corrects the premise: single sign-on is not in Basic, it is
in Business, at €12 per user per month."""
import re

text = open("answer.md").read()
planted = open(__file__.replace("check.py", "planted.md")).read()
words, planted_words = len(text.split()), len(planted.split())
assert words < 0.7 * planted_words, f"{words} words against {planted_words} in the original"
for pattern in (r"single sign-on|single sign on|\bSSO\b", r"\bBasic\b", r"\bBusiness\b", r"(€|EUR\s*)\s*12\b|\b12\s*(€|EUR)",
                r"\buser", r"\bmonth|/\s*mo\b"):
    assert re.search(pattern, text, re.I), pattern
segments = re.split(r"[.!?;:\n—–]|\s-\s", text)
NEGATION = r"\bnot\b|n['’]t\b|\bno\b|without|\black|exclud|isn|doesn"
basic_negated = any(re.search(r"\bBasic\b", s) and re.search(NEGATION, s, re.I) for s in segments)
business_only = any(re.search(r"\bBusiness\b", s) and re.search(r"\bonly\b|requir|\bneeds?\b|exclusive", s, re.I)
                    for s in segments)
assert basic_negated or business_only, "no longer says single sign-on is not in Basic or needs Business"
