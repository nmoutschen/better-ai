#!/usr/bin/env python3
"""Run each committed skills/<skill>/scripts/better.pyz as an agent would, with `python -I`.

    python3 -I tools/smoke.py [--skills DIR] [--src DIR] [--fixtures DIR] [SKILL ...]

For each skill the runner makes a fresh git repository in a temporary folder and runs, in order: `--help` (its first
line must be `better.pyz <skill> <hash>` with the hash from the .pyz's own _build.json), then the steps of
tests/fixtures/units/<skill>/smoke.json (create, add, set, check, render, serve --no-browser --once, run with the
stub harness of tests/fixtures/stub-harness first on PATH), then the steps listed as `worktree_steps` from a second git worktree of the same repository, such as an `add` into the main
checkout's unit. tests/fixtures/units/README.md says what a fixture holds.

Runs on every Python the project supports (3.10 and later) with the standard library only. Exit 0 when every step
of every skill passed, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STEP_TIMEOUT = 60
STUB_DIR = ROOT / "tests" / "fixtures" / "stub-harness"


def stub_env() -> dict[str, str]:
    """The environment of a run with the stub harness: it is found first on PATH, and the marker lets `serve` skip the
    browser."""
    env = dict(os.environ)
    env.update(PATH=f"{STUB_DIR}{os.pathsep}{env.get('PATH', '')}", CLAUDECODE="1", BETTER_AI_STUB_HARNESS="1")
    return env


def skill_names(src: Path) -> list[str]:
    return list(json.loads((src / "better_ai" / "skills.json").read_text())["skills"])


def git(cwd: Path, *args: str) -> None:
    cmd = ["git", "-c", "user.name=smoke", "-c", "user.email=smoke@example.com", *args]
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True)


def step_input(step: dict, fixture: Path, repo: Path) -> tuple[list[str], str | None]:
    """A fixture step's arguments, with `{repo}` filled in, and its stdin."""
    stdin = step.get("stdin")
    if "stdin_file" in step:
        stdin = (fixture / step["stdin_file"]).read_text()
    return [a.replace("{repo}", str(repo)) for a in step["args"]], stdin


def place_repo_files(spec: dict, fixture: Path, repo: Path) -> None:
    """Copy the fixture's `repo_files` into the repository."""
    for target, source in (spec.get("repo_files") or {}).items():
        (repo / target).parent.mkdir(parents=True, exist_ok=True)
        (repo / target).write_bytes((fixture / source).read_bytes())


def run_step(pyz: Path, step: dict, cwd: Path, fixture: Path, repo: Path) -> str | None:
    """Run one fixture step; return what went wrong, or None."""
    step_args, stdin = step_input(step, fixture, repo)
    args = [sys.executable, "-I", str(pyz), *step_args]
    label = " ".join(step_args)
    if step.get("serve"):
        return run_serve(args, cwd, label)
    try:
        result = subprocess.run(
            args, cwd=cwd, input=stdin, capture_output=True, text=True, timeout=STEP_TIMEOUT, env=stub_env()
        )
    except subprocess.TimeoutExpired:
        return f"{label}: no answer in {STEP_TIMEOUT}s"
    expected = step.get("exit", 0)
    if result.returncode != expected:
        return f"{label}: exit {result.returncode}, expected {expected}: {(result.stderr or result.stdout).strip()}"
    pattern = step.get("stdout_matches")
    if pattern and not re.search(pattern, result.stdout):
        return f"{label}: stdout does not match {pattern!r}: {result.stdout.strip()[:200]}"
    return None


def run_serve(args: list[str], cwd: Path, label: str) -> str | None:
    """`serve --no-browser --once`: the first line says `driver: on`, the second holds the address; fetch it once and the
    server, which went on in its own session, exits."""
    proc = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=stub_env())
    try:
        first = proc.stdout.readline().strip()
        if not first.startswith("driver: on "):
            return f"{label}: first line {first!r}; stderr: {proc.stderr.read().strip()[:200]}"
        found = re.search(r"https?://\S+", proc.stdout.readline())
        if found is None:
            return f"{label}: printed no URL; stderr: {proc.stderr.read().strip()[:200]}"
        url = found.group(0)
        if proc.wait(timeout=10) != 0:
            return f"{label}: exit {proc.returncode}: {proc.stderr.read().strip()[:200]}"
        with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310
            if response.status != 200:
                return f"{label}: {url} answered {response.status}"
        unit = cwd / next(a for a in args[args.index("serve") + 1 :] if not a.startswith("-"))
        for _ in range(100):  # --once: the server ends itself after that one request
            if not (unit / ".server").exists():
                return None
            time.sleep(0.1)
        return f"{label}: the server did not exit after one request"
    except Exception as err:  # a failed fetch or a wait that timed out is a failed step, not a crash
        return f"{label}: {type(err).__name__}: {err}"
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()


