import unittest
from decimal import Decimal

from payroll.payslip import gross_pay, overtime_pay


class PayslipTest(unittest.TestCase):
    def test_gross_pay(self):
        self.assertEqual(gross_pay("8", "12.50"), Decimal("100.00"))

    def test_overtime_pay(self):
        self.assertEqual(overtime_pay("2", "12.00"), Decimal("36.00"))


if __name__ == "__main__":
    unittest.main()
