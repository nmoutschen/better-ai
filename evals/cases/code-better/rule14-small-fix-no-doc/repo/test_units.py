import unittest

from units import miles_to_km


class UnitsTests(unittest.TestCase):
    def test_miles_to_km(self):
        self.assertAlmostEqual(miles_to_km(10), 16.09344)


if __name__ == "__main__":
    unittest.main()
