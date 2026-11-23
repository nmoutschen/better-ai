"""What research-better adds to the record verbs."""

from __future__ import annotations

from .. import paths, quotes, records


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
    stamped = ctx.run.now().strftime(records.TIME)
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


RAW_THEN = "save the text of the page you read to a file outside the board and run again with --raw <file>"


@records.add_guard("research-better", "claim")
def claim_starts_unchecked(ctx: records.AddContext) -> None:
    """A claim is added `unchecked`: only `set` by a verifier, with the page it read, makes it `verified`."""
    if ctx.record.get("status") != "unchecked":
        raise paths.refusal(
            ctx.unit.label, 'a new claim must have "status": "unchecked"', "add it unchecked: a verifier checks it"
        )


@records.set_step("research-better")
def verified_needs_the_page_read(ctx: records.SetContext) -> None:
    """A claim set `verified`, or a verified claim whose span or quote changes, needs `--raw`: the text of the page the
    verifier read. Each passage of the span (joined by " ... ") must occur in it, and the quote in the span; the
    command keeps the file's `sha256`. A claim that stops being verified loses its `sha256`."""
    record, patch = ctx.record, ctx.patch
    if record.get("type") != "claim":
        return
    status = patch.get("status", record.get("status"))
    if "sha256" in patch or ("sha256" in ctx.unsets and status == "verified"):
        raise paths.refusal(ctx.unit.label, "sha256 is computed by better.pyz from --raw", "leave sha256 out")
    if status != "verified":
        if "sha256" in record and "sha256" not in ctx.unsets:
            ctx.unsets = (*ctx.unsets, "sha256")
        return
    if record.get("status") == "verified" and "span" not in patch and "quote" not in patch:
        return
    span = patch.get("span", record.get("span"))
    if not isinstance(span, str) or not span.strip():
        raise paths.refusal(ctx.unit.label, "verified needs the span you copied from the page", 'set "span"')
    passages = [p for p in span.split(" ... ") if p.strip()]
    patch["sha256"] = quotes.check_read(ctx, passages, patch.get("quote", record.get("quote")), RAW_THEN)
