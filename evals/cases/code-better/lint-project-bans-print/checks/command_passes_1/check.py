import contextlib
import io
import logging
import warnings

from importer import read_orders

records = []


class Keep(logging.Handler):
    def emit(self, record):
        records.append(record.getMessage())


root = logging.getLogger()
root.addHandler(Keep())
root.setLevel(logging.DEBUG)
out, err = io.StringIO(), io.StringIO()
with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    orders = read_orders("sku,qty\nA-1,3\nB-7,three\nC-2,1\n")
assert orders == [("A-1", 3), ("C-2", 1)], orders
said = " ".join([*records, out.getvalue(), err.getvalue(), *(str(w.message) for w in caught)])
assert "B-7" in said, said
