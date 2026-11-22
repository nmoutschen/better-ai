"""show-better's checks across a presentation spec, named by `x-check` in its schema."""

from __future__ import annotations

from typing import Any

from ..schema import Context, hook, show


def _is_num(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _show_overview_labels(panel: dict) -> list:
    """The labels a later panel's `focus` may name: those of the overview panel's steps, events, nodes or groups."""

    def listed(key: str) -> list:
        found = panel.get(key)
        return found if isinstance(found, list) else []

    def labels(key: str) -> list:
        return [x.get("label") for x in listed(key) if isinstance(x, dict)]

    kind = panel.get("kind")
    if kind == "flow":
        return labels("steps")
    if kind == "timeline":
        return labels("events")
    if kind == "concept":
        return labels("nodes")
    found = []
    for group in listed("groups"):
        if isinstance(group, dict):
            inside = group.get("items")
            found += [group.get("label"), *map(str, inside if isinstance(inside, list) else [])]
    return found


def _show_visual(v: dict, where: str, document_sections: Any) -> list[tuple[str, str]]:
    """What one visual refers to inside itself: the node an edge names, the set a region names, the cells of a row."""
    problems: list[tuple[str, str]] = []
    kind = v.get("kind")

    def items(key: str) -> list:
        found = v.get(key)
        return found if isinstance(found, list) else []

    if kind == "map" and not (v.get("sections") or document_sections):
        problems.append((f"{where}.sections", "a map needs 'sections', or a top-level 'document' with 'sections'"))
    if kind == "concept":
        ids = {n["id"] for n in items("nodes") if isinstance(n, dict) and isinstance(n.get("id"), str)}
        for j, edge in enumerate(items("edges")):
            for end in ("from", "to"):
                if isinstance(edge, dict) and isinstance(edge.get(end), str) and edge[end] not in ids:
                    problems.append((f"{where}.edges[{j}].{end}", "names no node id of 'nodes'"))
    if kind == "sets":
        names = {n for n in items("sets") if isinstance(n, str)}
        for j, region in enumerate(items("regions")):
            ins = region.get("in") if isinstance(region, dict) else None
            if isinstance(ins, list) and not all(n in names for n in ins if isinstance(n, str)):
                problems.append((f"{where}.regions[{j}].in", "names a set that 'sets' does not list"))
    if kind == "lanes":
        actors = {a for a in items("actors") if isinstance(a, str)}
        for j, step in enumerate(items("steps")):
            if isinstance(step, dict) and isinstance(step.get("actor"), str) and step["actor"] not in actors:
                problems.append((f"{where}.steps[{j}].actor", "is not one of 'actors'"))
    if kind in ("matrix", "table"):
        columns = items("columns")
        for j, row in enumerate(items("rows")):
            cells = row if kind == "table" else row.get("cells") if isinstance(row, dict) else None
            if isinstance(cells, list) and len(cells) != len(columns):
                field = f"{where}.rows[{j}]" + (".cells" if kind == "matrix" else "")
                problems.append((field, f"has {len(cells)} cells for {len(columns)} columns"))
    if kind == "tree" and isinstance(v.get("root"), dict):

        def walk(node: dict, path: str) -> None:
            children = node.get("children") if isinstance(node.get("children"), list) else []
            kids = [k for k in children if isinstance(k, dict)]
            if kids and _is_num(node.get("value")) and all(_is_num(k.get("value")) for k in kids):
                total = sum(k["value"] for k in kids)
                if abs(total - node["value"]) > 1e-9 * max(1, abs(node["value"])) and total > node["value"]:
                    problems.append((path, f"its children sum to {total:g}, more than its value {node['value']:g}"))
            for j, kid in enumerate(children):
                if isinstance(kid, dict):
                    walk(kid, f"{path}.children[{j}]")

        walk(v["root"], f"{where}.root")
    return problems


@hook("show_spec")
def _show_spec(record: dict, context: Context) -> list[tuple[str, str]]:
    """What a show-better spec's panels say about each other and about themselves: a visual's references, an
    action's target panel, one overview, and the focus labels it holds."""
    panels = record.get("panels")
    if not isinstance(panels, list):
        return []
    document = record.get("document")
    sections = document.get("sections") if isinstance(document, dict) else None
    problems: list[tuple[str, str]] = []
    overview: tuple[int, list] | None = None  # the panel number and its labels, once a panel sets overview
    for i, panel in enumerate(panels):
        if not isinstance(panel, dict):
            continue
        at = f"panels[{i}]"
        template = panel.get("template") or "visual"
        if template == "visual":
            problems += _show_visual(panel, at, sections)
        elif template == "compare":
            for side in ("a", "b"):
                if isinstance(panel.get(side), dict):
                    problems += _show_visual(panel[side], f"{at}.{side}", sections)
        elif template == "title" and isinstance(panel.get("actions"), list):
            for j, action in enumerate(panel["actions"]):
                target = action.get("panel") if isinstance(action, dict) else None
                if isinstance(target, int) and not isinstance(target, bool) and not 1 <= target <= len(panels):
                    problems.append(
                        (f"{at}.actions[{j}].panel", f"points to panel {target}; there are {len(panels)} panels")
                    )
        if panel.get("overview") is True:
            if overview:
                problems.append(
                    (f"{at}.overview", f"only one panel may set 'overview'; panel {overview[0]} already does")
                )
            elif template == "visual" and panel.get("kind") in ("flow", "timeline", "concept", "groups"):
                overview = (i + 1, _show_overview_labels(panel))
        focus = panel.get("focus")
        if focus is not None:
            wanted = [focus] if isinstance(focus, str) else focus if isinstance(focus, list) else []
            if overview is None:
                problems.append((f"{at}.focus", 'needs an earlier panel with "overview": true'))
            else:
                for label in wanted:
                    if label not in overview[1]:
                        shown = ", ".join(map(str, overview[1]))
                        problems.append(
                            (
                                f"{at}.focus",
                                f"{show(label)} is not a label in the overview (panel {overview[0]}): {shown}",
                            )
                        )
    return problems
