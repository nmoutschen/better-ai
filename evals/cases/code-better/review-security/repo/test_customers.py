import sqlite3
import unittest

from web import handle_list


def sample_db():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE customers (id INTEGER PRIMARY KEY, account_id INTEGER, name TEXT)")
    conn.executemany(
        "INSERT INTO customers (account_id, name) VALUES (?, ?)",
        [(1, "Anna Berg"), (1, "Tom Reed"), (2, "Hana Mori")],
    )
    return conn


class CustomerPageTests(unittest.TestCase):
    def test_list_is_scoped_to_the_account(self):
        result = handle_list(sample_db(), {"account_id": 1}, {})
        self.assertEqual([c["name"] for c in result["customers"]], ["Anna Berg", "Tom Reed"])


if __name__ == "__main__":
    unittest.main()
