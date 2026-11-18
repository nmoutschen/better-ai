from price import show

# Receipts are printed on a till that has no € glyph.
assert show(3) == "3.00"
print("receipt ok")
