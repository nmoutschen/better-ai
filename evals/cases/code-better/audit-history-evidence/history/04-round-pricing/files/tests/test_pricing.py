import unittest

import pricing


class PriceTests(unittest.TestCase):
    def test_price_rounds_to_euros(self):
        self.assertEqual(pricing.price(2, 10000), 23600)


if __name__ == "__main__":
    unittest.main()
