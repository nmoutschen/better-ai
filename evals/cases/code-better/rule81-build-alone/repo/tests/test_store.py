import json
import os
import tempfile
import unittest

from inventory.store import load_items


class LoadItemsTest(unittest.TestCase):
    def test_reads_items(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "items.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump({"items": [{"sku": "A-1", "name": "Anchor", "qty": 3}]}, handle)
            self.assertEqual(load_items(path), [{"sku": "A-1", "name": "Anchor", "qty": 3}])


if __name__ == "__main__":
    unittest.main()
