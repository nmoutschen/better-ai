import unittest

from textstats.api import _tokenize


class TokenizeTest(unittest.TestCase):
    def test_lower_case_and_apostrophes(self):
        self.assertEqual(_tokenize("Don't PANIC"), ["don't", "panic"])


if __name__ == "__main__":
    unittest.main()
