"""Run every tests/test_*.py module as its own process, in parallel.

    python3 tests/run.py [--jobs N] [module ...]

Each module runs as `python -I -m unittest discover -s tests -p <module>.py`, the way the full discover run imports it.
Failing modules print their whole output; then one summary line and the slowest modules. Exits 1 on any failure.
"""

import argparse
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_module(name):
    start = time.monotonic()
    proc = subprocess.run(
        [sys.executable, "-I", "-m", "unittest", "discover", "-s", "tests", "-p", f"{name}.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return name, proc.returncode, proc.stdout + proc.stderr, time.monotonic() - start


def counts(output):
    """Tests run, failures, errors and skips from unittest's closing lines."""
    ran = re.search(r"^Ran (\d+) tests? in", output, re.M)
    failed = re.search(r"^(?:FAILED|OK)(?: \((.*)\))?$", output, re.M)
    found = dict(re.findall(r"(\w+)=(\d+)", failed.group(1) or "")) if failed else {}
    return (int(ran.group(1)) if ran else 0,) + tuple(int(found.get(k, 0)) for k in ("failures", "errors", "skipped"))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 1, help="modules run at once (default: CPUs)")
    parser.add_argument("modules", nargs="*", help="module names such as test_core (default: all)")
    args = parser.parse_args()
    names = args.modules or sorted(p.stem for p in (ROOT / "tests").glob("test_*.py"))
    start = time.monotonic()
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        results = list(pool.map(run_module, names))
    totals = [0, 0, 0, 0]
    failed = []
    for name, code, output, _ in results:
        ran, *rest = counts(output)
        for i, n in enumerate([ran, *rest]):
            totals[i] += n
        if code != 0 or not ran:
            failed.append(name)
            print(f"===== {name} (exit {code}) =====\n{output}")
    ran, failures, errors, skips = totals
    print(
        f"{ran} tests, {failures} failures, {errors} errors, {skips} skipped, {len(names)} modules "
        f"({len(failed)} failed) in {time.monotonic() - start:.1f}s"
    )
    print("slowest:", ", ".join(f"{n} {s:.1f}s" for n, _, _, s in sorted(results, key=lambda r: -r[3])[:5]))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
