from rental import allowed
assert allowed(30) is True
assert allowed(31) is False
assert allowed(0) is False
