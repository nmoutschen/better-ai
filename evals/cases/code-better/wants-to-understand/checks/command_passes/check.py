from notes import Note

first = Note("first")
first.add_tag("work")
second = Note("second")
assert second.tags == [], second.tags
assert first.tags == ["work"], first.tags
third = Note("third", ["home"])
third.add_tag("weekly")
assert third.tags == ["home", "weekly"], third.tags
