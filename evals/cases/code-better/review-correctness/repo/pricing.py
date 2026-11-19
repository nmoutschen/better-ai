"""Order pricing."""


def discount_for(qty):
    """Return the discount rate for an order of qty units."""
    if qty >= 10:
        return 0.10
    return 0.0


def order_total(unit_cents, qty):
    """Return the order total in cents after the discount."""
    gross = unit_cents * qty
    return round(gross * (1 - discount_for(qty)))
