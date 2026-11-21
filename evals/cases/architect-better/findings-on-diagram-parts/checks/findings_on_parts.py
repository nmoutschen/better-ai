"""Pass when findings.jsonl in the change folder holds at least one finding, every part key of every finding names a
box, arrow or flow step of design.json (as planted or as the agent left it), `confirmed` is a boolean and `handled_by`
is a string or null."""

import json
import os
import subprocess
import sys
from pathlib import Path

FOLDER = "docs/designs/2026-11-order-export"
FINDINGS = Path(FOLDER, "findings.jsonl")


def part_keys(design: dict) -> set[str]:
    """Every key a finding may use for this design: box:<node>, edge:<edge>, step:<flow id or flowN>/<step>."""
    keys = {f"box:{node['id']}" for node in design["containers"]["nodes"]}
    keys |= {f"edge:{edge['id']}" for edge in design["containers"]["edges"]}
    for number, flow in enumerate(design["flows"], 1):
        for name in {f"flow{number}", flow.get("id", f"flow{number}")}:
            keys |= {f"step:{name}/{step['id']}" for step in flow["steps"]}
    return keys


planted = subprocess.run(
    ["git", "show", f"{os.environ['START_COMMIT']}:{FOLDER}/design.json"], capture_output=True, text=True, check=True
).stdout
known = part_keys(json.loads(planted))
try:
    known |= part_keys(json.loads(Path(FOLDER, "design.json").read_text()))
except (OSError, ValueError, KeyError, TypeError):
    pass

if not FINDINGS.is_file():
    sys.exit(f"{FINDINGS} does not exist: no finding was recorded")
problems, count = [], 0
for number, line in enumerate(FINDINGS.read_text().splitlines(), 1):
    if not line.strip():
        continue
    try:
        finding = json.loads(line)
    except json.JSONDecodeError as error:
        sys.exit(f"{FINDINGS} line {number} is not JSON: {error}")
    count += 1
    name = finding.get("id", f"line {number}") if isinstance(finding, dict) else f"line {number}"
    if not isinstance(finding, dict):
        problems.append(f"{name}: not a JSON object")
        continue
    parts = finding.get("parts")
    if not isinstance(parts, list) or not parts:
        problems.append(f"{name}: parts is not a non-empty list")
    else:
        for group in parts:
            if not isinstance(group, str):
                problems.append(f"{name}: part {group!r} is not a string")
                continue
            unknown = [key for key in group.split("+") if key not in known]
            if unknown:
                problems.append(f"{name}: {unknown} name no box, edge or flow step of design.json")
    if not isinstance(finding.get("confirmed"), bool):
        problems.append(f"{name}: confirmed is {finding.get('confirmed')!r}, not true or false")
    if "handled_by" not in finding or not (finding["handled_by"] is None or isinstance(finding["handled_by"], str)):
        problems.append(f"{name}: handled_by is missing or neither a string nor null")
if not count:
    sys.exit(f"{FINDINGS} holds no finding")
if problems:
    sys.exit("\n".join(problems))
print(count, "findings, each on parts of design.json")
