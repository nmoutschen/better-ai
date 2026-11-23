"""The records and folders of code-better's tests: builders for a small valid change folder, written as the commands
would write it, and what the dashboard and `check` make of it. Used by the test modules of the dashboard, so none
imports another."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from better_ai import paths, resources, schema  # noqa: E402
from better_ai.code import SKILL, dashboard  # noqa: E402

DOCS = schema.load_schemas(*resources.schema_sources("code"))
AT = "2026-11-21T10:00:00Z"


def check_record(record, names):
    """The problems of one record against the named schemas of code-better, as (field, message)."""
    found = []
    for name in names:
        found += [(p.field, p.message) for p in schema.validate_instance(record, DOCS[name], DOCS)]
    return list(dict.fromkeys(found))


def load(folder: Path, unit=None) -> dict:
    """What the dashboard shows of a change folder; a loop over one folder resolves the unit once and passes it."""
    return dashboard.load(unit or paths.resolve_unit(str(folder), SKILL))


def write(folder: Path, relative: str, records, as_json=False):
    path = folder / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if as_json:
        path.write_text(json.dumps(records[0]) + "\n", encoding="utf-8")
    else:
        path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return path


def spec(identity, statement="The upload service shall reject empty files.", **more):
    record = {"type": "spec", "at": AT, "by": "coordinator", "id": identity, "statement": statement}
    record["source"] = {"type": "request", "sentence": "empty uploads should fail loudly"}
    record["checked_by"] = "code review"
    return {**record, **more}


def task(identity, **more):
    record = {
        "type": "task",
        "at": AT,
        "by": "coordinator",
        "id": identity,
        "task": "Reject empty uploads",
        "mode": "feature",
        "requirements": ["S1"],
        "check": "uv run pytest",
        "status": "todo",
    }
    return {**record, **more}


def code(mode="coordinate", design=None):
    design = design or {"type": "request", "text": "empty uploads should fail loudly"}
    return {
        "type": "code",
        "at": AT,
        "by": "coordinator",
        "goal": "Uploads fail loudly",
        "design": design,
        "mode": mode,
    }


def card(role, task_id, **more):
    return {"type": "card", "at": AT, "by": "coordinator", "role": role, "task": task_id, "branch": "b", **more}


def log(kind, by, text="x", **more):
    return {"type": kind, "at": AT, "by": by, "text": text, **more}


def change(root: Path, mode="coordinate", tasks=None, specs=None, design=None) -> Path:
    """A small valid change folder: code.json, one spec record, the given tasks."""
    folder = root / ".code" / "c"
    write(folder, "code.json", [code(mode, design)], as_json=True)
    if specs is not False:
        write(folder, "spec.jsonl", specs or [spec("S1")])
    write(folder, "tasks.jsonl", tasks or [task("T1")])
    return folder


def check(folder: Path):
    return schema.check_paths([folder], docs=DOCS)
