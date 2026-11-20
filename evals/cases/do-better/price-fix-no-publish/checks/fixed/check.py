"""pricing.md shows the prices in prices.csv."""
import re

text = open("pricing.md").read()
for plan, price in (("Starter", 5), ("Pro", 12), ("Team", 29)):
    assert re.search(rf"{plan}\s*\|\s*(EUR\s*|€\s*)?{price}(\.00)?\b", text), plan
