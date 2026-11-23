"""Wrong values for the fuzz tests of the pages' data: each record of a file with one field deleted, one field, inner
key or list item given a wrong value, or one extra field. Shared by the dashboard's and the research board's tests."""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sweep  # noqa: E402

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


def wrong_kind(label: str) -> str:
    """The class of a variant's label for the sample: the wrong value it sets, or `del` or `extra`."""
    return label.split("=", 1)[1] if "=" in label else label.split(" ")[0].split("[")[0]


def field_of(label: str) -> str:
    """The field a variant's label changes, without the record's index."""
    return label.removeprefix("del ").split("[")[0]


def fuzz(test, files, write, survives, wrong=WRONG):
    """The wrong-type loop of a page's tests. `files` is {name: records}; for each file, each variant (a sample unless
    BETTER_AI_SWEEP=full) is written with `write(name, records)`, then `survives(label)` checks what must not raise and
    returns the page's payload; the file is written back as it was. Each variant is a subTest of `test`. Returns the
    payloads, as {"label", "data"}, and how many variants there were before sampling."""
    payloads, total = [], 0
    keys = [lambda v: wrong_kind(v[0]), lambda v: field_of(v[0])]
    for name, records in files.items():
        every = list(variants(records, wrong))
        total += len(every)
        for label, changed in sweep.cases(every, key=keys):
            with test.subTest(f"{name}: {label}"):
                write(name, changed)
                payloads.append({"label": f"{name}: {label}", "data": survives(label)})
        write(name, records)
    return payloads, total


def render(script, payloads, test):
    """Draw `payloads` with node and tests/`script`, which the page's own code runs in; skip `test` without node."""
    node = shutil.which("node")
    if not node:
        test.skipTest("node is not installed")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "payloads.json"
        path.write_text(json.dumps(payloads, allow_nan=False))
        run = subprocess.run([node, str(HERE / script), str(path)], capture_output=True, text=True, timeout=300)
    test.assertEqual(run.returncode, 0, run.stderr[:3000])
