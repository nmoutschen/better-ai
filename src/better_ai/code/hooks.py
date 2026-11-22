"""What code-better adds to the shared `create` and `add` (design.md, Command contract and Data):

- `create` of a change whose `code.json` names an architect folder copies that folder's `spec.jsonl` into the change, after
  every line has been checked, and writes nothing if one fails. On a change that has `code.json` and no `spec.jsonl`
  (one started before the copy existed) it copies that file and nothing else;
- every verb but `create` refuses such a change and names `create`;
- `add` refuses a card for a name another agent of the change has, and a log line for an agent with no card.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .. import paths, records, resources, schema
from ..paths import Refused, Unit, refusal

SPEC = "spec.jsonl"
LOG_TYPES = ("start", "step", "asked", "blocked", "handed_back")


def design_folder(record) -> str | None:
    """The repo-relative folder `code.json` names as an architect design, or None."""
    design = record.get("design") if isinstance(record, dict) else None
    if isinstance(design, dict) and design.get("type") == "architect" and isinstance(design.get("folder"), str):
        return design["folder"].strip() or None
    return None


def _head(unit: Unit) -> dict | None:
    """The change's `code.json` as a dict, or None if it is missing or does not parse."""
    try:
        record = json.loads(paths.read_bytes(unit, unit.kind.head).decode("utf-8"))
    except (OSError, ValueError, RecursionError, Refused):
        return None
    return record if isinstance(record, dict) else None


def _has_spec(unit: Unit) -> bool:
    try:
        return unit.target(SPEC).is_file()
    except Refused:
        return True  # a symlink there is for the other verbs to report


def _read_design_spec(unit: Unit, folder: str) -> bytes:
    relative = f"{folder.rstrip('/')}/{SPEC}"
    try:
        return paths.read_repo_file(unit, relative)
    except FileNotFoundError:
        raise refusal(
            unit.label,
            f"its design folder {folder} holds no {SPEC}",
            "write the spec with architect-better first, or fix design.folder in code.json",
        ) from None
    except Refused as error:
        raise refusal(
            unit.label, f"cannot read the design's {SPEC}: {error}", "fix design.folder in code.json"
        ) from None


def _checked_copy(unit: Unit, folder: str, head: dict) -> bytes:
    """The bytes of the design folder's `spec.jsonl`, once every line has passed this skill's spec schema with the
    pointers resolved against that folder. Refuses, naming each line that fails, if one does not."""
    data = _read_design_spec(unit, folder)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise refusal(unit.label, f"{folder}/{SPEC} is not UTF-8 text", "fix the file in the design folder") from None
    target = unit.path / SPEC
    cache = {f"json:{os.path.normpath(target.resolve().parent / unit.kind.head)}": head}
    docs = schema.load_schemas(*resources.schema_sources("code"))
    errors = schema.check_text(target, text, docs, cache)
    if errors:
        shown = [f"{folder}/{SPEC}:{e.line}: {e.field}: {e.message}" for e in errors[:10]]
        more = f" (and {len(errors) - 10} more)" if len(errors) > 10 else ""
        raise refusal(
            unit.label,
            "the design's spec does not pass the check, so nothing was written:\n  " + "\n  ".join(shown) + more,
            "fix the spec in the design folder, then run create again",
        )
    return data


@records.create_step("code-better")
def copy_spec_at_create(ctx: records.CreateContext):
    """Before the head is written: check the architect folder's spec; after it is written: copy it into the change."""
    folder = design_folder(ctx.record) if ctx.unit.kind.head_type == "code" else None
    if folder is None:
        return None
    data = _checked_copy(ctx.unit, folder, ctx.record)

    def copy() -> None:
        paths.create_exclusive(ctx.unit, SPEC, data)

    return copy


@records.create_step("code-better", existing=True)
def copy_spec_to_started_change(ctx: records.CreateContext) -> bool:
    """A change that has `code.json` naming a design folder and no `spec.jsonl` gets that one file, and nothing else."""
    if ctx.unit.kind.head_type != "code" or _has_spec(ctx.unit):
        return False
    head = _head(ctx.unit)
    folder = design_folder(head)
    if folder is None:
        return False
    data = _checked_copy(ctx.unit, folder, head)
    paths.create_exclusive(ctx.unit, SPEC, data)
    ctx.run.out(f"copied {folder}/{SPEC} into {ctx.unit.label}")
    return True


@paths.unit_guard("code-better")
def needs_the_spec_copy(unit: Unit) -> None:
    """Every verb but `create` refuses a change whose design folder holds the spec and that has no copy of it yet."""
    if unit.kind.head_type != "code" or _has_spec(unit):
        return
    folder = design_folder(_head(unit))
    if folder is not None:
        raise refusal(
            unit.label,
            f"it names the design folder {folder} and has no {SPEC} yet",
            f"run create {unit.label} --by <your name> to copy the spec",
        )


@records.add_guard("code-better", "card")
def a_card_is_for_a_new_name(ctx: records.AddContext) -> None:
    """A card for a name that another agent of the change has is refused: each agent has a name of its own."""
    agent = ctx.for_agent
    taken = ctx.exists or _exists(ctx.unit, f"logs/{agent}.jsonl")
    if taken:
        raise refusal(
            ctx.unit.label,
            f"an agent named {agent} exists already",
            "give each agent a name of its own, and use that name in --for",
        )


@records.add_guard("code-better", *LOG_TYPES)
def a_log_line_needs_the_card(ctx: records.AddContext) -> None:
    """A log line for an agent with no card is refused: the coordinator writes the card before it starts the agent."""
    if not _exists(ctx.unit, f"logs/{ctx.for_agent}.card.json"):
        raise refusal(
            ctx.unit.label,
            f"{ctx.for_agent} has no card",
            f"write it first: add {ctx.unit.label} card --for {ctx.for_agent}",
        )


def _exists(unit: Unit, relative: str) -> bool:
    try:
        return Path(unit.target(relative)).is_file()
    except Refused:
        return True
