import unittest

from durations import format_duration, parse_duration


class DurationTest(unittest.TestCase):
    def test_hours(self):
        self.assertEqual(parse_duration("2h"), 120)

    def test_minutes(self):
        self.assertEqual(parse_duration("45m"), 45)

    def test_format(self):
        self.assertEqual(format_duration(90), "1h30m")


if __name__ == "__main__":
    unittest.main()
