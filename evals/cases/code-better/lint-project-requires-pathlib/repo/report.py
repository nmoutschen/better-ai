"""Summarise a day's sales file: python report.py sales.csv"""

import csv
import sys
from pathlib import Path


def summary(path):
    """Return the summary lines for a sales CSV."""
    with Path(path).open(newline="") as file:
        rows = list(csv.DictReader(file))
    total = sum(int(row["cents"]) for row in rows)
    return [f"Orders: {len(rows)}", f"Total: €{total / 100:.2f}"]


if __name__ == "__main__":
    print("\n".join(summary(sys.argv[1])))
