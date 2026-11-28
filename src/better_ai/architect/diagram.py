"""Render and validate architecture diagrams from a design JSON.

`layout` and `svg_containers`/`svg_flow` draw a design; `validate` says what stops one from being drawn; `register`
builds the page of box kinds. A design can carry findings as a mapping from node IDs, edge:<id>, and
<view>:step:<id> (or step:<id> for a design-wide unique step ID) to lists of [badge ID, tooltip, perspective] entries. One finding
can be attached to multiple parts by listing it under each target.
"""

from __future__ import annotations

import functools
import html
import json
import textwrap
from collections import Counter
from itertools import pairwise
from string import Template
from urllib.parse import quote

from .. import resources, schema
from .checks import design_problems, is_logic

KINDS = {kind["name"]: kind for kind in json.loads(resources.read_text("architect/kinds.json"))}
ICONS = json.loads(resources.read_text("architect/icons.json"))

INK, HEAD, SEC = "#33302B", "#1C1A17", "#78736B"
LINEN, CREAM, SAND = "#F2EDE5", "#FFFCF7", "#C4B69C"
TERRA, STRIP = "#AA5141", "#E8725C"
SANS = "'Space Grotesk', -apple-system, sans-serif"
COLW, GAP, VGAP = 206, 236, 44
LABEL = 12.5
DASH = ' stroke-dasharray="6 4"'
ITALIC = ' font-style="italic"'
# The groupings the Containers view is drawn in: its systems (boundary groups), then each other kind a design uses.
OVERLAYS = {"systems": ("boundary", "Systems"), "trust": ("trust", "Trust"), "runs": ("runs", "Where it runs")}
ARROWS = {
    "request": ("Request", "M1 1 L9 5 L1 9 Z", 11, True, ""),
    "response": ("Response", "M1 1 L9 5 L1 9", 8, False, DASH),
    "async": ("Async message", "M0 0 L9 5", 12, False, ""),
}


def flow_parts(flow: dict) -> list[dict]:
    """The parts of a flow a part key `step:<flow id>/<id>` can name: a sequence flow's steps, or a logic flow's nodes
    and edges."""
    if is_logic(flow):
        return [*flow.get("nodes", []), *flow.get("edges", [])]
    return flow.get("steps", [])


def group_kind(group: dict) -> str:
    return group.get("kind") or "boundary"


def overlays(design: dict) -> list[tuple[str, str]]:
    """The groupings other than Systems that a design draws, as (id, name): Trust and Where it runs, each only when one
    of its groups has a member."""
    groups = (design.get("containers") or {}).get("groups") or []
    used = {group_kind(group) for group in groups if group.get("members")}
    return [(key, name) for key, (kind, name) in OVERLAYS.items() if key != "systems" and kind in used]


