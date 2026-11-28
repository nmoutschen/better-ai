"""code-better's dashboard: what the page shows of a change, and `render`, which writes the page as one file.

The page shows the agents at work and their latest steps, the tasks with the requirements of the change's own `spec.jsonl`,
and the conversation with the coordinator, in which its decisions and questions appear. The shared shell (`page/`) supplies
the header, the conversation column and the strips; this module supplies the data and the main section. Every record is
checked on its own: the page shows each valid record, and lists the invalid ones, with where they are, which field and why,
in an errors band, so one bad record never hides the others.
"""

from __future__ import annotations

import contextlib
import os
import time
from datetime import datetime, timezone

from .. import page, paths, records, resources, schema
from ..paths import Unit
from . import activity

# What an agent's last log line says about it, as the page shows it: the line's type, and the state it leaves the agent in.
STATES = {"start": "working", "step": "working", "asked": "waiting", "blocked": "blocked", "handed_back": "finished"}
CHECKED_ONLY = (
    "progress.jsonl",
    "next-steps.jsonl",
    "instructions.jsonl",
    "lessons.jsonl",
)  # the page does not show them
STATIC = "dashboard.html"


class Reader:
    """Reads the files of one change record by record through the schemas (`schema.read_records`): the valid records
    come back, and each invalid one goes to `errors` with its file, line, field, reason and, if it parsed, its `by`."""

    def __init__(self, unit: Unit):
        self.unit, self.errors, self.cache = unit, [], {}
        self.docs, self.cutoff, self.now = schema.docs_for("code"), resources.cutoff(), datetime.now(timezone.utc)

    def records(self, relative: str, keep_invalid: bool = False) -> list:
        """The records of one file, in line order; none if it does not exist. A record with errors is left out, unless
        `keep_invalid`: then it stays, with its messages in `_errors`, so the page can show what it can of it."""
        return self.read(relative, keep_invalid).records

    def read(self, relative: str, keep_invalid: bool = False) -> schema.Read:
        """What `records` reads, with the line of each record."""
        read = schema.read_records(self.unit, relative, self.docs, self.cache, self.now, self.cutoff, keep_invalid)
        self.errors.extend(read.errors)
        return read

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
    written = reader.records(log)
    lines = [{key: line[key] for key in ("type", "text", "result", "at") if key in line} for line in written]
    heard = page.last_word(written, name)
    return {
        "name": name,
        **{key: about.get(key) or "" for key in ("role", "task", "branch", "at")},
        "mode": modes.get(about.get("task"), ""),
        "state": STATES.get(lines[-1]["type"], "working") if lines else "working",
        # its last 40 lines, and every start and hand-back before them: the page draws one phase per round from them,
        # as a coordinator may resume the same agent for the next round
        "lines": [
            line for i, line in enumerate(lines) if i >= len(lines) - 40 or line["type"] in ("start", "handed_back")
        ],
        # when the agent started: its first line, which the 40 lines kept for the page may no longer hold
        "started": lines[0]["at"] if lines and isinstance(lines[0].get("at"), str) else "",
        # its last word, by the rule every page shares: the page says a build is quiet from it
        "last_word": heard.strftime(records.TIME) if heard else None,
        "_changed": mtime(reader.unit, card, log),
    }


def git_activity(unit: Unit, agents: list) -> dict:
    """The git activity of each branch an agent's card names, since the first card that names it; a branch git cannot
    read is left out."""
    since: dict[str, float] = {}
    for a in agents:
        branch, at = a.get("branch"), a.get("at")
        if isinstance(branch, str) and branch and isinstance(at, str):
            with contextlib.suppress(ValueError):
                when = datetime.strptime(at, records.TIME).replace(tzinfo=timezone.utc).timestamp()
                since[branch] = min(since.get(branch, when), when)
    if not since:
        return {}
    trees = activity.worktrees(unit.root)
    found = {branch: activity.branch_activity(unit.root, branch, when, trees) for branch, when in since.items()}
    return {branch: data for branch, data in found.items() if data is not None}


def decision(record: dict, changed: float) -> dict:
    """A decision as the page shows it: the record, with where it is from and, if it did not validate, its messages in
    `_errors`. A decision whose `at` did not validate takes the time its file changed, so the thread can place it."""
    shown = dict(record)
    if not isinstance(shown.get("at"), str):
        shown["at"] = datetime.fromtimestamp(changed or time.time(), timezone.utc).strftime(records.TIME)
    about = shown.get("about") if isinstance(shown.get("about"), dict) else {}
    shown["task"] = about.get("task", "") if isinstance(about.get("task"), str) else ""
    shown["_changed"] = changed
    return shown


def load(unit: Unit) -> dict:
    """Everything the page shows from the folder's files, and `errors`, the records that are not valid. Only a file
    that cannot be read or parsed becomes an error entry; a failure in this code is a bug and reaches the page's bug path."""
    reader = Reader(unit)
    head = reader.records(unit.kind.head)  # its errors are shown; the tasks carry their own mode
    goal = head[0].get("goal") if head else None
    title = goal.strip().splitlines()[0].strip() if isinstance(goal, str) and goal.strip() else unit.slug
    tasks = reader.records("tasks.jsonl", keep_invalid=True)
    spec = reader.records("spec.jsonl")
    conversation_events = page.log_records(reader.read(page.LOG))  # with their lines, which `read` counts in
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
    rounds = reader.records("rounds.jsonl")
    times = [r.get("at") for r in [*head, *tasks, *agents, *rounds] if isinstance(r.get("at"), str)]
    times += [line["at"] for a in agents for line in a["lines"] if isinstance(line.get("at"), str)]
    return {
        "name": title,
        "start": min(times) if times else None,
        "tasks": tasks,
        "requirements": {r["id"]: r["statement"] for r in spec if r.get("type") == "spec"},
        "agents": agents,
        "rounds": [r for r in rounds if r.get("type") == "round"],
        "fixes": [r for r in rounds if r.get("type") == "fix"],
        "git": git_activity(unit, agents),
        "decisions": decisions,
        "conversation": conversation_events,
        "errors": reader.errors,
    }


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
    empty="Nothing yet. Click a task to ask about it, or write to the coordinator below.",
    rendered=STATIC,
    static_data=lambda unit, run: {**load(unit), "now": time.time()},
)
