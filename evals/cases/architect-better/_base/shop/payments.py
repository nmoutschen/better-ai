"""Card payments through PayLane, our payment provider (an external service)."""

import json
import os
import urllib.request

PAYLANE_URL = "https://api.paylane.example/v2/charges"


def charge(amount_cents: int, card_token: str, order_ref: str) -> str:
    """Charge a card through PayLane; return PayLane's charge reference. Raises on a declined card."""
    body = json.dumps({"amount": amount_cents, "currency": "EUR", "source": card_token, "reference": order_ref})
    request = urllib.request.Request(
        PAYLANE_URL,
        data=body.encode(),
        headers={"Authorization": f"Bearer {os.environ['PAYLANE_KEY']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)["id"]
