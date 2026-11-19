import unittest

from pricing import order_total


class OrderTotalTests(unittest.TestCase):
    def test_small_order(self):
        self.assertEqual(order_total(100, 5), 500)

    def test_bulk_order(self):
        self.assertEqual(order_total(100, 20), 1800)


if __name__ == "__main__":
    unittest.main()
