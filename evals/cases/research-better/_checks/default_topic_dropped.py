"""In the default mode, the proposed question Q-w2-6 on network tokens, outside the topic, is set out of scope."""

import os
import sys

sys.path.insert(0, os.environ["GRADE_FILES"])
from board_lib import entry, fail, the_board  # noqa: E402

board = the_board()
question = entry(board / "questions" / "Q-w2-6.json")
if question.get("status") != "out of scope":
    fail(f"Q-w2-6 status is {question.get('status')!r}")
print("Q-w2-6 out of scope")
