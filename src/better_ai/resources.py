"""Files bundled in the package, and what the running `.pyz` knows about itself.

Everything is read with `importlib.resources.files`, which works from a folder (tests, run from source) and from inside
a zip (a built `better.pyz`) on Python 3.10 or later.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from importlib import import_module
from importlib.resources import files
from typing import Any

PACKAGE = "better_ai"


def root() -> Any:
    """The package folder, as a Traversable (a Path from source, a zip path from a `.pyz`)."""
    return files(PACKAGE)


def path(name: str) -> Any:
    """A file or folder of the package by its path with `/`, such as `schemas` or `architect/kinds.json`."""
    node = root()
    for part in name.split("/"):
        node = node / part
    return node


def read_text(name: str) -> str:
    return path(name).read_text(encoding="utf-8")


def read_bytes(name: str) -> bytes:
    return path(name).read_bytes()


def exists(name: str) -> bool:
    return path(name).is_file()


@dataclass(frozen=True)
class BuildInfo:
    skill: str  # "code-better"
    package: str  # "code"
    hash: str  # the source hash the build wrote, or "source" when run from source
    cutoff: str  # records written before this time may be in the format before this change


def _source_cutoff(environ: Any) -> str:
    """The cutoff of a run from source: BETTER_AI_CUTOFF in `environ` (a test pins one in the past), else the
    `format_cutoff` of skills.json, the one place a release writes it."""
    return environ.get("BETTER_AI_CUTOFF") or json.loads(read_text("skills.json"))["format_cutoff"]


def build_info(environ: Any = None) -> BuildInfo:
    """What this run is. A built `.pyz` holds `_build.json`, written by the build. Run from source (the tests), the
    skill is BETTER_AI_SKILL in `environ` (os.environ by default), the hash is "source" and the cutoff is
    BETTER_AI_CUTOFF or the `format_cutoff` of skills.json. A run that cannot tell its skill raises LookupError."""
    environ = os.environ if environ is None else environ
    if exists("_build.json"):
        data = json.loads(read_text("_build.json"))
        return BuildInfo(data["skill"], data["package"], data["hash"], data["cutoff"])
    skill = environ.get("BETTER_AI_SKILL", "")
    if not skill.endswith("-better"):
        raise LookupError("BETTER_AI_SKILL is not set to a skill such as code-better, and this is not a built .pyz")
    return BuildInfo(skill, skill.removesuffix("-better"), "source", _source_cutoff(environ))


def cutoff(environ: Any = None) -> str:
    """The format cutoff of this run, also for a reader run in-process with no skill named."""
    environ = os.environ if environ is None else environ
    try:
        return build_info(environ).cutoff
    except LookupError:
        return _source_cutoff(environ)


def skill_package(package: str) -> Any:
    """The skill package module, such as `better_ai.code`."""
    return import_module(f"{PACKAGE}.{package}")


def schema_sources(package: str | None = None) -> list[Any]:
    """The folders of schemas a run loads: the shared ones, then the skill package's own (the running skill's, if no
    package is named). Later schemas replace earlier ones of the same file name."""
    if package is None:
        package = build_info().package
    return [path("schemas"), path(f"{package}/schemas")]