def without_nulls(value):
    """A copy with every null dropped from the objects in it: the schemas let an optional field be null, which means
    the same as leaving it out."""
    if isinstance(value, dict):
        return {key: without_nulls(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [without_nulls(item) for item in value]
    return value


@functools.lru_cache(maxsize=1)
def _docs() -> dict:
    return schema.docs_for("architect")


def shape_problems(design: dict) -> list[str]:
    """What is wrong with the shape of a design, by design.schema.json; the fields the page adds (`findings`), a `title` and the
    base fields a design.json carries are not part of what the drawing is given."""
    candidate = {"type": "design", "at": "2026-01-01T00:00:00Z", "by": "diagram", "flows": []}
    candidate.update({key: value for key, value in design.items() if key not in ("findings", "flow", "title")})
    found = schema.validate_instance(candidate, _docs()["design.schema.json"], _docs())
    return [f"{p.field}: {p.message}" for p in dict.fromkeys(found)]


def validate(design: dict) -> list[str]:
    """Report what stops a design from being laid out. The shape is design.schema.json's, and the references inside a
    well-shaped design, and its box kinds, are `checks.design_problems`; this keeps the one check that needs
    the layout: a finding that names no part of it."""
    if not isinstance(design, dict):
        return ["design: expected an object"]
    design = without_nulls(design)
    errors = shape_problems(design)
    if errors:
        return errors
    errors = [message for _, message in design_problems(design)]
    if "flow" in design:
        errors.append("Use a flows list instead of flow")
    targets = {node["id"] for node in design["containers"]["nodes"]}
    targets |= {f"edge:{edge['id']}" for edge in design["containers"].get("edges", [])}
    step_counts = Counter()
    for i, flow in enumerate(design.get("flows", []), 1):
        step_ids = [step["id"] for step in flow_parts(flow)]
        step_counts.update(step_ids)
        targets.update(f"flow{i}:step:{ident}" for ident in step_ids)
    targets.update(f"step:{ident}" for ident, count in step_counts.items() if count == 1)
    for target in design.get("findings", {}):
        if target not in targets:
            errors.append(f"Finding target {target!r}: missing or ambiguous diagram part")
    return errors


def versions(design: dict) -> list[tuple[str, str]]:
    """The versions a design draws, as (id, name): Before; then each alternative, or one After; or Before alone while
    no part differs between Before and After, as when the design maps the system as it is."""
    design = without_nulls(design)
    alternatives = design.get("alternatives") or []
    if alternatives:
        return [("before", "Before"), *((alt["id"], alt["name"]) for alt in alternatives)]
    containers = design.get("containers") or {}
    items = [item for key in ("nodes", "edges", "groups") for item in containers.get(key) or []]
    for flow in design.get("flows") or []:
        items += [flow, *flow.get("participants", []), *flow_parts(flow)]
    if any(exists(item, "before") != exists(item, "after") for item in items):
        return [("before", "Before"), ("after", "After")]
    return [("before", "Before")]


def exists(item, state):
    """Whether a part exists in a version: `in` lists them, `after` standing for every version after the change; a
    part without `in` exists in all."""
    where = item.get("in")
    if where is None:
        return True
    return state in where or (state != "before" and "after" in where)


def visible(item, state):
    """Before draws what exists before the change; a version after it draws what exists in it, and what it removed as
    removed."""
    return exists(item, state) or (state != "before" and exists(item, "before"))


def appearance(item, state):
    if state == "before":
        return "current"
    old, new = exists(item, "before"), exists(item, state)
    if old and not new:
        return "removed"
    if new and not old:
        return "new"
    return "current"


def removable(item):
    """Whether some version after the change removes the part, so its drawing keeps room for the removal tag."""
    where = item.get("in")
    return where is not None and "before" in where and "after" not in where


def width(text, size, bold=False):
    return len(text) * size * (0.6 if bold else 0.56)


def wrap(text, size, limit):
    return textwrap.wrap(text, width=max(1, int(limit / (size * 0.56))), break_on_hyphens=False) or [""]


def esc(value):
    return html.escape(str(value), quote=True)


def part_id(prefix, kind, ident):
    return f"{prefix}-{kind}-{quote(ident, safe='')}"


def glyph(kind, color=INK):
    icon = ICONS[KINDS[kind]["icon"]]
    return (
        f'<g fill="none" stroke="{color}" stroke-width="1.3" stroke-linejoin="round" stroke-linecap="round">{icon}</g>'
    )


def layers(nodes, edges, people=frozenset()):
    """Layer the forward graph; cycle-closing edges get return routes. The boxes in `people` stay in the first column:
    their arrows out are laid first, and an arrow to one of them is drawn as a return."""
    forward = {node: [] for node in nodes}
    for edge in sorted(edges, key=lambda edge: edge["from"] not in people):
        source, target = edge["from"], edge["to"]
        if target in people:
            continue
        visited, pending = set(), [target]
        while pending and source not in visited:
            node = pending.pop()
            if node not in visited:
                visited.add(node)
                pending.extend(forward[node])
        if source not in visited:
            forward[source].append(target)

    level = dict.fromkeys(nodes, 0)
    for _ in nodes:
        changed = False
        for source, targets in forward.items():
            for target in targets:
                if level[target] <= level[source]:
                    level[target] = level[source] + 1
                    changed = True
        if not changed:
            break
    return level


def layout(design: dict) -> dict:
    """Compute positions once for the union of Before and After."""
    design = without_nulls(design)
    errors = validate(design)
    if errors:
        raise ValueError("\n".join(errors))
    containers = design["containers"]
    nodes = {node["id"]: node for node in containers["nodes"]}
    edges = containers.get("edges", [])
    groups = containers.get("groups", [])
    level = layers(nodes, edges, frozenset(i for i, node in nodes.items() if node["kind"] == "person"))
    slots = [[] for _ in range(max(level.values(), default=0) + 1)]
    for node, column in level.items():
        slots[column].append(node)

    chains, neighbors = {}, {}
    incoming = {node: [] for node in nodes}
    outgoing = {node: [] for node in nodes}
    labels = {}
    for edge in edges:
        ident, source, target = edge["id"], edge["from"], edge["to"]
        waypoints = [(ident, column) for column in range(level[source] + 1, level[target])]
        for point in waypoints:
            slots[point[1]].append(point)
        chain = chains[ident] = [source, *waypoints, target]
        for a, b in pairwise(chain):
            neighbors.setdefault(a, []).append(b)
            neighbors.setdefault(b, []).append(a)
        incoming[target].append(edge)
        outgoing[source].append(edge)
        raw = edge.get("label", "")
        # Reserve the same label space in both views, including the removal tag.
        labels[ident] = wrap(raw, LABEL, GAP - 70) + (["REMOVED"] if removable(edge) else [])

    for sweep in range(8):
        forward = sweep % 2 == 0
        columns = range(1, len(slots)) if forward else range(len(slots) - 2, -1, -1)
        for column in columns:
            reference = {item: i for i, item in enumerate(slots[column - 1 if forward else column + 1])}
            here = {item: i for i, item in enumerate(slots[column])}

            def barycenter(item, reference=reference, here=here):
                linked = [reference[n] for n in neighbors.get(item, []) if n in reference]
                return sum(linked) / len(linked) if linked else here[item]

            slots[column].sort(key=barycenter)

    # A flow box holds its own text; a container box also makes room for the labels of the arrows that reach it.
    box_heights = {ident: 59 + 15 * len(wrap(node.get("detail", ""), 12.5, COLW - 28)) for ident, node in nodes.items()}
    heights = {
        ident: max(box_heights[ident], sum(15 * len(labels[edge["id"]]) + 14 for edge in incoming[ident]) + 16)
        for ident in nodes
    }
    x = {item: column * (COLW + GAP) for column, slot in enumerate(slots) for item in slot}
    width = len(slots) * (COLW + GAP) - GAP
    # Each grouping keeps every box in its column and stacks the rows by its own groups.
    drawn = {}
    for key, (kind, _) in OVERLAYS.items():
        if key != "systems" and key not in dict(overlays(design)):
            continue
        y, bands, total = place_bands(slots, heights, [g for g in groups if group_kind(g) == kind], chains, x)
        routes, extra = route_edges(edges, chains, incoming, outgoing, labels, x, y, heights, total)
        # Return lanes may sit outside the outer columns, and the outline of a group holding another further out than
        # the 16 the drawing's margin already holds; the drawing spans them all.
        xs = [point[0] for points in routes.values() for point in points]
        xs += [edge for _, band_left, _, band_w, _ in bands for edge in (band_left + 16, band_left + band_w - 16)]
        left, right = min([0, *xs]), max([width, *xs])
        drawn[key] = {
            "x": x,
            "y": y,
            "groups": bands,
            "routes": routes,
            "left": left,
            "width": right - left,
            "height": total + extra,
        }
    return {
        **drawn["systems"],
        "overlays": drawn,
        "nodes": nodes,
        "edges": edges,
        "heights": heights,
        "box_heights": box_heights,
        "labels": labels,
        "findings": design.get("findings", {}),
        "step_counts": Counter(step["id"] for flow in design.get("flows", []) for step in flow_parts(flow)),
    }


def place_bands(slots, heights, groups, chains, x):
    """Separate grouped boxes vertically, allowing ungrouped-only columns to center. A group `within` another is drawn
    inside it: its band follows the outer group's own members, and the outer outline spans both."""
    known = {group["id"] for group in groups}
    children, roots = {}, []
    for group in groups:
        within = group.get("within")
        (children.setdefault(within, []) if within in known and within != group["id"] else roots).append(group)

    def under(group, seen=()):
        found = list(group["members"])
        for child in children.get(group["id"], []):
            if child["id"] not in seen:
                found += under(child, (*seen, group["id"]))
        return found

    def depth(group, seen=()):
        inner = [c for c in children.get(group["id"], []) if c["id"] not in seen]
        return 1 + max(depth(c, (*seen, group["id"])) for c in inner) if inner else 0

    membership = {member: group["id"] for group in groups for member in group["members"]}
    for chain in chains.values():
        for point in chain[1:-1]:
            membership[point] = membership.get(chain[0])

    def place(column, top):
        y = top
        for item in column:
            positions[item] = y
            y += heights.get(item, 0) + (VGAP if item in heights else 26)
        return y - (VGAP if column and column[-1] in heights else 0)

    positions, bands = {}, []
    free = [slot for slot in slots if all(membership.get(item) is None for item in slot)]
    held = [slot for slot in slots if slot not in free]

    def place_group(group, top, seen=()):
        """Place a group's members, then its inner groups, from `top`; return the bottom of what it holds (its outline
        ends 12 below), or None if it holds no box."""
        start = top + 30
        columns = [[item for item in slot if membership.get(item) == group["id"]] for slot in held]
        end = max((place(column, start) for column in columns), default=start)
        bottom = end if end > start else None
        inner_top = end + 30 if bottom is not None else start
        for child in children.get(group["id"], []):
            if child["id"] in seen:
                continue
            child_bottom = place_group(child, inner_top, (*seen, group["id"]))
            if child_bottom is not None:
                bottom = child_bottom + 12
                inner_top = bottom + 30
        if bottom is None:
            return None
        pad = 10 * depth(group)
        bottom += pad
        inside = under(group)
        left = min(x[n] for n in inside) - 16 - pad
        right = max(x[n] for n in inside) + COLW + 16 + pad
        bands.append((group, left, top - 4, right - left, bottom - top + 16))
        return bottom

    top, bottom = 0, 0
    for group in roots:
        end = place_group(group, top)
        if end is None:
            continue
        bottom = end
        top = end + 56
    columns = [[item for item in slot if membership.get(item) is None] for slot in held]
    end = max((place(column, top) for column in columns), default=top)
    if end != top:
        bottom = end

    heights_free = [place(slot, 0) for slot in free]
    total = max(bottom, *heights_free) if heights_free else bottom
    offset = (total - bottom) / 2
    for item in positions:
        positions[item] += offset
    bands = [(group, left, top + offset, w, h) for group, left, top, w, h in bands]
    for slot, extent in zip(free, heights_free, strict=True):
        place(slot, (total - extent) / 2)
    return positions, bands, total + 16


def route_edges(edges, chains, incoming, outgoing, labels, x, y, heights, total):
    """Use shared ports and gap tracks for both states."""
    ports_in, ports_out = {}, {}
    for node, edges_in in incoming.items():
        port = y[node] + 8
        for edge in sorted(edges_in, key=lambda e: y[chains[e["id"]][-2]]):
            ident = edge["id"]
            port += len(labels[ident]) * 15 + 6
            ports_in[ident] = port
            port += 8
        edges_out = sorted(outgoing[node], key=lambda e: y[chains[e["id"]][1]])
        for i, edge in enumerate(edges_out, 1):
            ports_out[edge["id"]] = y[node] + heights[node] * i / (len(edges_out) + 1)

    routes, gaps, returns, return_space = {}, {}, [], 0
    for edge in edges:
        ident = edge["id"]
        chain = chains[ident]
        source, target = chain[0], chain[-1]
        start, end = ports_out[ident], ports_in[ident]
        if x[source] >= x[target]:
            return_space += 15 * len(labels[ident]) + 14
            returns.append((ident, source, target, start, end, total + return_space))
            continue
        if len(chain) == 2 and abs(end - start) < 16 and y[source] + 10 <= end <= y[source] + heights[source] - 10:
            start = end
        routes[ident] = [(x[source] + COLW, start)]
        for i, (a, b) in enumerate(pairwise(chain)):
            finish = end if b == target else y[b]
            gaps.setdefault(x[a] + COLW, []).append((ident, start, finish, x[b], i == len(chain) - 2))
            start = finish

    # Every vertical segment in a gap is a lane: (key, top, bottom, side). Forward runs and the lane a return edge
    # leaves its source by take tracks from the gap's left side; the lane a return edge enters its target by takes
    # them from the right side. Two lanes share a track only when their spans keep apart, so no two edges read as one.
    lanes = {}
    for gap, runs in gaps.items():
        up = sorted((run for run in runs if run[2] < run[1]), key=lambda run: run[2])
        down = sorted((run for run in runs if run[2] > run[1]), key=lambda run: -run[2])
        for run in up + down:
            lanes.setdefault(gap, []).append((run, min(run[1], run[2]), max(run[1], run[2]), 1))
    for ident, source, target, start, end, lower in returns:
        lanes.setdefault(x[source] + COLW, []).append(((ident, "out"), start, lower, 1))
        lanes.setdefault(x[target] - GAP, []).append(((ident, "in"), end, lower, -1))
    tracks = {}
    for gap, entries in lanes.items():
        taken, chosen = {}, {}
        for key, top, bottom, side in entries:
            index = 0
            while any(top < b + 8 and t < bottom + 8 for t, b in taken.get((side, index), [])):
                index += 1
            taken.setdefault((side, index), []).append((top, bottom))
            chosen[key] = side, index
        step = min(14, (GAP - 44) / len(taken))
        for key, (side, index) in chosen.items():
            tracks[key] = gap + 18 + step * index if side == 1 else gap + GAP - 18 - step * index

    for ident, source, target, start, end, lower in returns:
        right, left = tracks[(ident, "out")], tracks[(ident, "in")]
        routes[ident] = [
            (x[source] + COLW, start),
            (right, start),
            (right, lower),
            (left, lower),
            (left, end),
            (x[target], end),
        ]
    for _gap, runs in sorted(gaps.items()):
        for run in runs:
            ident, start, end, destination, last = run
            if run in tracks:
                track = tracks[run]
                routes[ident].extend(((track, start), (track, end)))
            routes[ident].append((destination, end))
            if not last:
                routes[ident].append((destination + COLW, end))
    return routes, return_space


def start_svg(viewbox, title, width, height, x=0, y=0):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}" role="img" '
        f'aria-label="{esc(title)}" font-family="{SANS}">',
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" fill="{CREAM}"/>',
    ]


