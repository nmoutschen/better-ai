from export import csv_row

# The accounting import reads plain numbers, without padding.
assert csv_row(7, 12.5) == "7,12.5"
