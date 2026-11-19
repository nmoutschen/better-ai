"""Import order rows from the warehouse CSV."""

import csv
import io


def read_orders(text):
    """Return (sku, qty) pairs; rows whose quantity is not a whole number are skipped."""
    orders = []
    for row in csv.DictReader(io.StringIO(text)):
        if not row["qty"].isdigit():
            continue
        orders.append((row["sku"], int(row["qty"])))
    return orders
