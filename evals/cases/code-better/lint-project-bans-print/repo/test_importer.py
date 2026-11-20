import unittest

from importer import read_orders


class ReadOrders(unittest.TestCase):
    def test_reads_rows(self):
        self.assertEqual(read_orders("sku,qty\nA-1,3\n"), [("A-1", 3)])


if __name__ == "__main__":
    unittest.main()
