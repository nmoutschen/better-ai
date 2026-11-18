import io, contextlib
from receipt import amount_label
from scanner import scanned_label
from till import print_total
assert scanned_label("  €8.00  ") == "Total: €8.00"
assert scanned_label("CHF 8.00") == "Total: CHF 8.00"
assert amount_label(8.0) == "Total: 8.0"
out = io.StringIO()
with contextlib.redirect_stdout(out):
    print_total(800)
assert out.getvalue() == "Total: 8.0\n"
