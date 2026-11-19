import datetime

from export import export_line, export_lines

assert export_line({"id": 17, "placed": datetime.date(2026, 3, 4), "total": 1999}) == "17;2026-03-04;1999"
assert export_lines([{"id": 3, "placed": datetime.date(2026, 12, 31), "total": 5}]) == ["3;2026-12-31;5"]
