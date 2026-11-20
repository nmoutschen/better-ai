"""Integration tests against the orders database."""

import os
import unittest

import orders_db

DATABASE = os.environ.get("ORDERS_DATABASE_URL")


@unittest.skipUnless(DATABASE, "needs ORDERS_DATABASE_URL")
class OrdersDatabaseTest(unittest.TestCase):
    def setUp(self):
        self.connection = orders_db.connect()

    def test_save_reference(self):
        orders_db.save_reference(self.connection, {"id": 42})

    def test_find_by_reference(self):
        self.assertEqual(orders_db.find_order(self.connection, "ORD-000042")["id"], 42)

    def test_find_by_lowercase_reference(self):
        self.assertEqual(orders_db.find_order(self.connection, "ord-000042")["id"], 42)

    def test_unknown_reference(self):
        self.assertIsNone(orders_db.find_order(self.connection, "ORD-999999"))


if __name__ == "__main__":
    unittest.main()
