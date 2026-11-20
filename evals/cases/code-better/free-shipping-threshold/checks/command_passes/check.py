from shipping import shipping_cost

assert shipping_cost(59.99) == 4.95, shipping_cost(59.99)
assert shipping_cost(60) == 0, shipping_cost(60)
assert shipping_cost(75) == 0
assert shipping_cost(50) == 4.95, shipping_cost(50)
