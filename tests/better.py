"""Run the `better.pyz` command from the source in `src/`, as the tests do before any `.pyz` exists.

    from better import run
    done = run("code-better", "check", ".code/my-change", cwd=repo)

`run` starts `python -I` with `src/` on `sys.path` and BETTER_AI_SKILL set, so it behaves as the built command of that
skill (the hash is "source"). Tests that need a real `.pyz` build one with `tools/build.py` into a temporary folder.
"""

from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

SRC = Path(__file__).resolve().parents[1] / "src"


# The release's format_cutoff may lie ahead of the clock; tests pin a past one, so "after the cutoff" is never a future
# time. Commands run from source, in this process or in a subprocess, read it from BETTER_AI_CUTOFF.
TEST_CUTOFF = "2026-11-22T00:00:00Z"
os.environ["BETTER_AI_CUTOFF"] = TEST_CUTOFF
AFTER_CUTOFF = "2026-11-22T00:01:00Z"
_BOOT = "import sys; sys.path.insert(0, sys.argv.pop(1)); from better_ai._entry import main; sys.exit(main())"


def command(*args: str) -> list[str]:
    return [sys.executable, "-I", "-c", _BOOT, str(SRC), *args]


def run(
    skill: str,
    *args: str,
    stdin: str | None = None,
    cwd: str | Path | None = None,
    env: dict[str, str] | None = None,
    python: str | None = None,
) -> subprocess.CompletedProcess:
    """The command's CompletedProcess (text mode, captured). `env` adds to the inherited environment; `python` picks
    another interpreter."""
    full = {**os.environ, "BETTER_AI_SKILL": skill, **(env or {})}
    argv = command(*args)
    if python:
        argv[0] = python
    return subprocess.run(
        argv, input=stdin, capture_output=True, text=True, cwd=cwd, env=full, check=False, timeout=120
    )


def call(
    skill: str,
    *args: str | Path,
    stdin: str | None = None,
    cwd: str | Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """The same command as `run`, in this process: `cli.main` with the same environment and the result fields of `run`
    (`returncode`, `stdout`, `stderr`). Several times faster, for the many cases a test loops over; keep one `run` for
    what only a process shows, such as the exit code of a crash."""
    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))
    from better_ai import cli

    argv = [str(a) for a in args]
    out, err = io.StringIO(), io.StringIO()
    here = os.getcwd()
    try:
        with (
            mock.patch.dict(os.environ, {"BETTER_AI_SKILL": skill, **(env or {})}),
            contextlib.redirect_stdout(out),
            contextlib.redirect_stderr(err),
        ):
            if cwd is not None:
                os.chdir(cwd)
            code = cli.main(argv, stdin=io.StringIO(stdin or ""))
    finally:
        os.chdir(here)
    return subprocess.CompletedProcess(argv, code, out.getvalue(), err.getvalue())
