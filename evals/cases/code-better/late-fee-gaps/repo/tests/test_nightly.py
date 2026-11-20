import datetime
import unittest

from nightly import next_open_day, reminder_text


class NightlyTest(unittest.TestCase):
    def test_next_open_day_skips_closed(self):
        closed = {datetime.date(2026, 3, 8)}
        self.assertEqual(next_open_day(datetime.date(2026, 3, 8), closed), datetime.date(2026, 3, 9))

    def test_reminder_names_title_and_due_date(self):
        text = reminder_text({"member": "Ana", "title": "Dune", "due": "2026-03-06"})
        self.assertEqual(text, 'Dear Ana, "Dune" was due on 2026-03-06. Please return it.')


if __name__ == "__main__":
    unittest.main()
