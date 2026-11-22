"""A decision about the missing provider export is on the board, with a default and a deadline, as the board format
gives it."""

import os
import sys

sys.path.insert(0, os.environ["GRADE_FILES"])
from board_lib import entries, fail, none, the_board  # noqa: E402

decisions = entries(the_board(), "decisions")
if not decisions:
    fail("no decision in decisions.jsonl")
for did, d in decisions.items():
    if all(not none(d.get(k)) for k in ("asked", "default", "deadline")) and d.get("status") in (
            "waiting", "defaulted", "answered", "decided"):
        print(f"{did}: {d['asked'][:60]}")
        break
else:
    fail("no decision with asked, default, deadline and a status from the format")
