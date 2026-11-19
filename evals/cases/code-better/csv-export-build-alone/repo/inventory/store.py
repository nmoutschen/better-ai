import json


def load_items(path):
    """Return the items of an inventory file: dicts with sku, name and qty."""
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)["items"]
