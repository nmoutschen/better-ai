import importer
from importer import FormatError, load

assert load("a.json", '[{"x": 1}]') == [{"x": 1}]
assert load("a.csv", "x\n1\n") == [{"x": "1"}]
assert load("a.json", "[]") == []
for bad in ("{bad", '{"x": 1}', "[1]", '[{"x": 1}, "y"]'):
    try:
        load("a.json", bad)
    except FormatError:
        continue
    raise AssertionError(f"{bad!r} should raise FormatError")
seen = []
importer.PARSERS["json"] = lambda text: seen.append(text) or ["registered"]
assert load("b.json", "[]") == ["registered"] and seen == ["[]"], "load() must reach the JSON parser through PARSERS"
