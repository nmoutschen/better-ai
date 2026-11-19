import subprocess
import sys

run = subprocess.run([sys.executable, "report.py", "samples/sales.csv"], capture_output=True, text=True)
assert run.returncode == 0, run.stderr
assert run.stdout.splitlines() == ["Orders: 3", "Total: €37.50", "Average: €12.50"], run.stdout
