VAT = 0.20


def lines(cart):
    return [f"{item['name']} x{item['qty']}: {item['price_cents'] * item['qty']}" for item in cart]


def render(order):
    net = sum(item["price_cents"] * item["qty"] for item in order["cart"])
    vat = round(net * VAT)
    body = "\n".join(lines(order["cart"]))
    shipping = order.get("shipping_cents", 0)
    return f"{body}\nVAT: {vat}\nShipping: {shipping}\nTotal: {net + vat + shipping}\n"
