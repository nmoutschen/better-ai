from inventory import count, in_stock

assert in_stock("tea") is True
assert in_stock("coffee") is False
assert in_stock("cake") is None
assert count("tea") == 12 and count("cake") is None
