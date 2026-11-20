"""Prices of consulting quotes, in cents."""


def price(hours, rate_cents):
    total = hours * rate_cents * 1.18
    return round(total)
