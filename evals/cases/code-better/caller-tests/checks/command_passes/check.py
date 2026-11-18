from quote import quote
from weights import billable
assert billable(2.2) == 3
assert billable(3) == 3
assert quote(2.2) == 12
