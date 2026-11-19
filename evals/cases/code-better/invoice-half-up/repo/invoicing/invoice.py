"""Invoice amounts."""

from decimal import Decimal

from common.money import round_amount


def line_amount(quantity, unit_price):
    """Amount of one invoice line, in euros."""
    return round_amount(Decimal(quantity) * Decimal(unit_price))


def invoice_total(lines):
    """Total of (quantity, unit_price) lines, each rounded first."""
    return sum((line_amount(quantity, price) for quantity, price in lines), Decimal("0.00"))
