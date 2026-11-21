"""Pass when docs/designs/2026-11-order-export/requirements.jsonl holds at least one record, every record has a source
of a known type, every `request` source quotes a sentence of the planted request.md word for word (whitespace
normalised), and every `file` source names a file that exists in the repository."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

FOLDER = "docs/designs/2026-11-order-export"
TYPES = {"request", "file", "user", "guessed"}


def normalise(text: str) -> str:
    """Collapse runs of whitespace, so a line wrap does not count as a change of words."""
    return re.sub(r"\s+", " ", text).strip()


request = normalise(
    subprocess.run(
        ["git", "show", f"{os.environ['START_COMMIT']}:{FOLDER}/request.md"], capture_output=True, text=True, check=True
    ).stdout
)
path = Path(FOLDER) / "requirements.jsonl"
if not path.exists():
    sys.exit(f"{path} does not exist")
records = []
for number, line in enumerate(path.read_text().splitlines(), 1):
    if line.strip():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as error:
            sys.exit(f"{path} line {number} is not JSON: {error}")
if not records:
    sys.exit(f"{path} holds no record")
for record in records:
    source = record.get("source") or {}
    kind = source.get("type")
    if kind not in TYPES:
        sys.exit(f"{record.get('id')}: source type {kind!r} is not one of {sorted(TYPES)}")
    if kind == "request" and (not source.get("sentence") or normalise(source["sentence"]) not in request):
        sys.exit(f"{record.get('id')}: request sentence is not in request.md word for word: {source.get('sentence')!r}")
    if kind == "file":
        named = re.split(r"[:#]", str(source.get("file") or ""), maxsplit=1)[0].removeprefix("./")
        if not named or not Path(named).is_file():
            sys.exit(f"{record.get('id')}: source file {source.get('file')!r} does not exist")
print(len(records), "requirements, every request and file source checks out")
