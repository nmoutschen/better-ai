"""architect-better's checks across records, named by `x-check` in its schemas: the parts of a design and the
references inside it, the perspectives a finding is on, and what a requirement quotes from the request."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .. import resources
from ..schema import Context, hook

_ONE_KEY = r"(?:(?:box|edge):[^\s:+/]+|step:[^\s:+/]+/[^\s:+/]+)"
PART_KEY = re.compile(_ONE_KEY)


def _design_parts(context: Context) -> tuple[set[str], list[str]] | None:
    """The part keys of design.json and its flow ids; None if design.json is missing or not an object (its own
    checks say so)."""
    design = context.read_json("design.json")
    if not isinstance(design, dict):
        return None
    keys: set[str] = set()
    flow_ids: list[str] = []
    containers = design.get("containers")
    if isinstance(containers, dict):
        for kind, prefix in (("nodes", "box"), ("edges", "edge")):
            for item in containers.get(kind) if isinstance(containers.get(kind), list) else []:
                if isinstance(item, dict) and isinstance(item.get("id"), str):
                    keys.add(f"{prefix}:{item['id']}")
    for flow in design.get("flows") if isinstance(design.get("flows"), list) else []:
        if isinstance(flow, dict) and isinstance(flow.get("id"), str):
            flow_ids.append(flow["id"])
            for step in flow.get("steps") if isinstance(flow.get("steps"), list) else []:
                if isinstance(step, dict) and isinstance(step.get("id"), str):
                    keys.add(f"step:{flow['id']}/{step['id']}")
    return keys, flow_ids


def _review_hashed(context: Context) -> set[str]:
    keys: set[str] = set()
    for review in context.read_jsonl("reviews.jsonl") or []:
        if isinstance(review, dict) and isinstance(review.get("hashes"), dict):
            keys.update(review["hashes"])
    return keys


@hook("finding-parts")
def _finding_parts(record: dict, context: Context) -> list[tuple[str, str]]:
    """Each part key of a finding names a part of design.json, or one a review once recorded (a part the design has
    since dropped). A key that is not in the grammar is the schema's to report."""
    parts = record.get("parts")
    found = _design_parts(context)
    if not isinstance(parts, list) or found is None:
        return []
    known = found[0] | _review_hashed(context)
    problems = []
    for index, group in enumerate(parts):
        for key in group.split("+") if isinstance(group, str) else []:
            if PART_KEY.fullmatch(key) and key not in known:
                forms = "use box:<id>, edge:<id>, step:<flow id>/<step id>"
                if found[1]:
                    forms += f" (flow ids: {', '.join(found[1])})"
                problems.append((f"parts[{index}]", f"unknown part {key!r}; {forms}"))
    return problems


@hook("finding-perspective-applies")
def _finding_perspective_applies(record: dict, context: Context) -> list[tuple[str, str]]:
    """A finding is on a perspective that applies."""
    name = record.get("perspective")
    for item in context.read_jsonl("perspectives.jsonl") or []:
        if isinstance(item, dict) and item.get("id") == name and item.get("applies") is False:
            return [("perspective", f"{name!r} does not apply (applies is false in perspectives.jsonl)")]
    return []


@hook("review-parts")
def _review_parts(record: dict, context: Context) -> list[tuple[str, str]]:
    """The keys of a review are parts, `labels` has one for each hashed part and no other, and `changed` names only
    parts this review hashed or the review before it did."""
    hashes, changed, labels = record.get("hashes"), record.get("changed"), record.get("labels")
    problems: list[tuple[str, str]] = []
    if not isinstance(hashes, dict):
        return problems
    problems += [("hashes", f"{key!r} is not a part key") for key in hashes if not PART_KEY.fullmatch(key)]
    if isinstance(labels, dict) and labels.keys() != hashes.keys():
        problems.append(("labels", "must have a label for each hashed part, and no other"))
    if isinstance(changed, list):
        reviews = context.read_jsonl("reviews.jsonl") or []
        index = next((i for i, r in enumerate(reviews) if r == record), 0)
        before = reviews[index - 1] if index else None
        earlier = before.get("hashes") if isinstance(before, dict) and isinstance(before.get("hashes"), dict) else {}
        for i, key in enumerate(changed):
            if isinstance(key, str) and key not in hashes and key not in earlier:
                problems.append(
                    (f"changed[{i}]", f"unknown changed part {key!r}: neither this review nor the one before hashed it")
                )
    return problems


@hook("request-sentence-in-request")
def _request_sentence(record: dict, context: Context) -> list[tuple[str, str]]:
    """A requirement quoting the request quotes a sentence that is in architect.json's request, word for word."""
    sentence = record.get("sentence")
    if not isinstance(sentence, str) or not sentence:
        return []
    design = context.read_json("architect.json")
    if design is None:
        return []  # a missing or unreadable architect.json is reported as such
    request = design.get("request") if isinstance(design, dict) else None
    text = request.get("text") if isinstance(request, dict) else None
    if not isinstance(text, str):
        return [("sentence", "architect.json holds no request to find it in")]
    return [] if sentence in text else [("sentence", "is not in the request of architect.json")]


