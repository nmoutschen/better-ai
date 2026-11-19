import unittest

from vat import with_vat


class WithVatTests(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(with_vat(0), 0)

    def test_standard_price(self):
        self.assertEqual(with_vat(1000), 1210)


if __name__ == "__main__":
    unittest.main()
