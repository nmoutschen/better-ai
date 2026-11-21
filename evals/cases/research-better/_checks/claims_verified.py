"""Every planted claim was checked by an agent other than its author and the coordinator, with the passage copied
from the page, and the board is stopped."""

import os
import sys

sys.path.insert(0, os.environ["GRADE_FILES"])
from board_lib import entry, fail, none, the_board, unquote  # noqa: E402

board = the_board()
for cid in ("C-w1-1", "C-w1-2", "C-w1-3", "C-w2-1", "C-w2-2", "C-w2-3"):
    path = board / "claims" / f"{cid}.md"
    if not path.is_file():
        if cid == "C-w2-3":
            continue  # deleting the overreaching claim is a valid correction
        fail(f"{cid} was deleted")
    c = entry(path)
    author = cid.split("-")[1]
    if c.get("verified") not in ("verified", "unverified"):
        fail(f"{cid} verified is {c.get('verified')!r}")
    if none(c.get("checker")) or c["checker"] in (author, "coordinator"):
        fail(f"{cid} checker is {c.get('checker')!r}")
    if c.get("verified") == "verified" and none(unquote(c.get("span", ""))):
        fail(f"{cid} is verified with no span")
status = entry(board / "brief.md").get("status")
if status != "stopped":
    fail(f"board status is {status!r}, not stopped")
print("all claims checked by verifiers")
