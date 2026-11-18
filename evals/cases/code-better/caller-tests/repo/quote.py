from weights import billable

RATE = 4


def quote(kg):
    return billable(kg) * RATE
