"""What research-better adds to the record verbs."""

from __future__ import annotations

from .. import paths, records

TIME = "%Y-%m-%dT%H:%M:%SZ"


@records.set_step("research-better")
def stamp_changes(ctx: records.SetContext) -> None:
    """The brief's `changes`: the patch holds the new entries first, then every earlier entry exactly as the brief holds it.
    The command stamps the new entries, so no agent types a time, and nothing earlier is dropped or rewritten. A patch
    that is not a list, or whose entries are not objects, is left to the schema."""
    changes = ctx.patch.get("changes")
    earlier = ctx.record.get("changes")
    if not isinstance(earlier, list):  # a brief written before `changes` existed: every entry of the patch is new
        earlier = []
    if not isinstance(changes, list):
        return
    fresh = len(changes) - len(earlier)
    if fresh < 0 or changes[fresh:] != earlier:
        raise paths.refusal(
            ctx.unit.label,
            "changes must hold the new entries first, then every earlier entry as the brief shows it",
            "Give the earlier entries back unchanged after the new ones",
        )
    new = changes[:fresh]
    if any(isinstance(entry, dict) and "at" in entry for entry in new):
        raise paths.refusal(ctx.unit.label, "a new entry in changes holds `at`", "remove 'at' from the new entries")
    stamped = ctx.run.now().strftime(TIME)
    ctx.patch["changes"] = [{"at": stamped, **e} if isinstance(e, dict) else e for e in new] + earlier


@records.set_step("research-better")
def old_decision_needs_the_new_fields(ctx: records.SetContext) -> None:
    """A decision written before this change has no `raised_by` or `about`: `set` on it must give them."""
    record = ctx.record
    if record.get("type") != "decision" or ("raised_by" in record and "about" in record):
        return
    missing = [name for name in ("raised_by", "about") if name not in record and name not in ctx.patch]
    if missing:
        raise paths.refusal(
            ctx.unit.label,
            f"{record.get('id')} was written before this change and has no {' or '.join(missing)}",
            "give "
            + " and ".join(missing)
            + ' in the same set, such as {"raised_by": "coordinator", "about": {"type": "board"}}',
        )


@records.create_step("research-better")
def new_board_has_no_changes(ctx: records.CreateContext):
    """A new board starts with no recorded change, so no agent types a change's time at `create`."""
    if ctx.record.get("changes"):
        raise paths.refusal(
            ctx.unit.label,
            "a new board's changes must be []",
            'create it with "changes": [], then set the brief to record a change',
        )
