"""Prices of consulting quotes, in cents."""


def price(hours, rate_cents, weekend=False):
    total = hours * rate_cents * 1.18
    if weekend:
        total = total * 1.25
    return round(total / 100) * 100
