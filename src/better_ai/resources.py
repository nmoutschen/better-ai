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
DEFAULT_CUTOFF = "2026-11-22T00:00:00Z"  # used only when running from source without skills.json


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


def build_info(environ: Any = None) -> BuildInfo:
    """What this run is. A built `.pyz` holds `_build.json`, written by the build. Run from source (the tests), the
    skill is the environment variable BETTER_AI_SKILL, the hash is "source" and the cutoff is `format_cutoff` of
    skills.json when that file exists. A run that cannot tell its skill raises LookupError."""
    environ = os.environ if environ is None else environ
    if exists("_build.json"):
        data = json.loads(read_text("_build.json"))
        return BuildInfo(data["skill"], data["package"], data["hash"], data["cutoff"])
    skill = environ.get("BETTER_AI_SKILL", "")
    if not skill.endswith("-better"):
        raise LookupError("BETTER_AI_SKILL is not set to a skill such as code-better, and this is not a built .pyz")
    cutoff = DEFAULT_CUTOFF
    if exists("skills.json"):
        cutoff = json.loads(read_text("skills.json")).get("format_cutoff", cutoff)
    # Run from source (tests), a test may pin the cutoff; a built .pyz always uses the one the build wrote.
    cutoff = os.environ.get("BETTER_AI_CUTOFF", cutoff)
    return BuildInfo(skill, skill.removesuffix("-better"), "source", cutoff)


def skill_package(package: str) -> Any:
    """The skill package module, such as `better_ai.code`."""
    return import_module(f"{PACKAGE}.{package}")


def schema_sources(package: str | None = None) -> list[Any]:
    """The folders of schemas a run loads: the shared ones, then the skill package's own (the running skill's, if no
    package is named). Later schemas replace earlier ones of the same file name."""
    if package is None:
        package = build_info().package
    return [path("schemas"), path(f"{package}/schemas")]
