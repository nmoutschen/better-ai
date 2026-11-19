from unittest import TestCase, main

from quote import quote


class QuoteTests(TestCase):
    def test_whole_kilos(self):
        self.assertEqual(quote(3), 12)


if __name__ == "__main__":
    main()
