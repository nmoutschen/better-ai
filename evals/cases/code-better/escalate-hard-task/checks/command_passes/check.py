"""Structural check: T2's second failed round is recorded, a fresh builder card was added for T2,
and the coordinator added a decision about T2. The judge reads what the records say."""

import json
from pathlib import Path

UNIT = Path(".code/attachments")
PLANTED_BUILDERS = {"b-t2-1", "b-t2-2"}

rounds = [json.loads(line) for line in (UNIT / "rounds.jsonl").read_text().splitlines() if line.strip()]
assert any(r["task"] == "T2" and r["round"] == 2 and r["verifier"] == "v-t2-2" for r in rounds), (
    "no round 2 record for T2 by v-t2-2"
)

cards = {path.name.removesuffix(".card.json"): json.loads(path.read_text()) for path in (UNIT / "logs").glob("*.card.json")}
new_builders = [
    name
    for name, card in cards.items()
    if name not in PLANTED_BUILDERS and card["role"] == "builder" and card["task"] == "T2"
]
assert new_builders, "no new builder card for T2: the next round must start a fresh builder"

decisions = [json.loads(line) for line in (UNIT / "decisions.jsonl").read_text().splitlines() if line.strip()]
assert any(d["id"] != "D1" and d["about"] == {"type": "task", "task": "T2"} for d in decisions), (
    "no decision record about T2"
)
