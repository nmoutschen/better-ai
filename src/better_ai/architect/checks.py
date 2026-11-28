"""architect-better's checks across records, named by `x-check` in its schemas: the parts of a design and the
references inside it, the perspectives a finding is on, and what a requirement quotes from the request."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .. import paths, resources
from ..paths import Unit
from ..schema import Context, hook
from . import SKILL

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
            # A sequence flow's steps, or a logic flow's nodes and edges: each is a step of its flow.
            for field in ("steps", "nodes", "edges"):
                for step in flow.get(field) if isinstance(flow.get(field), list) else []:
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
    not in the register, an edge, a group, a participant or a step that names what does not exist, a box in two groups,
    a version in `in` that is not `before`, `after` or an alternative.
    The messages are the ones the diagram has always given."""
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
    kind_of = {group["id"]: group.get("kind") or "boundary" for group in groups}
    for number, group in enumerate(groups):
        kind = kind_of[group["id"]]
        for member in group["members"]:
            if member not in node_ids:
                problems.append(
                    (f"containers.groups[{number}].members", f"Group {group['id']!r}: missing member {member!r}")
                )
            if (kind, member) in members:
                problems.append(
                    (
                        f"containers.groups[{number}].members",
                        f"Box {member!r} belongs to more than one group of kind {kind}, or is listed twice",
                    )
                )
            members.add((kind, member))
        within = group.get("within")
        if within is not None and kind_of.get(within) != kind:
            problems.append(
                (
                    f"containers.groups[{number}].within",
                    f"Group {group['id']!r}: within names {within!r}, which is not a {kind} group",
                )
            )
    parent = {group["id"]: group.get("within") for group in groups}
    for number, group in enumerate(groups):
        seen, at = {group["id"]}, parent.get(group["id"])
        while at in parent and at not in seen:
            seen.add(at)
            at = parent[at]
        if at == group["id"]:
            problems.append((f"containers.groups[{number}].within", f"Group {group['id']!r}: within forms a cycle"))
    alternatives = design.get("alternatives") or []
    versions = {"before", "after"} | set(index(alternatives, "Alternatives", "alternatives"))
    for number, alternative in enumerate(alternatives):
        if alternative["id"] in ("before", "after"):
            problems.append((f"alternatives[{number}].id", f"Alternative id {alternative['id']!r} names a version"))

    def versions_of(item, field):
        for value in item.get("in") or []:
            if value not in versions:
                problems.append((f"{field}.in", f"{field}: in names {value!r}, not before, after or an alternative"))

    for kind in ("nodes", "edges", "groups"):
        for number, item in enumerate(containers.get(kind) or []):
            versions_of(item, f"containers.{kind}[{number}]")
    for number, flow in enumerate(design.get("flows", [])):
        versions_of(flow, f"flows[{number}]")
        for key in ("nodes", "edges") if is_logic(flow) else ("participants", "steps"):
            for at, item in enumerate(flow[key]):
                if isinstance(item, dict):
                    versions_of(item, f"flows[{number}].{key}[{at}]")
    drawn = ["before", *(alternative["id"] for alternative in alternatives)] if alternatives else ["before", "after"]
    for number, flow in enumerate(design.get("flows", [])):
        where = f"Flow {number + 1}"
        if is_logic(flow):
            problems += _logic_problems(flow, number, node_ids, drawn, index, reference)
            continue
        participants = []
        for at, participant in enumerate(flow["participants"]):
            if isinstance(participant, dict):
                participants.append(participant)
            else:  # the schema refuses it; the drawing may be given a design that never met the schema
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


def is_logic(flow: dict) -> bool:
    """Whether a flow is a logic flow (nodes and edges) rather than a sequence flow (participants and steps)."""
    return flow.get("kind") == "logic"


def exists_in(item: dict, state: str) -> bool:
    """Whether a part exists in a version: `in` lists them, `after` standing for every version after the change."""
    where = item.get("in")
    return where is None or state in where or (state != "before" and "after" in where)


