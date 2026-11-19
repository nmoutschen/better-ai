from unittest import TestCase, main
from balance import display

class Tests(TestCase):
    def test_regular(self):
        self.assertEqual(display(8), '8')

if __name__ == "__main__":
    main()
