"""travel-policy.md has at least 3 Markdown headings, none of them a bare number or "Section N", and keeps every amount and deadline."""
import re

text = open("travel-policy.md").read()
headings = re.findall(r"^#{1,6}\s+(\S.*)$", text, re.M)
assert len(headings) >= 3, f"{len(headings)} headings"
for heading in headings:
    assert not re.fullmatch(r"\s*((section|part|chapter)\s*)?[\dIVX]+[.)]?\s*", heading, re.I), heading
for pattern in ('1(st)? January 2027|January 1(st)?,? 2027|2027-01-01', '2024', '25[ ,]?000', '(five|5) working days', '\\b14[- ]days?', '\\b(6|six)[- ]hours?', '1[ ,]?800', '2[ ,]?500', 'Johannesburg', 'Cape Town', '4[.,]84', '(?<![\\d,.])650(?!\\d)', '(?<![\\d,.])85(?!\\d)', 'half|50\\s*%', '\\b30[- ]days?', '(?<![\\d,.])200(?!\\d)', '\\b60[- ]days?', '(five|5)[- ]nights?', 'twice|two times|2 times', 'travel@umhlanga-eng\\.example', 'expenses@umhlanga-eng\\.example', 'chief financial officer|CFO'):
    assert re.search(pattern, text, re.I), pattern
