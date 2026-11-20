def order_reference(order_id):
    """The reference printed on invoices and quoted by customers, such as ord-000042."""
    return f"ord-{order_id:06d}"


def order_id(reference):
    """The order id in a reference, as customers type it."""
    return int(reference.strip().lower().removeprefix("ord-"))
