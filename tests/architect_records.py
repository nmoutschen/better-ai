"""Builders and helpers for the architect-better tests: the example records, a change folder in a repository, the
command run in this process. Shared by test_architect and test_architect_formats."""

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import better  # noqa: E402

from better_ai import paths, resources, schema  # noqa: E402
from better_ai.architect import SKILL as ARCHITECT  # noqa: E402
from better_ai.architect import model  # noqa: E402

SKILL_NAME = ARCHITECT.name


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "architect-better"
PACKAGE = ROOT / "src" / "better_ai" / "architect"
SCHEMAS = PACKAGE / "schemas"
EXAMPLES = json.loads((Path(__file__).parent / "fixtures" / "architect-better-examples.json").read_text())
AT = "2026-11-21T10:00:00Z"
DIGEST = "3a7f" * 16  # the spec page shows a digest as 3a7f…, cut short; the schema wants all 64 hex digits
DOCS = schema.load_schemas(*resources.schema_sources("architect"))


def unit_of(folder: Path) -> paths.Unit:
    """The unit a change folder is: it sits at `.architect/<slug>` of a repository."""
    return paths.resolve_unit(str(folder), ARCHITECT)


def load(folder: Path) -> dict:
    return model.load(unit_of(folder))


def read_folder(folder: Path) -> dict:
    return model.read_folder(unit_of(folder))


def run_cli(*args: str, stdin: str | None = None):
    """One command of architect-better, in this process: (exit code, stdout, stderr)."""
    done = better.call(SKILL_NAME, *args, stdin=stdin)
    return done.returncode, done.stdout, done.stderr


def check_record(record, names):
    problems = []
    for name in names:
        problems += [(p.field, p.message) for p in schema.validate_instance(record, DOCS[name], DOCS)]
    return list(dict.fromkeys(problems))


# The spec page's file kinds, and the schema each is checked against.
KINDS = {
    "architect.json": "architect.schema.json",
    "design.json": "design.schema.json",
    "requirements.jsonl": "requirements.schema.json",
    "perspectives.jsonl": "perspectives.schema.json",
    "findings.jsonl": "findings.schema.json",
    "decisions.jsonl": "decisions.schema.json",
    "reviews.jsonl": "reviews.schema.json",
    "spec.jsonl": "spec.schema.json",
}
JSON_FILES = ("architect.json", "design.json")


def examples(kind):
    out = []
    for e in EXAMPLES[kind]:
        record = json.loads(e["line"])
        if kind == "reviews.jsonl":
            record["hashes"] = {key: DIGEST for key in record["hashes"]}
        out.append((e["title"], record))
    return out


def write(folder: Path, name: str, records):
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if name in JSON_FILES:
        path.write_text(json.dumps(records[0], indent=1) + "\n", encoding="utf-8")
    else:
        path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return path


def read(folder: Path, name: str):
    text = (folder / name).read_text(encoding="utf-8")
    return json.loads(text) if name in JSON_FILES else [json.loads(line) for line in text.splitlines()]


def base(type_, **more):
    return {"type": type_, "at": AT, "by": "architect", **more}


def design():
    node = lambda ident, label, kind: {"id": ident, "label": label, "kind": kind}  # noqa: E731
    return base(
        "design",
        containers={
            "nodes": [node("user", "You", "person"), node("page", "Page", "page"), node("server", "Server", "service")],
            "edges": [
                {"id": "e1", "from": "user", "to": "page", "label": "reads"},
                {"id": "e3", "from": "page", "to": "server", "label": "POST /rpc"},
                {"id": "e4", "from": "server", "to": "page", "label": "answer"},
            ],
            "groups": [],
        },
        flows=[
            {
                "id": "ask",
                "name": "A builder asks",
                "participants": [{"id": "page", "box": "page"}, {"id": "server", "box": "server"}],
                "steps": [
                    {"id": "s6", "from": "page", "to": "server", "label": "POST"},
                    {"id": "s7", "from": "server", "to": "page", "label": "answer", "kind": "response"},
                ],
            }
        ],
    )


def folder_records():
    """A consistent folder: every pointer resolves, built from the spec page's examples."""
    request = "Add a dashboard that shows each agent's task, mode and state.\nShow each agent's task, mode and state."
    requirements = [r for _, r in examples("requirements.jsonl")]
    for ident, kind in (("F3", "functional"), ("Q1", "quality"), ("C1", "constraint")):
        requirements.append(base("requirement", id=ident, kind=kind, text=f"{ident} text.", source={"type": "guessed"}))
    review = examples("reviews.jsonl")[0][1]
    review["hashes"] = {"box:user": DIGEST, "edge:e1": DIGEST}
    review["labels"] = {"box:user": "You", "edge:e1": "You to Page: reads"}
    return {
        "architect.json": [
            {**examples("architect.json")[0][1], "request": {"text": request, "from": {"type": "chat"}}}
        ],
        "design.json": [design()],
        "requirements.jsonl": requirements,
        "perspectives.jsonl": [r for _, r in examples("perspectives.jsonl")],
        "findings.jsonl": [r for _, r in examples("findings.jsonl")],
        "decisions.jsonl": [r for _, r in examples("decisions.jsonl")],
        "reviews.jsonl": [review],
        "spec.jsonl": [r for _, r in examples("spec.jsonl")],
    }


def make_folder(root: Path, **changes):
    """A change folder in a repo (a .git next to it); `changes` replaces a file's records, or None leaves it out."""
    (root / ".git").mkdir(exist_ok=True)
    folder = root / ".architect" / "c"
    files = folder_records()
    files.update(changes)
    for name, records in files.items():
        if records is not None:
            write(folder, name, records)
    return folder


def example_folder(root: Path) -> Path:
    """The fixture change folder as `.architect/ex` of a repository: its file sources are files of that repository."""
    root.mkdir(parents=True, exist_ok=True)
    (root / ".git").mkdir(exist_ok=True)
    folder = root / ".architect" / "ex"
    shutil.copytree(ROOT / "tests" / "fixtures" / "architect-example", folder)
    for name in ("PRINCIPLES.md", "src/better_ai/page/__init__.py"):
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, root / name)
    return folder


def planted_cases():
    """The eval cases' architect folders: (case name, repo, the folder in its repo)."""
    found = sorted((ROOT / "evals" / "cases" / "architect-better").glob("*/repo/docs/designs/*/architect.json"))
    return [(f.parents[4].name, f.parents[3], f.parent) for f in found]


def planted_unit(root: Path, repo: Path, folder: Path) -> Path:
    """A case's repository, checked out as a repository of its own, with its change folder also at `.architect/<slug>`."""
    copy = root / "repo"
    shutil.copytree(repo, copy)
    (copy / ".git").mkdir()
    unit = copy / ".architect" / folder.name
    shutil.copytree(copy / folder.relative_to(repo), unit)
    return unit


def check(folder: Path):
    return schema.check_paths([folder], docs=DOCS)


def run_check(folder: Path):
    return run_cli("check", str(folder))
