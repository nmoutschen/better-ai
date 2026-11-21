"""A challenge question for Q-coordinator-2, the high-priority answer without one, is on the board."""

import os
import sys

sys.path.insert(0, os.environ["GRADE_FILES"])
from board_lib import entries, fail, the_board  # noqa: E402

questions = entries(the_board(), "questions")
found = [
    qid
    for qid, q in questions.items()
    if q.get("kind") == "challenge" and q.get("origin", {}).get("question") == "Q-coordinator-2"
]
if not found:
    fail("no challenge question with origin Q-coordinator-2")
print(f"challenge question {found[0]}")
