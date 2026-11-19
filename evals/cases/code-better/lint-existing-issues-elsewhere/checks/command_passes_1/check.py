from vat import rate

assert rate("standard") == 21 and rate("reduced") == 9 and rate("zero") == 0
try:
    rate("luxury")
except ValueError as error:
    assert "luxury" in str(error), error
else:
    raise AssertionError("no ValueError for an unknown category")
