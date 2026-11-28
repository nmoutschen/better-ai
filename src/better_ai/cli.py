"""The command line of `better.pyz`: one entry for every skill, with a registry the other modules add verbs to.

    python3 <skill dir>/scripts/better.pyz <verb> ...

`main` dispatches a verb of the running skill. A module adds a verb with `@verb(...)`:

    @verb("check", help="...", arguments=lambda parser: parser.add_argument("unit"))
    def check(args, run):
        ...
        return 0

`arguments` adds the verb's arguments to its argparse parser; the function gets the parsed `args` and a `Run` (the skill,
the build info, `out`/`err` and the stdin text) and returns the exit code (None is 0). It may raise `Refused` (exit 1:
nothing was written), `Busy` (4) or `TimedOut` (3); the message is printed as `<skill>: <message>`. A verb for one skill
only names it: `@verb(..., skills=("show-better",))`. The shared modules (`records`, `page`) and the skill's package
register their verbs when they are imported, which `load` does for the running skill.

Exit codes: 0 done, 1 refused or invalid (nothing written), 2 usage error (argparse), 3 `serve` found the page already
served, 4 busy (the file changed during the command: run it again; or a chat agent's write on a driven unit), 5 internal error. An internal error is one line,
`bug in better.pyz <skill> <hash>: <what> ...; set BETTER_AI_TRACEBACK=1 for the full trace`, and the full traceback
when that variable is 1.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path
from typing import Any

from . import paths, resources, schema
from ._entry import report_bug
from .paths import Refused, Unit
from .skill import Skill

EXIT_DONE, EXIT_REFUSED, EXIT_USAGE, EXIT_TIMEOUT, EXIT_BUSY, EXIT_BUG = 0, 1, 2, 3, 4, 5
SHARED_VERB_MODULES = ("records", "page")  # imported if present; each registers its verbs


class Busy(Exception):
    """The file changed while the command worked; nothing was written: run it again (exit 4)."""


class TimedOut(Exception):
    """A command found nothing in time (exit 3)."""


@dataclass
class Run:
    """What a verb is given besides its arguments."""

    skill: Skill
    info: resources.BuildInfo
    stdin: Any = None  # a text stream, read with `stdin_text`
    stdout: Any = field(default=None)
    stderr: Any = field(default=None)
    detach: bool = False  # set by the real entry point: `serve` may then fork its server into the background

    def out(self, text: str = "") -> None:
        print(text, file=self.stdout or sys.stdout, flush=True)  # a served page's address must reach a reader at once

    def err(self, text: str) -> None:
        print(text, file=self.stderr or sys.stderr)

    def stdin_text(self) -> str:
        return (self.stdin or sys.stdin).read()

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Verb:
    name: str
    help: str
    run: Callable[[argparse.Namespace, Run], int | None]
    arguments: Callable[[argparse.ArgumentParser], None] | None = None
    skills: tuple[str, ...] | None = None  # the skills that have it; None for every skill
    machine_output: bool = False  # its output is read by a program: no notice may be printed on stdout


VERBS: list[Verb] = []
# Functions `hook(args, run, code)` that run after every verb, with its exit code.
AFTER_VERB: list[Callable[[argparse.Namespace, Run, int], None]] = []
# Functions `hook(args, run) -> int | None` that run before every verb; one that returns an exit code ends the command
# with it. A module adds its own at import time (the page's check that a chat agent keeps off a driven unit).
BEFORE_VERB: list[Callable[[argparse.Namespace, Run], int | None]] = []
SHARED_PACKAGES = {"page", "schemas"}  # packages under better_ai/ that every skill shares; every other one is a skill


def verb(
    name: str,
    *,
    help: str,
    arguments: Callable[[argparse.ArgumentParser], None] | None = None,
    skills: tuple[str, ...] | None = None,
    machine_output: bool = False,
):
    """Register a verb. A name registered twice for the same skill is a bug in the source."""

    def register(function):
        part = (getattr(function, "__module__", "") or "").split(".")
        if skills is None and len(part) > 2 and part[0] == "better_ai" and part[1] not in SHARED_PACKAGES:
            raise ValueError(f"verb {name!r} comes from the skill package {part[1]!r}: name its skill in skills=")
        for old in VERBS:
            if old.name == name and (old.skills is None or skills is None or set(old.skills) & set(skills)):
                raise ValueError(f"verb {name!r} is registered twice")
        VERBS.append(Verb(name, help, function, arguments, skills, machine_output))
        return function

    return register


def _verbs_of(skill: Skill) -> list[Verb]:
    chosen = [v for v in VERBS if v.skills is None or skill.name in v.skills]
    return sorted(chosen, key=lambda v: v.name)


def load(info: resources.BuildInfo) -> Skill:
    """Import the skill package and the shared verb modules, so every verb is registered; the skill package's `SKILL`."""
    module = resources.skill_package(info.package)
    for name in SHARED_VERB_MODULES:
        try:
            import_module(f"{resources.PACKAGE}.{name}")
        except ModuleNotFoundError as error:  # a module another task adds; any other missing module is a bug
            if error.name != f"{resources.PACKAGE}.{name}":
                raise
    return module.SKILL


