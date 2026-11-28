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
import webbrowser
from pathlib import Path
from unittest import mock

SRC = Path(__file__).resolve().parents[1] / "src"


# The release's format_cutoff may lie ahead of the clock; tests pin a past one, so "after the cutoff" is never a future
# time. Commands run from source, in this process or in a subprocess, read it from BETTER_AI_CUTOFF.
TEST_CUTOFF = "2026-11-22T00:00:00Z"
os.environ["BETTER_AI_CUTOFF"] = TEST_CUTOFF
# A test never opens a browser: `serve` skips it where the stub harness's marker is set, and in-process `webbrowser.open`
# fails the test that calls it.
os.environ.setdefault("BETTER_AI_STUB_HARNESS", "1")


def _no_browser(*args, **kwargs):
    raise AssertionError("a test opened a real browser")


webbrowser.open = _no_browser
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


# ---------------------------------------------------------------- serving a page in a test

STUB = Path(__file__).resolve().parent / "fixtures" / "stub-harness"


def stub_env(skill: str, **changes: str | None) -> dict[str, str]:
    """The environment of a run that finds the stub harness as the user's own; a value of None removes a variable."""
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "BETTER_PAGE_SESSION")}
    env.update(
        PATH=f"{STUB}{os.pathsep}{env.get('PATH', '')}", CLAUDECODE="1", BETTER_AI_STUB_HARNESS="1", BROWSER="false"
    )
    env["BETTER_AI_SKILL"] = skill
    for key, value in changes.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    return env


def page_headers(secret: str, origin: str | None = None) -> dict[str, str]:
    """What a paired tab sends with each request."""
    headers = {"X-Page-Token": secret, "Sec-Fetch-Site": "same-origin"}
    if origin:
        headers["Origin"] = origin
    return headers


# What `.driver` held when `serve_page` served each unit, by its real path: `stop_page` ends a server from it when the
# unit's folder is already gone, and `leftover_servers` ends what no test stopped.
_SERVED: dict[str, dict] = {}


def _driver_state(unit: Path) -> dict | None:
    import json

    try:
        state = json.loads((Path(unit) / ".driver").read_text())
    except (OSError, ValueError):
        return None
    return state if isinstance(state, dict) else None


def _end(state: dict) -> bool:
    """End a server and its harness, as a harness ends a command; whether the server is gone within five seconds."""
    import signal
    import time

    for pid, kill in ((state.get("server_pid"), os.kill), (state.get("child_pid"), os.killpg)):
        if type(pid) is int and pid > 1 and pid != os.getpid():
            with contextlib.suppress(ProcessLookupError, PermissionError):
                kill(pid, signal.SIGTERM)
    for _ in range(100):
        try:
            os.kill(state.get("server_pid") or 0, 0)
        except (ProcessLookupError, PermissionError, OverflowError):
            return True
        time.sleep(0.05)
    return False


def stop_page(unit: Path) -> None:
    """End the server a test started and wait until it is gone, also after the unit's folder was removed."""
    key = os.path.realpath(unit)
    state = _driver_state(unit) or _SERVED.get(key)
    if state and _end(state):
        _SERVED.pop(key, None)


def leftover_servers() -> list[str]:
    """The units whose server `serve_page` started and no `stop_page` ended; ends them."""
    left = []
    for key, state in list(_SERVED.items()):
        try:
            os.kill(state.get("server_pid") or 0, 0)
            left.append(key)
        except (ProcessLookupError, PermissionError, OverflowError):
            pass
        _end(state)
    _SERVED.clear()
    return left


def serve_page(skill: str, unit: Path, *flags: str, cwd: str | Path | None = None) -> tuple[str, str]:
    """Serve a unit as a caller does and pair a tab as the page does: (the address, ending in "/", and the secret the tab
    sends in X-Page-Token). The server runs in its own session: call `stop_page(unit)` when the test ends."""
    import http.client
    import json
    import re

    done = subprocess.run(
        command("serve", str(unit), "--no-browser", *flags),
        input="",
        capture_output=True,
        text=True,
        cwd=cwd,
        env=stub_env(skill),
        timeout=60,
        check=False,
    )
    link = re.search(r"at (http://\S+)", done.stdout)
    if done.returncode != 0 or not link:
        raise AssertionError(f"serve failed: {done.stdout}{done.stderr}")
    folder = Path(cwd or ".") / unit
    state = _driver_state(folder)
    if state:
        _SERVED[os.path.realpath(folder)] = state
    address, token = link.group(1).split("#p=")
    host = address.split("//")[1].rstrip("/")
    connection = http.client.HTTPConnection(host, timeout=10)
    connection.request(
        "POST",
        "/pair",
        json.dumps({"token": token}),
        {"Content-Type": "application/json", "Origin": f"http://{host}", "Sec-Fetch-Site": "same-origin"},
    )
    reply = connection.getresponse()
    body = reply.read()
    connection.close()
    if reply.status != 200:
        raise AssertionError(f"pairing failed: {reply.status} {body!r}")
    return address, json.loads(body)["secret"]
