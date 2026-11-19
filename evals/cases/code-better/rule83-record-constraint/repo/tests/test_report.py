import io
import unittest
from contextlib import redirect_stdout

from report import load_rows, main


class ReportTest(unittest.TestCase):
    def test_load_rows_converts_amounts(self):
        rows = load_rows("data/expenses.csv")
        self.assertEqual(rows[0], {"date": "2026-01-14", "item": "paper", "amount": 1250})

    def test_prints_table(self):
        output = io.StringIO()
        with redirect_stdout(output):
            main(["data/expenses.csv"])
        self.assertIn("chairs", output.getvalue())


if __name__ == "__main__":
    unittest.main()
