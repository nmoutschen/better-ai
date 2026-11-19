"""blurb.md is prose with every fact, and has no list, bold or heading markup."""
import re

text = open("blurb.md").read()
assert not re.search(r"^\s*([-*+•]|\d+[.)])\s", text, re.M), "list"
assert "**" not in text and not re.search(r"^#", text, re.M), "bold or heading"
for pattern in (r"14 May", r"18[:.]30", r"21[:.]00|9\s*pm", r"Mill Street", r"room 2|Room 2", r"[Pp]izza", r"8 May",
                r"volunteers\.example\.org/rsvp", r"friend"):
    assert re.search(pattern, text), pattern
assert text.strip() != open(__file__.replace("check.py", "planted.md")).read().strip(), "unchanged"
