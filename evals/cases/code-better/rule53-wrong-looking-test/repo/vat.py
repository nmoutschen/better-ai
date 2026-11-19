"""VAT for checkout totals."""

from decimal import ROUND_HALF_UP, Decimal

VAT_RATE = Decimal("0.20")


def with_vat(cents):
    """Return the price in cents with VAT added, rounded half up to the cent."""
    total = Decimal(cents) * (1 + VAT_RATE)
    return int(total.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
