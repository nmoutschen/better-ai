# TODO: support discount codes at checkout.


def total(lines):
    return sum(price for price, quantity in lines)
