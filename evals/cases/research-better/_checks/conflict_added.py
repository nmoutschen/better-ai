"""A question of kind conflict is on the board: C-w2-6 and C-w2-7 each name a different change as the main cause."""

import os
import sys

sys.path.insert(0, os.environ["GRADE_FILES"])
from board_lib import entries, fail, the_board  # noqa: E402

found = [qid for qid, q in entries(the_board(), "questions").items() if q.get("kind") == "conflict"]
if not found:
    fail("no question of kind conflict")
print(f"conflict question {found[0]}")
