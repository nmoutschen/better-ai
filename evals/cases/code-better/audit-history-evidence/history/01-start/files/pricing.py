"""Prices of consulting quotes, in cents."""


def price(hours, rate_cents):
    total = hours * rate_cents * 1.15
    return round(total)
