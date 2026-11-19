import datetime
import unittest

from export import export_line


class ExportTest(unittest.TestCase):
    def test_line(self):
        order = {"id": 17, "placed": datetime.date(2026, 3, 4), "total": 1999}
        self.assertEqual(export_line(order), "17;04/03/2026;1999")


if __name__ == "__main__":
    unittest.main()