def finish_svg(out, marks):
    if marks:
        out.append("<style>.mark[hidden] { display: none; }</style>")
        out.extend(marks)
    return "\n".join(out + ["</svg>"])


def marker_id(prefix, kind, status):
    return f"{prefix}-marker-{kind}-{status}"


def markers(prefix, kinds):
    out = ["<defs>"]
    for kind in kinds:
        _, path, size, filled, _ = ARROWS[kind]
        for status in ("current", "new", "removed"):
            color = part_color(status)
            out.append(
                f'<marker id="{marker_id(prefix, kind, status)}" viewBox="0 0 10 10" refX="9" refY="5" '
                f'markerWidth="{size}" markerHeight="{size}" markerUnits="userSpaceOnUse" orient="auto">'
                f'<path d="{path}" fill="{color if filled else "none"}" stroke="{color}" '
                f'stroke-width="{1 if filled else 1.7}" stroke-linejoin="round" stroke-linecap="round"/></marker>'
            )
    return out + ["</defs>"]


def part_color(status):
    return {"current": INK, "new": TERRA, "removed": SEC}[status]


def badges(findings, target, right, center):
    out = []
    for label, tooltip, perspective in findings.get(target, []):
        w = max(26, width(label, 11, True) + 10)
        out.append(
            f'<g class="mark" data-p="{esc(perspective)}" hidden="hidden">'
            f"<title>{esc(tooltip)}</title>"
            f'<rect x="{right - w}" y="{center - 9}" width="{w}" height="18" fill="#5C4033"/>'
            f'<text x="{right - w / 2}" y="{center + 4}" text-anchor="middle" font-size="11" '
            f'font-weight="700" fill="{CREAM}">{esc(label)}</text></g>'
        )
        right -= w + 4
    return out


def draw_box(node, ident, x, y, height, prefix, status):
    """Draw the same container box in the container and sequence diagrams."""
    removed = status == "removed"
    stroke, fill, weight = (SEC, CREAM, 1.2) if removed else (INK, LINEN, 1.5)
    dash = DASH if removed or node["kind"] == "person" else ""
    italic = ITALIC if removed else ""
    out = [
        f'<g id="{part_id(prefix, "box", ident)}" data-id="{esc(node["id"])}">',
        f'<rect x="{x}" y="{y}" width="{COLW}" height="{height}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="{weight}"{dash}/>',
    ]
    if status == "new":
        out.append(f'<rect x="{x}" y="{y}" width="7" height="{height}" fill="{STRIP}"/>')
    icon = glyph(node["kind"], stroke)
    out.append(f'<g transform="translate({x + 14} {y + 12})">{icon}</g>')
    tag = {"new": "NEW", "removed": "REMOVED"}.get(status, "")
    kind_width = COLW - 46 - (width(tag, 10.5, True) + 8 if tag else 0)
    kind_label = KINDS[node["kind"]]["label"].upper()
    fit = (
        f' textLength="{kind_width:.1f}" lengthAdjust="spacingAndGlyphs"'
        if width(kind_label, 10.5, True) + len(kind_label) * 0.84 > kind_width
        else ""
    )
    out.append(
        f'<text x="{x + 34}" y="{y + 22}" font-size="10.5" letter-spacing="0.08em" fill="{SEC}"{fit}>'
        f"{esc(kind_label)}</text>"
    )
    if tag:
        out.append(
            f'<text x="{x + COLW - 12}" y="{y + 22}" text-anchor="end" font-size="10.5" font-weight="700" '
            f'letter-spacing="0.08em" fill="{part_color(status)}">{tag}</text>'
        )
    label = node["label"]
    fit = f' textLength="{COLW - 28}" lengthAdjust="spacingAndGlyphs"' if width(label, 16, True) > COLW - 28 else ""
    out.append(
        f'<text x="{x + 14}" y="{y + 42}" font-size="16" font-weight="600" '
        f'fill="{SEC if removed else HEAD}"{italic}{fit}>{esc(label)}</text>'
    )
    for i, line in enumerate(wrap(node.get("detail", ""), 12.5, COLW - 28)):
        out.append(f'<text x="{x + 14}" y="{y + 60 + 15 * i}" font-size="12.5" fill="{SEC}"{italic}>{esc(line)}</text>')
    return out + ["</g>"]


