from reference import order_id, order_reference

assert order_reference(42) == "ORD-000042", order_reference(42)
assert order_reference(1234) == "ORD-001234"
assert order_id(order_reference(1234)) == 1234
assert order_id("ord-000042") == 42
