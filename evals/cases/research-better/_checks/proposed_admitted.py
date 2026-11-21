"""The proposed duplicate Q-w2-6 is merged into Q-coordinator-1 (out of scope, with the merge noted), and the new
proposed question Q-w1-7 is opened, not left proposed or dropped."""

import os
import sys

sys.path.insert(0, os.environ["GRADE_FILES"])
from board_lib import entry, fail, the_board  # noqa: E402

board = the_board()
dup = entry(board / "questions" / "Q-w2-6.md")
if dup.get("status") != "out of scope" or "Q-coordinator-1" not in dup.get("note", ""):
    fail(f"Q-w2-6: status {dup.get('status')!r}, note {dup.get('note')!r}")
new = entry(board / "questions" / "Q-w1-7.md")
if new.get("status") in ("proposed", "out of scope"):
    fail(f"Q-w1-7 status is {new.get('status')!r}")
print("duplicate merged, new question opened")