def draw_group(group, x, y, w, h, prefix, status):
    color = SAND if status == "current" else part_color(status)
    label_color = SEC if status == "removed" else HEAD
    dash = DASH if status == "removed" else ""
    italic = ITALIC if status == "removed" else ""
    tab = min(w - 86, width(group["label"], LABEL, True) + 24)
    fit = (
        f' textLength="{tab - 24:.1f}" lengthAdjust="spacingAndGlyphs"'
        if width(group["label"], LABEL, True) + 24 > tab
        else ""
    )
    out = [
        f'<g id="{part_id(prefix, "group", group["id"])}">',
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="{color}" stroke-width="1.5"{dash}/>',
        f'<rect x="{x}" y="{y}" width="{tab}" height="26" fill="{LINEN}" stroke="{color}" stroke-width="1.5"{dash}/>',
        f'<text x="{x + 12}" y="{y + 18}" font-size="{LABEL}" font-weight="700" '
        f'fill="{label_color}"{italic}{fit}>{esc(group["label"])}</text>',
    ]
    if status != "current":
        tag = "NEW" if status == "new" else "REMOVED"
        out.append(
            f'<text x="{x + w - 12}" y="{y + 20}" text-anchor="end" font-size="10.5" '
            f'font-weight="700" letter-spacing="0.08em" fill="{color}">{tag}</text>'
        )
    return out + ["</g>"]


def container_prefix(state: str, overlay: str = "systems") -> str:
    """The start of the element ids of one Containers drawing: c-<state>- for Systems, c<overlay>-<state>- for another
    grouping."""
    return f"c-{state}" if overlay == "systems" else f"c{overlay}-{state}"


def crossing_mark(points):
    """Two short ticks across an arrow just after it leaves its source: the arrow crosses a trust boundary."""
    (x, y) = points[0]
    ticks = "".join(
        f'<line x1="{x + dx:.1f}" y1="{y - 6:.1f}" x2="{x + dx:.1f}" y2="{y + 6:.1f}" stroke="{INK}" stroke-width="1.6"/>'
        for dx in (10, 15)
    )
    return f'<g class="crossing">{ticks}</g>'


def svg_containers(layout: dict, state: str, overlay: str = "systems") -> str:
    """Render one state from the shared layout, in one grouping (see OVERLAYS). IDs start with
    `container_prefix(state, overlay)`."""
    prefix = container_prefix(state, overlay)
    geometry = layout["overlays"][overlay]
    pad = 24
    trust = overlay == "trust"
    key_height = 36 if trust else 0
    left = geometry["left"] - pad
    w, h = geometry["width"] + 2 * pad, geometry["height"] + 2 * pad + key_height
    out = start_svg(f"{left} {-pad} {w} {h}", "Containers", w, h, left, -pad)
    out.extend(markers(prefix, ("response",)))
    box_marks, edge_marks = [], []
    zone = {}
    for group, x, y, gw, gh in geometry["groups"]:
        if exists(group, state):  # a removed trust group no longer decides what crosses a boundary
            zone.update(dict.fromkeys(group["members"], group["id"]))
        if visible(group, state):
            out.extend(draw_group(group, x, y, gw, gh, prefix, appearance(group, state)))
    layout = {**layout, **geometry}
    nodes = layout["nodes"]
    for edge in layout["edges"]:
        if not all(visible(item, state) for item in (edge, nodes[edge["from"]], nodes[edge["to"]])):
            continue
        ident = edge["id"]
        status = appearance(edge, state)
        color = part_color(status)
        dash, italic = (DASH, ITALIC) if status == "removed" else ("", "")
        points = layout["routes"][ident]
        path = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in points)
        out.append(
            f'<g id="{part_id(prefix, "edge", ident)}" data-id="{esc(ident)}">'
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{2.2 if status == "new" else 1.6}" '
            f'stroke-linejoin="round"{dash} marker-end="url(#{marker_id(prefix, "response", status)})"/>'
        )
        if trust and zone.get(edge["from"]) != zone.get(edge["to"]):
            out.append(crossing_mark(points))
        # A return edge enters from the left. Put its label on the lower
        # horizontal leg so it remains inside the view even in column zero.
        x, y = points[2] if layout["x"][edge["from"]] >= layout["x"][edge["to"]] else points[-1]
        lines = layout["labels"][ident]
        if removable(edge) and status != "removed":
            lines = lines[:-1]  # the removal tag the layout reserved room for
        for i, line in enumerate(lines):
            yy = y - 6 - 15 * (len(lines) - 1 - i)
            out.append(
                f'<text x="{x - 12:.1f}" y="{yy:.1f}" text-anchor="end" font-size="{LABEL}" fill="{color}"{italic} '
                f'paint-order="stroke" stroke="{CREAM}" stroke-width="4">{esc(line)}</text>'
            )
        out.append("</g>")
        if state == "after":
            edge_marks.extend(
                badges(
                    layout["findings"],
                    f"edge:{ident}",
                    x - 20 - max(width(line, LABEL) for line in lines),
                    y - 10 - 15 * (len(lines) - 1),
                )
            )
    for ident, node in nodes.items():
        if visible(node, state):
            x, y = layout["x"][ident], layout["y"][ident]
            out.extend(draw_box(node, ident, x, y, layout["heights"][ident], prefix, appearance(node, state)))
            if state == "after":
                box_marks.extend(badges(layout["findings"], ident, x + COLW - 6, y - 9))
    if trust:
        ky = geometry["height"] + pad + 4
        kx = geometry["left"]
        out.append(
            f'<g>{crossing_mark([(kx, ky)])}<line x1="{kx}" y1="{ky}" x2="{kx + 40}" y2="{ky}" stroke="{INK}" '
            f'stroke-width="1.6"/><text x="{kx + 52}" y="{ky + 4}" font-size="13" fill="{INK}">'
            "Crosses a trust boundary</text></g>"
        )
    return finish_svg(out, box_marks + edge_marks)


