"""What the architecture page shows, read from a change folder: the records of each file, checked one by one, the
diagram's parts and their fingerprints, the fingerprints of the requirements and of each section of the design document,
what changed since the last review, and which perspectives must run again.

`load(unit)` is the page's payload and never raises for a bad file: what is wrong is in `errors`, each with its file,
line, field and reason, and a bad record stays on the page without the fields that failed. `read_folder` is the same
read for the commands (`review`, `specs`, `render`).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from .. import paths, resources, schema
from ..paths import Unit
from . import checks, diagram

FILES = (
    "architect.json",
    "design.json",
    "requirements.jsonl",
    "perspectives.jsonl",
    "findings.jsonl",
    "reviews.jsonl",
    "decisions.jsonl",
    "spec.jsonl",
)
CHECKED_ONLY = ("conversation.jsonl",)  # the page's log: checked here, read by the page module
TABS = ("requirements", "containers", "flows", "perspectives", "decisions", "spec")


def require(condition, message):
    if not condition:
        raise ValueError(message)


class Reader:
    """Reads the files of one change folder record by record through `schema.read_records`: the records come back, and
    each invalid one goes to `errors` with its file, line, field, reason and, if it parsed, its `by`."""

    def __init__(self, unit: Unit):
        self.unit, self.errors, self.cache = unit, [], {}
        self.docs = schema.docs_for("architect")
        self.now, self.cutoff = datetime.now(timezone.utc), resources.cutoff()

    def error(self, name, line, field, message):
        self.errors.append({"file": name, "line": line, "field": field, "message": message})

    def records(self, name: str, keep_invalid: bool = False) -> list:
        """The records of one file, in line order; with `keep_invalid`, a record with errors stays without the fields
        that failed, so the page can show what it can of it."""
        read = schema.read_records(self.unit, name, self.docs, self.cache, self.now, self.cutoff, keep_invalid)
        self.errors += read.errors
        return read.records


def blank(name: str, errors: list) -> dict:
    return {
        "errors": errors,
        "architect": {},
        "design": None,
        "parts": {},
        "hashes": {},
        "before": {},
        "requirements": [],
        "perspectives": [],
        "findings": [],
        "reviews": [],
        "decisions": [],
        "spec": [],
        "texts": {},
        "name": name,
    }


def read_design(reader: Reader):
    """The design as far as it is usable, with its parts and their fingerprints; no design if it cannot be drawn."""
    records = reader.records("design.json", keep_invalid=True)
    if not os.path.lexists(reader.unit.path / "design.json"):
        reader.error("design.json", 1, "(file)", "missing file")
    design = records[0] if records else None
    if design is None:
        return None, {}, ({}, {})
    usable = diagram.without_nulls({"containers": design.get("containers"), "flows": design.get("flows") or []})
    if not isinstance(usable.get("containers"), dict):
        return None, {}, ({}, {})
    try:
        parts, hashes, before = diagram_parts(usable)
        return usable, parts, (hashes, before)
    except (AttributeError, IndexError, KeyError, TypeError, ValueError) as exc:
        reader.error("design.json", 1, "(diagram)", str(exc))
        return None, {}, ({}, {})


def read_folder(unit: Unit) -> dict:
    """Read and validate the folder's files, record by record: the records, the diagram's parts, and `errors`."""
    try:
        reader = Reader(unit)
    except schema.SchemaError as exc:
        return blank(unit.slug, [{"file": "schemas", "line": 1, "field": "(schemas)", "message": str(exc)}])
    meta = reader.records("architect.json", keep_invalid=True)
    if not os.path.lexists(unit.path / "architect.json"):
        reader.error("architect.json", 1, "(file)", "missing file")
    architect = meta[0] if meta else {}
    design, parts, (hashes, before) = read_design(reader)
    data = blank(unit.slug, reader.errors)
    data.update(architect=architect, design=design, parts=parts, hashes=hashes)
    for name in FILES[2:]:
        data[Path(name).stem] = reader.records(name, keep_invalid=True)
    for name in CHECKED_ONLY:
        reader.records(name)
    data["texts"], before_texts = text_hashes(unit, architect, data["requirements"], reader)
    data["before"] = {**before, **before_texts}
    return data


fingerprint = schema.fingerprint  # the shared one: canonical JSON without `at` and `by`


def stored_fingerprint(value) -> str:
    """The fingerprint as reviews recorded it before the shared one, kept only so that a review written then still
    matches what it reviewed. Never written again."""
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def document_sections(text: str) -> dict[str, str]:
    """The sections of a Markdown document by their `## ` heading; what comes before the first is under `(start)`. A
    heading inside a fenced code block is text, and a heading used twice is numbered from its second use: `Risks (2)`."""
    sections: dict[str, list[str]] = {"(start)": []}
    current, fence = "(start)", None
    for line in text.splitlines():
        stripped = line.lstrip()
        if fence is None and stripped[:3] in ("```", "~~~"):
            fence = stripped[:3]
        elif fence is not None and stripped.startswith(fence):
            fence = None
        elif fence is None and line.startswith("## "):
            heading = line[3:].strip().rstrip("#").strip() or "(untitled)"
            current, n = heading, 1
            while current in sections:
                n += 1
                current = f"{heading} ({n})"
            sections[current] = []
            continue
        sections[current].append(line)
    return {heading: "\n".join(lines).strip() for heading, lines in sections.items()}


def text_label(key: str) -> str:
    """A text key in words: `section:<heading>` of the design document, or `requirement:<id>`."""
    kind, _, name = key.partition(":")
    return f"Requirement {name}" if kind == "requirement" else f"Design section {name}"


def document_text(unit: Unit, architect: dict, reader: Reader) -> str | None:
    """The text of the design document architect.json names; None if it names none, or one the source-file-exists
    check refuses (that check reports why)."""
    document = architect.get("document")
    name = document.get("file") if isinstance(document, dict) else None
    if not isinstance(name, str) or not name:
        return None
    try:
        return checks.read_repo_file(unit.root, name).decode("utf-8")
    except (paths.Refused, FileNotFoundError, IsADirectoryError):
        return None
    except (OSError, UnicodeDecodeError) as exc:
        reader.error("architect.json", 1, "document.file", f"cannot be read: {paths.reason(exc)}")
        return None


def text_hashes(
    unit: Unit, architect: dict, requirements: list, reader: Reader
) -> tuple[dict[str, str], dict[str, str]]:
    """The fingerprint of each requirement, without when and by whom it was written, and of each section of the design
    document: a review records them, so a change to either makes the review due again. Also the same in the form
    reviews stored before the shared fingerprint (`stored_fingerprint`)."""
    values = {
        f"requirement:{r['id']}": {k: v for k, v in r.items() if k not in ("at", "by")}
        for r in requirements
        if isinstance(r.get("id"), str)
    }
    text = document_text(unit, architect, reader)
    if text is not None:
        values.update((f"section:{heading}", body) for heading, body in document_sections(text).items())
    return (
        {key: fingerprint(value) for key, value in values.items()},
        {key: stored_fingerprint(value) for key, value in values.items()},
    )


def diagram_parts(design):
    """Index the same boxes, arrows and steps across both versions for links and comments, with each part's
    fingerprint, and the same in the form reviews stored before the shared fingerprint."""
    parts, hashes, before = {}, {}, {}

    def add(key, item, part):
        require(key not in parts, f"duplicate diagram part {key!r}")
        parts[key] = {**part, "key": key}
        hashes[key] = fingerprint(item, drop=())
        before[key] = stored_fingerprint(item)

    def ids(view, kind, ident):
        return [diagram.part_id(f"{view}-{state}", kind, ident) for state in diagram.STATES]

    nodes = {node["id"]: node for node in design["containers"]["nodes"]}
    for ident, node in nodes.items():
        add(
            f"box:{ident}",
            node,
            {
                "label": node["label"],
                "kind": "box",
                "ids": ids("c", "box", ident),
                "view": "containers",
                "icon": diagram.glyph(node["kind"]),
            },
        )
    for edge in design["containers"].get("edges", []):
        ident = edge["id"]
        route = f"{nodes[edge['from']]['label']} to {nodes[edge['to']]['label']}"
        add(
            f"edge:{ident}",
            edge,
            {
                "label": f"{route}: {edge.get('label', '')}",
                "route": route,
                "kind": "edge",
                "view": "containers",
                "ids": ids("c", "edge", ident),
            },
        )
    for i, flow in enumerate(design["flows"], 1):
        view = f"flow{i}"  # the drawing's own name for the flow; no stored key uses it
        participants = {p["id"]: nodes[p["box"]]["label"] for p in flow["participants"]}
        for participant in flow["participants"]:
            parts[f"box:{participant['box']}"]["ids"].extend(ids(view, "box", participant["id"]))
        for step, number in zip(flow["steps"], diagram.step_numbers(flow), strict=True):
            ident = step["id"]
            route = f"{participants[step['from']]} to {participants[step['to']]}"
            description = f"{step.get('label', '')} (Flows, step {number})"
            add(
                f"step:{flow['id']}/{ident}",
                step,
                {
                    "label": f"{route}: {description}",
                    "description": description,
                    "kind": "step",
                    "ids": ids(view, "step", ident),
                    "view": "flows",
                    "mark": f"{view}:step:{ident}",
                },
            )
    return parts, hashes, before


def _changed(now: dict, previous: dict, before: dict | None) -> list[str]:
    """The keys whose fingerprint differs from the one a review recorded, in either form it may have recorded."""
    before = before or {}
    return [
        key
        for key in dict.fromkeys((*now, *previous))
        if previous.get(key) != now.get(key) and (key not in before or previous.get(key) != before[key])
    ]


def changed_parts(hashes, review, before=None):
    previous = review["hashes"] if review else {}
    return _changed(hashes, previous, before)


def changed_texts(texts, review, before=None):
    """The requirements and design sections that changed since a review; none for a review that recorded no texts."""
    previous = review.get("texts") if review else None
    if previous is None:
        return []
    return _changed(texts, previous, before)


def render_diagrams(design, marks):
    try:
        layout = diagram.layout({**design, "findings": marks})
        containers = {s: diagram.svg_containers(layout, s) for s in diagram.STATES}
        flows = [
            {
                "name": flow["name"],
                "new": flow.get("in") == ["after"],
                "removed": flow.get("in") == ["before"],
                "versions": {
                    s: diagram.svg_flow(flow, s, layout, f"flow{i}") if diagram.visible(flow, s) else ""
                    for s in diagram.STATES
                },
            }
            for i, flow in enumerate(design["flows"], 1)
        ]
    except (AttributeError, IndexError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"design.json:1: {exc}") from exc
    return containers, flows


def text_of(record, key, default=""):
    value = record.get(key)
    return value if isinstance(value, str) else default


def list_of(record, key):
    value = record.get(key)
    return value if isinstance(value, list) else []


def shown(record, **defaults):
    """A record as the page draws it: the fields it has, and a harmless default for each one it lost to an error."""
    record = {k: v for k, v in record.items() if v is not None}  # an optional field that is null is absent
    return {**{k: v for k, v in defaults.items() if k not in record}, **record}


REQUIREMENT_KINDS = ("functional", "quality", "constraint")


def requirement_order(requirement):
    """Where a requirement sits on the page: by kind, then by the number in its ID (F2 before F10), whatever the order of
    the lines; a record whose kind or ID is not valid goes after the valid ones, in line order."""
    kind, ident = requirement["kind"], requirement.get("id", "")
    number = re.fullmatch(r"[A-Z]+([0-9]+)", ident) if isinstance(ident, str) else None
    if kind not in REQUIREMENT_KINDS or number is None:
        return len(REQUIREMENT_KINDS), float("inf")
    return REQUIREMENT_KINDS.index(kind), int(number[1])


def model(data):
    """What the page shows: the records, the diagrams with the findings marked, what changed since the last review and
    which perspectives must run again, and `errors`. It draws what it is given: a record that is not valid arrives
    without the fields that failed."""
    errors = list(data["errors"])
    design, parts = data["design"], data["parts"]
    reviews = [shown(r, perspectives=[], changed=[], hashes={}, labels={}, texts=None) for r in data["reviews"]]
    review = reviews[-1] if reviews else None
    texts = data.get("texts", {})
    before = data.get("before", {})
    changes = dict.fromkeys(changed_parts(data["hashes"], review, before) if design else [])
    changes.update(dict.fromkeys(changed_texts(texts, review, before)))
    known = set(parts)
    for recorded in reviews:
        known.update(recorded["hashes"])
    marks, findings_by_perspective = {}, {}
    findings = [shown(f, perspective="", parts=[], text="", confirmed=False, status="open") for f in data["findings"]]
    for finding in findings:
        keys = {part for group in finding["parts"] for part in group.split("+") if part in known}
        findings_by_perspective.setdefault(finding["perspective"], set()).update(keys)
        if review:
            for key in sorted(keys.intersection(parts)):
                target = parts[key].get("mark", key.removeprefix("box:"))
                marks.setdefault(target, []).append([finding["id"], finding["text"], finding["perspective"]])
        finding["handled_by"] = finding.get("handled_by") if finding["status"] == "handled" else None

    with_findings = set().union(*findings_by_perspective.values())
    last_reviews, labels = {}, {}
    for recorded in reviews:
        labels.update(recorded["labels"])
        for ident in recorded["perspectives"]:
            last_reviews[ident] = recorded
    labels.update((key, part["label"]) for key, part in parts.items())

    perspectives = [
        shown(p, name=p["id"], applies=False, why="", **{"from": {"type": "missing"}}) for p in data["perspectives"]
    ]
    rerun = []
    for perspective in perspectives:
        if perspective["applies"] is not True or not design:
            continue
        ident = perspective["id"]
        last = last_reviews.get(ident)
        own_findings = findings_by_perspective.get(ident, set())
        affected = (
            [
                key
                for key in changed_parts(data["hashes"], last, before)
                if key in own_findings or key not in with_findings
            ]
            if last
            else []
        )
        rewritten = changed_texts(texts, last, before)
        if last is None or affected or rewritten:
            rerun.append(ident)
            changes.update(dict.fromkeys(affected + rewritten))
    containers, flows = {state: "" for state in diagram.STATES}, []
    if design:
        try:
            containers, flows = render_diagrams(design, marks)
        except ValueError as exc:
            errors.append({"file": "design.json", "line": 1, "field": "(diagram)", "message": str(exc)})
    meta = data["architect"]
    requirements = [shown(r, kind="", text="", source={"type": "missing"}) for r in data["requirements"]]
    requirements.sort(key=requirement_order)  # stable: equal keys keep their line order
    return {
        "errors": errors,
        "title": text_of(meta, "title", data["name"]),
        "summary": text_of(meta, "summary"),
        "scope": text_of(meta, "scope"),
        "accepted": [t for t in list_of(meta, "accepted") if t in TABS],
        "requirements": [{**req, "wording": hashlib.sha256(req["text"].encode()).hexdigest()} for req in requirements],
        "perspectives": perspectives,
        "findings": findings,
        "reviews": reviews,
        "decisions": [shown(d, title="", drivers=[], chosen="", rejected=[], drawback="") for d in data["decisions"]],
        "spec": [shown(r, statement="", source=None, checked_by="") for r in data["spec"]],
        "parts": parts,
        "since": list(changes),
        "removed": [key for key in changes if key not in parts and key not in texts],
        "change_labels": {key: labels.get(key) or text_label(key) for key in changes},
        "removed_labels": {key: labels.get(key, key) for key in known if key not in parts},
        "rerun": rerun,
        "containers": containers,
        "flows": flows,
    }


def load(unit: Unit) -> dict:
    """The page's payload for a unit. A bad file is in `errors`; a failure in this code is a bug, not an error."""
    return model(read_folder(unit))
