from sales import load, monthly_total

rows = load("data/sales.csv")
assert monthly_total(rows, 2026, 2) == 30, monthly_total(rows, 2026, 2)
assert monthly_total(rows, 2026, 3) == 90, monthly_total(rows, 2026, 3)
assert monthly_total(rows, 2026, 4) == 25, monthly_total(rows, 2026, 4)
assert monthly_total([{"date": "2026-12-31", "amount": "5", "note": "sale"}], 2026, 12) == 5
