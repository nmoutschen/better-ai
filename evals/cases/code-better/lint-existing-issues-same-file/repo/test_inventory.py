import unittest

from inventory import count


class Count(unittest.TestCase):
    def test_known_item(self):
        self.assertEqual(count("tea"), 12)


if __name__ == "__main__":
    unittest.main()
