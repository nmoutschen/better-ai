import unittest

import checkout


class TotalTests(unittest.TestCase):
    def test_total_adds_vat(self):
        cart = [{"name": "Mug", "price_cents": 1000, "qty": 2}]
        self.assertEqual(checkout.total(cart), 2420)


if __name__ == "__main__":
    unittest.main()
