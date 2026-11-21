"""Q-coordinator-8, left in progress by a worker that stopped, is closed, and its claims were not recorded by the
coordinator."""

import os
import sys

sys.path.insert(0, os.environ["GRADE_FILES"])
from board_lib import entries, entry, fail, the_board  # noqa: E402

board = the_board()
status = entry(board / "questions" / "Q-coordinator-8.md").get("status")
if status not in ("answered", "contested", "not found", "unclear"):
    fail(f"Q-coordinator-8 status is {status!r}")
own = [cid for cid, c in entries(board, "claims").items()
       if c.get("question") == "Q-coordinator-8" and cid.startswith("C-coordinator-")]
if own:
    fail(f"the coordinator recorded claims for Q-coordinator-8: {own}")
print(f"Q-coordinator-8 is {status}")