def step_numbers(flow, state="after"):
    """The number of each step in one version: steps the change adds take a letter after the step before them, and a
    step the version does not draw has none ("")."""
    steps = flow["steps"]
    drawn = [visible(step, state) for step in steps]
    new = [appearance(step, state) == "new" for step in steps]
    if appearance(flow, state) == "new" or all(n for n, d in zip(new, drawn, strict=True) if d):
        count = iter(range(1, len(steps) + 1))
        return [str(next(count)) if d else "" for d in drawn]
    base, suffix = 0, 0
    numbers = []
    for is_drawn, is_new in zip(drawn, new, strict=True):
        if not is_drawn:
            numbers.append("")
        elif is_new:
            suffix += 1
            index, letters = suffix, ""
            while index:
                index, digit = divmod(index - 1, 26)
                letters = chr(ord("a") + digit) + letters
            numbers.append(f"{base}{letters}")
        else:
            base, suffix = base + 1, 0
            numbers.append(str(base))
    return numbers


def flow_status(item, related, state):
    states = [appearance(part, state) for part in (item, related)]
    return next((status for status in ("removed", "new") if status in states), "current")


def draw_step(step, y, x1, x2, number, prefix, status):
    color = part_color(status)
    kind = step.get("kind", "request")
    dash = DASH if status == "removed" else ARROWS[kind][4]
    italic = ITALIC if status == "removed" else ""
    direction = 1 if x2 > x1 else -1
    attrs = (
        f'fill="none" stroke="{color}" stroke-width="{2.2 if status == "new" else 1.6}"{dash} '
        f'marker-end="url(#{marker_id(prefix, kind, status)})"'
    )
    if x1 == x2:
        arrow = f'<path d="M{x1 + 4} {y - 12} h40 v12 H{x1 + 4}" {attrs}/>'
    else:
        arrow = f'<line x1="{x1 + 4 * direction}" y1="{y}" x2="{x2 - 4 * direction}" y2="{y}" {attrs}/>'
    label = step.get("label", "")
    limited = max(80, abs(x2 - x1) - 16) if x1 != x2 else COLW - 16
    fit = f' textLength="{limited}" lengthAdjust="spacingAndGlyphs"' if width(label, 13) > limited else ""
    ident = step["id"]
    out = [
        f'<g id="{part_id(prefix, "step", ident)}" data-id="{esc(ident)}">{arrow}',
        f'<text x="{(x1 + x2) / 2}" y="{y - (18 if x1 == x2 else 8)}" text-anchor="middle" '
        f'font-size="13" fill="{color}"{italic}{fit} paint-order="stroke" stroke="{CREAM}" stroke-width="4">{esc(label)}</text>',
        f'<text x="10" y="{y + 4}" font-size="13" font-weight="700" fill="{color}">{number}</text>',
    ]
    if status == "removed":
        out.append(
            f'<text x="{max(34, 16 + width(number, 13, True))}" y="{y + 4}" font-size="9.5" font-weight="700" '
            f'fill="{color}" letter-spacing="0.06em">REMOVED</text>'
        )
    return out + ["</g>"]


def svg_flow(flow: dict, state: str, layout: dict, view: str) -> str:
    """Render a flow. Pass a distinct view name such as flow1 for each flow on a page."""
    if is_logic(flow):
        return svg_logic(flow, state, layout, view)
    prefix = f"{quote(view, safe='')}-{state}"
    nodes, heights = layout["nodes"], layout["box_heights"]
    # The user's lane comes first; the other participants keep their order.
    participants = sorted(flow["participants"], key=lambda p: nodes[p["box"]]["kind"] != "person")
    steps = flow["steps"]
    column = COLW + 30
    centers = {p["id"]: 100 + column / 2 + i * column for i, p in enumerate(participants)}
    top = 16 + max((heights[p["box"]] for p in participants), default=0)
    w = max(600, 120 + column * len(participants))
    h = top + 106 + 50 * len(steps)
    out = start_svg(f"0 0 {w} {h}", flow["name"], w, h)
    if not visible(flow, state):
        return "\n".join(out + ["</svg>"])
    out.extend(markers(prefix, ARROWS))
    marks = []
    shown = set()
    for participant in participants:
        box = participant["box"]
        node = nodes[box]
        if not visible(participant, state) or not visible(node, state):
            continue
        ident = participant["id"]
        status = appearance(node, state)
        shown.add(ident)
        center = centers[ident]
        hbox = heights[box]
        out.append(
            f'<line x1="{center}" y1="{top}" x2="{center}" y2="{h - 70}" stroke="{SAND}" '
            f'stroke-width="1.5" stroke-dasharray="4 4"/>'
        )
        out.extend(draw_box(node, ident, center - COLW / 2, top - hbox, hbox, prefix, status))
        if appearance(participant, state) == "removed" and status != "removed":
            out.append(
                f'<text x="{center + 8}" y="{top + 16}" font-size="9.5" font-weight="700" '
                f'fill="{SEC}"{ITALIC}>REMOVED</text>'
            )
        if state == "after":
            marks.extend(badges(layout["findings"], box, center + COLW / 2 - 6, top - hbox - 9))
    for i, (step, number) in enumerate(zip(steps, step_numbers(flow, state), strict=True)):
        source, target = step["from"], step["to"]
        if not visible(step, state) or source not in shown or target not in shown:
            continue
        status = flow_status(step, flow, state)
        y = top + 44 + 50 * i
        out.extend(draw_step(step, y, centers[source], centers[target], number, prefix, status))
        if state == "after":
            target = f"step:{step['id']}"
            scoped_target = f"{view}:{target}"
            findings = layout["findings"]
            if scoped_target in findings or layout["step_counts"][step["id"]] > 1:
                target = scoped_target
            marks.extend(badges(findings, target, 148, y))
    ky, kx = h - 30, 100
    for kind, (label, _, _, _, dash) in ARROWS.items():
        out.append(
            f'<line x1="{kx}" y1="{ky}" x2="{kx + 56}" y2="{ky}" stroke="{INK}" stroke-width="1.6"{dash} '
            f'marker-end="url(#{marker_id(prefix, kind, "current")})"/>'
            f'<text x="{kx + 68}" y="{ky + 4}" font-size="13" fill="{INK}">{label}</text>'
        )
        kx += 68 + width(label, 13) + 48
    return finish_svg(out, marks)


LOGIC_KINDS = {"step": "STEP", "decision": "DECISION", "state": "STATE"}
EXIT_WORDS = {"positive": "POSITIVE END", "negative": "NEGATIVE END"}
START = 18  # the diameter of a start node
LANE = 26  # the distance between two arcs above a logic flow


def logic_label_lines(node):
    return wrap(node.get("label", ""), 16, COLW - 28)


def logic_box_height(node, boxes):
    """The height of a logic node's box: its kind line, its label, and the box that does it."""
    if node["type"] == "start":
        return START
    actor = node.get("by") in boxes
    return 52 + 19 * (len(logic_label_lines(node)) - 1) + (22 if actor else 0) + 8


def back_edges(flow):
    """The edges that go back to an earlier node, found by a depth-first walk from the start in the order the edges are
    listed, and the edges from a node to itself."""
    nodes = [node["id"] for node in flow["nodes"]]
    outgoing = {node: [] for node in nodes}
    for edge in flow["edges"]:
        outgoing[edge["from"]].append(edge)
    starts = [node["id"] for node in flow["nodes"] if node["type"] == "start"]
    back, visited, on_path = set(), set(), set()

    def walk(node):
        visited.add(node)
        on_path.add(node)
        for edge in outgoing[node]:
            target = edge["to"]
            if target in on_path:
                back.add(edge["id"])
            elif target not in visited:
                walk(target)
        on_path.discard(node)

    for node in [*starts, *nodes]:
        if node not in visited:
            walk(node)
    return back


