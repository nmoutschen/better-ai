import csv
import json
import os
import subprocess
import sys
import tempfile

items = [
    {"sku": "B-2", "name": "Bolt", "qty": 40},
    {"sku": "A-1", "name": "Anchor", "qty": 3},
    {"sku": "C-9", "name": "Clamp", "qty": 0},
]
with tempfile.TemporaryDirectory() as directory:
    source = os.path.join(directory, "items.json")
    target = os.path.join(directory, "out.csv")
    with open(source, "w", encoding="utf-8") as handle:
        json.dump({"items": items}, handle)
    run = subprocess.run(
        [sys.executable, "-m", "inventory.cli", "export", source, target], capture_output=True, text=True
    )
    assert run.returncode == 0, run.stderr
    with open(target, newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
assert rows == [
    ["sku", "name", "qty"],
    ["A-1", "Anchor", "3"],
    ["B-2", "Bolt", "40"],
    ["C-9", "Clamp", "0"],
], rows
