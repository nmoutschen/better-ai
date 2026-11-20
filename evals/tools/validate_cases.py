"""Check a skill's cases by replaying scripted runs through the deterministic graders, with no model.

Each case's `replays/good-*.yaml` must pass every deterministic grader and each `bad-*.yaml` must fail
at least one. A run that does nothing must fail one too, unless `case.yaml` sets
`validation.do_nothing_fails_only_by_judge`, and each hidden `command_passes` check must fail on the
untouched repository unless listed under `validation.hidden_checks_pass_untouched`. Top-level judges
are skipped; a judge inside `any_of` is assumed to pass, or to fail when the replay sets `judge: false`.
Replays run in a local temporary directory with this Python on PATH as `python`.

    uv run python -m tools.validate_cases code-better [-v] [CASE_ID ...]
"""

import argparse
import asyncio
import math
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from inspect_ai.model import ChatMessageAssistant
from inspect_ai.tool import ToolCall
from inspect_ai.util._sandbox.local import LocalSandboxEnvironment

from skill_evals.agent import IGNORED_PATHS, READ_TOOL, SHELL_TOOL, START_SCRIPT, WRITE_TOOL
from skill_evals.cases import case_dirs, load_case, replays
from skill_evals.grading.files import Checkout
from skill_evals.grading.judge import NO_JUDGE
from skill_evals.grading.scorer import NOT_APPLICABLE, Grading, grader_keys


class ReplayGrading(Grading):
    """Grading that skips top-level judges and assumes a verdict for judges inside any_of."""

    def __init__(self, repo: Checkout, assumed: bool, actions: list[dict[str, Any]]) -> None:
        """Grade the replayed checkout and its actions as a transcript, assuming `assumed` for nested judges."""
        super().__init__(SimpleNamespace(messages=replay_messages(actions)), repo, NO_JUDGE)  # type: ignore[arg-type]
        self.assumed = assumed

    async def run(self, key: str, spec: dict[str, Any]) -> float:
        """Return the grader's value, with judges skipped or assumed."""
        if spec["type"] == "judge":
            return int(self.assumed) if "." in key else NOT_APPLICABLE
        return await super().run(key, spec)


def replay_messages(actions: list[dict[str, Any]]) -> list[ChatMessageAssistant]:
    """Turn a replay's writes, reads and commands into tool calls, as the agent's transcript would hold them."""
    messages = []
    for number, action in enumerate(actions):
        if "write" in action:
            name, arguments = WRITE_TOOL, {"file_path": action["write"], "content": action["content"]}
        elif "read" in action:
            name, arguments = READ_TOOL, {"file_path": action["read"]}
        else:
            name, arguments = SHELL_TOOL, {"command": action["bash"]}
        call = ToolCall(id=f"replay-{number}", function=name, arguments=arguments)
        messages.append(ChatMessageAssistant(content="", tool_calls=[call]))
    return messages


def put_python_on_path() -> None:
    """Make `python` and `python3` in replayed commands run this interpreter."""
    directory = Path(tempfile.mkdtemp())
    for name in ("python", "python3"):
        (directory / name).symlink_to(sys.executable)
    os.environ["PATH"] = f"{directory}{os.pathsep}{os.environ['PATH']}"


async def play_actions(sandbox_env: LocalSandboxEnvironment, actions: list[dict[str, Any]]) -> None:
    """Carry out a replay's writes and Bash commands; reads change nothing."""
    for action in actions:
        if "write" in action:
            await sandbox_env.write_file(action["write"], action["content"])
        elif "bash" in action:
            await sandbox_env.exec(["bash", "-c", action["bash"]], timeout=60)


def nested_commands(specs: list[dict[str, Any]], prefix: str = "") -> list[tuple[str, dict[str, Any]]]:
    """Return each command_passes grader inside an any_of, with the key the scorer gives it, such as any_of.1."""
    found = []
    for key, spec in zip(grader_keys(specs), specs, strict=True):
        key = f"{prefix}{key}"
        if spec["type"] == "any_of":
            for number, inner in enumerate(spec["graders"], 1):
                if inner["type"] == "command_passes":
                    found.append((f"{key}.{number}", inner))
                elif inner["type"] == "any_of":
                    found += nested_commands([inner], f"{key}.{number}.")
    return found


async def replay(case: dict[str, Any], run: dict[str, Any]) -> tuple[dict[str, float], list[str], dict[str, float]]:
    """Plant the case, play the run, and return each deterministic grader's value, the notes, and the nested ones.

    The nested values are those of the command_passes graders inside any_of, by their scorer keys.
    """
    sandbox_env = LocalSandboxEnvironment()
    try:
        for path, source in case["files"].items():
            await sandbox_env.write_file(path, source.read_bytes())
        started = await sandbox_env.exec(["bash", "-ec", START_SCRIPT, "bash", *IGNORED_PATHS])
        repo = Checkout(sandbox_env, started.stdout.split()[-1], sandbox_env.directory.name)
        await play_actions(sandbox_env, run.get("actions") or [])
        grading = ReplayGrading(repo, run.get("judge", True), run.get("actions") or [])
        values = {}
        for key, spec in zip(grader_keys(case["graders"]), case["graders"], strict=True):
            value = await grading.run(key, spec)
            if not math.isnan(value):
                values[key] = value
        nested = {key: await grading.run(key, spec) for key, spec in nested_commands(case["graders"])}
        return values, repo.notes, nested
    finally:
        sandbox_env.directory.cleanup()


async def validate(directory: Path, verbose: bool) -> list[str]:
    """Return the problems found in one case."""
    case = load_case(directory)
    checks = case.get("validation") or {}
    problems = []
    for name, run in replays(directory).items():
        values, notes, _ = await replay(case, run)
        failed = [key for key, value in values.items() if not value]
        if name.startswith("good") and failed:
            problems.append(f"{name} fails {failed} {notes or ''}")
        elif name.startswith("bad") and not failed:
            problems.append(f"{name} passes every deterministic grader")
        elif name.startswith("bad") and verbose:
            print(f"    {name} fails {failed}")
    values, _, nested = await replay(case, {"actions": [], "reply": ""})
    if all(values.values()) and not checks.get("do_nothing_fails_only_by_judge"):
        problems.append("a do-nothing run passes every deterministic grader")
    allowed = set(checks.get("hidden_checks_pass_untouched") or [])
    for key, value in {**values, **nested}.items():
        if (key.startswith("command_passes") or key in nested) and value and key not in allowed:
            problems.append(f"{key} passes on the untouched repo")
    return problems


def main(argv: list[str] | None = None) -> int:
    """Validate the selected cases and print one line per case; exit 1 on any problem."""
    parser = argparse.ArgumentParser(description="Replay each case's scripted runs through its graders.")
    parser.add_argument("skill")
    parser.add_argument("cases", nargs="*")
    parser.add_argument("-v", "--verbose", action="store_true", help="show which grader fails each bad run")
    args = parser.parse_args(argv)
    try:
        directories = case_dirs(args.skill)
    except ValueError as error:
        print(error)
        return 1
    if unknown := sorted(set(args.cases) - {directory.name for directory in directories}):
        print(f"No case {', '.join(unknown)} in {args.skill!r}")
        return 1
    put_python_on_path()
    ok = True
    for directory in directories:
        if args.cases and directory.name not in args.cases:
            continue
        problems = asyncio.run(validate(directory, args.verbose))
        print(f"{directory.name:26} {'ok' if not problems else 'PROBLEMS'}")
        for problem in problems:
            print("    ", problem)
        ok &= not problems
    print("ALL OK" if ok else "PROBLEMS")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