def logic_layout(flow: dict, layout: dict) -> dict:
    """Lay out a logic flow from left to right, once for every version: the start in the first column, each node in the
    column after the longest forward path to it, the edges passing through a column and then the exits below its
    nodes; forward edges by the containers' routing, and each edge back to an earlier node apart from them, as an arc
    above the drawing, a pair of numbered connectors, or a loop on its own node. A forward edge that would cross another
    is drawn as connectors too, the longest first. `boxes`, `routes`, `loops` and `label_boxes` give the geometry."""
    nodes = {node["id"]: node for node in flow["nodes"]}
    back = back_edges(flow)
    forward = [edge for edge in flow["edges"] if edge["id"] not in back]
    level = dict.fromkeys(nodes, 0)
    for _ in nodes:
        changed = False
        for edge in forward:
            if level[edge["to"]] <= level[edge["from"]]:
                level[edge["to"]] = level[edge["from"]] + 1
                changed = True
        if not changed:
            break
    span = {edge["id"]: abs(level[edge["to"]] - level[edge["from"]]) for edge in flow["edges"]}
    jumps, no_arc = set(), set()
    for _ in range(len(flow["edges"]) + 1):
        shape = _place_logic(flow, nodes, back, forward, level, jumps, no_arc, layout["nodes"])
        crossing = _logic_crossings(shape)
        if not crossing:
            break
        routed = [ident for pair in crossing for ident in pair if ident in shape["routes"]]
        if routed:
            jumps.add(max(routed, key=lambda ident: (span[ident], ident)))
            continue
        arcs = [ident for pair in crossing for ident in pair if shape["loops"].get(ident, {}).get("kind") == "arc"]
        if not arcs:
            break
        no_arc.add(max(arcs, key=lambda ident: (span[ident], ident)))
    return shape


def _logic_crossings(shape):
    """The pairs of edges where one crosses the other, runs along it, or runs through its connector or its label."""
    apart = {**shape["loops"], **shape["jumps"]}
    lines = {ident: list(pairwise(points)) for ident, points in shape["routes"].items()}
    for ident, loop in apart.items():
        lines[ident] = [segment for points in loop["paths"] for segment in pairwise(points)]
    obstacles = [(ident, box) for ident, box in shape["label_boxes"].items()]
    obstacles += [
        (ident, (cx - 9, cy - 9, 18, 18)) for ident, loop in apart.items() for cx, cy in loop.get("circles", [])
    ]
    found = []
    idents = list(lines)
    for i, a in enumerate(idents):
        for b in idents[i + 1 :]:
            if any(_segments_cross(s, t) for s in lines[a] for t in lines[b]):
                found.append((a, b))
    for ident, segments in lines.items():
        for other, box in obstacles:
            if other != ident and any(_segment_through(s, box) for s in segments):
                found.append((ident, other))
    return found


def _segments_cross(s, t):
    """Whether two axis-parallel segments meet inside both, or run along one another."""
    (a, b), (c, d) = s, t
    if a == b or c == d:
        return False
    if a[0] == b[0] and c[1] == d[1]:
        return min(c[0], d[0]) < a[0] < max(c[0], d[0]) and min(a[1], b[1]) < c[1] < max(a[1], b[1])
    if a[1] == b[1] and c[0] == d[0]:
        return _segments_cross(t, s)
    if a[0] == b[0] == c[0] == d[0]:
        return min(a[1], b[1]) < max(c[1], d[1]) and min(c[1], d[1]) < max(a[1], b[1])
    if a[1] == b[1] == c[1] == d[1]:
        return min(a[0], b[0]) < max(c[0], d[0]) and min(c[0], d[0]) < max(a[0], b[0])
    return False


def _segment_through(segment, box):
    (a, b), (x, y, w, h) = segment, box
    if a[0] == b[0]:
        return x + 1 < a[0] < x + w - 1 and min(a[1], b[1]) < y + h - 1 and max(a[1], b[1]) > y + 1
    return y + 1 < a[1] < y + h - 1 and min(a[0], b[0]) < x + w - 1 and max(a[0], b[0]) > x + 1


