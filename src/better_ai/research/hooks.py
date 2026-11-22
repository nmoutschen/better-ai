"""What research-better adds to the record verbs."""

from __future__ import annotations

from .. import records

TIME = "%Y-%m-%dT%H:%M:%SZ"


@records.set_step("research-better")
def stamp_changes(ctx: records.SetContext) -> None:
    """An entry of the brief's `changes` that comes without an `at` is a new one: the command stamps it, as it stamps every
    record, so the agent types no time. The entries it keeps carry their own `at` and are given back as they are."""
    changes = ctx.patch.get("changes")
    if not isinstance(changes, list):
        return
    stamped = ctx.run.now().strftime(TIME)
    ctx.patch["changes"] = [
        {"at": stamped, **entry} if isinstance(entry, dict) and "at" not in entry else entry for entry in changes
    ]
