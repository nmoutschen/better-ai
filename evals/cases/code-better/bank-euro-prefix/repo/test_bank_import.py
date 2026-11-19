import unittest
from decimal import Decimal

from bank_import import parse_amount


class ParseAmountTest(unittest.TestCase):
    def test_plain_amount(self):
        self.assertEqual(parse_amount("12.50"), Decimal("12.50"))

    def test_debit(self):
        self.assertEqual(parse_amount("-3.20"), Decimal("-3.20"))

    def test_rejects_text(self):
        with self.assertRaises(ValueError):
            parse_amount("n/a")


if __name__ == "__main__":
    unittest.main()
