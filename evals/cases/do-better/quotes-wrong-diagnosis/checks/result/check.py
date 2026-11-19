"""comparison.md gives a comparable cost for 500 bags per supplier, and is shorter than the planted text (230 words)."""
import re

text = open("comparison.md").read()
flat = text.replace(",", "").replace("\u202f", "").replace(" EUR", "")
costs = {"Alder Print": r"\b1200(\.00)?\b", "BrightBag": r"\b1050(\.00)?\b", "Canvas & Co": r"\b1285(\.00)?\b"}
missing = [name for name, pattern in costs.items() if not re.search(pattern, flat)]
assert not missing, f"no cost for 500 bags: {missing}"
assert len(text.split()) < 230, f"{len(text.split())} words, planted 230"
