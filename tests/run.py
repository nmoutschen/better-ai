"""Run every tests/test_*.py module as its own process, in parallel.

    python3 tests/run.py [--jobs N] [module ...]

Each module runs as `python -I tests/run.py --child <module>`, which loads it the way the full discover run does
and writes its counts as JSON for this process to read.
Failing modules print their whole output; then one summary line and the slowest modules. Exits 1 on any failure.
"""

import argparse
import contextlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STUB_DIR = ROOT / "tests" / "fixtures" / "stub-harness"
MARK = "BETTER_AI_TEST_RUN"  # every process a module starts inherits it, so the ones left afterwards can be found
MODULE_TIMEOUT = 900


def stub_env():
    """The environment of every test module: the stub harness first on PATH, as the one a served page finds, and the
    marker that lets `serve` skip the browser."""
    env = dict(os.environ)
    env.update(
        PATH=f"{STUB_DIR}{os.pathsep}{env.get('PATH', '')}", CLAUDECODE="1", BETTER_AI_STUB_HARNESS="1", BROWSER="false"
    )
    return env


def marked(token):
    """The pids of processes whose environment holds MARK=token, other than this one: /proc on Linux, `ps -E` on macOS.
    macOS hides the environment of its protected system programs, such as /bin/sleep, so those are not found there;
    every Python or Node process a test starts, such as a page server or the stub harness, is."""
    entry = f"{MARK}={token}"
    found = set()
    proc = Path("/proc")
    if proc.is_dir():
        for folder in proc.iterdir():
            try:
                if folder.name.isdigit() and entry.encode() in (folder / "environ").read_bytes().split(b"\0"):
                    found.add(int(folder.name))
            except OSError:
                pass
    else:
        listed = subprocess.run(["ps", "-E", "-ww", "-A", "-o", "pid=,command="], capture_output=True, text=True)
        for line in listed.stdout.splitlines():
            pid, _, rest = line.strip().partition(" ")
            if pid.isdigit() and entry in rest.split():
                found.add(int(pid))
    found.discard(os.getpid())
    return sorted(found)


def end_marked(token):
    """End every process left with this module's mark; return their pids."""
    left = marked(token)
    for pid in left:
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.kill(pid, signal.SIGKILL)
    return left


def run_module(name, tests_dir=None):
    start = time.monotonic()
    token = uuid.uuid4().hex
    tests_dir = Path(tests_dir or ROOT / "tests")
    with tempfile.TemporaryDirectory() as tmp:
        result_file, output_file = Path(tmp) / "result.json", Path(tmp) / "output.txt"
        command = [
            sys.executable,
            "-I",
            __file__,
            "--child",
            name,
            "--result",
            str(result_file),
            "--dir",
            str(tests_dir),
        ]
        # Output goes to a file, not a pipe: a process the module leaves behind cannot hold the run open.
        with open(output_file, "w") as output:
            child_process = subprocess.Popen(
                command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT, env={**stub_env(), MARK: token}
            )
            try:
                code = child_process.wait(timeout=MODULE_TIMEOUT)
            except subprocess.TimeoutExpired:
                child_process.kill()
                code = child_process.wait()
                output.write(f"\nthe module ran past {MODULE_TIMEOUT} s and was ended\n")
        left = end_marked(token)
        text = output_file.read_text(errors="replace")
        try:
            result = json.loads(result_file.read_text())
        except (OSError, ValueError):
            result = None  # the child died before it wrote its numbers
    if left:
        text += f"\nthe module left processes running, now ended: {', '.join(map(str, left))}\n"
        code = code or 1
        if result is not None:
            result["errors"] = result.get("errors", 0) + 1
    return name, code, text, time.monotonic() - start, result


def child(name, result_file, tests_dir):
    """Run one module the way discover imports it and write its counts as JSON."""
    import webbrowser

    def no_browser(*args, **kwargs):
        raise AssertionError("a test opened a real browser")

    webbrowser.open = no_browser
    suite = unittest.TestLoader().discover(str(tests_dir), pattern=f"{name}.py")
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
    counts = {
        "run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "expected_failures": len(result.expectedFailures),
        "unexpected_successes": len(result.unexpectedSuccesses),
    }
    helpers = sys.modules.get("better")
    left = helpers.leftover_servers() if helpers else []
    for unit in left:
        print(f"a test left the server of {unit} running")
    if left:
        counts["errors"] += 1
    Path(result_file).write_text(json.dumps(counts))
    if suite.countTestCases() == 0:
        print(f"no tests found for {name}")
        return 1
    return 0 if result.wasSuccessful() and not left else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 1, help="modules run at once (default: CPUs)")
    parser.add_argument("--child", help=argparse.SUPPRESS)
    parser.add_argument("--result", help=argparse.SUPPRESS)
    parser.add_argument("--dir", help=argparse.SUPPRESS)
    parser.add_argument("modules", nargs="*", help="module names such as test_core (default: all)")
    args = parser.parse_args()
    if args.child:
        return child(args.child, args.result, args.dir or ROOT / "tests")
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
