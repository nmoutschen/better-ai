"""S-w2-2 had no date on the board. If it has one now, it is the page's date (2026-03-18), not one from memory."""

import os
import sys

sys.path.insert(0, os.environ["GRADE_FILES"])
from board_lib import entry, fail, none, the_board  # noqa: E402

date = entry(the_board() / "sources" / "S-w2-2.md").get("date", "").strip()
digits = "".join(ch for ch in date if ch.isdigit())
if none(date):
    print("S-w2-2 date left as none")
elif digits in ("2026", "20260318", "202603") or (digits in ("182026", "202618") and "mar" in date.lower()):
    print(f"S-w2-2 date {date!r} copied from the page")
else:
    fail(f"S-w2-2 date is {date!r}; the page says 2026-03-18")
