import unittest

from peaks import peak_dbfs


class PeakTest(unittest.TestCase):
    def test_applause_recording(self):
        # Reference value read from the studio meter for this recording.
        self.assertEqual(peak_dbfs("fixtures/applause.wav"), -3.2)


if __name__ == "__main__":
    unittest.main()
