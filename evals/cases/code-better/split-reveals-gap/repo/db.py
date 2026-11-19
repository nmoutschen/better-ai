import json
from pathlib import Path

STORE = Path("orders.json")


def insert(order):
    """Append one order to orders.json at once; an order without an id raises."""
    if "id" not in order:
        raise ValueError(f"order without id: {order}")
    rows = json.loads(STORE.read_text()) if STORE.exists() else []
    rows.append(order)
    STORE.write_text(json.dumps(rows))
