"""Pass when the After design keeps every planted Before part by its id and marks every new part as added.

Planted parts are the nodes, edges, groups, flows and flow steps of design.json at $START_COMMIT, all in Before.
Each must still be in the final design.json with the same id, its `in` absent or holding "before" (a removed part
stays, marked ["before"]). Each part not in the planted file must have `in` == ["after"]; a step may instead omit
`in` when its flow is new and marked ["after"]. At least one part must be added.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

PATH = "docs/designs/2026-11-order-export/design.json"


def parts(design: dict) -> dict:
    """Map each part's key, such as node:api or step:order/s1, to (part, its flow or None)."""
    found = {}
    containers = design.get("containers", {})
    for kind, name in (("nodes", "node"), ("edges", "edge"), ("groups", "group")):
        for item in containers.get(kind, []):
            found[f"{name}:{item.get('id')}"] = (item, None)
    for index, flow in enumerate(design.get("flows", []), start=1):
        flow_id = flow.get("id") or f"flow{index}"
        found[f"flow:{flow_id}"] = (flow, None)
        for step in flow.get("steps", []):
            found[f"step:{flow_id}/{step.get('id')}"] = (step, flow)
    return found


planted = json.loads(
    subprocess.run(
        ["git", "show", f"{os.environ['START_COMMIT']}:{PATH}"], capture_output=True, text=True, check=True
    ).stdout
)
try:
    final = json.loads(Path(PATH).read_text())
except (OSError, ValueError) as error:
    sys.exit(f"cannot read {PATH}: {error}")

before, after = parts(planted), parts(final)
problems = []
for key in before:
    if key not in after:
        problems.append(f"{key} is gone (a removed part stays with in: [\"before\"])")
    elif "in" in after[key][0] and "before" not in after[key][0]["in"]:
        problems.append(f"{key} was in Before but has in: {after[key][0]['in']}")
added = [key for key in after if key not in before]
for key in added:
    part, flow = after[key]
    if part.get("in") == ["after"]:
        continue
    if key.startswith("step:") and "in" not in part and flow is not None and flow.get("in") == ["after"]:
        continue
    problems.append(f"{key} is new but has in: {part.get('in', 'absent')}")
if not added:
    problems.append("no part was added to After")
if problems:
    sys.exit("\n".join(problems))
print(f"all {len(before)} planted parts kept; {len(added)} added, each marked after")
