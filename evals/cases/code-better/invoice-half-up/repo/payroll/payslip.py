"""Payslip amounts."""

from decimal import Decimal

from common.money import round_amount


def gross_pay(hours, hourly_rate):
    """Gross pay for the hours worked, in euros."""
    return round_amount(Decimal(hours) * Decimal(hourly_rate))


def overtime_pay(hours, hourly_rate, premium="1.5"):
    """Pay for overtime hours at the premium rate, in euros."""
    return round_amount(Decimal(hours) * Decimal(hourly_rate) * Decimal(premium))
