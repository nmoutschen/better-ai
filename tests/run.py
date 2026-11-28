"""Run every tests/test_*.py module as its own process, in parallel.

    python3 tests/run.py [--jobs N] [module ...]

Each module runs as `python -I tests/run.py --child <module>`, which loads it the way the full discover run does
and writes its counts as JSON for this process to read.
Failing modules print their whole output; then one summary line and the slowest modules. Exits 1 on any failure.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STUB_DIR = ROOT / "tests" / "fixtures" / "stub-harness"


def stub_env():
    """The environment of every test module: the stub harness first on PATH, as the one a served page finds, and the
    marker that lets `serve` skip the browser."""
    env = dict(os.environ)
    env.update(
        PATH=f"{STUB_DIR}{os.pathsep}{env.get('PATH', '')}", CLAUDECODE="1", BETTER_AI_STUB_HARNESS="1", BROWSER="false"
    )
    return env


def run_module(name):
    start = time.monotonic()
    with tempfile.TemporaryDirectory() as tmp:
        result_file = Path(tmp) / "result.json"
        proc = subprocess.run(
            [sys.executable, "-I", __file__, "--child", name, "--result", str(result_file)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env=stub_env(),
        )
        try:
            result = json.loads(result_file.read_text())
        except (OSError, ValueError):
            result = None  # the child died before it wrote its numbers
    return name, proc.returncode, proc.stdout + proc.stderr, time.monotonic() - start, result


def child(name, result_file):
    """Run one module the way discover imports it and write its counts as JSON."""
    import webbrowser

    def no_browser(*args, **kwargs):
        raise AssertionError("a test opened a real browser")

    webbrowser.open = no_browser
    suite = unittest.TestLoader().discover("tests", pattern=f"{name}.py")
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    counts = {
        "run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "expected_failures": len(result.expectedFailures),
        "unexpected_successes": len(result.unexpectedSuccesses),
    }
    Path(result_file).write_text(json.dumps(counts))
    if suite.countTestCases() == 0:
        print(f"no tests found for {name}")
        return 1
    return 0 if result.wasSuccessful() else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 1, help="modules run at once (default: CPUs)")
    parser.add_argument("--child", help=argparse.SUPPRESS)
    parser.add_argument("--result", help=argparse.SUPPRESS)
    parser.add_argument("modules", nargs="*", help="module names such as test_core (default: all)")
    args = parser.parse_args()
    if args.child:
        return child(args.child, args.result)
    names = args.modules or sorted(p.stem for p in (ROOT / "tests").glob("test_*.py"))
    start = time.monotonic()
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        results = list(pool.map(run_module, names))
    totals = dict.fromkeys(("run", "failures", "errors", "skipped"), 0)
    failed = []
    for name, code, output, _, counts in results:
        for key in totals:
            totals[key] += (counts or {}).get(key, 0)
        if code != 0 or counts is None:
            failed.append(name)
            print(f"===== {name} (exit {code}) =====\n{output}")
    ran, failures, errors, skips = totals.values()
    print(
        f"{ran} tests, {failures} failures, {errors} errors, {skips} skipped, {len(names)} modules "
        f"({len(failed)} failed) in {time.monotonic() - start:.1f}s"
    )
    print("slowest:", ", ".join(f"{n} {s:.1f}s" for n, _, _, s, _ in sorted(results, key=lambda r: -r[3])[:5]))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
