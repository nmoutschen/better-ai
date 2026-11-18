from quota import allowed
assert allowed(12) is True
assert allowed(13) is False
