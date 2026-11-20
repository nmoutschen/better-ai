import datetime
import unittest

import slots


class SlotTests(unittest.TestCase):
    def test_eight_slots_from_six(self):
        found = slots.slots(datetime.date(2026, 5, 4))
        self.assertEqual((len(found), found[0].hour), (8, 18))


if __name__ == "__main__":
    unittest.main()
