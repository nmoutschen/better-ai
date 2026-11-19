"""Run every check_*.py script and report which failed."""

import pathlib
import subprocess
import sys

failed = []
for script in sorted(pathlib.Path(__file__).parent.glob("check_*.py")):
    result = subprocess.run([sys.executable, script.name], cwd=script.parent)
    if result.returncode:
        failed.append(script.name)
print("FAILED: " + ", ".join(failed) if failed else "all checks passed")
sys.exit(1 if failed else 0)
