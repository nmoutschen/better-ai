import json

CUSTOMERS = "data/customers.json"
ORDERS = "data/orders.json"


def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def save(path, records):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(records, handle, indent=2)
        handle.write("\n")
