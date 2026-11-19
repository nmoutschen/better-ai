"""Order lifecycle."""

from dataclasses import dataclass, field

import audit


@dataclass
class Order:
    id: str
    customer_id: str
    lines: list = field(default_factory=list)
    status: str = "open"


def cancel(order):
    """Cancel an open order."""
    if order.status != "open":
        raise ValueError(f"order {order.id} is {order.status}")
    order.status = "cancelled"
    audit.record("order.cancelled", order_id=order.id, customer_id=order.customer_id)
    return order
