import re

from visits import monthly_summary, summary_line

zero = summary_line("Cleo", [])
assert re.fullmatch(r"Cleo: 0 visits, avg 0(\.0)? min", zero), zero
one = summary_line("Dee", [25])
assert one == "Dee: 1 visit, avg 25.0 min", one
assert summary_line("Ana", [30, 45]) == "Ana: 2 visits, avg 37.5 min"
summary = monthly_summary({"Cleo": [], "Ana": [30, 45]})
assert summary.splitlines()[0] == "Ana: 2 visits, avg 37.5 min", summary
assert summary.splitlines()[1] == zero, summary
