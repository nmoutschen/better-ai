import unittest

from report import summary


class Summary(unittest.TestCase):
    def test_lines(self):
        self.assertEqual(summary("samples/sales.csv"), ["Orders: 3", "Total: €37.50"])


if __name__ == "__main__":
    unittest.main()
