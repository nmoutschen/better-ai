"""Stock lookups for the shop."""

from typing import Optional

STOCK = {"tea": 12, "coffee": 0}


def count(item: str) -> Optional[int]:
    """Return how many of an item are in stock, or None for an item we don't stock."""
    return STOCK.get(item)
