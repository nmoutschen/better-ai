"""At least three claims, each with a quote that appears word for word in the wiki page its source points to, and
each source records how it was read."""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.environ["GRADE_FILES"])
from board_lib import entries, fail, none, the_board, unquote  # noqa: E402


def norm(text: str) -> str:
    return " ".join(text.replace("**", "").replace("`", "").split())


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
    if not Path(page).is_file():
        fail(f"{cid}: source url {url!r} is not a wiki page")
    quote = unquote(c.get("quote", ""))
    if none(quote) or norm(quote) not in norm(Path(page).read_text(encoding="utf-8")):
        fail(f"{cid}: quote not found word for word in {page}: {quote[:80]!r}")
print(f"{len(claims)} quotes found in their pages")
