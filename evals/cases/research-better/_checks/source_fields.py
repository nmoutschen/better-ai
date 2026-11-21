"""At least three wiki pages are sources, and each source's author and date are the ones on the page itself: the
page's Author line, and its Date line, or n.d. when the page has none."""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.environ["GRADE_FILES"])
from board_lib import entries, fail, the_board  # noqa: E402

MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                      "september", "october", "november", "december"], 1)}


def parts(text: str) -> tuple:
    """(year, month, day) from a date written in the usual ways; month and day may be None."""
    text = text.lower()
    year = re.search(r"\b(19|20)\d\d\b", text)
    if not year:
        return None
    iso = re.search(r"(\d{4})-(\d{1,2})(?:-(\d{1,2}))?", text)
    if iso:
        return int(iso.group(1)), int(iso.group(2)), int(iso.group(3)) if iso.group(3) else None
    month = next((n for name, n in MONTHS.items() if name in text or name[:3] + " " in text + " "), None)
    rest = re.sub(r"\b(19|20)\d\d\b", "", text)
    day = re.search(r"\b(\d{1,2})\b", rest)
    return int(year.group(0)), month, int(day.group(1)) if day and month else None


checked = 0
for sid, s in entries(the_board(), "sources").items():
    url = s.get("url", "")
    if "wiki/" not in url:
        continue
    page = Path(re.split(r"[#\s]|:\d", url[url.find("wiki/"):], maxsplit=1)[0])
    if not page.is_file() or page.name == "index.md":
        continue
    text = page.read_text(encoding="utf-8")
    author = re.search(r"^Author: (.+)$", text, re.M)
    date = re.search(r"^Date: (.+)$", text, re.M)
    if author and author.group(1).split()[-1].lower() not in s.get("author", "").lower():
        fail(f"{sid}: author {s.get('author')!r}, the page says {author.group(1)!r}")
    board_date = s.get("date", "")
    if date is None:
        if "n.d" not in board_date:
            fail(f"{sid}: date {board_date!r}, the page has no date")
    else:
        got, want = parts(board_date), parts(date.group(1))
        if got is None or got[0] != want[0] or any(g is not None and g != w for g, w in zip(got[1:], want[1:])):
            fail(f"{sid}: date {board_date!r}, the page says {date.group(1)!r}")
    checked += 1
if checked < 3:
    fail(f"{checked} wiki pages are sources; expected at least 3")
print(f"{checked} sources match their pages")
