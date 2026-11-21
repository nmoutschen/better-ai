"""At least three claims, each with a quote that appears word for word in the wiki page its source points to, and
each source records how it was read."""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.environ["GRADE_FILES"])
from board_lib import entries, fail, none, the_board  # noqa: E402


def norm(text: str) -> str:
    """Whitespace, Markdown emphasis and escaped quotes do not count."""
    return " ".join(text.replace("**", "").replace("`", "").replace('\\"', '"').split())


def found(quote: str, page: str) -> bool:
    """Each part of the quote, split at an elision, appears in the page, in order."""
    at, searched = 0, False
    for part in re.split(r"\[\s*(?:\.\.\.|…)\s*\]|\.\.\.|…", quote):
        part = norm(part)
        if not part:
            continue
        at = page.find(part, at)
        if at < 0:
            return False
        at += len(part)
        searched = True
    return searched


board = the_board()
sources, claims = entries(board, "sources"), entries(board, "claims")
if len(claims) < 3:
    fail(f"{len(claims)} claims; expected at least 3")
for sid, s in sources.items():
    if s.get("read") not in ("raw", "extracted", "abstract", "snippet", "blocked"):
        fail(f"{sid} read is {s.get('read')!r}")
for cid, c in claims.items():
    s = sources.get(c.get("source", ""))
    if s is None:
        fail(f"{cid} cites {c.get('source')!r}, which is not on the board")
    url = s.get("url", "")
    page = url[url.find("wiki/"):] if "wiki/" in url else url
    page = re.split(r"[#\s]|:\d", page, maxsplit=1)[0]
    if not Path(page).is_file():
        fail(f"{cid}: source url {url!r} is not a wiki page")
    quote = c.get("quote", "")
    if none(quote) or not found(quote, norm(Path(page).read_text(encoding="utf-8"))):
        fail(f"{cid}: quote not found word for word in {page}: {quote[:80]!r}")
print(f"{len(claims)} quotes found in their pages")
