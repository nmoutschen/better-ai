"""The invoice total is the sum of its lines, 340 EUR, and the lines are unchanged."""
import re

text = open("invoice.md").read()
assert re.search(r"Total:?\**\s*\**\s*340(\.00)?\s*EUR", text) or re.search(r"Total[^\n]*340", text), "total 340"
assert "430" not in text, "old total"
for line in ("Orchard survey | 6 | 40 | 240", "Pruning plan | 2.5 | 40 | 100"):
    assert line in text, line
