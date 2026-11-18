from money import fmt


def csv_row(order_id, amount):
    return f"{order_id},{fmt(amount)}"
