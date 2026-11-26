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


def select(
    events: list[dict],
    items: list[tuple[dict, str, dict]],
    item_types: tuple[str, ...],
    after: int,
    carry_ids: frozenset[str],
    recover_ids: frozenset[str],
) -> Delivery:
    selected = [
        {**item, "status": state, **extra}
        for item, state, extra in items
        if state in READY
        or (state == "seen" and item["id"] in carry_ids)
        or (state in ("seen", "working") and item["id"] in recover_ids)
    ]
    item_ids = {item["id"] for item, _, _ in items}
    # A note attached to another item is a user event, even when the parent is working and cannot be delivered.
    if after > len(events):
        after = 0
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
