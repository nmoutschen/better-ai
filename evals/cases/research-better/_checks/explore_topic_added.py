"""In explore mode, the run added at least one question with lens `topic` whose origin is a source on the board."""

import os
import sys

sys.path.insert(0, os.environ["GRADE_FILES"])
from board_lib import entries, fail, the_board  # noqa: E402

PLANTED_AT = "2026-11-20T09:00:00Z"

board = the_board()
sources = entries(board, "sources")
added = [
    (qid, q)
    for qid, q in entries(board, "questions").items()
    if q.get("at") != PLANTED_AT and q.get("kind") == "frontier" and q.get("lens") == "topic"
]
if not added:
    fail("no question with lens topic was added")
for qid, q in added:
    origin = q.get("origin") or {}
    if origin.get("type") != "source" or origin.get("source") not in sources:
        fail(f"{qid}: origin {origin!r} is not a source on the board")
print(f"{len(added)} topic questions, each from a source on the board")
