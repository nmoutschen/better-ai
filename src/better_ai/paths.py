"""Every rule about where the command may read and write, in one place (design.md, Paths and units).

A unit is a folder at `<root>/<skill folder>/<slug>`, where `<root>` is the top level of the repository that holds it.
Every other module reaches a unit's files through `Unit.target` and the open and write helpers here, which refuse a path
that leaves the unit or passes through a symlink, and open files with `O_NOFOLLOW`, so no verb repeats these checks.
The only write outside a unit is `add_exclude`, one line in the repository's `info/exclude`.

Refusals are `Refused`, whose text is `<what>: <reason>. <next command>`; `cli` prints it after the skill name and
exits 1.
"""

from __future__ import annotations

import contextlib
import errno
import os
import re
import secrets
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .skill import OWNER_BY_HEAD, OWNER_BY_ROOT, Skill, UnitKind

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
AGENT = re.compile(r"^[a-z][a-z0-9-]*$")
NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)


class Refused(Exception):
    """The command refuses: nothing was written. The text is `<what>: <reason>. <next command>`."""


class NameRefused(Refused):
    """A value that becomes part of a path was refused (`check_slug`, `check_agent`, `check_by`, `check_pattern`). The
    verb that knows its unit puts the unit in front of the message."""


def reason(error: BaseException) -> str:
    """What a reader shows for a file it could not read: a refusal's own words, or only the kind of any other error."""
    return str(error) if isinstance(error, Refused) else type(error).__name__


def refusal(what: str, reason: str, then: str | None = None) -> Refused:
    return Refused(f"{what}: {reason}." + (f" {then}" if then else ""))


# ---------------------------------------------------------------- names


def _named(what: str, reason: str, then: str | None = None) -> NameRefused:
    return NameRefused(f"{what}: {reason}." + (f" {then}" if then else ""))


def check_slug(value: str, what: str = "slug") -> str:
    """A unit folder name: lower case letters, digits and hyphens, starting with a letter or digit."""
    if not isinstance(value, str) or not SLUG.fullmatch(value):
        raise _named(
            repr(value), f"not a valid {what} (use {SLUG.pattern})", "choose a name of lower case letters and hyphens"
        )
    return value


def check_agent(value: str, what: str = "agent name") -> str:
    """An agent's name, which becomes part of file names: `^[a-z][a-z0-9-]*$`. Checked before any path is built."""
    if not isinstance(value, str) or not AGENT.fullmatch(value):
        raise _named(repr(value), f"not a valid {what} (use {AGENT.pattern})", "use lower case letters and hyphens")
    return value


def check_by(value: str) -> str:
    """The `--by` name: an agent name, and never `user`, which only the page writes."""
    check_agent(value, "--by name")
    if value == "user":
        raise _named("user", "--by user is the page's name, not an agent's", "use your own agent name")
    return value


def check_pattern(value: str, pattern: str, what: str) -> str:
    """A value that becomes part of a file name (a generated id, `--id`) must match its id pattern."""
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise _named(repr(value), f"not a valid {what} (use {pattern})")
    return value


# ---------------------------------------------------------------- units


@dataclass(frozen=True)
class Unit:
    """A unit found by `resolve_unit`. `path` is absolute and normalised, `root` the repository top level (the folder
    above the skill folder outside a repository), `kind` the kind of this skill whose folder it is in."""

    path: Path
    root: Path
    kind: UnitKind
    skill: Skill

    @property
    def slug(self) -> str:
        return self.path.name

    @property
    def label(self) -> str:
        """The unit as `<skill folder>/<slug>`, for messages."""
        return str(self.path.relative_to(self.root))

    def exists(self) -> bool:
        return self.path.is_dir() and (self.path / self.kind.head).is_file()

    def target(self, relative: str) -> Path:
        """The path of a file or folder inside the unit, checked: relative, without `..`, no symlink on the way, and
        (once resolved) still inside the unit."""
        pure = PurePosixPath(relative)
        if pure.is_absolute() or not pure.parts or {"..", "."} & set(pure.parts) or "\0" in relative:
            raise refusal(f"{self.label}/{relative}", "not a path inside the unit")
        current = self.path
        for part in pure.parts:
            current = current / part
            if os.path.islink(current):
                raise refusal(f"{self.label}/{relative}", f"{part} is a symlink", "remove the symlink")
        base = Path(os.path.realpath(self.path))
        if not Path(os.path.realpath(current)).is_relative_to(base):
            raise refusal(f"{self.label}/{relative}", "the path leaves the unit")
        return current


def _nearest_existing(path: Path) -> Path:
    for folder in (path, *path.parents):
        if folder.is_dir():
            return folder
    return Path(path.anchor or "/")


