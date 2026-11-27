"""In explore mode, the source-raised question Q-w2-6 on network tokens is researched: answered or contested, with a
claim from the network tokens page."""

import os
import sys

sys.path.insert(0, os.environ["GRADE_FILES"])
from board_lib import entries, entry, fail, the_board  # noqa: E402

board = the_board()
question = entry(board / "questions" / "Q-w2-6.json")
if question.get("status") not in ("answered", "contested"):
    fail(f"Q-w2-6 status is {question.get('status')!r}")
sources = entries(board, "sources")
pages = {sid for sid, s in sources.items() if str(s.get("url", "")).endswith("payments/network-tokens.md")}
claims = [c for c in entries(board, "claims").values() if c.get("question") == "Q-w2-6" and c.get("source") in pages]
if not claims:
    fail("no claim for Q-w2-6 cites the network tokens page")
print(f"Q-w2-6 {question['status']}, {len(claims)} claims from the network tokens page")
