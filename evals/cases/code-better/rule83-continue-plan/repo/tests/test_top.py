import unittest

from textstats.api import top_words


class TopWordsTest(unittest.TestCase):
    def test_most_frequent_first(self):
        self.assertEqual(top_words("kiwi fig kiwi", 2), [("kiwi", 2), ("fig", 1)])

    def test_ties_in_alphabetical_order(self):
        self.assertEqual(top_words("pear apple pear apple fig", 2), [("apple", 2), ("pear", 2)])


if __name__ == "__main__":
    unittest.main()
