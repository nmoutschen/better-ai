"""code-better's dashboard: what the page shows of a change, and `render`, which writes the page as one file.

The page shows the agents at work and their latest steps, the tasks with the requirements of the change's own `spec.jsonl`,
and the conversation with the coordinator, in which its decisions and questions appear. The shared shell (`page/`) supplies
the header, the conversation column and the strips; this module supplies the data and the main section. Every record is
checked on its own: the page shows each valid record, and lists the invalid ones, with where they are, which field and why,
in an errors band, so one bad record never hides the others.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import time
from datetime import datetime, timezone

from .. import cli, page, paths, resources, schema
from ..paths import Unit

LOG = "conversation.jsonl"
# What an agent's last log line says about it, as the page shows it: the line's type, and the state it leaves the agent in.
STATES = {"start": "working", "step": "working", "asked": "waiting", "blocked": "blocked", "handed_back": "finished"}
CHECKED_ONLY = (
    "progress.jsonl",
    "next-steps.jsonl",
    "instructions.jsonl",
    "lessons.jsonl",
)  # the page does not show them
STATIC = "dashboard.html"


def lines_of(text: str, jsonl: bool) -> list:
    """The lines of a JSONL file, split on newlines only, without the empty piece after the last; a JSON file is one."""
    if not jsonl:
        return [text]
    pieces = [piece.removesuffix("\r") for piece in text.split("\n")]
    return pieces[:-1] if pieces and pieces[-1] == "" else pieces


def _cutoff() -> str:
    try:
        return resources.build_info().cutoff
    except LookupError:  # run in-process without a skill named: the shared default
        return resources.DEFAULT_CUTOFF


class Reader:
    """Reads the files of one change record by record through the schemas: the valid records come back, and each invalid
    one goes to `errors` with its file, line, field, reason and, if it parsed, its `by`. Lines in the format before this
    change are counted in `old`."""

    def __init__(self, unit: Unit):
        self.unit, self.errors, self.old, self.cache = unit, [], 0, {}
        self.docs = schema.load_schemas(*resources.schema_sources("code"))
        self.cutoff = _cutoff()

    def records(self, relative: str, keep_invalid: bool = False) -> list:
        """What `_records` reads; whatever else goes wrong with one file, for any reason, is that file's error."""
        try:
            return self._records(relative, keep_invalid)
        except Exception as error:
            self.errors.append(
                {
                    "file": relative,
                    "line": 1,
                    "field": "(file)",
                    "message": f"could not be shown: {type(error).__name__}",
                }
            )
            return []

    def _records(self, relative: str, keep_invalid: bool = False) -> list:
        """The records of one file, in line order; none if it does not exist. The file is read once and that text is
        validated and shown, so a write in between is in neither. A record with errors is left out, unless
        `keep_invalid`: then it stays, with its messages in `_errors`, so the page can show what it can of it. A line
        that is not JSON is never a record."""
        path = self.unit.target(relative)
        if not path.is_file():
            return []
        jsonl = path.suffix == ".jsonl"
        try:
            text = schema.read_checked(path, jsonl)
        except (OSError, UnicodeDecodeError) as error:
            self.errors.append({"file": relative, "line": 1, "field": "(file)", "message": f"cannot be read: {error}"})
            return []
        notices: list = []
        found = schema.check_text(path, text, self.docs, self.cache, cutoff=self.cutoff, notices=notices)
        self.old += len(notices)
        parsed = {}
        for number, piece in enumerate(lines_of(text, jsonl), 1):
            try:
                value = json.loads(piece)
            except (ValueError, RecursionError):
                continue
            parsed[number] = value if isinstance(value, dict) else None
        by_line: dict = {}
        for error in found:
            record = parsed.get(error.line)
            by = record.get("by") if record else None
            entry = {"file": relative, "line": error.line, "field": error.field, "message": error.message}
            self.errors.append({**entry, "by": schema.plain(by)} if isinstance(by, str) and by else entry)
            by_line.setdefault(error.line, []).append(error)
        kept = []
        for number, record in parsed.items():
            if record is None or (number in by_line and not keep_invalid):
                continue
            if number in by_line:
                status = record.get("status")
                record = schema.strip_invalid(record, by_line[number])
                if isinstance(status, str):
                    record["status"] = schema.plain(
                        status
                    )  # only text on the page, so a status that failed shows as written
                if not isinstance(record.get("id"), str) or not record["id"]:
                    record["id"] = f"(line {number})"
            kept.append(record)
        return kept

    def folder(self, pattern: str) -> list:
        return sorted(self.unit.path.glob(pattern))


def mtime(unit: Unit, *relatives: str) -> float:
    """The latest modification time of the files that exist, or 0."""
    found = 0.0
    for relative in relatives:
        with contextlib.suppress(OSError, paths.Refused):
            found = max(found, os.stat(unit.target(relative)).st_mtime)
    return found


def agent(reader: Reader, name: str, modes: dict) -> dict:
    """An agent from its two files in logs/: what it works on from <name>.card.json, which the coordinator writes when
    it starts the agent (role, task, branch), and its state from the last valid line of <name>.jsonl, the log the agent
    writes. Its mode is its task's."""
    card, log = f"logs/{name}.card.json", f"logs/{name}.jsonl"
    about = next(iter(reader.records(card)), {})
    lines = [
        {key: line[key] for key in ("type", "text", "result", "at") if key in line} for line in reader.records(log)
    ]
    return {
        "name": name,
        **{key: about.get(key) or "" for key in ("role", "task", "branch")},
        "mode": modes.get(about.get("task"), ""),
        "state": STATES.get(lines[-1]["type"], "working") if lines else "working",
        "lines": lines[-40:],
        "_changed": mtime(reader.unit, card, log),
    }


