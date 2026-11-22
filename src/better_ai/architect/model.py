"""What the architecture page shows, read from a change folder: the records of each file, checked one by one, the
diagram's parts and their fingerprints, what changed since the last review, and which perspectives must run again.

`load(unit)` is the page's payload and never raises for a bad file: what is wrong is in `errors`, each with its file,
line, field and reason, and a bad record stays on the page without the fields that failed. `read_folder` is the same
read for the commands (`review`, `specs`, `render`).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .. import paths, resources, schema
from ..paths import Unit
from . import diagram

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


def lines_of(text: str, jsonl: bool) -> list:
    """The lines of a JSONL file, split on newlines only, without the empty piece after the last; a JSON file is one."""
    if not jsonl:
        return [text]
    pieces = [piece.removesuffix("\r") for piece in text.split("\n")]
    return pieces[:-1] if pieces and pieces[-1] == "" else pieces


MAX_DEPTH = 50  # no record of these files nests deeper than a design.json step


def parse(piece: str):
    """One JSON value as the page can show it: no NaN or Infinity (the browser cannot read them), and nothing nested
    so deep that Python gives up."""

    def refuse(word):
        raise ValueError(f"{word} is not a JSON value")

    def finite(word):
        value = float(word)
        if value in (float("inf"), float("-inf")):
            raise ValueError(f"{word} is too large")
        return value

    try:
        value = json.loads(piece, parse_constant=refuse, parse_float=finite)
    except RecursionError:
        raise ValueError("nested too deeply") from None
    pending = [(value, 1)]
    while pending:  # no recursion: a line may be as deep as it likes
        item, depth = pending.pop()
        if isinstance(item, (dict, list)):
            if depth > MAX_DEPTH:
                raise ValueError(f"nested more than {MAX_DEPTH} levels deep")
            pending.extend((inner, depth + 1) for inner in (item.values() if isinstance(item, dict) else item))
    return value


class Reader:
    """Reads the files of one change folder record by record through the schema module: the records come back, and each
    invalid one goes to `errors` with its file, line, field, reason and, if it parsed, its `by`."""

    def __init__(self, unit: Unit):
        self.unit, self.errors, self.cache = unit, [], {}
        self.docs = schema.load_schemas(*resources.schema_sources("architect"))

    def error(self, name, line, field, message, by=None):
        entry = {"file": name, "line": line, "field": field, "message": message}
        self.errors.append({**entry, "by": schema.plain(by)} if isinstance(by, str) and by else entry)

    def records(self, name: str, keep_invalid: bool = False) -> list:
        """What `_records` reads; whatever else goes wrong with one file, for any reason, is that file's error."""
        try:
            return self._records(name, keep_invalid)
        except Exception as exc:
            self.error(name, 1, "(file)", f"could not be shown: {paths.reason(exc)}")
            return []

    def _records(self, name: str, keep_invalid: bool = False) -> list:
        """The records of one file, in line order; none if it does not exist. The file is read once and that text is
        validated and shown, so a write in between is in neither. A record with errors is left out, unless
        `keep_invalid`: then it stays without the fields that failed, and its messages in `_errors`, so the page can
        show what it can of it. A line that is not JSON is never a record."""
        path = self.unit.target(name)  # refuses a symlink on the way
        if not path.is_file():
            return []
        jsonl = path.suffix == ".jsonl"
        try:
            text = schema.read_checked(path, jsonl)
        except (OSError, UnicodeDecodeError) as exc:
            self.error(name, 1, "(file)", f"cannot be read: {exc}")
            return []
        try:
            found = schema.check_text(path, text, self.docs, self.cache)
        except (RecursionError, ValueError, TypeError, KeyError, AttributeError, OverflowError) as exc:
            self.error(name, 1, "(file)", f"cannot be checked: {exc}")
            return []
        flagged = {problem.line for problem in found}
        parsed = {}
        for number, piece in enumerate(lines_of(text, jsonl), 1):
            try:
                value = parse(piece)
            except ValueError as exc:
                if number not in flagged:  # valid for the schema, but not for the page
                    self.error(name, number, "(record)", f"not valid JSON: {exc}")
                continue
            parsed[number] = value if isinstance(value, dict) else None
        by_line: dict = {}
        for problem in found:
            record = parsed.get(problem.line)
            self.error(name, problem.line, problem.field, problem.message, record.get("by") if record else None)
            by_line.setdefault(problem.line, []).append(problem)
        kept = []
        for number, record in parsed.items():
            if record is None or (number in by_line and not keep_invalid):
                continue
            if number in by_line:
                record = schema.strip_invalid(record, by_line[number])
                if not isinstance(record.get("id"), str) or not record["id"]:
                    record["id"] = f"(line {number})"
            kept.append(record)
        return kept


def blank(name: str, errors: list) -> dict:
    return {
        "errors": errors,
        "architect": {},
        "design": None,
        "parts": {},
        "hashes": {},
        "requirements": [],
        "perspectives": [],
        "findings": [],
        "reviews": [],
        "decisions": [],
        "spec": [],
        "name": name,
    }


