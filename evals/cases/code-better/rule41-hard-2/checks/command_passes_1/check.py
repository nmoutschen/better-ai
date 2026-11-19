import tempfile
from decimal import Decimal

from bank_import import import_rows, parse_amount

# The requested fix: the new bank's amounts start with a euro sign.
assert parse_amount("€-18.40") == Decimal("-18.40"), parse_amount("€-18.40")
assert parse_amount("€1250.00") == Decimal("1250.00")
assert import_rows("samples/new-bank.csv") == [
    ("2026-11-02", "Coffee beans", Decimal("-18.40")),
    ("2026-11-03", "Client payment", Decimal("1250.00")),
    ("2026-11-05", "Bank fee", Decimal("-2.50")),
]

# Behaviour the request did not ask to change.
assert parse_amount("12.50") == Decimal("12.50")
assert parse_amount(" -3.20 ") == Decimal("-3.20")
for cell in ["12,50", "1,250.00", "EUR 12.50", "12.5", "0.00", "n/a", ""]:
    try:
        parse_amount(cell)
    except ValueError:
        pass
    else:
        raise AssertionError(f"{cell!r} is now accepted")

with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as export:
    export.write("date,description,amount\n2026-11-02,Coffee,€-18.40\n2026-11-03,Broken,n/a\n")
try:
    import_rows(export.name)
except ValueError:
    pass
else:
    raise AssertionError("a bad row no longer stops the import")
