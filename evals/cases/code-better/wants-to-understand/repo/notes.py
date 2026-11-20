"""Notes with tags."""


class Note:
    """A note with a title and a list of tags."""

    def __init__(self, title, tags=[]):
        self.title = title
        self.tags = tags

    def add_tag(self, tag):
        """Add tag unless the note already has it."""
        if tag not in self.tags:
            self.tags.append(tag)