def _box_kinds() -> set[str] | None:
    """The names of the box kinds of architect-better's register (`kinds.json` in this package); None if it cannot be
    read."""
    try:
        data = json.loads(resources.read_text("architect/kinds.json"))
        return {kind["name"] for kind in data}
    except (OSError, ValueError, KeyError, TypeError):
        return None


def design_problems(design: dict) -> list[tuple[str, str]]:
    """What is wrong with the references inside a design that has the right shape: an id used twice, a box kind that is
    not in the register, an edge, a group, a participant or a step that names what does not exist, a box in two groups.
    The messages are the ones diagram.py has always given."""
    problems: list[tuple[str, str]] = []

    def index(items, scope, field):
        ids: set = set()
        for number, item in enumerate(items):
            ident = item["id"]
            if ident in ids:
                problems.append((f"{field}[{number}].id", f"{scope}: Duplicate id {ident!r}"))
            ids.add(ident)
        return ids

    def reference(item, key, ids, scope, field):
        if item[key] not in ids:
            problems.append((f"{field}.{key}", f"{scope} {item['id']!r}: {key} references missing {item[key]!r}"))

    containers = design["containers"]
    nodes, edges, groups = containers["nodes"], containers.get("edges") or [], containers.get("groups") or []
    node_ids = index(nodes, "Container nodes", "containers.nodes")
    index(edges, "Container edges", "containers.edges")
    index(groups, "Container groups", "containers.groups")
    kinds = _box_kinds()
    for number, node in enumerate(nodes):
        if kinds is not None and node["kind"] not in kinds:
            problems.append((f"containers.nodes[{number}].kind", f"Box {node['id']!r}: unknown kind {node['kind']!r}"))
    for number, edge in enumerate(edges):
        for key in ("from", "to"):
            reference(edge, key, node_ids, "Edge", f"containers.edges[{number}]")
    members: set = set()
    for number, group in enumerate(groups):
        for member in group["members"]:
            if member not in node_ids:
                problems.append(
                    (f"containers.groups[{number}].members", f"Group {group['id']!r}: missing member {member!r}")
                )
            if member in members:
                problems.append(
                    (
                        f"containers.groups[{number}].members",
                        f"Box {member!r} belongs to more than one group or is listed twice",
                    )
                )
            members.add(member)
    for number, flow in enumerate(design.get("flows", [])):
        where = f"Flow {number + 1}"
        participants = []
        for at, participant in enumerate(flow["participants"]):
            if isinstance(participant, dict):
                participants.append(participant)
            else:  # the schema refuses it; diagram.py may be given a design that never met the schema
                message = f"{where} participant {participant!r}: expected an object with id and box"
                problems.append((f"flows[{number}].participants[{at}]", message))
        participant_ids = index(participants, f"{where} participants", f"flows[{number}].participants")
        index(flow["steps"], f"{where} steps", f"flows[{number}].steps")
        for at, participant in enumerate(participants):
            reference(participant, "box", node_ids, f"{where} participant", f"flows[{number}].participants[{at}]")
        for at, step in enumerate(flow["steps"]):
            for key in ("from", "to"):
                reference(step, key, participant_ids, f"{where} step", f"flows[{number}].steps[{at}]")
    return problems


@hook("design-references")
def _design_references(record: dict, context: Context) -> list[tuple[str, str]]:
    """The references inside design.json resolve: see design_problems."""
    return design_problems(record)


@hook("source-file-exists")
def _source_file_exists(record: dict, context: Context) -> list[tuple[str, str]]:
    """A `file` source of a requirement names a file of the repository the change folder is in (the nearest folder up
    with a .git; the change folder itself if there is none), reached without leaving it, and never inside .git."""
    path = record.get("file")
    if not isinstance(path, str) or not path:
        return []
    name = Path(path)
    if name.is_absolute() or {"..", ".git"} & set(name.parts):
        return [("file", f"invalid source path {path!r}")]
    root = (context.repo_root() or context.directory).resolve()
    target = (root / name).resolve()
    if not (target.is_relative_to(root) and target.is_file()):
        return [("file", f"missing or out-of-scope source {path!r}")]
    return []


@hook("design-flow-ids")
def _design_flow_ids(record: dict, context: Context) -> list[tuple[str, str]]:
    """A flow id is used once, so a part key names one flow."""
    flows = record.get("flows")
    seen: dict[str, int] = {}
    problems = []
    for index, flow in enumerate(flows if isinstance(flows, list) else []):
        ident = flow.get("id") if isinstance(flow, dict) else None
        if isinstance(ident, str):
            if ident in seen:
                problems.append((f"flows[{index}].id", f"{ident!r} is also the id of flows[{seen[ident]}]"))
            seen.setdefault(ident, index)
    return problems
