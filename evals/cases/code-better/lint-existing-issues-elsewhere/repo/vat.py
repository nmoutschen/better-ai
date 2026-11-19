"""VAT rates by product category."""

RATES = {"standard": 21, "reduced": 9, "zero": 0}


def rate(category):
    """Return the VAT rate in percent for a category."""
    return RATES[category]
