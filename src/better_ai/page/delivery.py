"""Select conversation work for one agent turn or a fallback listener."""

from dataclasses import dataclass

READY = frozenset({"new", "replied", "followup", "reopened"})


def from_user(event: dict) -> bool:
    """The actor recorded in the event. The driver checks who sent it separately when deciding what wakes a turn."""
    return event.get("by") == "user"


@dataclass(frozen=True)
class Delivery:
    items: list[dict]
    events: list[dict]
    position: int

    def prompt_items(self) -> list[dict]:
        if len(self.items) <= 20:
            return self.items
        return [{"id": item["id"], "status": item["status"]} for item in self.items]


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
) -> Delivery:
    if after > len(events):
        after = 0
    updated = _updated_items(events, item_types, after)
    selected = [
        {**item, "status": state, **extra}
        for item, state, extra in items
        if state in READY
        or (item["type"], item["id"]) in updated
        or (state == "seen" and item["id"] in carry_ids)
        or (state in ("seen", "working") and item["id"] in recover_ids)
    ]
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
    return Delivery(selected, other, len(events))
