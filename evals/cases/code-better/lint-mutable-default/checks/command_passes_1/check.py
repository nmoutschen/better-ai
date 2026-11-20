import notes

first = notes.add_note("printer jam")
assert first["tags"] == [], first
first["tags"].append("hardware")
second = notes.add_note("password reset")
assert second["tags"] == [], second
third = notes.add_note("vpn down", ["network"])
assert third["tags"] == ["network"], third
