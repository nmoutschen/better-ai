import unittest

import notes


class AddNote(unittest.TestCase):
    def test_returns_the_note(self):
        self.assertEqual(notes.add_note("printer jam")["text"], "printer jam")


if __name__ == "__main__":
    unittest.main()
