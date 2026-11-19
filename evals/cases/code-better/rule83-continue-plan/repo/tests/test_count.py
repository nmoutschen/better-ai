import unittest

from textstats.api import word_count


class WordCountTest(unittest.TestCase):
    def test_ignores_punctuation(self):
        self.assertEqual(word_count("Hello, world -- again!"), 3)


if __name__ == "__main__":
    unittest.main()