def read_design(reader: Reader):
    """The design as far as it is usable, with its parts and their fingerprints; no design if it cannot be drawn."""
    records = reader.records("design.json", keep_invalid=True)
    if not (reader.unit.target("design.json")).is_file():
        reader.error("design.json", 1, "(file)", "missing file")
    design = records[0] if records else None
    if design is None:
        return None, {}, {}
    usable = diagram.without_nulls({"containers": design.get("containers"), "flows": design.get("flows") or []})
    if not isinstance(usable.get("containers"), dict):
        return None, {}, {}
    try:
        parts, hashes = diagram_parts(usable)
        return usable, parts, hashes
    except (AttributeError, IndexError, KeyError, TypeError, ValueError) as exc:
        reader.error("design.json", 1, "(diagram)", str(exc))
        return None, {}, {}


def read_folder(unit: Unit) -> dict:
    """Read and validate the folder's files, record by record: the records, the diagram's parts, and `errors`."""
    try:
        reader = Reader(unit)
    except schema.SchemaError as exc:
        return blank(unit.slug, [{"file": "schemas", "line": 1, "field": "(schemas)", "message": str(exc)}])
    meta = reader.records("architect.json", keep_invalid=True)
    if not unit.target("architect.json").is_file():
        reader.error("architect.json", 1, "(file)", "missing file")
    architect = meta[0] if meta else {}
    design, parts, hashes = read_design(reader)
    data = blank(unit.slug, reader.errors)
    data.update(architect=architect, design=design, parts=parts, hashes=hashes)
    for name in FILES[2:]:
        data[Path(name).stem] = reader.records(name, keep_invalid=True)
    for name in CHECKED_ONLY:
        reader.records(name)
    return data


def diagram_parts(design):
    """Index the same boxes, arrows and steps across both versions for links and comments."""
    parts, hashes = {}, {}

    def add(key, item, part):
        require(key not in parts, f"duplicate diagram part {key!r}")
        parts[key] = {**part, "key": key}
        hashes[key] = hashlib.sha256(json.dumps(item, sort_keys=True).encode()).hexdigest()

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
    return parts, hashes


def changed_parts(hashes, review):
    previous = review["hashes"] if review else {}
    return [key for key in dict.fromkeys((*hashes, *previous)) if hashes.get(key) != previous.get(key)]


def render_diagrams(design, marks):
    try:
        layout = diagram.layout({**design, "findings": marks})
        containers = {s: diagram.svg_containers(layout, s) for s in diagram.STATES}
        flows = [
            {
                "name": flow["name"],
                "new": flow.get("in") == ["after"],
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


def model(data):
    """What the page shows: the records, the diagrams with the findings marked, what changed since the last review and
    which perspectives must run again, and `errors`. It draws what it is given: a record that is not valid arrives
    without the fields that failed."""
    errors = list(data["errors"])
    design, parts = data["design"], data["parts"]
    reviews = [shown(r, perspectives=[], changed=[], hashes={}, labels={}) for r in data["reviews"]]
    review = reviews[-1] if reviews else None
    changes = dict.fromkeys(changed_parts(data["hashes"], review) if design else [])
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
            [key for key in changed_parts(data["hashes"], last) if key in own_findings or key not in with_findings]
            if last
            else []
        )
        if last is None or affected:
            rerun.append(ident)
            changes.update(dict.fromkeys(affected))
    containers, flows = {state: "" for state in diagram.STATES}, []
    if design:
        try:
            containers, flows = render_diagrams(design, marks)
        except ValueError as exc:
            errors.append({"file": "design.json", "line": 1, "field": "(diagram)", "message": str(exc)})
    meta = data["architect"]
    requirements = [shown(r, kind="", text="", source={"type": "missing"}) for r in data["requirements"]]
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
        "removed": [key for key in changes if key not in parts],
        "change_labels": {key: labels.get(key, key) for key in changes},
        "removed_labels": {key: labels.get(key, key) for key in known if key not in parts},
        "rerun": rerun,
        "containers": containers,
        "flows": flows,
    }


def load(unit: Unit) -> dict:
    """The page's payload for a unit. It never raises for a bad file: what is wrong is in `errors`."""
    try:
        return model(read_folder(unit))
    except Exception as exc:  # for any reason: the page shows its errors band, not a failure
        message = f"could not be shown: {paths.reason(exc)}"
        error = {"file": "(unit)", "line": 1, "field": "(unit)", "message": message}
        return empty_model(unit.slug, error)


def empty_model(name: str, error: dict) -> dict:
    """What `model` makes of a folder with nothing readable, written out so that no failure can reach it."""
    return {
        "errors": [error],
        "title": name,
        "summary": "",
        "scope": "",
        "accepted": [],
        "requirements": [],
        "perspectives": [],
        "findings": [],
        "reviews": [],
        "decisions": [],
        "spec": [],
        "parts": {},
        "since": [],
        "removed": [],
        "change_labels": {},
        "removed_labels": {},
        "rerun": [],
        "containers": {state: "" for state in ("before", "after")},
        "flows": [],
    }
