"""Select conversation work for one agent turn, and write the prompt that carries it."""

import json
import shlex
from dataclasses import dataclass

# An item's status in a batch, as `pending` prints it: its thread's step (new, seen or working) while it is the agent's
# turn, else asked (the user's turn) or done (page `threads`, the one thread state machine).
READY = frozenset(
    {"new"}
)  # the user wrote in the thread since the agent last read it: a follow-up, an answer, a reopen
SETTLED = frozenset({"asked", "done"})
HIDDEN = ("step", "closed_by_user")  # what `pending` leaves out of an item's extra fields
MOST = 20  # past this many items a prompt names ids only

HEADER = "every word for the user through reply; end the turn when the items are handled; never serve"
RESUME = "check the records and the working tree before acting on these again"
STOPPED = "do not resume stopped work unless the user asks"
ENDED = (
    "your harness process was ended ({}); background workers you started are gone; "
    "check the records and the working tree, then restart them or report what is unfinished"
)
NOTE = "from the chat, written {}; where it differs, the records and your own session are newer"
CONTINUE = "continue from the current step"


def from_user(event: dict) -> bool:
    """The actor recorded in the event. The driver checks who sent it separately when deciding what wakes a turn."""
    return event.get("by") == "user"


def terminal_json(value) -> str:
    """JSON for a terminal: readable, and escaped where UTF-8 cannot hold a character (a lone surrogate), so printing
    it never fails."""
    text = json.dumps(value, ensure_ascii=False)
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return json.dumps(value)
    return text


def item_status(state: str, extra: dict) -> str:
    """An item's status as `pending` prints it, from its thread's state and step."""
    return extra.get("step", "new") if state == "agent" else "asked" if state == "you" else "done"


def item_entry(item: dict, state: str, extra: dict) -> dict:
    """An item as `pending` prints it: the event that started its thread, its status and its thread's extra fields."""
    return {**item, "status": item_status(state, extra), **{k: v for k, v in extra.items() if k not in HIDDEN}}


@dataclass(frozen=True)
class Delivery:
    items: list[dict]
    events: list[dict]
    position: int
    read: int = -1  # the line of the last event the batch shows, which the agent passes as --read

    def prompt_items(self) -> list[dict]:
        if len(self.items) <= MOST:
            return self.items
        return [{"id": item["id"]} for item in self.items]

    def lines(self, compact: bool = False) -> list[str]:
        """What `pending` prints for this batch; a turn's prompt holds the same, with ids only past MOST items."""
        items = self.prompt_items() if compact else self.items
        last = f"{len(self.items)} not done." + (
            f" Pass --read {self.read} to status and reply." if self.read >= 0 else ""
        )
        return [terminal_json(entry) for entry in [*items, *self.events]] + [last]


def ended_label(outcome: str) -> str:
    """How a turn that did not end normally is named to the agent."""
    return outcome if outcome in ("stopped by the user", "stalled") else "crashed"


def _updated_items(events: list[dict], item_types: tuple[str, ...], after: int) -> set[tuple[str, str]]:
    """Find new versions of items, including updates to items that aren't otherwise ready."""
    seen, updated = set(), set()
    for index, event in enumerate(events):
        kind, ident = event.get("type"), event.get("id")
        if from_user(event) and kind in item_types and ident:
            key = (kind, ident)
            if index >= after and key in seen:
                updated.add(key)
            seen.add(key)
    return updated


def select(
    events: list[dict],
    items: list[tuple[dict, str, dict]],
    item_types: tuple[str, ...],
    after: int,
    carry_ids: frozenset[str],
    recover_ids: frozenset[str],
    *,
    admitted_edits: set[tuple[str, str]] | None = None,
    all_working: bool = False,
    read_only: frozenset[str] = frozenset(),
) -> Delivery:
    """The items the agent may be given: those new (the user wrote in the thread: a new item, an answer, a follow-up, a
    reopen), those seen only by a --read that covered them (READ_ONLY: no status of the agent's since the user's latest
    event, so it may never have been delivered), an edited one that is not settled, the items the last normal turn left
    seen, those an abnormal end left seen or working, and, with `all_working`, every item still working. Never one asked
    or done (SETTLED), also when the user edits it. ITEMS are page `all_items`."""
    if after > len(events):
        after = 0
    updated = _updated_items(events, item_types, after)
    if admitted_edits is not None:
        updated &= admitted_edits
    selected = []
    for item, state, extra in items:
        entry = item_entry(item, state, extra)
        status = entry["status"]
        if (
            status in READY
            or (status == "seen" and item["id"] in read_only)
            or ((item["type"], item["id"]) in updated and status not in SETTLED)
            or (status == "seen" and item["id"] in carry_ids)
            or (status in ("seen", "working") and item["id"] in recover_ids)
            or (status == "working" and all_working)
        ):
            selected.append(entry)
    item_ids = {item["id"] for item, _, _ in items}
    # A note attached to another item is a user event, even when the parent is working and cannot be delivered.
    other = [
        event
        for event in events[after:]
        if from_user(event)
        and (
            event.get("type") not in item_types
            or (event.get("type") == "note" and event.get("to") and event.get("id") not in item_ids)
        )
    ]
    return Delivery(selected, other, len(events), len(events) - 1)


def turn_prompt(
    *,
    unit: str,
    form: str,
    batch: Delivery,
    triggers: tuple[dict, ...] = (),
    first: str = "",
    note: str = "",
    ended: str = "",
    resent: bool = False,
    after_stop: bool = False,
) -> str:
    """One turn's prompt: the header, then the opening text of a first turn, the hand-off note, how the last harness
    process ended, what was sent before, the items and events as `pending` prints them (ids only past MOST items), and
    the skill triggers. The batch's items and events already carry their `sent_before`."""
    parts = [f"Unit: {unit}\nApproved without asking: {form}\nRules: {HEADER}."]
    parts.extend(part for part in (first, note) if part)
    if ended:
        parts.append(f"Items still working: {ENDED.format(ended)}.")
    if resent:
        parts.append(f"Sent before: {RESUME}" + (f"; {STOPPED}" if after_stop else "") + ".")
    parts.append("\n".join(batch.lines(compact=True)))
    if len(batch.items) > MOST:
        parts.append(f"For the full copy of the items, run pending {shlex.quote(unit)}.")
    if triggers:
        parts.append("Skill triggers:\n" + "\n".join(terminal_json(trigger) for trigger in triggers))
    return "\n\n".join(parts)