def _parser(skill: Skill, info: resources.BuildInfo) -> argparse.ArgumentParser:
    header = f"better.pyz {skill.name} {info.hash}"

    class Parser(argparse.ArgumentParser):
        def format_help(self) -> str:
            return f"{header}\n\n{super().format_help()}"

    parser = Parser(prog="better.pyz", description=f"The commands of the {skill.name} skill.")
    commands = parser.add_subparsers(dest="verb", metavar="<verb>", required=True, parser_class=Parser, title="verbs")
    for entry in _verbs_of(skill):
        sub = commands.add_parser(entry.name, help=entry.help, description=entry.help)
        sub.set_defaults(_verb=entry)
        if entry.arguments:
            entry.arguments(sub)
    return parser


def main(argv: list[str] | None = None, *, stdin: Any = None, detach: bool = False) -> int:
    """Run one command and return its exit code. Whatever a verb raises that it did not mean to is an internal error."""
    for stream in (sys.stdout, sys.stderr):  # a value that is not text prints escaped, never as a failure
        with contextlib.suppress(Exception):
            stream.reconfigure(errors="backslashreplace")
    skill_name, hash = "unknown", "unknown"
    try:
        try:
            info = resources.build_info()
        except LookupError as error:
            print(f"better.pyz: {error}", file=sys.stderr)
            return EXIT_USAGE
        skill_name, hash = info.skill, info.hash
        skill = load(info)
        parser = _parser(skill, info)
        args = parser.parse_args(argv if argv is not None else sys.argv[1:])
        run = Run(skill, info, stdin, detach=detach)
        try:
            code = next((c for c in (hook(args, run) for hook in BEFORE_VERB) if c is not None), None)
            if code is None:
                code = args._verb.run(args, run)
        except Refused as refusal:
            run.err(f"{skill.name}: {refusal}")
            code = EXIT_REFUSED
        except Busy as busy:
            run.err(f"{skill.name}: busy: {busy}")
            code = EXIT_BUSY
        except TimedOut as late:
            run.err(f"{skill.name}: {late}")
            code = EXIT_TIMEOUT
        code = EXIT_DONE if code is None else int(code)
        for hook in AFTER_VERB:
            hook(args, run, code)
        return code
    except SystemExit as stop:  # argparse: --help is 0, a usage error is 2
        return stop.code if isinstance(stop.code, int) else (EXIT_DONE if stop.code is None else EXIT_USAGE)
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        return report_bug(skill_name, hash, error)


# ---------------------------------------------------------------- check


CHECK_STEPS: dict[str, list[Callable[[Unit, Run], int | None]]] = {}


def check_step(skill: str):
    """Register a step `fn(unit, run) -> int | None` that a skill's `check` runs after every record passed its schemas,
    for what the schemas cannot say. A step prints its own lines and returns 1 when it found an error."""

    def register(function):
        CHECK_STEPS.setdefault(skill, []).append(function)
        return function

    return register


def _check_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("unit", help="the unit to check, such as .code/my-change")


@verb(
    "check",
    help="check every record of a unit against its schemas; exit 1 if any is invalid",
    arguments=_check_arguments,
)
def check(args: argparse.Namespace, run: Run) -> int:
    """One line per problem, `<file>:<line>: <field>: <reason>`. A record whose `at` is more than five minutes ahead of
    this machine's clock is a problem. A record from before the build's cutoff in the format before this change is
    reported as such and is not a problem."""
    unit = paths.resolve_unit(args.unit, run.skill)
    docs = schema.docs_for(run.info.package)
    shown = os.path.relpath(unit.path)
    typed = Path(os.path.abspath(args.unit))  # the path as given, which may reach the unit through a symlink
    root = Path(shown) if not shown.startswith("..") else typed if typed.resolve() == unit.path else unit.path
    notices: list[schema.Error] = []
    errors = schema.check_paths(
        [root], docs=docs, now=run.now(), cutoff=run.info.cutoff, notices=notices, root=unit.root
    )
    for error in errors:
        run.out(str(error))
    for notice in notices:
        run.out(str(notice))
    if errors:
        return EXIT_REFUSED
    stopped = [step(unit, run) for step in CHECK_STEPS.get(run.skill.name, [])]
    return EXIT_REFUSED if any(stopped) else EXIT_DONE
