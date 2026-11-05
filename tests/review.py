"""Blind human review. Every test run rebuilds the page, so nothing here is run by hand.

The page compares the current skill with its previous version if SKILL.md changed since an earlier
run, and with the baseline otherwise. Which output is which stays in a separate key file. Download
your choices from the page, and the next run prints the tally.
"""

import html
import json
import random
from collections import Counter, defaultdict
from pathlib import Path


PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Blind review</title><style>
body {{ font: 16px/1.5 system-ui, sans-serif; margin: 2rem auto; max-width: 1200px; padding: 0 1rem; }}
.outputs {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }}
pre {{ background: #f5f5f4; color: #1c1917; font: inherit; margin: 0; overflow-wrap: anywhere;
       padding: 1rem; white-space: pre-wrap; }}
section {{ border-top: 1px solid #a8a29e; margin-top: 2rem; padding-top: 1rem; }}
label {{ margin-right: 1rem; }} textarea {{ box-sizing: border-box; font: inherit; width: 100%; }}
button {{ font: inherit; padding: .5rem 1rem; }}
@media (max-width: 800px) {{ .outputs {{ grid-template-columns: 1fr; }} }}
@media (prefers-color-scheme: dark) {{ body {{ background: #1c1917; color: #f5f5f4; }}
  pre {{ background: #292524; color: #f5f5f4; }} }}
</style></head><body>
<h1>Which output would you rather read, and what bothers you?</h1>
<p>{count} pairs. Choose an output or mark a tie, then note anything that bothers you in either one.
When you finish, download your choices.</p>
{sections}
<section><button id="save">Download choices</button></section>
<script>
document.getElementById("save").onclick = () => {{
  const choices = [...document.querySelectorAll("section[data-pair]")].map((s) => ({{
    pair: s.dataset.pair,
    choice: s.querySelector("input:checked")?.value ?? null,
    reason: s.querySelector("textarea[data-note=why]").value,
    notes_a: s.querySelector("textarea[data-note=a]").value,
    notes_b: s.querySelector("textarea[data-note=b]").value,
  }}));
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([JSON.stringify(choices, null, 2)]));
  link.download = "choices.json";
  link.click();
}};
</script></body></html>
"""

SECTION = """<section data-pair="{pair}">
<h2>Pair {number}: {effect}</h2>
{context}
<div class="outputs">
<div><h3>A</h3><pre>{a}</pre>
<textarea data-note="a" rows="2" placeholder="What bothers you in A?" aria-label="Notes on A, pair {number}"></textarea></div>
<div><h3>B</h3><pre>{b}</pre>
<textarea data-note="b" rows="2" placeholder="What bothers you in B?" aria-label="Notes on B, pair {number}"></textarea></div>
</div>
<p><label><input type="radio" name="p{pair}" value="A"> A</label>
<label><input type="radio" name="p{pair}" value="B"> B</label>
<label><input type="radio" name="p{pair}" value="tie"> Tie</label></p>
<textarea data-note="why" rows="2" placeholder="Why? (optional)" aria-label="Why, for pair {number}"></textarea>
</section>
"""


def _original_text(effect_id: str) -> str | None:
    """The text being rewritten, so the reviewer can check an output against it."""
    from suites.write_better import EVAL

    for effect in EVAL.effects:
        if effect.id == effect_id:
            return effect.previous_reply if effect.previous_reply is not None else effect.text
    return None


def build(run_path: Path, against: Path | None = None) -> Path:
    run = json.loads(run_path.read_text(encoding="utf-8"))
    rng = random.SystemRandom()
    labels = {"first": "new version", "second": "old version"} if against else {
        "first": "skill", "second": "baseline"
    }
    older = {}
    if against:
        older = {e["effect"]: e["skill"] for e in json.loads(against.read_text(encoding="utf-8"))["effects"]}
    pairs = []
    for entry in run["effects"]:
        # Held-out outputs stay unread, and research runs are reviewed separately.
        if entry["suite"] != "write-better" or entry["effect"].startswith("holdout-"):
            continue
        others = older.get(entry["effect"], []) if against else entry["baseline"]
        for skill, baseline in zip(entry["skill"], others):
            skill_side = rng.choice("AB")
            pairs.append(
                {
                    "effect": entry["effect"],
                    "skill_side": skill_side,
                    "A": skill["output"] if skill_side == "A" else baseline["output"],
                    "B": baseline["output"] if skill_side == "A" else skill["output"],
                }
            )
    rng.shuffle(pairs)

    sections = []
    key = {}
    for number, pair in enumerate(pairs, 1):
        original = _original_text(pair["effect"])
        context = (
            f"<details><summary>Original text</summary><pre>{html.escape(original)}</pre></details>"
            if original
            else ""
        )
        sections.append(
            SECTION.format(
                pair=number,
                number=number,
                effect=html.escape(pair["effect"]),
                context=context,
                a=html.escape(pair["A"]),
                b=html.escape(pair["B"]),
            )
        )
        key[str(number)] = {"effect": pair["effect"], "skill_side": pair["skill_side"], **labels}

    page = run_path.with_name("review.html")
    key_path = run_path.with_name("review-key.json")
    page.write_text(PAGE.format(count=len(pairs), sections="".join(sections)), encoding="utf-8")
    key_path.write_text(json.dumps(key, indent=2), encoding="utf-8")
    return page


def latest_choices() -> Path | None:
    downloads = list((Path.home() / "Downloads").glob("choices*.json"))
    return max(downloads, key=lambda path: path.stat().st_mtime, default=None)


def tally(key_path: Path, choices_path: Path) -> list[str]:
    key = json.loads(key_path.read_text(encoding="utf-8"))
    choices = json.loads(choices_path.read_text(encoding="utf-8"))
    totals: Counter[str] = Counter()
    by_effect: dict[str, Counter[str]] = defaultdict(Counter)
    reasons = []
    for item in choices:
        pair = key[item["pair"]]
        if item["choice"] is None:
            verdict = "unanswered"
        elif item["choice"] == "tie":
            verdict = "tie"
        else:
            first_wins = item["choice"] == pair["skill_side"]
            verdict = pair.get("first" if first_wins else "second", "skill" if first_wins else "baseline")
        totals[verdict] += 1
        by_effect[pair["effect"]][verdict] += 1
        if item["reason"].strip():
            reasons.append(f"[{pair['effect']}, chose {verdict}] {item['reason'].strip()}")
        for side in "AB":
            note = item.get(f"notes_{side.lower()}", "").strip()
            if note:
                is_first = side == pair["skill_side"]
                label = pair.get("first" if is_first else "second", "skill" if is_first else "baseline")
                reasons.append(f"[{pair['effect']}, about {label}] {note}")
    return [
        f"Overall: {dict(totals)}",
        *(f"  {effect}: {dict(counts)}" for effect, counts in by_effect.items()),
        *reasons,
    ]
