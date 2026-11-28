"""tests/run.py ends and reports every process a test module leaves running, and a leaked process that holds the
module's output does not hang the run (D20, D22, lesson L6)."""

import importlib.util
import os
import signal
import subprocess
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

RUN = Path(__file__).resolve().parent / "run.py"
LEAK = textwrap.dedent(
    """
    import subprocess
    import sys
    import unittest


    class Leak(unittest.TestCase):
        def test_leaves_a_detached_process(self):
            child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"], start_new_session=True)
            open(__file__ + ".pid", "w").write(str(child.pid))
    """
)


def load_run():
    spec = importlib.util.spec_from_file_location("run_under_test", RUN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def alive(pid, wait=5.0):
    """Whether pid still runs after up to `wait` s; an ended process can stay a zombie until init reaps it."""
    end = time.monotonic() + wait
    while True:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
        if state.startswith("Z") or time.monotonic() > end:
            return not state.startswith("Z")
        time.sleep(0.1)


class RunGuardTest(unittest.TestCase):
    def test_a_module_that_leaves_a_process_fails_and_the_process_is_ended(self):
        run = load_run()
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "test_leak.py").write_text(LEAK)
            started = time.monotonic()
            name, code, output, _, counts = run.run_module("test_leak", tests_dir=Path(tmp))
            pid = int((Path(tmp) / "test_leak.py.pid").read_text())
            try:
                self.assertLess(time.monotonic() - started, 60, "the leaked process held the run")
                self.assertNotEqual(code, 0, output)
                self.assertIn("left processes running", output)
                self.assertIn(str(pid), output)
                self.assertGreaterEqual(counts["errors"], 1)
                self.assertFalse(alive(pid))
            finally:
                if alive(pid):
                    os.kill(pid, signal.SIGKILL)
