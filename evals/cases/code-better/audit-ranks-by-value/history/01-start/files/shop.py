import checkout
import invoice
import shipping


def handle(order, card_token):
    order["shipping_cents"] = shipping.shipping_cost(order, express=order.get("express", False))
    checkout.place_order(order, card_token)
    return invoice.render(order)