def _logic_problems(flow, number, box_ids, drawn, index, reference) -> list[tuple[str, str]]:
    """What is wrong in a logic flow: ids used twice among its nodes and edges, an edge or a `by` that names nothing,
    not one start, a decision without two labelled outcomes, an exit with an outgoing edge, and, in each version the
    flow is drawn in, a node the start cannot reach or that cannot reach an exit."""
    problems: list[tuple[str, str]] = []
    where, field = f"Flow {number + 1}", f"flows[{number}]"
    nodes, edges = flow["nodes"], flow["edges"]
    index(nodes, f"{where} nodes", f"{field}.nodes")
    node_and_edge = index(edges, f"{where} edges", f"{field}.edges") & {node["id"] for node in nodes}
    for at, edge in enumerate(edges):
        if edge["id"] in node_and_edge:
            problems.append((f"{field}.edges[{at}].id", f"{where} edges: Duplicate id {edge['id']!r} (also a node)"))
    node_ids = {node["id"] for node in nodes}
    kinds = {node["id"]: node["type"] for node in nodes}
    for at, node in enumerate(nodes):
        if node.get("by") is not None:
            reference(node, "by", box_ids, f"{where} node", f"{field}.nodes[{at}]")
    for at, edge in enumerate(edges):
        for key in ("from", "to"):
            reference(edge, key, node_ids, f"{where} edge", f"{field}.edges[{at}]")
    for at, edge in enumerate(edges):
        if kinds.get(edge["from"]) == "exit":
            problems.append((f"{field}.edges[{at}]", f"{where} edge {edge['id']!r}: an exit has no outgoing edge"))

    found: dict[tuple[str, str, str], list[str]] = {}
    for state in drawn:
        if not exists_in(flow, state):
            continue
        here = {node["id"] for node in nodes if exists_in(node, state)}
        starts = [node["id"] for node in nodes if node["type"] == "start" and node["id"] in here]
        if len(starts) != 1:
            found.setdefault(("", "flow", f"needs exactly one start node, has {len(starts)}"), []).append(state)
        links = [e for e in edges if exists_in(e, state) and e["from"] in here and e["to"] in here]
        outgoing: dict[str, list[dict]] = {}
        for edge in links:
            outgoing.setdefault(edge["from"], []).append(edge)
        for node in sorted(here):
            if kinds[node] != "decision":
                continue
            out = outgoing.get(node, [])
            if len(out) < 2:
                found.setdefault((node, "decision", "needs two outcomes or more, each with a label"), []).append(state)
            for edge in out:
                if not edge.get("label"):
                    message = f"outcome {edge['id']!r} needs a label"
                    found.setdefault((node, "decision", message), []).append(state)
        if len(starts) != 1:
            continue
        reached, pending = set(), [starts[0]]
        while pending:
            node = pending.pop()
            if node not in reached:
                reached.add(node)
                pending += [edge["to"] for edge in outgoing.get(node, [])]
        incoming: dict[str, list[str]] = {}
        for edge in links:
            incoming.setdefault(edge["to"], []).append(edge["from"])
        ending, pending = set(), [node for node in here if kinds[node] == "exit"]
        while pending:
            node = pending.pop()
            if node not in ending:
                ending.add(node)
                pending += incoming.get(node, [])
        for node in sorted(here):
            if node not in reached:
                found.setdefault((node, "node", "cannot be reached from the start"), []).append(state)
            elif node not in ending:
                found.setdefault((node, "node", "cannot reach an exit"), []).append(state)
    for (node, what, message), states in found.items():
        subject = f"{where}" if what == "flow" else f"{where} {what} {node!r}"
        problems.append((f"{field}.nodes", f"{subject}: {message} (in {', '.join(states)})"))
    return problems


@hook("design-references")
def _design_references(record: dict, context: Context) -> list[tuple[str, str]]:
    """The references inside design.json resolve: see design_problems."""
    return design_problems(record)


@hook("design-renders")
def _design_renders(record: dict, context: Context) -> list[tuple[str, str]]:
    """A design that is well shaped and whose references resolve can be laid out and drawn: what stops the drawing is
    an error of design.json, so `check` says it as the page would."""
    from . import diagram  # not at the top: the diagram imports this module for design_problems

    candidate = diagram.without_nulls(
        {key: value for key, value in record.items() if key in ("containers", "flows", "alternatives")}
    )
    try:
        if diagram.shape_problems(candidate) or design_problems(candidate):
            return []  # reported by the schema and design-references
        diagram.layout(candidate)
    except (AttributeError, IndexError, KeyError, TypeError, ValueError) as error:
        return [("(diagram)", str(error))]
    return []


@hook("source-file-exists")
def _source_file_exists(record: dict, context: Context) -> list[tuple[str, str]]:
    """A `file` source of a requirement names a file of the repository the change folder is in (the nearest folder up
    with a .git; the change folder itself if there is none), reached without leaving it, and never inside .git. The same
    holds for the design document architect.json names."""
    path = record.get("file") if isinstance(record, dict) else None
    if not isinstance(path, str) or not path:
        return []
    try:
        read_repo_file(context.repo_root() or context.directory, path)
    except paths.Refused:
        return [("file", f"invalid source path {path!r}")]
    except PermissionError:
        return [("file", f"cannot read source {path!r}")]
    except OSError:
        return [("file", f"missing or out-of-scope source {path!r}")]
    return []


def read_repo_file(root: Path, path: str) -> bytes:
    """The bytes of the file `path` names in the repository at `root`, by the rules of `paths.read_repo_file`. Raises
    `paths.Refused` or an OSError if it names none."""
    return paths.read_repo_file(Unit(root, root, SKILL.kinds[0], SKILL), path)


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
