from ship import label
assert label({"zip": "00100"}) == "Postal: 00100"
assert label({"zip": " 01230 "}) == "Postal: 01230"
