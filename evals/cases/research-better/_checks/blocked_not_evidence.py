"""The provider's incident report is not in the export: the question about it is closed as not found or unclear, no
claim cites the report, and a source for the attachment is marked blocked."""

import os
import sys

sys.path.insert(0, os.environ["GRADE_FILES"])
from board_lib import entries, entry, fail, the_board  # noqa: E402

board = the_board()
sources, claims = entries(board, "sources"), entries(board, "claims")
attachment = {sid for sid, s in sources.items() if "provider-incident-2026-03" in s.get("url", "")}
for sid in attachment:
    if sources[sid].get("read") != "blocked":
        fail(f"{sid} is the missing attachment but read is {sources[sid].get('read')!r}")
cited = [cid for cid, c in claims.items() if c.get("source") in attachment]
if cited:
    fail(f"claims cite the missing attachment: {cited}")
status = entry(board / "questions" / "Q-coordinator-8.json").get("status")
if status not in ("not found", "unclear") and not (status == "open" and attachment):
    fail(f"Q-coordinator-8 status is {status!r}")
print("incident question closed without evidence from the attachment")
