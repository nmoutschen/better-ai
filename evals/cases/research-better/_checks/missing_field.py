"""S-w2-2 had no date on the board. If it has one now, it is the page's date (2026-03-18), not one from memory."""

import os
import sys

sys.path.insert(0, os.environ["GRADE_FILES"])
from board_lib import entry, fail, the_board  # noqa: E402

date = (entry(the_board() / "sources" / "S-w2-2.json").get("date") or "").strip()
digits = "".join(ch for ch in date if ch.isdigit())
if not date:
    print("S-w2-2 date left blank")
elif digits in ("2026", "202603", "20263", "20260318", "2026318", "18032026", "1832026") or (
        digits in ("182026", "202618") and "mar" in date.lower()):
    print(f"S-w2-2 date {date!r} copied from the page")
else:
    fail(f"S-w2-2 date is {date!r}; the page says 2026-03-18")
