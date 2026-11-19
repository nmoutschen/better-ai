"""release-notes.md follows STYLE.md (ISO dates, v-prefixed versions) and keeps every change."""
import re

text = open("release-notes.md").read()
assert "2026-03-03" in text, "ISO date"
assert not re.search(r"\b(March 3|3 March|Mar\.? 3)\b", text), "non-ISO date"
assert not re.search(r"(?<![v\w.])\d+\.\d+\.\d+", text), "version without v"
for fact in (r"[Dd]ark mode", r"trailing comma", r"30 minutes", r"/v1/export"):
    assert re.search(fact, text), fact
