import unittest

from vat import rate


class Rate(unittest.TestCase):
    def test_standard(self):
        self.assertEqual(rate("standard"), 21)


if __name__ == "__main__":
    unittest.main()
