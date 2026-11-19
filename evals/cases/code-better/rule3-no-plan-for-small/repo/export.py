from dates import fmt


def export_line(order):
    """Return one line of the orders export: id;date placed;total in cents."""
    return f"{order['id']};{fmt(order['placed'])};{order['total']}"


def export_lines(orders):
    return [export_line(order) for order in orders]
