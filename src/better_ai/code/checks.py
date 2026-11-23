"""code-better's checks across records, named by `x-check` in its schemas."""

from __future__ import annotations

from ..schema import Context, hook, show


@hook("verified-needs-passing-verifier")
def _verified_needs_passing_verifier(record: dict, context: Context) -> list[tuple[str, str]]:
    """A task is `verified` only when its latest verifier (a `logs/<agent>.card.json` with role verifier and this
    task) ended its `logs/<agent>.jsonl` with a handed_back line whose result is passes."""
    task = record.get("id")
    cards = []
    for card_path in sorted(context.path("logs").glob("*.card.json")):
        card = context.read_json(f"logs/{card_path.name}")
        if isinstance(card, dict) and card.get("role") == "verifier" and card.get("task") == task:
            cards.append((str(card.get("at")), card_path.name.removesuffix(".card.json")))
    if not cards:
        return [("status", f'"verified" needs a verifier card for {task} in logs/')]
    agent = max(cards)[1]
    lines = context.read_jsonl(f"logs/{agent}.jsonl") or []
    last = lines[-1] if lines else None
    need = f'"verified" needs the latest verifier of {task} ({agent}) to hand back "passes"'
    if not isinstance(last, dict) or last.get("type") != "handed_back":
        return [("status", f"{need}; it has not handed back")]
    if last.get("result") != "passes":
        return [("status", f"{need}; it handed back {show(last.get('result'))}")]
    return []
