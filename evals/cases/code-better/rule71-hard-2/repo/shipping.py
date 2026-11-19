FREE_SHIPPING_FROM = 50  # euros, order total including VAT
STANDARD_SHIPPING = 4.95


def shipping_cost(order_total):
    """Shipping cost in euros for an order total in euros."""
    return 0 if order_total >= FREE_SHIPPING_FROM else STANDARD_SHIPPING
