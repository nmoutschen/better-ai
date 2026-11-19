import json
import os
import subprocess
import sys
import tempfile

with tempfile.TemporaryDirectory() as directory:
    path = os.path.join(directory, "in.csv")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("date,item,amount\n2026-03-31,ink,900\n2026-04-01,desk,25000\n2026-04-09,lamp,4200\n")
    run = subprocess.run(
        [sys.executable, "report.py", path, "--since", "2026-04-01", "--json"], capture_output=True, text=True
    )
assert run.returncode == 0, run.stderr
rows = json.loads(run.stdout)
# Amounts may come out as numbers or strings; the dates and order must match.
normalised = [{key: str(value) for key, value in row.items()} for row in rows]
assert normalised == [
    {"date": "2026-04-01", "item": "desk", "amount": "25000"},
    {"date": "2026-04-09", "item": "lamp", "amount": "4200"},
], rows
