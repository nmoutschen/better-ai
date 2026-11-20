import subprocess
import sys
from pathlib import Path

saved = Path("samples/sales.summary.txt")
saved.unlink(missing_ok=True)
run = subprocess.run([sys.executable, "report.py", "samples/sales.csv"], capture_output=True, text=True)
assert run.returncode == 0, run.stderr
assert run.stdout.splitlines() == ["Orders: 3", "Total: €37.50"], run.stdout
assert saved.exists(), "no samples/sales.summary.txt"
assert saved.read_text().splitlines() == ["Orders: 3", "Total: €37.50"], saved.read_text()
