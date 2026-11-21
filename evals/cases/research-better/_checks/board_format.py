"""The board is on disk in .research/<slug>/, in the board.md format, with questions that say when they are done,
and is not committed."""

import os
import subprocess
import sys

sys.path.insert(0, os.environ["GRADE_FILES"])
from board_lib import entries, entry, fail, none, the_board  # noqa: E402

board = the_board()
brief = entry(board / "brief.md")
for key in ("topic", "goal", "stop-at", "collections", "status"):
    if none(brief.get(key)):
        fail(f"brief.md has no {key}")
if brief["stop-at"] not in ("high", "medium", "low"):
    fail(f"stop-at is {brief['stop-at']!r}")
if brief["status"] not in ("running", "checking", "stopped"):
    fail(f"status is {brief['status']!r}")
questions = entries(board, "questions")
if not questions:
    fail("no questions/ files")
for qid, q in questions.items():
    for key in ("question", "priority", "status", "kind", "done-when"):
        if none(q.get(key)):
            fail(f"{qid} has no {key}")
log = subprocess.run(["git", "log", "--name-only", "--format=", os.environ["START_COMMIT"] + "..HEAD"],
                     capture_output=True, text=True).stdout
if ".research/" in log:
    fail("the board was committed")
print(f"{board}: {len(questions)} questions")
