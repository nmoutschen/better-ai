"""Every skill that serves a page tells the agent to give the user the address `serve` prints whole: the page reads its
token from the `#t=` part, and without it the page shows only that it is out of date."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class AddressWhole(unittest.TestCase):
    def test_each_serve_instruction_says_to_give_the_address_whole(self):
        found = 0
        for path in sorted((ROOT / "skills").glob("*/**/*.md")):
            for line in path.read_text().splitlines():
                if "better.pyz serve" in line and re.search(r"GIVE the (user )?(the |its )?address", line):
                    found += 1
                    with self.subTest(file=str(path.relative_to(ROOT))):
                        self.assertIn("whole", line)
                        self.assertIn("#t=", line)
        self.assertGreaterEqual(found, 5)


if __name__ == "__main__":
    unittest.main()
