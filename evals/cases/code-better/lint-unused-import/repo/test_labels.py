import unittest

from labels import price_line, title_lines


class Labels(unittest.TestCase):
    def test_short_title(self):
        self.assertEqual(title_lines("Green tea"), ["Green tea"])

    def test_price(self):
        self.assertEqual(price_line(350), "€3.50")


if __name__ == "__main__":
    unittest.main()
