"""Run the `better.pyz` command from the source in `src/`, as the tests do before any `.pyz` exists.

    from better import run
    done = run("code-better", "check", ".code/my-change", cwd=repo)

`run` starts `python -I` with `src/` on `sys.path` and BETTER_AI_SKILL set, so it behaves as the built command of that
skill (the hash is "source"). Tests that need a real `.pyz` build one with `tools/build.py` into a temporary folder.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
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
