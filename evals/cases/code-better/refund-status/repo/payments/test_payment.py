import unittest

from payments.payment import Payment, charge, refund


def new_payment():
    return Payment(id="pay_1", amount_cents=990, customer_id="cus_1", customer_email="sam@example.com")


class PaymentTest(unittest.TestCase):
    def test_charge(self):
        self.assertEqual(charge(new_payment()).status, "charged")

    def test_refund_after_charge(self):
        self.assertEqual(refund(charge(new_payment())).status, "refunded")

    def test_refund_before_charge_is_refused(self):
        with self.assertRaises(ValueError):
            refund(new_payment())


if __name__ == "__main__":
    unittest.main()
