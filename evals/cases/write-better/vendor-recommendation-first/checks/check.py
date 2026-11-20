"""vendor-comparison.md names Kestrel in its first 60 words and keeps the decision facts of every bid."""
import re

text = open("vendor-comparison.md").read()
FACTS = (
    r"Ostrava",
    r"31\s*December|December\s*31|31\s*Dec\b|2026-12-31|31/12",
    r"2[.,]08",
    r"1[.,]1\s*(million|m\b)|1[,. ]100[,. ]000",
    r"(?<![\d.,])8\s*(%|per\s*cent)",
    r"cold[- ]chain|chilled",
    r"(three|3)[- ]year",
    r"1\s*January|January\s*1\b|1\s*Jan\b|2027-01-01",
    r"Baobab",
    r"2[.,]10",
    r"93\s*(%|per\s*cent)",
    r"1[.,]94",
    r"96[.,]5\s*(%|per\s*cent)",
    r"154[,. ]?000|154\s*k\b",
    r"Q2\s*2027|second quarter of 2027|(April|May|June)\s*2027",
    r"Tidewater",
    r"2[.,]05",
    r"94\s*(%|per\s*cent)",
    r"1[.,]2\s*(million|m\b)|1[,. ]200[,. ]000",
    r"extension",
)
missing = [p for p in FACTS if not re.search(p, text, re.I)]
assert not missing, f"missing facts: {missing}"
opening = " ".join(text.split()[:60])
assert re.search(r"Kestrel", opening), "Kestrel is not in the first 60 words"
