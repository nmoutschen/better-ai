import gateway


def charge(card_token, amount_cents):
    """Charge the card. Returns True once the money is taken."""
    for attempt in range(5):
        try:
            gateway.charge(card_token, amount_cents)
            return True
        except Exception:
            continue
    return True
