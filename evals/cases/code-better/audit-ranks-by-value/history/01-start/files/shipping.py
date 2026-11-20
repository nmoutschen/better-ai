def calcWeight(order):
    return sum(item.get("grams", 0) * item["qty"] for item in order["cart"])


def shipping_cost(order, express=False):
    grams = calcWeight(order)
    cost = 495 if grams <= 2000 else 895
    if express:
        cost += 700
    return cost
