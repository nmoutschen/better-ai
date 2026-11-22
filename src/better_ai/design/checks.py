"""design-better's check across a unit, named by `x-check` in canvas.schema.json."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

from .. import paths
from ..page import ADDRESS, LOG, SEEN
from ..schema import Context, hook

PAGE = "index.html"  # what `render` writes in the unit: no version may be this file
STATE = (LOG, ADDRESS, SEEN)  # the live page's own files


def is_page(path: str | None) -> bool:
    """True when `path` is, or on a case-insensitive file system may be, a file the page owns: the index.html that
    `render` writes, or the page's state files."""
    return isinstance(path, str) and path.casefold() in (PAGE, *STATE)


def page_reason(path: str) -> str:
    """Why a version may not be `path`, for a file `is_page` names."""
    if path.casefold() == PAGE:
        return f"{PAGE} is the compare page render writes: rename the version"
    return f"{path} is one of the live page's own files: rename the version"


def version_path(file: Any) -> str | None:
    """The unit-relative path a version's `file` names, or None when it does not name a path inside the unit."""
    if not isinstance(file, str) or not file or "\0" in file or "\\" in file:
        return None
    pure = PurePosixPath(file)
    if pure.is_absolute() or {"..", "."} & set(pure.parts):
        return None
    return str(pure)


def unit_of(directory) -> paths.Unit:
    """The unit whose folder is `directory`, for the same file helpers `render` and `serve` read the versions with."""
    from . import SKILL

    root = directory
    for folder in (directory, *directory.parents):
        if (folder / ".git").exists():
            root = folder
            break
    return paths.Unit(path=directory, root=root, kind=SKILL.kinds[0], skill=SKILL)


def version_problem(unit: paths.Unit, path: str) -> str | None:
    """Why a version's file cannot be read as `render` reads it (the same `paths.read_bytes`), or None."""
    if is_page(path):
        return page_reason(path)
    try:
        paths.read_bytes(unit, path)
    except paths.Refused as error:
        if "symlink" in str(error):
            return f"{path} is a symlink: copy the file into the unit"
        return f"{path} is not a file of the unit"
    except OSError:
        return f"{path} is not a file of the unit"
    return None


@hook("canvas-versions")
def _canvas_versions(record: dict, context: Context) -> list[tuple[str, str]]:
    """Two versions with one label are told apart by nothing on the page; a `file` must be a file of the unit's folder."""
    problems: list[tuple[str, str]] = []
    versions = record.get("versions")
    if not isinstance(versions, list):
        return problems
    seen: dict[str, int] = {}
    for index, version in enumerate(versions):
        if not isinstance(version, dict):
            continue
        label = version.get("label")
        if isinstance(label, str):
            if label in seen:
                problems.append((f"versions/{index}/label", f"the same label as version {seen[label]}"))
            seen.setdefault(label, index)
        if "file" not in version:
            continue
        path = version_path(version["file"])
        if path is None:
            problems.append((f"versions/{index}/file", "must be a path inside the unit's folder, without .."))
        else:
            why = version_problem(unit_of(context.directory), path)
            if why:
                problems.append((f"versions/{index}/file", why))
    return problems
