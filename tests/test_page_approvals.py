"""The paired session: one token is exchanged once, and a second tab replaces the first only when it pairs. The checks
of the routes and of `link` are in test_page_pairing_v2.py; the approvals themselves are the driver's (test_page_driver_v2.py)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from better_ai.page.approvals import Pairing  # noqa: E402

ORIGIN = "http://localhost:54321"


class PairingTest(unittest.TestCase):
    def test_pairing(self):
        pairing = Pairing(ORIGIN)
        token = pairing.issue()
        with self.assertRaises(ValueError):
            pairing.exchange(token, "http://localhost:54322")
        secret = pairing.exchange(token, ORIGIN)
        self.assertTrue(pairing.valid(secret, ORIGIN))
        self.assertFalse(pairing.valid(secret, "null"))
        with self.assertRaises(ValueError):
            pairing.exchange(token, ORIGIN)
        pairing.issue()
        self.assertTrue(pairing.valid(secret, ORIGIN))  # a token that is not used unpairs nobody


if __name__ == "__main__":
    unittest.main()
