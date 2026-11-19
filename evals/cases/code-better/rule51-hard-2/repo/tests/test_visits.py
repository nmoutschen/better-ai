import unittest

from visits import monthly_summary, summary_line

# name, visit lengths in minutes, expected summary line
CASES = [
    ("Ana", [30, 45], "Ana: 2 visits, avg 37.5 min"),
    ("Ben", [60, 20, 40], "Ben: 3 visits, avg 40.0 min"),
]


class SummaryLineTest(unittest.TestCase):
    def test_cases(self):
        for name, minutes, expected in CASES:
            with self.subTest(name=name):
                self.assertEqual(summary_line(name, minutes), expected)

    def test_monthly_summary_sorts_by_name(self):
        summary = monthly_summary({"Ben": [60, 20, 40], "Ana": [30, 45]})
        self.assertEqual(summary.splitlines()[0], "Ana: 2 visits, avg 37.5 min")


if __name__ == "__main__":
    unittest.main()
