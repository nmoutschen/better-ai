"""Charging and refunding card payments."""

import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass
class Payment:
    id: str
    amount_cents: int
    customer_id: str
    customer_email: str
    status: str = "pending"


def charge(payment):
    """Charge the customer's card."""
    if payment.status != "pending":
        raise ValueError(f"payment {payment.id} is {payment.status}")
    log.debug("charging payment %s for %d cents", payment.id, payment.amount_cents)
    payment.status = "charged"
    log.debug("payment %s charged", payment.id)
    return payment


def refund(payment):
    """Refund a charged payment in full."""
    if payment.status != "charged":
        raise ValueError(f"payment {payment.id} is {payment.status}")
    payment.status = "refunded"
    return payment
