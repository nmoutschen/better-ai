"""Monthly sales totals from the shop's CSV export."""

import csv


def load(path):
    """Read the export's rows as dicts with date, amount and note."""
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


def monthly_total(rows, year, month):
    """Total of one month's rows. Refunds are negative amounts, so they reduce the total."""
    start = f"{year}-{month:02d}-01"
    end = f"{year}-{month:02d}-31"
    return sum(int(row["amount"]) for row in rows if start <= row["date"] < end)


if __name__ == "__main__":
    import sys

    print(monthly_total(load("data/sales.csv"), int(sys.argv[1]), int(sys.argv[2])))
