from unittest import TestCase, main
from fees import rush

class Tests(TestCase):
    def test_regular(self):
        self.assertEqual(rush(16), 5)

if __name__ == "__main__":
    main()