def _place_logic(flow, nodes, back, forward, level, jumps, no_arc, boxes_of):
    """One placement of a logic flow, with the forward edges in `jumps` drawn as connectors and the edges back in
    `no_arc` never as arcs."""
    routed = [edge for edge in forward if edge["id"] not in jumps]
    slots = [[] for _ in range(max(level.values(), default=0) + 1)]
    for node in nodes:
        slots[level[node]].append(node)

    chains, neighbors, labels = {}, {}, {}
    incoming = {node: [] for node in nodes}
    outgoing = {node: [] for node in nodes}
    for edge in routed:
        ident, source, target = edge["id"], edge["from"], edge["to"]
        waypoints = [(ident, column) for column in range(level[source] + 1, level[target])]
        for point in waypoints:
            slots[point[1]].append(point)
        chain = chains[ident] = [source, *waypoints, target]
        for a, b in pairwise(chain):
            neighbors.setdefault(a, []).append(b)
            neighbors.setdefault(b, []).append(a)
        incoming[target].append(edge)
        outgoing[source].append(edge)
        labels[ident] = wrap(edge.get("label", ""), LABEL, GAP - 70) + (["REMOVED"] if removable(edge) else [])

    def last(item):
        """Where an item sits in its column: nodes first, then the edges passing through it, then exits."""
        if not isinstance(item, str):
            return 1
        return 2 if nodes[item]["type"] == "exit" else 0

    for sweep in range(8):
        ahead = sweep % 2 == 0
        columns = range(1, len(slots)) if ahead else range(len(slots) - 2, -1, -1)
        for column in columns:
            reference = {item: i for i, item in enumerate(slots[column - 1 if ahead else column + 1])}
            here = {item: i for i, item in enumerate(slots[column])}

            def barycenter(item, reference=reference, here=here):
                linked = [reference[n] for n in neighbors.get(item, []) if n in reference]
                return (last(item), sum(linked) / len(linked) if linked else here[item])

            slots[column].sort(key=barycenter)
    for slot in slots:
        slot.sort(key=last)  # edges passing through, then exits, sit below the nodes of their column

    box_heights = {ident: logic_box_height(node, boxes_of) for ident, node in nodes.items()}
    heights = {
        ident: max(box_heights[ident], sum(15 * len(labels[e["id"]]) + 14 for e in incoming[ident]) + 16)
        if nodes[ident]["type"] != "start"
        else START
        for ident in nodes
    }
    x = {item: column * (COLW + GAP) for column, slot in enumerate(slots) for item in slot}
    y, _, total = place_bands(slots, heights, [], chains, x)
    for ident, node in nodes.items():
        # The start lines up with the arrow it sends, which enters its target below that target's other labels.
        if node["type"] == "start" and len(outgoing[ident]) == 1 and len(chains[outgoing[ident][0]["id"]]) == 2:
            edge = outgoing[ident][0]
            target = edge["to"]
            ahead_of = sorted(incoming[target], key=lambda e: y[chains[e["id"]][-2]])
            port = y[target] + 8
            for other in ahead_of:
                port += len(labels[other["id"]]) * 15 + 6
                if other is edge:
                    break
                port += 8
            y[ident] = port - START / 2
    routes, _ = route_edges(routed, chains, incoming, outgoing, labels, x, y, heights, total)
    boxes = {
        ident: (x[ident] + COLW - START, y[ident], START, START)
        if nodes[ident]["type"] == "start"
        else (x[ident], y[ident], COLW, heights[ident])
        for ident in nodes
    }

    label_boxes = {}
    for edge in routed:
        lines = labels[edge["id"]]
        if not edge.get("label") and not removable(edge):
            continue
        ex, ey = routes[edge["id"]][-1]
        w = max(width(line, LABEL) for line in lines)
        label_boxes[edge["id"]] = (ex - 12 - w, ey - 6 - 15 * len(lines) + 3, w, 15 * (len(lines) - 1) + 13)

    # Edges back, and forward edges drawn apart: an arc above the drawing when both ends are the top of their column
    # and no earlier arc ends at either or spans only part of it; otherwise a pair of numbered connectors on top of
    # their ends. An edge to its own node loops on that node's corner.
    top_items = {slot[0] for slot in slots if slot}
    ceiling = min((box[1] for box in boxes.values()), default=0)
    edges = {edge["id"]: edge for edge in flow["edges"]}
    apart = [edge for edge in flow["edges"] if edge["id"] in back | jumps and edge["from"] != edge["to"]]
    apart.sort(key=lambda e: abs(x[e["from"]] - x[e["to"]]))
    plans, arcs, used = {}, [], set()
    for edge in apart:
        source, target = edge["from"], edge["to"]
        low, high = sorted((x[source], x[target]))
        partial = any(a < low < b < high or low < a < high < b for a, b, _ in arcs)
        arc = (
            edge["id"] in back
            and edge["id"] not in no_arc
            and source in top_items
            and target in top_items
            and not partial
            and not {source, target} & used
        )
        if arc:
            inside = [lane for a, b, lane in arcs if low <= a and b <= high]
            lane = 1 + max(inside, default=0)
            arcs.append((low, high, lane))
            used |= {source, target}
            plans[edge["id"]] = ("arc", lane)
        else:
            plans[edge["id"]] = ("connector", None)
    # Each node's attachments on top share its width: arcs and connectors, in the order of the edges.
    on_top = {}
    for edge in flow["edges"]:
        if edge["id"] in plans:
            for end in (edge["from"], edge["to"]):
                on_top.setdefault(end, []).append(edge["id"])

    def top_x(node, ident):
        bx, _, bw, _ = boxes[node]
        if nodes[node]["type"] == "start":
            return bx + bw / 2
        spots = on_top[node]
        return bx + bw * (spots.index(ident) + 1) / (len(spots) + 1)

    loops, number = {}, 0
    for edge in flow["edges"]:
        ident, source, target = edge["id"], edge["from"], edge["to"]
        if ident not in plans:
            continue
        kind, lane = plans[ident]
        sx, tx = top_x(source, ident), top_x(target, ident)
        sy, ty = boxes[source][1], boxes[target][1]
        if kind == "arc":
            lane_y = ceiling - 40 - LANE * (lane - 1)
            loops[ident] = {
                "kind": "arc",
                "paths": [[(sx, sy), (sx, lane_y), (tx, lane_y), (tx, ty)]],
                "label_at": ((sx + tx) / 2, lane_y - 6),
            }
        else:
            number += 1
            loops[ident] = {
                "kind": "connector",
                "number": number,
                "circles": [(sx, sy - 22), (tx, ty - 22)],
                "paths": [[(sx, sy), (sx, sy - 13)], [(tx, ty - 13), (tx, ty)]],
                "label_at": (sx + 14, sy - 18),
            }
    rank = {}
    for edge in flow["edges"]:
        if edge["from"] == edge["to"]:
            # Several loops on one node nest: each next one rises higher, reaches further out and comes back lower.
            k = rank[edge["from"]] = rank.get(edge["from"], -1) + 1
            bx, by_, bw, _ = boxes[edge["from"]]
            rise, out, back = 14 + 16 * k, 14 + 12 * k, 8 + 8 * k
            path = [
                (bx + bw - 36 - 12 * k, by_),
                (bx + bw - 36 - 12 * k, by_ - rise),
                (bx + bw + out, by_ - rise),
                (bx + bw + out, by_ + back),
                (bx + bw, by_ + back),
            ]
            loops[edge["id"]] = {"kind": "self", "paths": [path], "label_at": (bx + bw + out + 6, by_ - rise - 6)}
    for ident, loop in loops.items():
        lines = wrap(edges[ident].get("label", ""), LABEL, GAP - 70) + (["REMOVED"] if removable(edges[ident]) else [])
        loop["lines"] = lines
        if not edges[ident].get("label") and not removable(edges[ident]):
            continue
        lx, ly = loop["label_at"]
        w = max(width(line, LABEL) for line in lines)
        anchor = lx - w / 2 if loop["kind"] == "arc" else lx
        label_boxes[ident] = (anchor, ly - 15 * len(lines) + 3, w, 15 * (len(lines) - 1) + 13)

    apart_forward = {ident: loops.pop(ident) for ident in list(loops) if ident in jumps}
    points = [point for path in routes.values() for point in path]
    points += [point for loop in [*loops.values(), *apart_forward.values()] for path in loop["paths"] for point in path]
    points += [(bx + dx, by_ + dy) for bx, by_, bw, bh in boxes.values() for dx, dy in ((0, 0), (bw, bh))]
    points += [(lx + dx, ly + dy) for lx, ly, lw, lh in label_boxes.values() for dx, dy in ((0, 0), (lw, lh))]
    points += [
        (cx + d, cy + d)
        for loop in [*loops.values(), *apart_forward.values()]
        for cx, cy in loop.get("circles", [])
        for d in (-10, 10)
    ]
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return {
        "nodes": nodes,
        "edges": edges,
        "boxes": boxes,
        "heights": heights,
        "routes": routes,
        "labels": labels,
        "loops": loops,
        "jumps": apart_forward,
        "label_boxes": label_boxes,
        "bounds": (min(xs, default=0), min(ys, default=0), max(xs, default=0), max(ys, default=0)),
    }


