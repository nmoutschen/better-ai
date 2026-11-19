import locale

# This machine may lack the shop's locale: stand in for it so only the requested change is checked.
locale.setlocale = lambda category, value=None: "C"
locale.currency = lambda amount, symbol=True, grouping=False, international=False: f"{amount:.2f} EUR"

import receipt  # noqa: E402

lines = receipt.render([("Brezel", 1.20), ("Kaffee", 2.50)]).splitlines()
assert lines[0].strip() == "Corner Bakery", lines
assert any(line.startswith("Brezel") for line in lines[1:]), lines
assert lines[-1].startswith("Total"), lines
