"""report.md bolds between 1 and 6 short phrases (8 words at most) and keeps every fact."""
import re

text = open("report.md").read()
spans = re.findall(r"\*\*(?!\s)(.+?)\*\*", text) + re.findall(r"(?<![\w_])__(?!\s)(.+?)__(?![\w_])", text)
assert 1 <= len(spans) <= 6, f"{len(spans)} bold spans"
for span in spans:
    assert len(span.split()) <= 8, f"bold span too long: {span}"
for pattern in ('\\b22\\b', '2025', '1[ ,.]?340', '4[.,]8', '61\\s*%', '\\b176\\b', '\\b214\\b', '\\b38\\b', 'Sri Sumangala', 'St\\.? Anne', 'Pallewela Central', '450[ ,.]?000', '1[.,]1\\s*(tonnes|t\\b)', '\\bfive\\b|\\b5\\b', '\\btwo\\b|\\b2\\b', '612[ ,.]?000', '84[ ,.]?000', '548[ ,.]?000', '64[ ,.]?000', 'Anjali Perera', 'Joseph Fernando', '\\b25\\b', 'February', '23(rd)? January|January 23|2027-01-23', '10[:.]00|10\\s*a\\.?m', 'treasurer', 'safety lead', 'Mei Ling Wong', 'Ravi Jayasuriya', '\\b9 January|January 9|2027-01-09'):
    assert re.search(pattern, text, re.I), pattern
