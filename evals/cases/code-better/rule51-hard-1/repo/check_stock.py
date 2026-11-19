from stock import read_stock, stock_report

assert read_stock("item,qty\nbolt,4\n") == [("bolt", 4)]
assert stock_report("item,qty\nbolt,4\nnut,12\n") == "bolt: 4\nnut: 12\ntotal: 16"
print("stock checks passed")
