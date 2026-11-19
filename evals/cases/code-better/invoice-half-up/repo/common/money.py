"""Money helpers shared by the billing packages."""

from decimal import ROUND_HALF_EVEN, Decimal

CENT = Decimal("0.01")


def round_amount(amount):
    """Round an amount to whole cents."""
    return Decimal(amount).quantize(CENT, rounding=ROUND_HALF_EVEN)
