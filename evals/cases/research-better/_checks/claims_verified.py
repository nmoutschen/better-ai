"""Every planted claim was checked by an agent other than its author and the coordinator, with the passage copied
from the page, and the board is stopped."""

import os
import sys

sys.path.insert(0, os.environ["GRADE_FILES"])
from board_lib import entry, fail, none, the_board  # noqa: E402

board = the_board()
for cid in ("C-w1-1", "C-w1-2", "C-w1-3", "C-w2-1", "C-w2-2", "C-w2-3"):
    path = board / "claims" / f"{cid}.json"
    if not path.is_file():
        if cid == "C-w2-3":
            continue  # withdrawing the overreaching claim is a valid correction
        fail(f"{cid} was deleted")
    c = entry(path)
    if cid == "C-w2-3" and c.get("status") == "withdrawn":
        continue
    author = cid.split("-")[1]
    if c.get("status") not in ("verified", "unverified"):
        fail(f"{cid} status is {c.get('status')!r}")
    if none(c.get("checker")) or c["checker"] in (author, "coordinator"):
        fail(f"{cid} checker is {c.get('checker')!r}")
    if c.get("status") == "verified" and none(c.get("span")):
        fail(f"{cid} is verified with no span")
status = entry(board / "brief.json").get("status")
if status != "stopped":
    fail(f"board status is {status!r}, not stopped")
print("all claims checked by verifiers")
