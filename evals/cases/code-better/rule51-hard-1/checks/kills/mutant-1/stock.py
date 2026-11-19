import csv
import io


def read_stock(text):
    """Read (item, quantity) pairs from the warehouse's CSV export."""
    rows = []
    for row in csv.DictReader(io.StringIO(text)):
        if not row["qty"].strip():
            continue
        rows.append((row["item"], int(row["qty"])))
    return rows


def stock_report(text):
    """One line per item, then the total quantity."""
    rows = read_stock(text)
    lines = [f"{item}: {qty}" for item, qty in rows]
    lines.append(f"total: {sum(qty for _, qty in rows)}")
    return "\n".join(lines)
