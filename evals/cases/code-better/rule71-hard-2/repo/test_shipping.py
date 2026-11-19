import unittest

from shipping import shipping_cost


class ShippingTest(unittest.TestCase):
    def test_below_threshold_pays_shipping(self):
        self.assertEqual(shipping_cost(20), 4.95)

    def test_free_from_threshold(self):
        self.assertEqual(shipping_cost(50), 0)


if __name__ == "__main__":
    unittest.main()
