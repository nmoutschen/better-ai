"""design-better's check across a unit, named by `x-check` in canvas.schema.json."""

from __future__ import annotations

import os
from pathlib import PurePosixPath
from typing import Any

from ..schema import Context, hook


def version_path(file: Any) -> str | None:
    """The unit-relative path a version's `file` names, or None when it does not name a path inside the unit."""
    if not isinstance(file, str) or not file or "\0" in file or "\\" in file:
        return None
    pure = PurePosixPath(file)
    if pure.is_absolute() or {"..", "."} & set(pure.parts):
        return None
    return str(pure)


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
        elif not os.path.isfile(context.path(path)):
            problems.append((f"versions/{index}/file", f"{path} is not a file of the unit"))
    return problems
