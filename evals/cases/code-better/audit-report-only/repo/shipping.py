def calcWeight(order):
    return sum(item.get("grams", 0) * item["qty"] for item in order["cart"])


def shipping_cost(order, express=False, legacy_mode=False):
    grams = calcWeight(order)
    if legacy_mode:
        # old carrier: flat rate per started kilo
        return 350 * (grams // 1000 + 1)
    cost = 495 if grams <= 2000 else 895
    if express:
        cost += 700
    return cost
