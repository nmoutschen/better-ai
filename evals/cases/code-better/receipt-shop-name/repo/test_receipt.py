import unittest

from receipt import render


class ReceiptTest(unittest.TestCase):
    def test_receipt(self):
        lines = render([("Brezel", 1.20), ("Kaffee", 2.50)]).splitlines()
        self.assertEqual(lines[0], "Corner Bakery")
        self.assertEqual(lines[1], f"{'Brezel':<20}{'1,20 €':>12}")
        self.assertEqual(lines[2], f"{'Kaffee':<20}{'2,50 €':>12}")
        self.assertEqual(lines[3], f"{'Total':<20}{'3,70 €':>12}")


if __name__ == "__main__":
    unittest.main()
