import unittest
from decimal import Decimal

from invoicing.invoice import invoice_total, line_amount


class InvoiceTest(unittest.TestCase):
    def test_line_amount(self):
        self.assertEqual(line_amount("2", "1.10"), Decimal("2.20"))

    def test_total_adds_rounded_lines(self):
        self.assertEqual(invoice_total([("3", "0.333"), ("1", "4.50")]), Decimal("5.50"))


if __name__ == "__main__":
    unittest.main()