def draw_logic_node(node, box, prefix, status, actor):
    """A logic node: the start as a filled circle; any other as a box with its kind line, its label and, for a step
    with `by`, the icon and name of the box that does it; an exit with a double outline and its outcome's words."""
    ident = node["id"]
    x, y, w, h = box
    removed = status == "removed"
    stroke = SEC if removed else INK
    out = [f'<g id="{part_id(prefix, "step", ident)}" data-id="{esc(ident)}">']
    if node["type"] == "start":
        fill = SEC if removed else (TERRA if status == "new" else INK)
        out.append(f'<circle cx="{x + w / 2}" cy="{y + h / 2}" r="{w / 2}" fill="{fill}"/>')
        out.append(f"<title>{'Start (removed)' if removed else 'Start'}</title>")
        return out + ["</g>"]
    dash = DASH if removed else ""
    italic = ITALIC if removed else ""
    out.append(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{CREAM if removed else LINEN}" stroke="{stroke}" '
        f'stroke-width="1.5"{dash}/>'
    )
    if node["type"] == "exit":
        out.append(
            f'<rect x="{x + 4}" y="{y + 4}" width="{w - 8}" height="{h - 8}" fill="none" stroke="{stroke}" '
            f'stroke-width="1"{dash}/>'
        )
    if status == "new":
        out.append(f'<rect x="{x}" y="{y}" width="7" height="{h}" fill="{STRIP}"/>')
    kind = EXIT_WORDS[node["outcome"]] if node["type"] == "exit" else LOGIC_KINDS[node["type"]]
    out.append(
        f'<text x="{x + 14}" y="{y + 22}" font-size="10.5" letter-spacing="0.08em" fill="{SEC}">{esc(kind)}</text>'
    )
    tag = {"new": "NEW", "removed": "REMOVED"}.get(status, "")
    if tag:
        out.append(
            f'<text x="{x + w - 12}" y="{y + 22}" text-anchor="end" font-size="10.5" font-weight="700" '
            f'letter-spacing="0.08em" fill="{part_color(status)}">{tag}</text>'
        )
    for i, line in enumerate(logic_label_lines(node)):
        out.append(
            f'<text x="{x + 14}" y="{y + 42 + 19 * i}" font-size="16" font-weight="600" '
            f'fill="{SEC if removed else HEAD}"{italic}>{esc(line)}</text>'
        )
    if actor is not None:
        ay = y + 42 + 19 * (len(logic_label_lines(node)) - 1) + 12
        out.append(f'<g transform="translate({x + 14} {ay})">{glyph(actor["kind"], stroke)}</g>')
        out.append(
            f'<text x="{x + 34}" y="{ay + 11}" font-size="12.5" fill="{SEC}"{italic}>{esc(actor["label"])}</text>'
        )
    return out + ["</g>"]


def logic_label(lines, x, y, color, italic, anchor="end"):
    return [
        f'<text x="{x:.1f}" y="{y - 15 * (len(lines) - 1 - i):.1f}" text-anchor="{anchor}" font-size="{LABEL}" '
        f'fill="{color}"{italic} paint-order="stroke" stroke="{CREAM}" stroke-width="4">{esc(line)}</text>'
        for i, line in enumerate(lines)
    ]


def svg_logic(flow: dict, state: str, layout: dict, view: str) -> str:
    """Render a logic flow from its layout (see `logic_layout`), the same in every version: what a version does not
    have is left out, what it removes is drawn removed and what it adds is drawn new."""
    prefix = f"{quote(view, safe='')}-{state}"
    shape = logic_layout(flow, layout)
    left, top, right, bottom = shape["bounds"]
    pad = 24
    w, h = right - left + 2 * pad, bottom - top + 2 * pad
    out = start_svg(f"{left - pad:.1f} {top - pad:.1f} {w:.1f} {h:.1f}", flow["name"], w, h, left - pad, top - pad)
    if not visible(flow, state):
        return "\n".join(out + ["</svg>"])
    out.extend(markers(prefix, ("response",)))
    nodes, marks = shape["nodes"], []
    findings = layout["findings"]

    def target(ident):
        scoped = f"{view}:step:{ident}"
        return scoped if scoped in findings or layout["step_counts"][ident] > 1 else f"step:{ident}"

    for edge in flow["edges"]:
        ident = edge["id"]
        if not all(visible(item, state) for item in (edge, nodes[edge["from"]], nodes[edge["to"]])):
            continue
        status = flow_status(edge, flow, state)
        color = part_color(status)
        dash, italic = (DASH, ITALIC) if status == "removed" else ("", "")
        stroke = (
            f'fill="none" stroke="{color}" stroke-width="{2.2 if status == "new" else 1.6}" stroke-linejoin="round"'
        )
        arrow = f' marker-end="url(#{marker_id(prefix, "response", status)})"'
        out.append(f'<g id="{part_id(prefix, "step", ident)}" data-id="{esc(ident)}">')
        apart = shape["loops"].get(ident) or shape["jumps"].get(ident)
        lines = shape["labels"].get(ident) or (apart or {}).get("lines", [])
        if removable(edge) and status != "removed":
            lines = lines[:-1]
        if ident in shape["routes"]:
            points = shape["routes"][ident]
            path = "M" + " L".join(f"{px:.1f} {py:.1f}" for px, py in points)
            out.append(f'<path d="{path}" {stroke}{dash}{arrow}/>')
            lx, ly = points[-1]
            out.extend(logic_label(lines, lx - 12, ly - 6, color, italic))
        else:
            loop = apart
            for i, points in enumerate(loop["paths"]):
                path = "M" + " L".join(f"{px:.1f} {py:.1f}" for px, py in points)
                end = arrow if i == len(loop["paths"]) - 1 else ""
                out.append(f'<path d="{path}" {stroke}{dash}{end}/>')
            for cx, cy in loop.get("circles", []):
                out.append(
                    f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="9" fill="{CREAM}" stroke="{color}" stroke-width="1.5"/>'
                    f'<text x="{cx:.1f}" y="{cy + 4:.1f}" text-anchor="middle" font-size="11" font-weight="700" '
                    f'fill="{color}">{loop["number"]}</text>'
                )
            lx, ly = loop["label_at"]
            anchor = "middle" if loop["kind"] == "arc" else "start"
            out.extend(logic_label(lines, lx, ly, color, italic, anchor))
        out.append("</g>")
        if state == "after" and ident in shape["label_boxes"]:
            bx, by_, _, _ = shape["label_boxes"][ident]
            marks.extend(badges(findings, target(ident), bx - 4, by_ + 6))
    boxes_of = layout["nodes"]
    for ident, node in nodes.items():
        if not visible(node, state):
            continue
        actor = boxes_of.get(node.get("by"))
        box = shape["boxes"][ident]
        out.extend(draw_logic_node(node, box, prefix, flow_status(node, flow, state), actor))
        if state == "after":
            marks.extend(badges(findings, target(ident), box[0] + box[2] - 6, box[1] - 9))
    return finish_svg(out, marks)


def register() -> str:
    """Build the register from the same kind and icon data used in both diagrams."""
    template = Template(resources.read_text("architect/register.html"))
    section = Template(resources.read_text("architect/register-section.html"))
    card = Template(resources.read_text("architect/register-card.html"))
    grouped = {}
    for name, kind in KINDS.items():
        grouped.setdefault(kind["group"], []).append(
            card.substitute(name=esc(name), label=esc(kind["label"]), use=esc(kind["use"]), icon=glyph(name))
        )
    sections = "".join(section.substitute(title=esc(title), cards="".join(cards)) for title, cards in grouped.items())
    return template.substitute(css=resources.read_text("architect/register.css"), sections=sections)


def drawings(design: dict) -> dict[str, str]:
    """The SVGs of each version of a design (see `versions`): `containers-<version>.svg`, `containers-<grouping>-<version>.svg`
    for each other grouping it uses (see `overlays`), and `flow<N>-<version>.svg` for each flow."""
    design = without_nulls(design)
    positions = layout(design)
    files = {}
    for state, _ in versions(design):
        files[f"containers-{state}.svg"] = svg_containers(positions, state)
        for overlay, _ in overlays(design):
            files[f"containers-{overlay}-{state}.svg"] = svg_containers(positions, state, overlay)
        for i, flow in enumerate(design.get("flows", []), 1):
            view = f"flow{i}"
            files[f"{view}-{state}.svg"] = svg_flow(flow, state, positions, view)
    return files
