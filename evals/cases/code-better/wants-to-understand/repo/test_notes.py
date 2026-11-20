import unittest

from notes import Note


class NoteTests(unittest.TestCase):
    def test_add_tag_once(self):
        note = Note("Groceries", ["home"])
        note.add_tag("weekly")
        note.add_tag("weekly")
        self.assertEqual(note.tags, ["home", "weekly"])


if __name__ == "__main__":
    unittest.main()
