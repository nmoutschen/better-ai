"""warranty-summary.md is a list that keeps each coverage claim with its exception in the same item."""
import re
from pathlib import Path

text = Path("warranty-summary.md").read_text()
LIST_ITEM = re.compile(r"^\s*([-*+]|\d+[.)])\s+")


def blocks(markdown: str) -> list[str]:
    """Split into list items (with their indented continuation lines), table rows and paragraphs."""
    found: list[str] = []
    current: list[str] = []
    for line in markdown.splitlines():
        starts_new = LIST_ITEM.match(line) and not line.startswith((" ", "\t")) or line.lstrip().startswith("|")
        if not line.strip() or starts_new:
            if current:
                found.append(" ".join(current))
            current = [line] if line.strip() else []
            if line.lstrip().startswith("|"):
                found.append(line)
                current = []
        else:
            current.append(line)
    if current:
        found.append(" ".join(current))
    return found


assert len([line for line in text.splitlines() if LIST_ITEM.match(line)]) >= 3, "not a list of at least three items"
FACTS = (r"\b5\b|five", r"frame|motor", r"commercial", r"\b2\b|two", r"battery", r"70\s*(%|per\s*cent)", r"500",
         r"charger", r"original|genuine|Corvo", r"free|no cost|no charge|without charge", r"island", r"35")
missing = [p for p in FACTS if not re.search(p, text, re.I)]
assert not missing, f"missing facts: {missing}"
PAIRS = (
    (r"commercial", r"\b5\b|five", "the commercial-use exception is not in the item about 5-year frame and motor cover"),
    (r"charger", r"500|70\s*%|\b2\s*years|two years", "the charger exception is not in the item about battery cover"),
    (r"island", r"free|no cost|no charge|without charge|mainland", "the islands exception is not in the item about free collection"),
)
items = blocks(text)
for exception, claim, message in PAIRS:
    holding = [item for item in items if re.search(exception, item, re.I)]
    assert holding and all(re.search(claim, item, re.I) for item in holding), message
