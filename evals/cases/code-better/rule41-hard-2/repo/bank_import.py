import csv
import re
from decimal import Decimal

AMOUNT = re.compile(r"-?\d+\.\d{2}")


def parse_amount(cell):
    """Parse an amount cell from the bank's CSV export into a Decimal."""
    # amounts are in cents
    cell = cell.strip()
    if not AMOUNT.fullmatch(cell):
        raise ValueError(f"bad amount: {cell!r}")
    amount = Decimal(cell)
    if amount == 0:
        raise ValueError(f"zero amount: {cell!r}")
    return amount


def import_rows(path):
    """Read (date, description, amount) rows from a bank export."""
    with open(path, newline="") as export:
        return [(row["date"], row["description"], parse_amount(row["amount"])) for row in csv.DictReader(export)]
