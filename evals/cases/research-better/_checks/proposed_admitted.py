"""The proposed duplicate Q-w2-6 is merged into Q-coordinator-1 (status merged, merged_into naming it), and the new
proposed question Q-w1-7 is opened, not left proposed or dropped."""

import os
import sys

sys.path.insert(0, os.environ["GRADE_FILES"])
from board_lib import entry, fail, the_board  # noqa: E402

board = the_board()
dup = entry(board / "questions" / "Q-w2-6.json")
if dup.get("status") != "merged" or dup.get("merged_into") != "Q-coordinator-1":
    fail(f"Q-w2-6: status {dup.get('status')!r}, merged_into {dup.get('merged_into')!r}")
new = entry(board / "questions" / "Q-w1-7.json")
if new.get("status") in ("proposed", "out of scope"):
    fail(f"Q-w1-7 status is {new.get('status')!r}")
print("duplicate merged, new question opened")
