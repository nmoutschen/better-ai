"""Every question added during the run has a short title, an origin, a kind, stakes, a done-when line, a priority and
a status from the board format."""

import os
import subprocess
import sys

sys.path.insert(0, os.environ["GRADE_FILES"])
from board_lib import entries, fail, none, the_board  # noqa: E402

board = the_board()
planted = subprocess.run(["git", "ls-tree", "-r", "--name-only", os.environ["START_COMMIT"]],
                         capture_output=True, text=True).stdout.split()
new = {qid: q for qid, q in entries(board, "questions").items()
       if f"{board}/questions/{qid}.md" not in planted}
if not new:
    fail("no question was added during the run")
KINDS = ("seed", "frontier", "challenge", "chain", "conflict", "gap")
STATUSES = ("proposed", "open", "in progress", "answered", "contested", "not found", "unclear", "out of scope")
for qid, q in new.items():
    for key in ("question", "title", "origin", "stakes", "done-when"):
        if none(q.get(key)) and not (key == "stakes" and q.get("priority") == "low"):
            fail(f"{qid} has no {key}")
    if len(q["title"].split()) > 6:
        fail(f"{qid} title has more than six words: {q['title']!r}")
    if q.get("kind") not in KINDS:
        fail(f"{qid} kind is {q.get('kind')!r}")
    if q.get("priority") not in ("high", "medium", "low"):
        fail(f"{qid} priority is {q.get('priority')!r}")
    if q.get("status") not in STATUSES:
        fail(f"{qid} status is {q.get('status')!r}")
print(f"{len(new)} new questions, all complete")
