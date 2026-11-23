"""What a skill package says about itself, so the shared commands know the skill's units.

Every skill package (`better_ai.architect`, `.code`, `.design`, `.research`, `.show`) exports `SKILL`, a `Skill`. The
shared modules read it; they never import a skill package themselves except the one a run is for (`cli`).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UnitKind:
    """One kind of unit a skill works in: a folder of records with one head file that names its kind."""

    kind: str  # "change", "audit", "board", "design", "canvas", "slides": what `check` and messages call the unit
    folder: str  # where units of this kind live, from the repository top level: ".code", ".code/audit"
    head: str  # the head file: "code.json"
    head_type: str  # the `type` of the head record: "code"
    folders: tuple[str, ...] = ()  # the folders `create` makes inside a new unit: ("logs",)


@dataclass(frozen=True)
class Skill:
    name: str  # "code-better"
    package: str  # "code": the folder in src/better_ai/
    kinds: tuple[UnitKind, ...]
    exclude: str | None = (
        None  # the line `create` adds to the repository's info/exclude, such as ".code/"; None adds none
    )

    @property
    def root(self) -> str:
        """The skill's own folder at the repository top level, such as ".code": every unit lives under it."""
        return self.kinds[0].folder.split("/")[0]

    def reserved(self, folder: str) -> set[str]:
        """Names a slug may not take in `folder` because another kind's folder is nested there: `audit` in `.code`."""
        prefix = folder + "/"
        return {k.folder[len(prefix) :].split("/")[0] for k in self.kinds if k.folder.startswith(prefix)}


# Which skill owns which folder and head file, so a refusal can name the owner of a unit it was not built for.
OWNER_BY_ROOT = {
    ".architect": "architect-better",
    ".code": "code-better",
    ".design": "design-better",
    ".research": "research-better",
    ".show": "show-better",
}
OWNER_BY_HEAD = {
    "architect.json": "architect-better",
    "code.json": "code-better",
    "audit.json": "code-better",
    "canvas.json": "design-better",
    "brief.json": "research-better",
    "spec.json": "show-better",
}
