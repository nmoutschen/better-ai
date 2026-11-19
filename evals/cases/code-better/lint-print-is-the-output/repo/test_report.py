import subprocess
import sys
import unittest


class Report(unittest.TestCase):
    def test_summary(self):
        out = subprocess.run([sys.executable, "report.py", "samples/sales.csv"], capture_output=True, text=True)
        self.assertIn("Orders: 3", out.stdout)


if __name__ == "__main__":
    unittest.main()