def git_toplevel(folder: Path) -> Path | None:
    """The top level of the repository that holds `folder` (`git rev-parse --show-toplevel`), or None outside one or
    when git cannot be run. `folder` is the unit's nearest existing parent, never the caller's working directory."""
    try:
        done = subprocess.run(
            ["git", "-C", str(folder), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    top = done.stdout.strip()
    return Path(os.path.realpath(top)) if done.returncode == 0 and top else None


def resolve_unit(argument: str, skill: Skill, *, creating: bool = False) -> Unit:
    """The unit `argument` names, or a refusal. It must sit at `<root>/<skill folder>/<slug>` of one of the skill's
    kinds, with a slug that matches `^[a-z0-9][a-z0-9-]*$` (and is not a name another kind's folder takes, such as
    `audit` under `.code`), and no symlink from the skill folder down. Unless `creating`, it must be a folder with the
    head file of its kind; a unit of another skill is refused naming that skill."""
    text = os.fspath(argument)
    if not text or "\0" in text:
        raise refusal(
            repr(text), "not a path to a unit", f"name it as <skill folder>/<slug>, such as {skill.root}/my-change"
        )
    absolute = Path(os.path.abspath(text))
    parts = absolute.parts
    slug = parts[-1] if len(parts) > 1 else ""
    found = None
    for kind in sorted(skill.kinds, key=lambda k: -len(k.folder)):
        folder_parts = tuple(kind.folder.split("/"))
        if len(parts) > len(folder_parts) + 1 and parts[-1 - len(folder_parts) : -1] == folder_parts:
            found = (kind, folder_parts)
            break
    if found is None:
        owner = _owner_by_location(parts)
        if owner and owner != skill.name:
            raise refusal(text, f"it belongs to {owner}, not to {skill.name}", f"run it with {owner}'s better.pyz")
        folders = ", ".join(f"<root>/{k.folder}/<slug>" for k in skill.kinds)
        raise refusal(text, f"not at a place a {skill.name} unit can be (units are at {folders})")
    kind, folder_parts = found
    check_slug(slug, "unit name")
    if slug in skill.reserved(kind.folder):
        raise refusal(text, f"{slug!r} is reserved under {kind.folder}", "choose another name")
    root_path = Path(*parts[: -1 - len(folder_parts)])
    top = git_toplevel(_nearest_existing(absolute.parent))
    if top is not None and Path(os.path.realpath(root_path)) != top:
        raise refusal(
            text,
            f"the unit must be at the top of its repository ({top}), not under {root_path}",
            f"use {top / kind.folder / slug}",
        )
    root = top if top is not None else Path(os.path.realpath(root_path))  # resolved here, in or outside git, once
    unit_path = root / kind.folder / slug
    shown = str(unit_path.relative_to(root))
    probe = root
    for part in (*folder_parts, slug):
        probe = probe / part
        if os.path.islink(probe):
            raise refusal(shown, f"{probe.name} is a symlink", "remove the symlink")
    unit = Unit(unit_path, root, kind, skill)
    if creating:
        return unit
    if not unit_path.is_dir():
        raise refusal(shown, "no such unit", f"run create {shown} --by <your name>")
    head = unit_path / kind.head
    if os.path.islink(head):
        raise refusal(shown, f"{kind.head} is a symlink", "remove the symlink")
    if not head.is_file():
        owner = next((OWNER_BY_HEAD[n] for n in OWNER_BY_HEAD if (unit_path / n).is_file()), None)
        if owner and owner != skill.name:
            raise refusal(shown, f"it belongs to {owner}, not to {skill.name}", f"run it with {owner}'s better.pyz")
        raise refusal(shown, f"no {kind.head} here", f"run create {shown} --by <your name>")
    for guard in UNIT_GUARDS.get(skill.name, []):
        guard(unit)
    return unit


UNIT_GUARDS: dict[str, list] = {}


def unit_guard(skill: str):
    """Register a check a skill makes on every unit a verb other than `create` resolves (code-better: a change that
    names a design folder but holds no copy of its spec). The function takes the `Unit` and raises `Refused`."""

    def register(function):
        UNIT_GUARDS.setdefault(skill, []).append(function)
        return function

    return register


def read_repo_file(unit: Unit, relative: str) -> bytes:
    """A file elsewhere in the unit's repository (a design folder's `spec.jsonl`), by its repo-relative path, under the
    same rules as a file of the unit: no `..`, no symlink on the way, still inside the repository, opened with
    O_NOFOLLOW, and never inside `.git`. FileNotFoundError if it is not there."""
    pure = PurePosixPath(relative)
    if pure.is_absolute() or not pure.parts or {"..", ".", ".git"} & set(pure.parts) or "\0" in relative:
        raise refusal(relative, "not a path inside the repository")
    return read_bytes(Unit(unit.root, unit.root, unit.kind, unit.skill), relative)


def repo_root(folder: Path) -> Path | None:
    """The repository root above `folder` for a caller that has no `Unit` (its `.root` is the answer): the nearest
    folder up that holds `.git`, or None."""
    return next((f for f in (folder, *folder.parents) if (f / ".git").exists()), None)


def _owner_by_location(parts: tuple[str, ...]) -> str | None:
    for part in parts[-3:-1]:
        if part in OWNER_BY_ROOT:
            return OWNER_BY_ROOT[part]
    return None


# ---------------------------------------------------------------- opening and writing files


def _open(unit: Unit, relative: str, flags: int, mode: int = 0o644) -> int:
    path = unit.target(relative)
    try:
        return os.open(path, flags | NOFOLLOW, mode)
    except OSError as error:
        if error.errno in (errno.ELOOP, errno.EMLINK):  # what O_NOFOLLOW answers for a symlink
            raise refusal(f"{unit.label}/{relative}", "it is a symlink", "remove the symlink") from None
        raise


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        view = view[os.write(fd, view) :]


def read_bytes(unit: Unit, relative: str) -> bytes:
    """A file of the unit, opened with O_NOFOLLOW. FileNotFoundError if it is not there."""
    fd = _open(unit, relative, os.O_RDONLY)
    with os.fdopen(fd, "rb") as handle:
        return handle.read()


def append_line(unit: Unit, relative: str, data: bytes) -> None:
    """Append `data` (one line, ending in a newline) to a JSONL file of the unit in a single `write` on a file opened
    with O_APPEND and O_NOFOLLOW, so concurrent appenders never interleave inside a line."""
    if not data.endswith(b"\n"):
        data += b"\n"
    fd = _open(unit, relative, os.O_WRONLY | os.O_APPEND | os.O_CREAT)
    try:
        if os.write(fd, data) != len(data):
            raise OSError(errno.EIO, "short write", relative)
    finally:
        os.close(fd)


def create_exclusive(unit: Unit, relative: str, data: bytes) -> None:
    """Create a file that must not exist (a folder entry, `<id>.json`): O_CREAT|O_EXCL|O_NOFOLLOW. FileExistsError if
    the name is taken, for the caller to retry on the next number."""
    fd = _open(unit, relative, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    try:
        _write_all(fd, data)
    finally:
        os.close(fd)


def write_atomic(unit: Unit, relative: str, data: bytes) -> None:
    """Replace or create a file of the unit: write a temporary file with a random name in the same folder, created with
    O_CREAT|O_EXCL|O_NOFOLLOW, then `os.replace` it over the target. The temporary file is removed if anything fails."""
    path = unit.target(relative)
    temporary = f".{path.name}.{secrets.token_hex(8)}.tmp"
    relative_temporary = str(PurePosixPath(relative).with_name(temporary))
    fd = _open(unit, relative_temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    try:
        try:
            _write_all(fd, data)
        finally:
            os.close(fd)
        os.replace(path.with_name(temporary), path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(path.with_name(temporary))
        raise


def write_state(unit: Unit, relative: str, data: bytes) -> None:
    """Write a small state file of the page (`.server`, `.conversation-seen`), opened with O_NOFOLLOW."""
    fd = _open(unit, relative, os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
    try:
        _write_all(fd, data)
    finally:
        os.close(fd)


def make_unit_folder(unit: Unit) -> None:
    """Make the unit's own folder, and the skill folder above it if it is missing (`resolve_unit` has refused a symlink
    on the way). Only `create` calls it."""
    os.makedirs(unit.path, exist_ok=True)


def make_folder(unit: Unit, relative: str) -> None:
    """Make a folder inside the unit (and the folders above it inside the unit), refusing a symlink on the way."""
    pure = PurePosixPath(relative)
    for index in range(1, len(pure.parts) + 1):
        path = unit.target(str(PurePosixPath(*pure.parts[:index])))
        if not path.is_dir():
            os.mkdir(path)


def add_exclude(unit: Unit, line: str) -> str:
    """Add `line` to the repository's `info/exclude` if it is not there yet, never rewriting the file: the one write
    outside a unit. The file is where `git rev-parse --git-path info/exclude` says, so it works in a worktree too.
    Returns "added", "present", or "skipped: <why>" (outside a git repository, or git cannot be run)."""
    try:
        done = subprocess.run(
            ["git", "-C", str(unit.path), "rev-parse", "--git-path", "info/exclude"],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "skipped: git cannot be run"
    if done.returncode != 0 or not done.stdout.strip():
        return "skipped: not a git repository"
    exclude = Path(done.stdout.strip())
    if not exclude.is_absolute():
        exclude = unit.path / exclude
    try:
        fd = os.open(exclude, os.O_RDONLY | NOFOLLOW)
    except FileNotFoundError:
        existing = ""
    else:
        with os.fdopen(fd, "rb") as handle:
            existing = handle.read().decode("utf-8", "replace")
    if line in existing.splitlines():
        return "present"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(exclude, os.O_WRONLY | os.O_APPEND | os.O_CREAT | NOFOLLOW, 0o644)
    try:
        prefix = "" if not existing or existing.endswith("\n") else "\n"
        os.write(fd, f"{prefix}{line}\n".encode())
    finally:
        os.close(fd)
    return "added"
