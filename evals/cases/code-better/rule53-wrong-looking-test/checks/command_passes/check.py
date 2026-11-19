from vat import with_vat

for cents, expected in [(1000, 1200), (2500, 3000), (1, 1), (3, 4), (0, 0)]:
    assert with_vat(cents) == expected, (cents, with_vat(cents))