def decision(record: dict, changed: float) -> dict:
    """A decision as the page shows it: the record, with where it is from and, if it did not validate, its messages in
    `_errors`. A decision whose `at` did not validate takes the time its file changed, so the thread can place it."""
    shown = dict(record)
    if not isinstance(shown.get("at"), str):
        shown["at"] = datetime.fromtimestamp(changed or time.time(), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    about = shown.get("about") if isinstance(shown.get("about"), dict) else {}
    shown["task"] = about.get("task", "") if isinstance(about.get("task"), str) else ""
    shown["_changed"] = changed
    return shown


def collect(unit: Unit) -> dict:
    """Everything the page shows from the folder's files, and `errors`, the records that are not valid. It never
    raises, whatever the reason: a failure is an error entry."""
    try:
        return _collect(unit)
    except Exception as error:
        message = f"could not be shown: {type(error).__name__}"
        return {
            "name": unit.slug,
            "tasks": [],
            "requirements": {},
            "agents": [],
            "decisions": [],
            "conversation": [],
            "old": 0,
            "errors": [{"file": "(folder)", "line": 1, "field": "(folder)", "message": message}],
        }


def _collect(unit: Unit) -> dict:
    try:
        reader = Reader(unit)
    except schema.SchemaError as error:
        return {
            "name": unit.slug,
            "tasks": [],
            "requirements": {},
            "agents": [],
            "decisions": [],
            "conversation": [],
            "old": 0,
            "errors": [{"file": "schemas", "line": 1, "field": "(schemas)", "message": str(error)}],
        }
    head = reader.records(unit.kind.head)  # its errors are shown; the tasks carry their own mode
    goal = head[0].get("goal") if head else None
    title = goal.strip().splitlines()[0].strip() if isinstance(goal, str) and goal.strip() else unit.slug
    tasks = reader.records("tasks.jsonl", keep_invalid=True)
    spec = reader.records("spec.jsonl")
    conversation_events = reader.records(LOG)
    changed = mtime(unit, "decisions.jsonl")
    decisions = [decision(r, changed) for r in reader.records("decisions.jsonl", keep_invalid=True)]
    modes = {t["id"]: t.get("mode", "") for t in tasks if "id" in t}
    names = sorted(
        {
            f.name.removesuffix(".card.json").removesuffix(".jsonl")
            for f in [*reader.folder("logs/*.card.json"), *reader.folder("logs/*.jsonl")]
        }
    )
    agents = [agent(reader, name, modes) for name in names]
    for name in CHECKED_ONLY:
        reader.records(name)
    return {
        "name": title,
        "tasks": tasks,
        "requirements": {r["id"]: r["statement"] for r in spec if r.get("type") == "spec"},
        "agents": agents,
        "decisions": decisions,
        "conversation": conversation_events,
        "old": reader.old,
        "errors": reader.errors,
    }


def load(unit: Unit) -> dict:
    return collect(unit)


SPEC = page.PageSpec(
    title="Change dashboard",
    agent="coordinator",
    main="code/dashboard.html",
    load=load,
    events="dashboard-events.schema.json",
    assets={"/dashboard.css": "code/dashboard.css", "/dashboard.js": "code/dashboard.js"},
    css=("/dashboard.css",),
    js=("/dashboard.js",),
    capabilities=("decisions",),
    methods=("comment",),
    items=("comment", "note", "answer"),
    empty="Nothing yet. Click an agent to ask about its work, or write to the coordinator below.",
)


# ---------------------------------------------------------------- render


def static_page(unit: Unit) -> str:
    """The page as one file that opens without a server: the shell with its CSS and JS inline and the data of now in it.
    What the user writes in it stays in the page; nothing reaches the agent."""
    text = page.shell(SPEC)
    for url, name in SPEC.table().items():
        asset = resources.read_text(name)
        if url.endswith(".css"):
            text = text.replace(f'<link href="{url}" rel="stylesheet">', "<style>\n" + asset + "\n</style>")
        elif url == "/page.js":
            data = page._json_for_html({**load(unit), "now": time.time()})
            text = text.replace(
                f'<script src="{url}"></script>',
                f'<script type="application/json" id="page-data">{data}</script>\n<script>\n'
                + asset.replace("</script", "<\\/script")
                + "\n</script>",
            )
        elif url.endswith(".js"):
            text = text.replace(
                f'<script src="{url}"></script>', "<script>\n" + asset.replace("</script", "<\\/script") + "\n</script>"
            )
    return text


def _render_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("unit", help="the change, such as .code/my-change")


@cli.verb(
    "render",
    help=f"write the dashboard as one page, {STATIC}, in the unit",
    arguments=_render_arguments,
)
def render(args: argparse.Namespace, run: cli.Run) -> int:
    unit = paths.resolve_unit(args.unit, run.skill)
    paths.write_atomic(unit, STATIC, static_page(unit).encode("utf-8"))
    run.out(f"{unit.label}/{STATIC}")
    return cli.EXIT_DONE
