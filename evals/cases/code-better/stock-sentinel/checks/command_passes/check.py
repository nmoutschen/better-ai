from shelf import label
assert label({}) == "unknown"
assert label({"qty": 0}) == "0"
assert label({"qty": 4}) == "4"
