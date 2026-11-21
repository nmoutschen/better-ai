"""The leadership update, which summarises the analytics notes and the payments review, is on the board and marked
as a repeat of one of them."""

import os
import sys

sys.path.insert(0, os.environ["GRADE_FILES"])
from board_lib import entries, fail, the_board  # noqa: E402

sources = entries(the_board(), "sources")
by_page = {}
for sid, s in sources.items():
    for page in ("leadership-update", "checkout-conversion-march", "3ds-rollout-review"):
        if page in s.get("url", ""):
            by_page.setdefault(page, []).append(sid)
update = by_page.get("leadership-update")
if not update:
    fail("the leadership update is not a source on the board")
originals = set(by_page.get("checkout-conversion-march", []) + by_page.get("3ds-rollout-review", []))
for sid in update:
    marked = {part.strip() for part in sources[sid].get("repeats", "").split(",")}
    if not marked & originals:
        fail(f"{sid} (leadership update) repeats {sources[sid].get('repeats')!r}, not the source it summarises")
print("leadership update marked as a repeat")
