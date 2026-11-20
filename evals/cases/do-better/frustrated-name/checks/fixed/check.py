"""reply.md greets Maria by her name and still declines and offers both times."""
import re

text = open("reply.md").read()
assert re.search(r"\bMaria\b", text) and not re.search(r"\bMarie\b|Kellner", text), "name"
for pattern in (r"Thursday[^.?!]*10[:.]00", r"Thursday[^.?!]*15[:.]00", r"Friday[^.?!]*9[:.]30"):
    assert re.search(pattern, text), pattern