REQUIRED_VERBS = ("create", "add", "set", "check", "render")


def offered_verbs(help_text: str) -> set[str] | None:
    """The verbs a better.pyz lists under `verbs:` in its --help, or None when it lists none (then every verb is asked)."""
    if "verbs:" not in help_text:
        return None
    return set(re.findall(r"^    ([a-z]+) ", help_text.split("verbs:", 1)[1], re.M)) or None


def coverage_problems(spec: dict, offered: set[str] | None = None) -> list[str]:
    """S41: the fixture must exercise create, add, set, check, render (when the skill offers it, as `offered`, the verbs
    of its --help, says), serve and an add from a second worktree."""
    steps = spec.get("steps", [])
    verbs = {step["args"][0] for step in steps if step.get("args")}
    required = [v for v in REQUIRED_VERBS if offered is None or v != "render" or v in offered]
    missing = [v for v in required if v not in verbs]
    if not any(step.get("serve") for step in steps):
        missing.append('serve (a step with "serve": true)')
    if not any(step.get("args", [""])[0] == "add" for step in spec.get("worktree_steps", [])):
        missing.append("an add in worktree_steps")
    return [f"fixture does not cover: {', '.join(missing)}"] if missing else []


def smoke_skill(skill: str, skills: Path, fixtures: Path) -> list[str]:
    pyz = skills / skill / "scripts" / "better.pyz"
    if not pyz.is_file():
        return [f"{skill}: {pyz} is missing: run python3 tools/build.py"]
    fixture = fixtures / skill
    spec_path = fixture / "smoke.json"
    if not spec_path.is_file():
        return [f"{skill}: no fixture unit: add {spec_path}"]
    spec = json.loads(spec_path.read_text())
    try:
        info = json.loads(zipfile.ZipFile(pyz).read("better_ai/_build.json"))
    except (OSError, KeyError, ValueError, zipfile.BadZipFile) as err:
        return [f"{skill}: {pyz}: no readable better_ai/_build.json ({err})"]
    help_run = subprocess.run(
        [sys.executable, "-I", str(pyz), "--help"], capture_output=True, text=True, timeout=STEP_TIMEOUT
    )
    first = help_run.stdout.splitlines()[0] if help_run.stdout else ""
    problems: list[str] = [f"{skill}: {p}" for p in coverage_problems(spec, offered_verbs(help_run.stdout))]
    if help_run.returncode != 0 or first != f"better.pyz {info['skill']} {info['hash']}":
        problems.append(f"{skill}: --help: exit {help_run.returncode}, first line {first!r}")
    with tempfile.TemporaryDirectory(prefix="better-smoke-") as scratch:
        repo = Path(scratch) / "repo"
        repo.mkdir()
        git(repo, "init", "-q", "-b", "main")
        place_repo_files(spec, fixture, repo)
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "--allow-empty", "-m", "start")
        for step in spec.get("steps", []):
            problem = run_step(pyz, step, repo, fixture, repo)
            if problem:
                problems.append(f"{skill}: {problem}")
                break
        worktree_steps = spec.get("worktree_steps", [])
        if worktree_steps and not problems:
            other = Path(scratch) / "second"
            git(repo, "worktree", "add", "-q", "-b", "smoke-second", str(other))
            for step in worktree_steps:
                problem = run_step(pyz, step, other, fixture, repo)
                if problem:
                    problems.append(f"{skill}: second worktree: {problem}")
                    break
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="smoke.py", description="Run each committed better.pyz against its fixture.")
    parser.add_argument("skill", nargs="*", help="skills to run (default: every skill in skills.json)")
    parser.add_argument("--src", type=Path, default=ROOT / "src")
    parser.add_argument("--skills", type=Path, default=ROOT / "skills")
    parser.add_argument("--fixtures", type=Path, default=ROOT / "tests" / "fixtures" / "units")
    args = parser.parse_args(argv)
    failed = False
    for skill in args.skill or skill_names(args.src):
        problems = smoke_skill(skill, args.skills, args.fixtures)
        for problem in problems:
            print(f"smoke: {problem}", file=sys.stderr)
        print(f"{skill}: {'FAILED' if problems else 'ok'}")
        failed = failed or bool(problems)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
