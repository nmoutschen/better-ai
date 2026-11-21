"""Wrong values for the fuzz tests of the pages' data: each record of a file with one field deleted, one field, inner
key or list item given a wrong value, or one extra field. Shared by the dashboard's and the research board's tests."""

import json

# A list, a nested list, a list of objects, an object, an object holding a list, empty ones, numbers, a boolean, null
# and strings.
WRONG = [[1], [[1]], [{"k": 1}], {"k": 1}, {"k": [1]}, {}, [], 5, -1, 1.5, True, None, "", "x"]
# A line that is not a record, as a file's first line.
RAW_LINES = ["[1]", "null", '"x"', "5", "{", "NaN", '{"id": NaN}', "[" * 5000 + "]" * 5000]


def variants(records, wrong=WRONG):
    """(label, records) pairs: `records` (the lines of one file) each with one change at a time."""
    for index, record in enumerate(records):
        for key, value in record.items():
            deleted = json.loads(json.dumps(records))
            del deleted[index][key]
            yield f"del {key}[{index}]", deleted
            options = [(key,)]
            if isinstance(value, dict):
                options += [(key, inner) for inner in value]
            if isinstance(value, list):
                options += [(key, item) for item in range(len(value))]
            for path in options:
                original = value if len(path) == 1 else value[path[1]]
                for bad in wrong:
                    if bad == original and type(bad) is type(original):
                        continue
                    changed = json.loads(json.dumps(records))
                    target = changed[index][key] if len(path) == 2 else changed[index]
                    target[path[-1]] = bad
                    yield f"{'.'.join(map(str, path))}[{index}]={bad!r}", changed
        extra = json.loads(json.dumps(records))
        extra[index]["extra"] = [1]
        yield f"extra[{index}]", extra
