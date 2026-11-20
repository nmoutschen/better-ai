"""In-memory notes for the help desk."""

NOTES = []


def add_note(text):
    """Store a note and return it."""
    note = {"text": text}
    NOTES.append(note)
    return note
