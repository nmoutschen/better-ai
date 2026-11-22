"""Build the real better.pyz files for a test.

`build_into(tmp)` runs tools/build.py on the repository's src/ and writes the files under `tmp`, as
`tmp/<skill>/scripts/better.pyz`. It returns {skill: path}. The build needs Python 3.12 or later, so when the
test runs on an older Python the helper looks for a newer interpreter on PATH and skips the test if there is none.
"""

import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "tools" / "build.py"
CANDIDATES = ["python3.15", "python3.14", "python3.13", "python3.12", "python3"]


def build_python() -> str:
    """An interpreter that can run tools/build.py (Python 3.12 or later), or a skipped test."""
    if sys.version_info >= (3, 12):
        return sys.executable
    for name in CANDIDATES:
        found = shutil.which(name)
        if found and subprocess.run([found, "-c", "import sys; sys.exit(sys.version_info < (3, 12))"]).returncode == 0:
            return found
    raise unittest.SkipTest("tools/build.py needs Python 3.12 or later and none is on PATH")


def build_into(tmp, src=None) -> dict[str, Path]:
    """Build every skill's .pyz into `tmp`; `src` is the folder holding better_ai/ (default: the repository's)."""
    out = Path(tmp)
    cmd = [build_python(), "-I", str(BUILD), "--skills", str(out), "--src", str(src or ROOT / "src")]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"build failed: {result.stderr}")
    names = json.loads(((Path(src) if src else ROOT / "src") / "better_ai" / "skills.json").read_text())["skills"]
    return {skill: out / skill / "scripts" / "better.pyz" for skill in names}
