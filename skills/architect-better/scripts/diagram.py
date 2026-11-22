"""Render and validate architecture diagrams from a design JSON.

A design can carry findings as a mapping from node IDs, edge:<id>, and
<view>:step:<id> (or step:<id> for a design-wide unique step ID) to lists of [badge ID, tooltip, perspective] entries. One finding
can be attached to multiple parts by listing it under each target.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
import textwrap
from collections import Counter
from itertools import pairwise
from pathlib import Path
from string import Template
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # schema.py, which checks a design's references, is next to this script
import schema  # noqa: E402

KINDS = {kind["name"]: kind for kind in json.loads((HERE / "kinds.json").read_text(encoding="utf-8"))}
ICONS = json.loads((HERE / "icons.json").read_text(encoding="utf-8"))

STATES = ("before", "after")
INK, HEAD, SEC = "#33302B", "#1C1A17", "#78736B"
LINEN, CREAM, SAND = "#F2EDE5", "#FFFCF7", "#C4B69C"
TERRA, STRIP = "#AA5141", "#E8725C"
SANS = "'Space Grotesk', -apple-system, sans-serif"
COLW, GAP, VGAP = 206, 236, 44
LABEL = 12.5
DASH = ' stroke-dasharray="6 4"'
ITALIC = ' font-style="italic"'
ARROWS = {
    "request": ("Request", "M1 1 L9 5 L1 9 Z", 11, True, ""),
    "response": ("Response", "M1 1 L9 5 L1 9", 8, False, DASH),
    "async": ("Async message", "M0 0 L9 5", 12, False, ""),
}


def without_nulls(value):
    """A copy with every null dropped from the objects in it: the schemas let an optional field be null, which means
    the same as leaving it out."""
    if isinstance(value, dict):
        return {key: without_nulls(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [without_nulls(item) for item in value]
    return value


def shape_problems(design: dict) -> list[str]:
    """What is wrong with the shape of a design, by design.schema.json; the fields the page adds (`findings`), a `title` and the
    base fields a design.json carries are not part of what diagram.py is given."""
    candidate = {"type": "design", "at": "2026-01-01T00:00:00Z", "by": "diagram.py", "flows": []}
    candidate.update({key: value for key, value in design.items() if key not in ("findings", "flow", "title")})
    found = schema.check_record(candidate, ["design.schema.json"], HERE.parent / "schemas")
    return [f"{field}: {message}" for field, message in found]


def validate(design: dict) -> list[str]:
    """Report what stops a design from being laid out. The shape is design.schema.json's, and the references inside a
    well-shaped design, and its box kinds, are schema.py's (`design_problems`); this keeps the one check that needs
    the layout: a finding that names no part of it."""
    if not isinstance(design, dict):
        return ["design: expected an object"]
    design = without_nulls(design)
    errors = shape_problems(design)
    if errors:
        return errors
    errors = [message for _, message in schema.design_problems(design)]
    if "flow" in design:
        errors.append("Use a flows list instead of flow")
    targets = {node["id"] for node in design["containers"]["nodes"]}
    targets |= {f"edge:{edge['id']}" for edge in design["containers"].get("edges", [])}
    step_counts = Counter()
    for i, flow in enumerate(design.get("flows", []), 1):
        step_ids = [step["id"] for step in flow["steps"]]
        step_counts.update(step_ids)
        targets.update(f"flow{i}:step:{ident}" for ident in step_ids)
    targets.update(f"step:{ident}" for ident, count in step_counts.items() if count == 1)
    for target in design.get("findings", {}):
        if target not in targets:
            errors.append(f"Finding target {target!r}: missing or ambiguous diagram part")
    return errors


def visible(item, state):
    states = item.get("in", STATES)
    return state == "after" or set(states) == set(STATES)


def appearance(item, state):
    if state == "after" and item.get("in") == ["before"]:
        return "removed"
    if state == "after" and item.get("in") == ["after"]:
        return "new"
    return "current"


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


def layers(nodes, edges):
    """Layer the forward graph; cycle-closing edges get return routes."""
    forward = {node: [] for node in nodes}
    for edge in edges:
        source, target = edge["from"], edge["to"]
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
    groups = [group for group in containers.get("groups", []) if group["members"]]
    level = layers(nodes, edges)
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
        labels[ident] = wrap(raw, LABEL, GAP - 70) + (["REMOVED"] if edge.get("in") == ["before"] else [])

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

    heights = {
        ident: max(
            59 + 15 * len(wrap(node.get("detail", ""), 12.5, COLW - 28)),
            sum(15 * len(labels[edge["id"]]) + 14 for edge in incoming[ident]) + 16,
        )
        for ident, node in nodes.items()
    }
    x = {item: column * (COLW + GAP) for column, slot in enumerate(slots) for item in slot}
    y, bands, total = place_bands(slots, heights, groups, chains, x)
    routes, extra = route_edges(edges, chains, incoming, outgoing, labels, x, y, heights, total)
    return {
        "nodes": nodes,
        "edges": edges,
        "groups": bands,
        "x": x,
        "y": y,
        "heights": heights,
        "labels": labels,
        "routes": routes,
        "width": len(slots) * (COLW + GAP) - GAP,
        "height": total + extra,
        "findings": design.get("findings", {}),
        "step_counts": Counter(step["id"] for flow in design.get("flows", []) for step in flow["steps"]),
    }


def place_bands(slots, heights, groups, chains, x):
    """Separate grouped boxes vertically, allowing ungrouped-only columns to center."""
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
    top, bottom = 0, 0
    for group in [*groups, None]:
        key = group["id"] if group else None
        start = top + (30 if group else 0)
        columns = [[item for item in slot if membership.get(item) == key] for slot in slots if slot not in free]
        end = max((place(column, start) for column in columns), default=start)
        if end == start:
            continue
        bottom = end
        if group:
            left = min(x[n] for n in group["members"]) - 16
            right = max(x[n] for n in group["members"]) + COLW + 16
            bands.append((group, left, top - 4, right - left, end - top + 16))
        top = end + 56

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

    routes, gaps, return_space = {}, {}, 0
    for edge in edges:
        ident = edge["id"]
        chain = chains[ident]
        source, target = chain[0], chain[-1]
        start, end = ports_out[ident], ports_in[ident]
        if x[source] >= x[target]:
            return_space += 15 * len(labels[ident]) + 14
            lower = total + return_space
            right, left = x[source] + COLW + 18, x[target] - 18
            routes[ident] = [
                (right - 18, start),
                (right, start),
                (right, lower),
                (left, lower),
                (left, end),
                (x[target], end),
            ]
            continue
        if len(chain) == 2 and abs(end - start) < 16 and y[source] + 10 <= end <= y[source] + heights[source] - 10:
            start = end
        routes[ident] = [(x[source] + COLW, start)]
        for i, (a, b) in enumerate(pairwise(chain)):
            finish = end if b == target else y[b]
            gaps.setdefault(x[a] + COLW, []).append((ident, start, finish, x[b], i == len(chain) - 2))
            start = finish

    for gap, runs in sorted(gaps.items()):
        up = sorted((run for run in runs if run[2] < run[1]), key=lambda run: run[2])
        down = sorted((run for run in runs if run[2] > run[1]), key=lambda run: -run[2])
        tracks = {
            run: gap + 18 + min(14, (GAP - 44) / max(1, len(direction))) * i
            for direction in (up, down)
            for i, run in enumerate(direction)
        }
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


def svg_containers(layout: dict, state: str) -> str:
    """Render one state from the shared layout. IDs start with c-<state>-."""
    prefix = f"c-{state}"
    pad = 24
    w, h = layout["width"] + 2 * pad, layout["height"] + 2 * pad
    out = start_svg(f"{-pad} {-pad} {w} {h}", "Containers", w, h, -pad, -pad)
    out.extend(markers(prefix, ("response",)))
    box_marks, edge_marks = [], []
    for group, x, y, gw, gh in layout["groups"]:
        if visible(group, state):
            out.extend(draw_group(group, x, y, gw, gh, prefix, appearance(group, state)))
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
        # A return edge enters from the left. Put its label on the lower
        # horizontal leg so it remains inside the view even in column zero.
        x, y = points[2] if layout["x"][edge["from"]] >= layout["x"][edge["to"]] else points[-1]
        lines = layout["labels"][ident]
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
    return finish_svg(out, box_marks + edge_marks)


def step_numbers(flow):
    steps = flow["steps"]
    if flow.get("in") == ["after"] or all(step.get("in") == ["after"] for step in steps):
        return [str(i) for i in range(1, len(steps) + 1)]
    base, suffix = 0, 0
    numbers = []
    for step in steps:
        if step.get("in") == ["after"]:
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


def flow_status(item, related):
    states = [appearance(part, "after") for part in (item, related)]
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
    prefix = f"{quote(view, safe='')}-{state}"
    participants = flow["participants"]
    nodes, heights = layout["nodes"], layout["heights"]
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
    for i, (step, number) in enumerate(zip(steps, step_numbers(flow), strict=True)):
        source, target = step["from"], step["to"]
        if not visible(step, state) or source not in shown or target not in shown:
            continue
        status = flow_status(step, flow) if state == "after" else "current"
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


def register():
    """Build the register from the same kind and icon data used in both diagrams."""
    template = Template((HERE / "register.html").read_text(encoding="utf-8"))
    section = Template((HERE / "register-section.html").read_text(encoding="utf-8"))
    card = Template((HERE / "register-card.html").read_text(encoding="utf-8"))
    grouped = {}
    for name, kind in KINDS.items():
        grouped.setdefault(kind["group"], []).append(
            card.substitute(name=esc(name), label=esc(kind["label"]), use=esc(kind["use"]), icon=glyph(name))
        )
    sections = "".join(section.substitute(title=esc(title), cards="".join(cards)) for title, cards in grouped.items())
    return template.substitute(css=(HERE / "register.css").read_text(encoding="utf-8"), sections=sections)


@schema.never_raise("design", {"render": "rendered", "register": "written", "": "checked"})
def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    render = commands.add_parser("render", help="write Before and After SVGs")
    render.add_argument("design", type=Path)
    render.add_argument("--out", type=Path, required=True)
    check = commands.add_parser("check", help="validate a design")
    check.add_argument("design", type=Path)
    index = commands.add_parser("register", help="write the kind register as HTML")
    index.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "register":
            args.out.write_text(register(), encoding="utf-8")
            return 0
        design = json.loads(args.design.read_text(encoding="utf-8"))
        if not isinstance(design, dict):
            raise ValueError("design: expected an object")
        design = without_nulls(design)  # an optional field that is null is absent: no render path sees one
        if args.command == "check":
            errors = validate(design)
            if errors:
                raise ValueError("\n".join(errors))
            return 0
        positions = layout(design)
        files = {}
        for state in STATES:
            files[f"containers-{state}.svg"] = svg_containers(positions, state)
            for i, flow in enumerate(design.get("flows", []), 1):
                view = f"flow{i}"
                files[f"{view}-{state}.svg"] = svg_flow(flow, state, positions, view)
        args.out.mkdir(parents=True, exist_ok=True)
        for name, svg in files.items():
            (args.out / name).write_text(svg + "\n", encoding="utf-8")
    except (OSError, ValueError) as error:  # a file that cannot be read, a JSON error, what validate found
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
