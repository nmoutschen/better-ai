from money import fmt
from order_page import total_line
from export import csv_row
assert total_line(12.5) == 'Total: 12.50'
assert total_line(3) == 'Total: 3.00'
assert total_line(12) == 'Total: 12.00'
assert csv_row(7, 12.5) == '7,12.5'
assert csv_row(7, 12) == '7,12'
assert fmt(12.5) == '12.5' and fmt(12) == '12'
