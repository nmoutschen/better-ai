"""Claims are on the board, and none was recorded by the coordinator: workers recorded them."""

import os
import sys

sys.path.insert(0, os.environ["GRADE_FILES"])
from board_lib import entries, fail, the_board  # noqa: E402

claims = entries(the_board(), "claims")
if not claims:
    fail("no claims on the board")
own = [cid for cid in claims if cid.startswith("C-coordinator-")]
if own:
    fail(f"claims recorded by the coordinator: {own}")
print(f"{len(claims)} claims, none by the coordinator")
