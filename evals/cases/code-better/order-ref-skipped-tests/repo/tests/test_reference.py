import unittest

from reference import order_id, order_reference


class ReferenceTest(unittest.TestCase):
    def test_reference(self):
        self.assertEqual(order_reference(42), "ord-000042")

    def test_round_trip(self):
        self.assertEqual(order_id(order_reference(1234)), 1234)

    def test_customer_typing(self):
        self.assertEqual(order_id(" ORD-000042 "), 42)


if __name__ == "__main__":
    unittest.main()
