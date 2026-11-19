import unittest

from split import split


class SplitTests(unittest.TestCase):
    def test_even(self):
        self.assertEqual(split(900, 3), [300, 300, 300])

    def test_shares_add_up(self):
        for total, people in [(100, 3), (10, 4), (7, 2), (2501, 6)]:
            self.assertEqual(sum(split(total, people)), total)

    def test_three_way_thousand(self):
        self.assertEqual(split(1000, 3), [333, 333, 333])


if __name__ == "__main__":
    unittest.main()
