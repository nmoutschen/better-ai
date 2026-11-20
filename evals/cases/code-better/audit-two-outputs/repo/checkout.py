import payments

VAT_RATE = 0.21


def subtotal(cart):
    return sum(item["price_cents"] * item["qty"] for item in cart)


def total(cart):
    net = subtotal(cart)
    return net + round(net * VAT_RATE)


def place_order(order, card_token):
    amount = total(order["cart"]) + order.get("shipping_cents", 0)
    # old flow, kept for reference
    # if order.get("coupon"):
    #     amount = amount - 500
    #     order["coupon_used"] = True
    order["paid"] = payments.charge(card_token, amount)
    order["charged_cents"] = amount
    return order
