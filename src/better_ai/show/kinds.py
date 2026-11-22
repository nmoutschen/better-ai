"""The kinds of visual: for each, what its data must meet to draw, its HTML and SVG drawing and its plain-text form."""

import math
import re
from html.parser import HTMLParser

from .lib import (
    EVIDENCE_WORDS,
    KINDS,
    LIMITS,
    MARKS,
    OUTCOMES,
    SANS,
    C,
    W,
    _as_list,
    _is_num,
    arrow,
    axis_start,
    count_highlights,
    dattr,
    dot,
    esc,
    ev_of,
    listed,
    median,
    nice_ticks,
    num,
    plain,
    rich,
    svg_wrap,
    table_html,
    table_lines,
    tbox,
    tcut,
    text_el,
    tfmt,
    twrap,
    wrap,
)

# ---------- map: check, HTML, text ----------


def check_map(p, where, errors, warnings, digest, spec=None):
    secs = p.get("sections") or ((spec or {}).get("document") or {}).get("sections")
    if len(secs) > 9:
        warnings.append(f"{where}: {len(secs)} sections; group them into at most 9 parts")
    if p.get("sections"):
        for sec in secs:
            if len(str(sec.get("gist", ""))) > 50:
                warnings.append(
                    f"{where}: the gist of '{sec.get('label')}' is {len(sec['gist'])} characters; keep it under 50, a few words"
                )
    for s in secs:
        digest.append(
            f"    {s.get('id', '')} {s['label']}{(' — ' + s['gist']) if s.get('gist') else ''}"
            f"{'  [highlight]' if s.get('highlight') or s.get('id') in _as_list(p.get('highlight')) else ''}"
        )


def v_map(p, spec=None):
    """The document's parts in order, as segments of one rule: the organizer the reader returns to."""
    secs = p.get("sections") or spec["document"]["sections"]
    hl_ids = set(_as_list(p.get("highlight")))
    n = len(secs)
    body = []
    if n <= 5:  # one rule, a segment per part: label above, gist below
        gap = 14
        bw = (W - gap * (n - 1)) / n
        llines = [wrap(sec["label"], int(bw / 8.8), 2) for sec in secs]
        glines = [wrap(sec.get("gist", ""), int(bw / 7.2), 3) if sec.get("gist") else [] for sec in secs]
        y = 18 + 19 * max(len(lab) for lab in llines)
        for k, sec in enumerate(secs):
            x = k * (bw + gap)
            hl = sec.get("highlight") or sec.get("id") in hl_ids
            body.append(
                text_el(
                    x,
                    y - 14 - 19 * (len(llines[k]) - 1),
                    llines[k],
                    15.5,
                    700 if hl else 500,
                    C["heading"],
                    gap=19,
                    d=sec,
                )
            )
            body.append(
                f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + bw:.1f}" y2="{y:.1f}" stroke="{C["terracotta"] if hl else C["ink"]}" stroke-width="{3 if hl else 1}"{dattr(sec)}/>'
            )
            if glines[k]:
                body.append(text_el(x, y + 22, glines[k], 13, 500, C["muted"], gap=17))
        h = y + 22 + 17 * max([len(gl) for gl in glines] + [0])
    else:  # one row per part, on hairlines
        rh = 40
        for k, sec in enumerate(secs):
            y = 26 + k * rh
            hl = sec.get("highlight") or sec.get("id") in hl_ids
            body.append(dot(10, y - 5, sec, hl))
            body.append(text_el(30, y, wrap(sec["label"], 34, 1), 15.5, 700 if hl else 500, C["heading"], d=sec))
            if sec.get("gist"):
                body.append(text_el(370, y, wrap(sec["gist"], 52, 1), 13.5, 500, C["muted"]))
            body.append(
                f'<line x1="0" y1="{y + 13:.1f}" x2="{W}" y2="{y + 13:.1f}" stroke="{C["line"]}" stroke-width="1"/>'
            )
        h = 26 + n * rh - 20
    text = (
        "<ol>"
        + "".join(
            f"<li{dattr(sec)}><b>{esc(sec['label'])}</b>{(': ' + esc(sec['gist'])) if sec.get('gist') else ''}</li>"
            for sec in secs
        )
        + "</ol>"
    )
    return svg_wrap("".join(body), h + 4, p["headline"]), text


def t_map(p, W, g, spec=None):
    secs = p.get("sections") or spec["document"]["sections"]
    hl_ids = set(_as_list(p.get("highlight")))
    out = []
    for s in secs:
        hl = s.get("highlight") or s.get("id") in hl_ids
        head = f"{g['hl'] if hl else ' '} {s['label']}"
        out.append(head)
        if s.get("gist"):
            out += twrap(s["gist"], W - 4, "   ")
    return out


# ---------- concept: check, HTML, text ----------


def _layers(nodes, edges):
    ids = [n["id"] for n in nodes]
    succ = {i: [] for i in ids}
    for e in edges:
        succ[e["from"]].append(e["to"])
    # drop back edges found by depth-first search, so the layering has no cycles
    state, back = {}, set()

    def dfs(u):
        state[u] = 1
        for v in succ[u]:
            if state.get(v) == 1:
                back.add((u, v))
            elif v not in state:
                dfs(v)
        state[u] = 2

    for i in ids:
        if i not in state:
            dfs(i)
    layer = {i: 0 for i in ids}
    for _ in ids:
        for e in edges:
            if (e["from"], e["to"]) not in back:
                layer[e["to"]] = max(layer[e["to"]], layer[e["from"]] + 1)
    cols = {}
    for i in ids:
        cols.setdefault(layer[i], []).append(i)
    order = [cols[k] for k in sorted(cols)]
    pos = {}
    for _ in range(3):  # barycentre ordering, two sweeps per pass
        for k, col in enumerate(order):
            for j, i in enumerate(col):
                pos[i] = j
            if k:
                preds = {i: [pos[e["from"]] for e in edges if e["to"] == i and e["from"] in order[k - 1]] for i in col}
                col.sort(key=lambda i: sum(preds[i]) / len(preds[i]) if preds[i] else pos[i])
    return order, back


def check_concept(p, where, errors, warnings, digest):
    nodes = listed(p, "nodes", where, warnings, 12, "concepts")
    count_highlights(nodes, where, warnings)
    labels = {n["id"]: n["label"] for n in nodes}
    for e in p["edges"]:
        if len(e["label"]) > 40:
            warnings.append(
                f"{where}: relation '{e['label']}' is {len(e['label'])} characters; keep relations to a few words and put conditions in the note"
            )
        digest.append(f"    {labels[e['from']]} —{e['label']}→ {labels[e['to']]}")


def v_concept(p):
    """Concepts and the labelled relations between them, laid out left to right."""
    nodes, edges = p["nodes"], p["edges"]
    order, back = _layers(nodes, edges)
    by_id = {n["id"]: n for n in nodes}
    L = len(order)
    nw = min(176, (W - 70 * (L - 1)) / L) if L > 1 else 220
    xgap = (W - nw * L) / (L - 1) if L > 1 else 0
    lines_of = {i: wrap(by_id[i]["label"], max(int(nw / 8.4), 8), 3) for i in by_id}
    nh = {i: 22 + 18 * len(lines_of[i]) for i in by_id}
    col_of = {i: k for k, col in enumerate(order) for i in col}
    long_edges = [e for e in edges if (e["from"], e["to"]) not in back and col_of[e["to"]] - col_of[e["from"]] > 1]
    lab_chars = max(int((xgap - 12) / 7.2), 10) if L > 1 else 18
    top = 30 + (16 * 3 + 30 if long_edges else 0)  # room above the nodes for edges that skip a column
    col_h = [sum(nh[i] for i in c) + 46 * (len(c) - 1) for c in order]
    H = max(col_h) + top + 20
    box = {}
    for k, col in enumerate(order):
        x = k * (nw + xgap)
        y = top + (H - top - 20 - col_h[k]) / 2
        for i in col:
            box[i] = (x, y, nw, nh[i])
            y += nh[i] + 46
    body, labels = [], []
    for e in edges:
        x1, y1, w1, h1 = box[e["from"]]
        x2, y2, w2, h2 = box[e["to"]]
        hl = e.get("highlight")
        color = C["terracotta"] if hl else C["ink"]
        if (e["from"], e["to"]) in back or x2 <= x1:
            sx, sy, tx, ty = x1 + w1 / 2, y1 + h1, x2 + w2 / 2, y2 + h2
            dip = max(sy, ty) + 34
            path = f"M{sx:.1f} {sy:.1f} C{sx:.1f} {dip:.1f} {tx:.1f} {dip:.1f} {tx:.1f} {ty + 6:.1f}"
            mx, my = (sx + tx) / 2, dip - 6
            H = max(H, dip + 30)
        elif e in long_edges:  # skips a column: arc over the nodes between, label at the top of the arc
            sx, sy, tx, ty = x1 + w1 / 2, y1, x2 + w2 / 2, y2
            arc = 22
            path = f"M{sx:.1f} {sy:.1f} C{sx:.1f} {arc} {tx:.1f} {arc} {tx:.1f} {ty - 7:.1f}"
            mx, my = (sx + tx) / 2, 0.75 * arc + 0.25 * (sy + ty) / 2 - 4
        else:
            sx, sy, tx, ty = x1 + w1, y1 + h1 / 2, x2, y2 + h2 / 2
            cx = (sx + tx) / 2
            path = f"M{sx:.1f} {sy:.1f} C{cx:.1f} {sy:.1f} {cx:.1f} {ty:.1f} {tx - 7:.1f} {ty:.1f}"
            mx, my = cx, (sy + ty) / 2
        body.append(
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{2 if hl else 1.2}" marker-end="url(#ah{"h" if hl else ""})"/>'
        )
        lab = wrap(e["label"], 24 if e in long_edges else lab_chars, 4)
        lw = max(len(part) for part in lab) * 7.2 + 10
        my -= (len(lab) - 1) * 8  # centre a multi-line label on its edge
        labels.append(
            f'<rect x="{mx - lw / 2:.1f}" y="{my - 13:.1f}" width="{lw:.1f}" height="{len(lab) * 16 + 6}" rx="3" fill="{C["cream"]}"/>'
            + text_el(mx, my + 1, lab, 13, 600 if hl else 500, C["heading"] if hl else C["muted"], "middle", True, 16)
        )
    for i, (x, y, w, h) in box.items():
        n = by_id[i]
        hl = n.get("highlight")
        body.append(
            f'<line x1="{x:.1f}" y1="{y + h - 4:.1f}" x2="{x + w:.1f}" y2="{y + h - 4:.1f}" '
            f'stroke="{C["terracotta"] if hl else C["ink"]}" stroke-width="{3 if hl else 1}"{dattr(n)}/>'
        )
        body.append(
            text_el(x + w / 2, y + 26, lines_of[i], 15, 700 if hl else 600, C["heading"], "middle", gap=18, d=n)
        )
    defs = (
        f'<defs><marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0L10 5L0 10z" fill="{C["ink"]}"/></marker>'
        f'<marker id="ahh" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0 0L10 5L0 10z" fill="{C["terracotta"]}"/></marker></defs>'
    )
    text = (
        "<ul>"
        + "".join(
            f"<li><span{dattr(by_id[e['from']])}>{esc(by_id[e['from']]['label'])}</span> <i>{esc(e['label'])}</i> "
            f"<span{dattr(by_id[e['to']])}>{esc(by_id[e['to']]['label'])}</span></li>"
            for e in edges
        )
        + "</ul>"
    )
    return svg_wrap(defs + "".join(body) + "".join(labels), H, p["headline"]), text


def t_concept(p, W, g):
    by = {n["id"]: n for n in p["nodes"]}
    out = []
    order = [n["id"] for n in p["nodes"]]
    for nid in order:
        es = [e for e in p["edges"] if e["from"] == nid]
        if not es:
            continue
        n = by[nid]
        out.append(f"{g['hl'] if n.get('highlight') else ' '}{n['label']}")
        for k, e in enumerate(es):
            branch = g["end"] if k == len(es) - 1 else g["tee"]
            t = by[e["to"]]
            out += twrap(
                f"{branch}{g['h']} {e['label']} {g['arrow']} {t['label']}{' ' + g['hl'] if t.get('highlight') else ''}",
                W - 2,
                "  ",
            )
    lonely = [by[i]["label"] for i in order if not any(i in (e["from"], e["to"]) for e in p["edges"])]
    if lonely:
        out.append("Unlinked: " + ", ".join(lonely))
    return out


# ---------- flow: check, HTML, text ----------


def flow_boxes(labels, notes, hls, W, g, arrow_word):
    n = len(labels)
    aw = len(g["arrow"]) + 2
    bw = (W - aw * (n - 1)) // n if n else W
    out = []
    if n <= 4 and bw >= 14:
        boxes = []
        for lab, hl in zip(labels, hls, strict=False):
            boxes.append(tbox(twrap(lab, bw - 4), bw, g, hl))
        h = max(len(b) for b in boxes)
        for b in boxes:
            while len(b) < h:
                b.insert(-1, f"{g['v']}{' ' * (bw - 2)}{g['v']}")
        mid = h // 2
        for row in range(h):
            out.append(
                "".join(
                    b[row]
                    + ((" " + g["arrow"] + " ") if (k < n - 1 and row == mid) else (" " * aw if k < n - 1 else ""))
                    for k, b in enumerate(boxes)
                )
            )
        for k, note in enumerate(notes):
            if note:
                out += twrap(f"{k + 1}. {note}", W)
    else:
        width = min(W, 48)
        for k, (lab, note, hl) in enumerate(zip(labels, notes, hls, strict=False)):
            out += tbox(twrap(lab, width - 4) + (twrap(note, width - 4) if note else []), width, g, hl)
            if k < n - 1:
                out.append(" " * (width // 2) + g["down"])
    out.append(f"{g['arrow']} means: {arrow_word}")
    return out


def check_flow(p, where, errors, warnings, digest):
    steps = listed(p, "steps", where, warnings, LIMITS["flow"], "steps")
    count_highlights(steps, where, warnings)
    for s in steps:
        digest.append(
            f"    → {s['label']}{'  [highlight]' if s.get('highlight') else ''}"
            + (f" ({s['note']})" if s.get("note") else "")
        )


def v_flow(p):
    """Steps as marks on one line, each labelled on the drawing, joined by thin arrows."""
    steps = p["steps"]
    n = len(steps)
    body = []
    if n <= 5:  # one row, left to right
        cw = W / n
        chars = max(int((cw - 16) / 8.4), 8)
        labels = [wrap(s["label"], chars, 3) for s in steps]
        y = 20 + 19 * max(len(lab) for lab in labels)
        for i, s in enumerate(steps):
            x = cw * (i + 0.5)
            hl = s.get("highlight")
            body.append(
                text_el(
                    x,
                    y - 16 - 19 * (len(labels[i]) - 1),
                    labels[i],
                    15,
                    700 if hl else 500,
                    C["heading"],
                    "middle",
                    gap=19,
                    d=s,
                )
            )
            body.append(dot(x, y, s, hl))
            if s.get("note"):
                body.append(
                    text_el(
                        x, y + 28, wrap(s["note"], int((cw - 16) / 7.2), 3), 13, 500, C["muted"], "middle", True, 17
                    )
                )
            if i < n - 1:
                body.append(arrow(x + 12, y, x + cw - 12, y, C["ink"]))
        h = y + (28 + 17 * 3 if any(s.get("note") for s in steps) else 16)
    else:  # one column, top to bottom
        rh = 58
        for i, s in enumerate(steps):
            y = 14 + i * rh
            hl = s.get("highlight")
            body.append(dot(12, y, s, hl))
            body.append(text_el(34, y + 5, wrap(s["label"], 40, 1), 15, 700 if hl else 500, C["heading"], d=s))
            if s.get("note"):
                body.append(text_el(34, y + 24, wrap(s["note"], 80, 1), 13, 500, C["muted"], italic=True))
            if i < n - 1:
                body.append(arrow(12, y + 10, 12, y + rh - 10, C["ink"]))
        h = 14 + (n - 1) * rh + 34
    legend = f'<p class="legend"><span class="arrow">→</span> {esc(p["arrow"])}</p>'
    steps_text = (
        "<ol>"
        + "".join(
            f"<li{dattr(s)}>{esc(s['label'])}{(' — ' + esc(s['note'])) if s.get('note') else ''}</li>" for s in steps
        )
        + "</ol>"
    )
    return svg_wrap("".join(body), h, p["headline"]) + legend, steps_text


def t_flow(p, W, g):
    st = p["steps"]
    return flow_boxes(
        [s["label"] for s in st], [s.get("note") for s in st], [s.get("highlight") for s in st], W, g, p["arrow"]
    )


# ---------- groups: check, HTML, text ----------


def check_groups(p, where, errors, warnings, digest):
    groups = listed(p, "groups", where, warnings, LIMITS["groups"], "groups")
    count_highlights(groups, where, warnings)
    total = 0
    for g in groups:
        items = g.get("items") or []
        total += len(items)
        digest.append(
            f"    {g.get('label')}: {', '.join(map(str, items))}{'  [highlight]' if g.get('highlight') else ''}"
        )
    if total > LIMITS["group_items"]:
        warnings.append(f"{where}: {total} items in groups; more than {LIMITS['group_items']} nodes is hard to read")


def v_groups(p):
    """Categories as thin outlines, each item a small mark with its label."""
    groups = p["groups"]
    n = len(groups)
    gap = 24
    gw = (W - gap * (n - 1)) / n
    chars = max(int((gw - 50) / 7.6), 8)
    item_lines = [[wrap(str(it), chars, 2) for it in g.get("items") or []] for g in groups]
    gh = 52 + max(sum(10 + 18 * len(lines) for lines in col) for col in item_lines)
    body = []
    for i, g in enumerate(groups):
        x = i * (gw + gap)
        hl = g.get("highlight")
        body.append(
            f'<rect x="{x + 0.5:.1f}" y="0.5" width="{gw - 1:.1f}" height="{gh:.1f}" fill="none" stroke="{C["terracotta"] if hl else C["line"]}" stroke-width="{1.5 if hl else 1}"/>'
        )
        body.append(
            text_el(
                x + 16,
                26,
                wrap(str(g.get("label", "")).upper(), int(gw / 9.5), 1),
                12.5,
                700,
                C["heading"] if hl else C["muted"],
                d=g,
            )
        )
        y = 50
        for lines in item_lines[i]:
            body.append(dot(x + 20, y - 5, None, False))
            body.append(text_el(x + 34, y, lines, 14.5, 500, C["heading"], gap=18))
            y += 10 + 18 * len(lines)
    text = (
        "<ul>"
        + "".join(
            f"<li{dattr(g)}><b>{esc(g.get('label', ''))}</b>: {esc(', '.join(map(str, g.get('items') or [])))}</li>"
            for g in groups
        )
        + "</ul>"
    )
    return svg_wrap("".join(body), gh + 2, p["headline"]), text


def t_groups(p, W, g):
    out = []
    for grp in p["groups"]:
        out += tbox(
            [grp["label"].upper()] + [f"{g['pt']} {it}" for it in grp.get("items") or []],
            min(W, 48),
            g,
            grp.get("highlight"),
        )
    return out


# ---------- tree: check, HTML, text ----------


def check_tree(p, where, errors, warnings, digest):
    count = [0]
    hl = [0]

    def walk(n, depth):
        count[0] += 1
        hl[0] += 1 if n.get("highlight") else 0
        if depth > 3:
            errors.append(f"{where}: '{n['label']}' is deeper than 4 levels; cut the tree or split it")
            return
        kids = n.get("children") or []
        digest.append(
            "    "
            + "  " * depth
            + f"{n['label']}{(' = ' + num(n['value'])) if 'value' in n else ''}"
            + ("  [highlight]" if n.get("highlight") else "")
        )
        for k in kids:
            walk(k, depth + 1)

    walk(p["root"], 0)
    if count[0] > 30:
        warnings.append(f"{where}: {count[0]} nodes; more than about 30 cannot be labelled")
    if hl[0] > LIMITS["highlights"]:
        warnings.append(f"{where}: {hl[0]} highlighted nodes; emphasis works on one or two")


def v_tree(p):
    """An icicle: each level a column, each node's height proportional to its value."""
    root = p["root"]

    def val(n):
        if _is_num(n.get("value")):
            return n["value"]
        kids = n.get("children") or []
        return sum(val(k) for k in kids) if kids else 1

    def depth(n):
        return 1 + max([depth(k) for k in n.get("children") or []] or [0])

    D = depth(root)
    rootw = 130 if D > 1 else W  # the root carries no comparison, so give the levels below it the room
    cw = (W - rootw) / (D - 1) if D > 1 else W

    def colx(d):
        return 0 if d == 0 else rootw + (d - 1) * cw

    def colw(d):
        return rootw if d == 0 else cw

    H = 300
    body, rows, row_items = [], [], []
    unit = p.get("unit", "")

    def draw(n, d, y, h, path):
        hl = n.get("highlight")
        x, w = colx(d), colw(d)
        body.append(
            f'<rect x="{x + 1:.1f}" y="{y + 1:.1f}" width="{w - 2:.1f}" height="{max(h - 2, 0.5):.1f}" fill="none" stroke="{C["line"]}" stroke-width="1"{dattr(n)}/>'
            + (
                f'<rect x="{x + 1:.1f}" y="{y + 1:.1f}" width="4" height="{max(h - 2, 0.5):.1f}" fill="{C["terracotta"]}"/>'
                if hl
                else ""
            )
        )
        if h >= 22:
            lines = wrap(n["label"], int(w / 8), max(1, min(3, int((h - 6) / 17))))
            if _is_num(n.get("value")) and h >= 22 + 17 * len(lines):
                lines = lines + [num(n["value"]) + (f" {unit}" if unit else "")]
            body.append(text_el(x + 10, y + 19, lines, 13.5, 700 if hl else 500, C["heading"], gap=17, d=n))
        rows.append([" / ".join(path + [n["label"]]), num(val(n))])
        row_items.append(n)
        kids = n.get("children") or []
        tot = sum(val(k) for k in kids) or 1
        yy = y
        for k in kids:
            kh = h * val(k) / max(val(n), tot)
            draw(k, d + 1, yy, kh, path + [n["label"]])
            yy += kh

    draw(root, 0, 0, H, [])
    data = table_html(["Node", f"Value{f' ({unit})' if unit else ''}"], rows, num_cols={1}, items=row_items)
    return svg_wrap("".join(body), H + 4, p["headline"]), data


def t_tree(p, W, g):
    unit = p.get("unit", "")

    def val(n):
        if isinstance(n.get("value"), (int, float)):
            return n["value"]
        kids = n.get("children") or []
        return sum(val(k) for k in kids) if kids else None

    root = p["root"]
    total = val(root)
    out = []

    def walk(n, prefix, last, depth):
        v = val(n)
        share = f"{v / total * 100:.0f}%" if v is not None and total else ""
        bar = g["bar"] * max(1, round((v or 0) / (total or 1) * 20)) if v is not None and depth else ""
        mark = g["hl"] if n.get("highlight") else ""
        conn = "" if depth == 0 else (g["end"] if last else g["tee"]) + g["h"] + " "
        label = f"{prefix}{conn}{mark}{n['label']}"
        vtxt = (f"{tfmt(v)} {unit}".strip() + f"  {share}") if v is not None else ""
        out.append(f"{tcut(label, W - 32):<{W - 32}} {bar:<20} {vtxt}".rstrip())
        kids = n.get("children") or []
        for k, c in enumerate(kids):
            walk(c, prefix + ("" if depth == 0 else ("   " if last else g["v"] + "  ")), k == len(kids) - 1, depth + 1)

    walk(root, "", True, 0)
    return out


# ---------- sets: check, HTML, text ----------


def _region_order(sets, regions):
    return sorted(range(len(regions)), key=lambda k: [0 if s in regions[k]["in"] else 1 for s in sets])


def check_sets(p, where, errors, warnings, digest):
    listed(p, "sets", where, warnings, 6, "sets")
    regions = listed(p, "regions", where, warnings, 12, "regions")
    for r in regions:
        ins = r["in"]
        digest.append(
            f"    in {' & '.join(ins)}: {r.get('label', '')} {('(' + num(r['count']) + ')') if 'count' in r else ''}".rstrip()
            + ("  [highlight]" if r.get("highlight") else "")
        )
    count_highlights(regions, where, warnings)


def v_sets(p):
    """A linear diagram: one row per set, one column per region; a bar shows membership."""
    sets, regions = [str(s) for s in p["sets"]], p["regions"]
    order = _region_order(sets, regions)
    left = 170
    n = len(order)
    cw = (W - left) / n
    head_lines = max(len(wrap(regions[k].get("label", ""), int(cw / 7.2), 3)) for k in order)
    top = 18 + head_lines * 16 + 22
    rh = 34
    body = []
    for j, k in enumerate(order):
        r = regions[k]
        x = left + j * cw
        hl = r.get("highlight")
        lab = wrap(r.get("label", ""), int(cw / 7.2), 3)
        body.append(text_el(x + cw / 2, 20, lab, 12.5, 700 if hl else 500, C["heading"], "middle", gap=16, d=r))
        if "count" in r:
            body.append(
                text_el(
                    x + cw / 2,
                    20 + len(lab) * 16 + 4,
                    [num(r["count"])],
                    14,
                    700,
                    C["heading"] if hl else C["ink"],
                    "middle",
                )
            )
    for i, s in enumerate(sets):
        y = top + i * rh
        body.append(text_el(left - 14, y + rh / 2 + 5, wrap(s, 20, 1), 14, 600, C["heading"], "end"))
        body.append(
            f'<line x1="{left}" y1="{y + rh / 2:.1f}" x2="{W}" y2="{y + rh / 2:.1f}" stroke="{C["line"]}" stroke-width="1"/>'
        )
        if not any(s in r["in"] for r in regions):
            body.append(text_el(left + 12, y + rh / 2 + 5, ["none found"], 13, 600, C["ink"], italic=True))
        j = 0
        while j < n:  # merge adjacent columns into one bar
            if s in regions[order[j]]["in"]:
                start = j
                while j + 1 < n and s in regions[order[j + 1]]["in"]:
                    j += 1
                for jj in range(start, j + 1):
                    hl = regions[order[jj]].get("highlight")
                    body.append(
                        f'<rect x="{left + jj * cw + (3 if jj == start else 0):.1f}" y="{y + rh / 2 - 4:.1f}" width="{cw - (3 if jj == start else 0) - (3 if jj == j else 0):.1f}" height="8" fill="{C["terracotta"] if hl else C["muted"]}"/>'
                    )
            j += 1
    rows = [[r.get("label", ""), " & ".join(r["in"]), num(r["count"]) if "count" in r else ""] for r in regions]
    data = table_html(["Region", "In sets", "Count"], rows, num_cols={2}, items=regions)
    return svg_wrap("".join(body), top + len(sets) * rh + 8, p["headline"]), data


def t_sets(p, W, g):
    sets = [str(s) for s in p["sets"]]
    regions = p["regions"]
    order = _region_order(sets, regions)
    lw = min(max(len(s) for s in sets), 24)
    cw = max(3, min((W - lw - 2) // len(order), 8))
    out = [" " * (lw + 1) + "".join(f"{j + 1}".center(cw) for j in range(len(order)))]
    for s in sets:
        row = ""
        for k in order:
            on = s in regions[k]["in"]
            row += ((g["seg"] if not regions[k].get("highlight") else g["bar"]) * cw) if on else " " * cw
        out.append(f"{tcut(s, lw):>{lw}} {row}")
    out.append("")
    for j, k in enumerate(order):
        r = regions[k]
        cnt = f" ({tfmt(r['count'])})" if "count" in r else ""
        out += twrap(
            f"{j + 1}{'*' if r.get('highlight') else ''} {r.get('label', '')}{cnt}: in {' & '.join(r['in'])}", W
        )
    return out


# ---------- matrix: check, HTML, text ----------


def _mark(cell):
    """A matrix cell is a mark, or an object with a 'mark'."""
    return cell.get("mark") if isinstance(cell, dict) else cell


def _label(col):
    return col.get("label", "") if isinstance(col, dict) else str(col)


def mark_svg(mark, hl):
    """A cell mark whose shape carries the meaning, drawn in lines so it does not look like an evidence mark; colour
    only repeats it. The point of the slide is underlined in terracotta."""
    ring = f'<path d="M10 44h28" stroke="{C["terracotta"]}" stroke-width="3"/>' if hl else ""
    shapes = {
        "yes": f'<path d="M14 25l7 7 13-15" fill="none" stroke="{C["moss"]}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>',
        "no": f'<path d="M17 17l14 14M31 17l-14 14" stroke="{C["muted"]}" stroke-width="2.4" stroke-linecap="round"/>',
        "up": f'<path d="M24 14 L34 31 H14 Z" fill="{C["moss"]}"/>',
        "down": f'<path d="M24 34 L34 17 H14 Z" fill="{C["ink"]}"/>',
        "same": f'<path d="M15 20.5h18M15 27.5h18" stroke="{C["ink"]}" stroke-width="2.4" stroke-linecap="round"/>',
    }
    if mark is None:
        return f'<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M20 24h8" stroke="{C["line"]}" stroke-width="2" stroke-linecap="round"/>{ring}</svg>'
    return f'<svg viewBox="0 0 48 48" aria-hidden="true">{shapes[mark]}{ring}</svg>'


def check_matrix(p, where, errors, warnings, digest):
    cols = listed(p, "columns", where, warnings, LIMITS["matrix_cols"], "columns")
    rows = listed(p, "rows", where, warnings, LIMITS["matrix_rows"], "rows")
    n_hl = 0
    for r in rows:
        cells = r["cells"]
        out = []
        for c in cells:
            mark = _mark(c)
            n_hl += 1 if isinstance(c, dict) and c.get("highlight") else 0
            out.append(mark or "–")
        n_hl += 1 if r.get("highlight") else 0
        group = f"{r['group']} / " if r.get("group") else ""
        digest.append(
            f"    {group}{r['label']}: " + ", ".join(f"{_label(col)}={m}" for col, m in zip(cols, out, strict=False))
        )
    if n_hl > LIMITS["highlights"]:
        warnings.append(
            f"{where}: {n_hl} highlighted rows or cells; emphasis works when it marks the one or two that carry the point"
        )
    if len(cols) == 1:
        warnings.append(
            f"{where}: a matrix with one column is a list of marks; use 'pairs' if each item comes in a good and a bad form, or 'effects' for a list of findings"
        )
    measured = {}
    for r in rows:
        if isinstance(r.get("cells"), list):
            key = r.get("group") or r.get("label")
            measured.setdefault(key, set()).update(k for k, c in enumerate(r["cells"]) if _mark(c))
    keys = [k for k in measured if measured[k]]
    for a in range(len(keys)):
        for b in range(a + 1, len(keys)):
            if not measured[keys[a]] & measured[keys[b]]:
                warnings.append(
                    f"{where}: '{keys[a]}' and '{keys[b]}' share no measured column, so they measure different things; use 'effects', which names each row's outcome, or separate panels"
                )


def v_matrix(p):
    """Rows by columns of marks, so the pattern of where effects fall is seen at once."""
    cols = [c if isinstance(c, dict) else {"label": c} for c in p["columns"]]
    words = {**MARKS, **(p.get("legend") or {})}
    blank = p.get("blank", "not measured")
    n = len(cols)
    out = [
        f'<div class="matrix" style="--mcols:{n}" role="table" aria-label="{esc(p["headline"])}">',
        '<div class="mrow mhead" role="row"><span role="columnheader"></span>'
        + "".join(
            f'<span role="columnheader" class="{"hl" if c.get("highlight") else ""}">{esc(c["label"])}</span>'
            for c in cols
        )
        + "</div>",
    ]
    used, group, rows_text = [], None, []
    for r in p["rows"]:
        if r.get("group") and r["group"] != group:
            group = r["group"]
            out.append(f'<div class="mgroup" role="row"><span role="rowheader">{esc(group)}</span></div>')
        cells = []
        for c, col in zip(r["cells"], cols, strict=False):
            mark = _mark(c)
            hl = isinstance(c, dict) and c.get("highlight")
            word = words.get(mark, blank) if mark else blank
            if mark not in used:
                used.append(mark)
            text = c.get("text") if isinstance(c, dict) and c.get("text") else ""
            cells.append(
                f'<span role="cell" class="mcell{" hl" if hl else ""}" title="{esc(word)}">{mark_svg(mark, hl)}'
                f'<span class="sr">{esc(col["label"])}: {esc(word)}</span>'
                f"{f'<small>{esc(text)}</small>' if text else ''}</span>"
            )
        out.append(
            f'<div class="mrow{" hl" if r.get("highlight") else ""}" role="row"><span role="rowheader" class="mlab"{dattr(r)}>{esc(r["label"])}</span>{"".join(cells)}</div>'
        )
        rows_text.append(
            [(f"{r['group']}: " if r.get("group") else "") + r["label"]]
            + [words.get(_mark(c), blank) if _mark(c) else blank for c in r["cells"]]
        )
    out.append("</div>")
    legend = "".join(
        f"<span>{mark_svg(m, False)}{esc(words.get(m, blank) if m else blank)}</span>"
        for m in [m for m in MARKS if m in used] + ([None] if None in used else [])
    )
    out.append(f'<p class="mlegend">{legend}</p>')
    return "".join(out), table_html([""] + [c["label"] for c in cols], rows_text, items=p["rows"])


def t_matrix(p, W, g):
    cols = [c if isinstance(c, dict) else {"label": c} for c in p["columns"]]
    sym = {"yes": g["yes"], "no": g["no"], "up": g["up"], "down": g["dn"], "same": g["same"], None: g["blank"]}
    words = {**MARKS, **(p.get("legend") or {})}
    lw = min(max(len(r["label"]) for r in p["rows"]) + 2, int(W * 0.45))
    cw = max(6, min((W - lw) // len(cols), 16))
    heads = [twrap(c["label"], cw - 2) for c in cols]
    hn = max(len(h) for h in heads)
    out = [" " * lw + "".join((h[k] if k < len(h) else "").center(cw) for h in heads) for k in range(hn)]
    group = None
    used = []
    for r in p["rows"]:
        if r.get("group") and r["group"] != group:
            group = r["group"]
            out.append(tcut(group.upper(), W))
        cells = []
        for c in r["cells"]:
            m = _mark(c)
            used.append(m)
            s = sym[m]
            if isinstance(c, dict) and c.get("highlight"):
                s = f"[{s}]"
            cells.append(s.center(cw))
        mark = g["hl"] if r.get("highlight") else " "
        out.append(f"{mark}{tcut(r['label'], lw - 2):<{lw - 1}}" + "".join(cells))
    legend = [
        f"{sym[m]} {words.get(m, p.get('blank', 'not measured')) if m else p.get('blank', 'not measured')}"
        for m in ["yes", "no", "up", "down", "same", None]
        if m in used
    ]
    out += [""] + twrap("   ".join(legend), W)
    return out


def ev_circle(cx, cy, r, ev, fill, hl=False, item=None, evmode=False):
    """One item's mark on a kind that shows evidence. Its evidence sets the fill: strong filled ink, moderate half
    filled, weak hollow. On a slide that shows evidence, an item without it gets a small muted dot ("no evidence
    given"). On a slide that shows none, the mark takes the kind's own fill. The point of the slide is terracotta: a
    ring around an evidence mark or the small dot, or a terracotta fill when the slide shows no evidence."""
    tag = dattr(item)
    ring = f' stroke="{C["terracotta"]}" stroke-width="2.5"' if hl else f' stroke="{C["ink"]}" stroke-width="1.5"'
    if ev == "strong":
        return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{C["ink"]}"{ring}{tag}/>'
    if ev == "moderate":
        return (
            f'<g{tag}><circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{C["cream"]}"{ring}/>'
            f'<path d="M{cx:.1f} {cy - r:.1f}A{r:.1f} {r:.1f} 0 0 0 {cx:.1f} {cy + r:.1f}Z" fill="{C["ink"]}"/></g>'
        )
    if ev == "weak":
        return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{C["cream"]}"{ring}{tag}/>'
    if evmode:
        point = (
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="none" stroke="{C["terracotta"]}" stroke-width="2.5"/>'
            if hl
            else ""
        )
        return (
            f'<g{tag}><circle cx="{cx:.1f}" cy="{cy:.1f}" r="{max(r * 0.5, 2.5):.1f}" fill="{C["muted"]}"/>{point}</g>'
        )
    if hl:
        return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{C["terracotta"]}"{tag}/>'
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r * (0.6 if fill == C["muted"] and r > 6 else 1):.1f}" fill="{fill}"{tag}/>'


def marked_items(p):
    """The items of a kind that draws one mark per item and can show evidence on it."""
    key = {"dots": "groups", "effects": "rows", "fork": "branches", "lanes": "steps"}.get(p.get("kind"))
    return [it for it in p.get(key) or [] if isinstance(it, dict)] if key else []


def evidence_used(p):
    """The entries of a panel's key: each evidence strength drawn, "none" when some marks have no evidence, and
    "point" when a mark is the point of the slide. Empty when the panel shows no evidence."""
    items = marked_items(p)
    used = {ev_of(it) for it in items} & set(EVIDENCE_WORDS)
    if not used:
        return set()
    if any(ev_of(it) is None for it in items):
        used.add("none")
    if any(it.get("highlight") for it in items):
        used.add("point")
    return used


KEY_WORDS = {**EVIDENCE_WORDS, "none": "no evidence given", "point": "the slide's point"}


def evidence_key(used):
    """The key for the marks, in a fixed order, drawn once per slide: every fill and ring the marks use."""
    icon = {ev: ev_circle(8, 8, 5.5, ev, C["sand"]) for ev in EVIDENCE_WORDS}
    icon["none"] = ev_circle(8, 8, 5.5, None, C["sand"], evmode=True)
    icon["point"] = ev_circle(8, 8, 5.5, None, C["sand"], hl=True, evmode=True)
    return "".join(
        f'<span><svg viewBox="0 0 16 16" aria-hidden="true">{icon[k]}</svg>{KEY_WORDS[k]}</span>'
        for k in KEY_WORDS
        if k in used
    )


# ---------- effects and pairs: shared mark ----------

EFFECTS = ("up", "down", "same")
EFFECT_WORDS = {"up": "raises", "down": "lowers", "same": "no clear effect"}


def mark_shape(cx, cy, m, ev=None, item=None, evmode=False, hl=False):
    """See _mark_shape; the point of the slide also gets a terracotta ring, as in the key."""
    mark = _mark_shape(cx, cy, m, ev, item, evmode)
    if not hl or (m == "same" and (ev or evmode)):
        return mark if not hl else ev_circle(cx, cy, 6, ev, C["sand"], True, item, evmode)
    return (
        mark + f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="12" fill="none" stroke="{C["terracotta"]}" stroke-width="2"/>'
    )


def _mark_shape(cx, cy, m, ev=None, item=None, evmode=False):
    """An effect mark: the shape carries the effect (▲ raises, ▼ lowers, = no clear effect), colour only repeats it.
    On a slide that shows evidence, the fill shows its strength instead, and an item without evidence is muted."""
    tag = dattr(item)
    if m == "same":
        if ev or evmode:
            return ev_circle(cx, cy, 6, ev, C["sand"], False, item, evmode)
        return f'<path d="M{cx - 6:.1f} {cy - 3:.1f}h12M{cx - 6:.1f} {cy + 3:.1f}h12" stroke="{C["ink"]}" stroke-width="1.8"{tag}/>'
    tip, base = (cy - 8, cy + 6) if m == "up" else (cy + 8, cy - 6)
    d = f"M{cx:.1f} {tip:.1f} L{cx + 8:.1f} {base:.1f} H{cx - 8:.1f} Z"
    if ev is None:
        fill = C["muted"] if evmode else (C["moss"] if m == "up" else C["ink"])
        return f'<path d="{d}" fill="{fill}"{tag}/>'
    outline = (
        f'<path d="{d}" fill="{C["ink"] if ev == "strong" else C["cream"]}" stroke="{C["ink"]}" stroke-width="1.3"/>'
    )
    half = f'<path d="M{cx:.1f} {tip:.1f} V{base:.1f} H{cx - 8:.1f} Z" fill="{C["ink"]}"/>' if ev == "moderate" else ""
    return f"<g{tag}>{outline}{half}</g>"


def effect_legend(used, g=None):
    marks = {"up": "▲", "down": "▼", "same": "="} if g is None else {"up": g["up"], "down": g["dn"], "same": g["same"]}
    return "   ".join(f"{marks[m]} {EFFECT_WORDS[m]}" for m in EFFECTS if m in used)


# ---------- effects: check, HTML, text ----------


def check_effects(p, where, errors, warnings, digest):
    rows = listed(p, "rows", where, warnings, 12, "findings")
    count_highlights(rows, where, warnings)
    for r in rows:
        g = f"{r['group']} / " if r.get("group") else ""
        digest.append(
            f"    {g}{r['label']}{(' on ' + r['outcome']) if r.get('outcome') else ''}: {EFFECT_WORDS[r['effect']]}"
            + ("  [highlight]" if r.get("highlight") else "")
        )
    if not any(r.get("outcome") for r in rows):
        warnings.append(
            f"{where}: no row names its 'outcome'; when every finding has the same outcome and each item comes in a good and a bad form, use 'pairs'"
        )


def v_effects(p):
    """One row per finding, its mark placed in a lowers / no clear effect / raises column; each row names its outcome."""
    rows = p["rows"]
    heads = p.get("columns") or ["Lowers", "No clear effect", "Raises"]
    left = 360
    zw = (W - left) / 3
    zone = {"down": 0, "same": 1, "up": 2}
    evm = bool(evidence_used(p))
    body = [
        f'<line x1="{left + zw * k:.1f}" y1="30" x2="{left + zw * k:.1f}" y2="__H__" stroke="{C["line"]}" stroke-width="1"/>'
        for k in (1, 2)
    ]
    for k, h in enumerate(heads):
        body.append(text_el(left + zw * k + zw / 2, 20, [h.upper()], 12, 700, C["muted"], "middle"))
    y, group = 40, None
    for r in rows:
        if r.get("group") and r["group"] != group:
            group = r["group"]
            y += 22
            body.append(text_el(0, y, [group.upper()], 12.5, 700, C["heading"]))
            y += 8
        hl = r.get("highlight")
        lab = wrap(r["label"], 40, 2)
        out = wrap("on " + r["outcome"], 46, 2) if r.get("outcome") else []
        rh = 14 + 19 * len(lab) + 16 * len(out)
        body.append(text_el(0, y + 18, lab, 16, 700 if hl else 600, C["heading"], gap=19, d=r))
        if out:
            body.append(text_el(0, y + 18 + 19 * len(lab) - 2, out, 13, 500, C["muted"], italic=True, gap=16))
        body.append(
            mark_shape(
                left + zw * zone[r["effect"]] + zw / 2, y + rh / 2, r["effect"], ev_of(r), r, evm, r.get("highlight")
            )
        )
        body.append(f'<line x1="0" y1="{y + rh:.1f}" x2="{W}" y2="{y + rh:.1f}" stroke="{C["line"]}"/>')
        y += rh
    H = y + 8
    text = (
        "<ul>"
        + "".join(
            f"<li{dattr(r)}>{esc(r.get('group', ''))}{': ' if r.get('group') else ''}{esc(r['label'])}"
            f"{(' on ' + esc(r['outcome'])) if r.get('outcome') else ''}: {EFFECT_WORDS[r['effect']]}</li>"
            for r in rows
        )
        + "</ul>"
    )
    return svg_wrap("".join(body).replace("__H__", f"{H:.0f}"), H, p["headline"]), text


def t_effects(p, W, g):
    heads = p.get("columns") or ["Lowers", "No clear effect", "Raises"]
    sym = {"up": g["up"], "down": g["dn"], "same": g["same"]}
    zone = {"down": 0, "same": 1, "up": 2}
    cw = 10
    lw = max(W - 3 * cw - 2, 20)
    hl = [twrap(h, cw - 1) for h in heads]
    out = [
        " " * (lw + 1) + "".join((h[k] if k < len(h) else "").center(cw) for h in hl) for k in range(max(map(len, hl)))
    ]
    group = None
    for r in p["rows"]:
        if r.get("group") and r["group"] != group:
            group = r["group"]
            out.append(tcut(group.upper(), W))
        label = r["label"] + (f" (on {r['outcome']})" if r.get("outcome") else "")
        lines = twrap(label, lw - 2)
        cells = ["".center(cw)] * 3
        cells[zone[r["effect"]]] = sym[r["effect"]].center(cw)
        mark = g["hl"] if r.get("highlight") else " "
        out.append(f"{mark}{lines[0]:<{lw}}" + "".join(cells))
        out += [f" {line}" for line in lines[1:]]
    return out + ["", effect_legend({r["effect"] for r in p["rows"]}, g)]


# ---------- pairs: check, HTML, text ----------


def check_pairs(p, where, errors, warnings, digest):
    heads = p["columns"]
    digest.append(f"    columns: {heads[0]} | {heads[1]}")
    rows = listed(p, "rows", where, warnings, 7, "items")
    count_highlights(rows, where, warnings)
    for r in rows:
        digest.append(
            f"    {r['label']}: "
            + " | ".join(
                ", ".join(
                    f"{c['label']}{(' [' + EFFECT_WORDS.get(c.get('effect'), '') + ']') if c.get('effect') else ''}"
                    for c in r.get(side) or []
                )
                or "–"
                for side in ("left", "right")
            )
        )


def v_pairs(p):
    """One row per item, its two contrasting forms side by side."""
    heads = p["columns"]
    left = 240
    cw = (W - left) / 2
    body = [
        text_el(left + 40, 20, [heads[0].upper()], 12, 700, C["muted"]),
        text_el(left + cw + 40, 20, [heads[1].upper()], 12, 700, C["muted"]),
        f'<line x1="0" y1="32" x2="{W}" y2="32" stroke="{C["line"]}" stroke-width="2"/>',
    ]
    y = 40
    for r in p["rows"]:
        hl = r.get("highlight")
        sides = [r.get("left") or [], r.get("right") or []]
        lines = [[wrap(c["label"], int((cw - 50) / 8), 2) for c in s] for s in sides]
        heights = [sum(10 + 19 * len(cell) for cell in s) for s in lines]
        lab = wrap(r["label"], 24, 3)
        rh = max(heights + [19 * len(lab)]) + 16
        body.append(text_el(0, y + 26, lab, 16, 700, C["heading"], gap=19, d=r))
        for k, (s, ls) in enumerate(zip(sides, lines, strict=False)):
            yy = y + 8
            x = left + cw * k
            for c, cell_lines in zip(s, ls, strict=False):
                h = 10 + 19 * len(cell_lines)
                if c.get("effect"):
                    body.append(mark_shape(x + 16, yy + h / 2, c["effect"], None, c))
                body.append(text_el(x + 40, yy + 18, cell_lines, 15, 600 if hl else 500, C["ink"], gap=19, d=c))
                yy += h
        body.append(f'<line x1="0" y1="{y + rh:.1f}" x2="{W}" y2="{y + rh:.1f}" stroke="{C["line"]}"/>')
        y += rh
    text = table_html(
        ["", heads[0], heads[1]],
        [
            [r["label"]]
            + [
                "; ".join(
                    c["label"] + (f" ({EFFECT_WORDS[c['effect']]})" if c.get("effect") else "") for c in r.get(s) or []
                )
                or "–"
                for s in ("left", "right")
            ]
            for r in p["rows"]
        ],
        items=p["rows"],
    )
    return svg_wrap("".join(body), y + 6, p["headline"]), text


def t_pairs(p, W, g):
    heads = p["columns"]
    sym = {"up": g["up"], "down": g["dn"], "same": g["same"], None: " "}
    lw = 18
    cw = (W - lw - 2) // 2
    ha, hb = twrap(heads[0].upper(), cw - 2), twrap(heads[1].upper(), cw - 2)
    out = [
        " " * lw + "  " + (ha[k] if k < len(ha) else "").ljust(cw) + (hb[k] if k < len(hb) else "")
        for k in range(max(len(ha), len(hb)))
    ]
    out = [line.rstrip() for line in out] + [g["h"] * W]
    used = set()
    for r in p["rows"]:
        cols = []
        for s in (r.get("left") or [], r.get("right") or []):
            lines = []
            for c in s:
                used.add(c.get("effect"))
                w = twrap(c["label"], cw - 4)
                lines.append(f"{sym[c.get('effect')]} {w[0]}")
                lines += [f"  {line}" for line in w[1:]]
            cols.append(lines or ["–"])
        lab = twrap(r["label"], lw - 1)
        n = max(len(cols[0]), len(cols[1]), len(lab))
        for k in range(n):
            a = lab[k] if k < len(lab) else ""
            b = cols[0][k] if k < len(cols[0]) else ""
            c = cols[1][k] if k < len(cols[1]) else ""
            out.append(f"{(g['hl'] if r.get('highlight') and k == 0 else ' ')}{a:<{lw - 1}}  {b:<{cw}}{c}".rstrip())
        out.append("")
    return out + [effect_legend(used, g)]


# ---------- quadrant: check, HTML, text ----------


def check_quadrant(p, where, errors, warnings, digest):
    items = listed(p, "items", where, warnings, 10, "items")
    count_highlights(items, where, warnings)
    for it in items:
        digest.append(
            f"    {it.get('label')}: x={it['x']}, y={it['y']}{'  [highlight]' if it.get('highlight') else ''}"
        )
    digest.append(f"    basis: {p['basis']}")


def v_quadrant(p):
    """Items placed on two judged dimensions, with the four regions named."""
    left, top, pw, ph = 40, 30, W - 80, 290

    def X(v):
        return left + v * pw

    def Y(v):
        return top + ph - v * ph

    body = [
        f'<line x1="{left + pw / 2}" y1="{top}" x2="{left + pw / 2}" y2="{top + ph}" stroke="{C["line"]}" stroke-width="1"/>',
        f'<line x1="{left}" y1="{top + ph / 2}" x2="{left + pw}" y2="{top + ph / 2}" stroke="{C["line"]}" stroke-width="1"/>',
    ]
    q = p.get("quadrants") or {}
    corners = {
        "top_left": (left + 12, top + 24, "start"),
        "top_right": (left + pw - 12, top + 24, "end"),
        "bottom_left": (left + 12, top + ph - 12, "start"),
        "bottom_right": (left + pw - 12, top + ph - 12, "end"),
    }
    for k, (x, y, a) in corners.items():
        if q.get(k):
            body.append(text_el(x, y, [q[k].upper()], 12.5, 700, C["muted"], a))
    xa, ya = p["x"], p["y"]
    body.append(text_el(left, top + ph + 22, [f"← {xa['low']}"], 13, 500, C["muted"]))
    body.append(text_el(left + pw, top + ph + 22, [f"{xa['high']} →"], 13, 500, C["muted"], "end"))
    body.append(text_el(left + pw / 2, top + ph + 22, [xa["label"]], 13, 700, C["ink"], "middle"))
    body.append(
        f'<text x="{left - 14}" y="{top + ph / 2}" font-family="{SANS}" font-size="13" font-weight="700" fill="{C["ink"]}" text-anchor="middle" transform="rotate(-90 {left - 14} {top + ph / 2})">{esc(ya["label"])}</text>'
    )
    body.append(text_el(left - 6, top - 10, [f"↑ {ya['high']}"], 13, 500, C["muted"]))
    body.append(text_el(left - 6, top + ph + 40, [f"↓ {ya['low']}"], 13, 500, C["muted"]))
    placed = []
    for it in sorted(p["items"], key=lambda i: bool(i.get("highlight"))):
        hl = it.get("highlight")
        cx, cy = X(it["x"]), Y(it["y"])
        body.append(dot(cx, cy, it, hl))
        anchor = "end" if cx > left + pw * 0.72 else "start"
        ty = cy + 5
        for px, py in placed:  # nudge labels that would sit on top of each other
            if abs(px - cx) < 160 and abs(py - ty) < 18:
                ty = py + 18
        placed.append((cx, ty))
        body.append(
            text_el(
                cx + (-13 if anchor == "end" else 13),
                ty,
                wrap(it["label"], LIMITS["quadrant_label"], 1),
                14,
                700 if hl else 500,
                C["heading"],
                anchor,
                d=it,
            )
        )
    rows = [[it["label"], f"{it['x']:.2f}", f"{it['y']:.2f}"] for it in p["items"]]
    data = f"<p>{esc(p['basis'])}</p>" + table_html(
        ["Item", xa["label"] + " (0–1)", ya["label"] + " (0–1)"], rows, num_cols={1, 2}, items=p["items"]
    )
    return svg_wrap("".join(body), top + ph + 50, p["headline"]), data


def t_quadrant(p, W, g):
    xa, ya, q = p["x"], p["y"], p.get("quadrants") or {}
    cells = {"top_left": [], "top_right": [], "bottom_left": [], "bottom_right": []}
    for it in p["items"]:
        key = ("top" if it["y"] >= 0.5 else "bottom") + "_" + ("right" if it["x"] >= 0.5 else "left")
        cells[key].append(f"{g['hl'] if it.get('highlight') else g['pt']} {it['label']}")
    half = (min(W, 72) - 3) // 2

    def quad(key):
        return [tcut((q.get(key) or "").upper(), half - 2)] + [tcut(c, half - 2) for c in cells[key]]

    out = [f"{g['up']} {ya['label']}: {ya['high']}"]
    for a, b in (("top_left", "top_right"), ("bottom_left", "bottom_right")):
        L, R = quad(a), quad(b)
        h = max(len(L), len(R), 3)
        L += [""] * (h - len(L))
        R += [""] * (h - len(R))
        for left_text, r in zip(L, R, strict=False):
            out.append(f" {left_text:<{half}}{g['v']} {r}")
        if a == "top_left":
            out.append(" " + g["h"] * half + g["cross"] + g["h"] * half)
    out.append(f"{g['dn']} {ya['low']}")
    out.append(f"{xa['label']}: {xa['low']} (left) {g['arrow']} {xa['high']} (right)")
    out += twrap(f"Positions: {p['basis']}", W)
    return out


# ---------- numbers: check, HTML, text ----------


def check_numbers(p, where, errors, warnings, digest):
    for it in listed(p, "figures", where, warnings, LIMITS["numbers"], "figures"):
        digest.append(f"    {it['value']} — {it['label']}")


def v_numbers(p):
    cells = "".join(
        f'<div class="fig{" hl" if it.get("highlight") else ""}"><div class="val">{esc(it["value"])}</div>'
        f'<div class="lab"{dattr(it)}>{esc(it["label"])}</div></div>'
        for it in p["figures"]
    )
    return f'<div class="figures">{cells}</div>', ""


def t_numbers(p, W, g):
    out = []
    for f in p["figures"]:
        mark = g["hl"] + " " if f.get("highlight") else "  "
        out.append(f"{mark}{f['value']}")
        out += twrap(f["label"], W - 4, "    ")
    return out


# ---------- units: check, HTML, text ----------


def check_units(p, where, errors, warnings, digest):
    parts = listed(p, "parts", where, warnings, LIMITS["unit_parts"], "parts")
    count_highlights(parts, where, warnings)
    total = 0
    for it in parts:
        n = it["count"]
        total += n
        digest.append(f"    {n} {it['label']}{'  [highlight]' if it.get('highlight') else ''}")
    if total > LIMITS["units"]:
        errors.append(
            f"{where}: {total} units; above {LIMITS['units']} the marks cannot be counted, so use 'bars' or 'numbers'"
        )
    if not p.get("unit"):
        warnings.append(f"{where}: no 'unit'; say what one mark counts, such as 'questions'")
    digest.append(f"    total: {total} {p.get('unit', '')}".rstrip())


def v_units(p):
    """One mark per counted thing, so a count out of a total is seen as a proportion."""
    parts, unit = p["parts"], p.get("unit", "")
    total = sum(it["count"] for it in parts)
    cols = total if total <= 20 else (10 if total <= 50 else 20)
    nrows = math.ceil(total / cols)
    gap = 10 if cols <= 20 else 6
    size = min(26, (W - gap * (cols - 1)) / cols)
    # Fill and shape both mark the part, so colour is not the only signal: highlighted parts are solid
    # terracotta, the others solid moss, then outlined.
    styles, plain = [], [("muted", None), (None, "muted"), ("linen", "sand")]
    for it in parts:
        styles.append(("terracotta", None) if it.get("highlight") else plain.pop(0) if plain else ("linen", "sand"))
    body, k, spans = [], 0, []
    for it, (fill, stroke) in zip(parts, styles, strict=False):
        start = k
        for _ in range(it["count"]):
            r, c = divmod(k, cols)
            x, y = c * (size + gap), r * (size + gap)
            attrs = f'fill="{C[fill]}"' if fill else 'fill="none"'
            if stroke:
                attrs += f' stroke="{C[stroke]}" stroke-width="2"'
            inset = 1 if stroke else 0
            body.append(
                f'<rect x="{x + inset:.1f}" y="{y + inset:.1f}" width="{size - 2 * inset:.1f}" height="{size - 2 * inset:.1f}" rx="3" {attrs}{dattr(it)}/>'
            )
            k += 1
        spans.append((start, k - 1, it))
    h = nrows * (size + gap) - gap
    if nrows == 1:  # label each part under its own marks
        y = h + 18
        for a, b, it in spans:
            x1, x2 = a * (size + gap), b * (size + gap) + size
            body.append(
                f'<path d="M{x1 + 1:.1f} {y - 8} V{y} H{x2 - 1:.1f} V{y - 8}" fill="none" stroke="{C["ink"]}" stroke-width="1.25"/>'
            )
            hl = it.get("highlight")
            mid = (x1 + x2) / 2
            lines = wrap(f"{it['count']} {it['label']}", max(int((x2 - x1) / 8.5), 10), 3)
            half = max(len(line) for line in lines) * 4.6
            mid = min(max(mid, half), W - half)
            body.append(text_el(mid, y + 24, lines, 17, 700 if hl else 500, C["heading"], "middle", gap=21, d=it))
        h = (
            y
            + 24
            + 21
            * max(
                len(wrap(f"{it['count']} {it['label']}", max(int(((b - a + 1) * (size + gap) - gap) / 8.5), 10), 3))
                for a, b, it in spans
            )
        )
    else:  # a legend below the grid
        y = h + 28
        for (fill, stroke), it in zip(styles, parts, strict=False):
            attrs = (f'fill="{C[fill]}"' if fill else 'fill="none"') + (
                f' stroke="{C[stroke]}" stroke-width="2"' if stroke else ""
            )
            body.append(f'<rect x="1" y="{y - 15}" width="18" height="18" rx="2" {attrs}/>')
            body.append(
                text_el(
                    30, y, [f"{it['count']} {it['label']}"], 17, 700 if it.get("highlight") else 500, C["heading"], d=it
                )
            )
            y += 28
        h = y - 10
    if unit:
        body.append(text_el(W, h + 26, [f"Each mark is one of {total} {unit}"], 14, 500, C["muted"], "end"))
        h += 34
    data = table_html(
        ["Part", f"Count{f' ({unit})' if unit else ''}"],
        [[it["label"], it["count"]] for it in parts] + [["Total", total]],
        num_cols={1},
        items=parts,
    )
    return svg_wrap("".join(body), h + 4, p["headline"]), data


def t_units(p, W, g):
    marks = []
    plain = [g["box2"], g["box3"]]
    for it in p["parts"]:
        marks.append(g["box"] if it.get("highlight") else (plain.pop(0) if plain else g["box3"]))
    total = sum(it["count"] for it in p["parts"])
    per_row = 20 if total > 20 else total
    cells = "".join(m * it["count"] for m, it in zip(marks, p["parts"], strict=False))
    out = [" ".join(cells[i : i + per_row]) for i in range(0, len(cells), per_row)]
    out.append("")
    for m, it in zip(marks, p["parts"], strict=False):
        out += twrap(f"{m} {it['count']} {it['label']}", W)
    if p.get("unit"):
        out.append(f"Each mark is one of {total} {p['unit']}.")
    return out


# ---------- bars: check, HTML, text ----------


def check_bars(p, where, errors, warnings, digest):
    items = listed(p, "items", where, warnings, LIMITS["bars"], "bars")
    count_highlights(items, where, warnings)
    unit = p.get("unit", "")
    for it in items:
        v = it["value"]
        digest.append(
            f"    {it.get('label')}: {num(v)}{(' ' + unit) if unit else ''}{'  [highlight]' if it.get('highlight') else ''}"
        )
    if not unit:
        warnings.append(f"{where}: no 'unit'; say what the values measure")


def v_bars(p):
    """Horizontal bars from a zero baseline, drawn in HTML so they reflow on narrow screens."""
    items = list(p["items"])
    if p.get("sort") == "desc":
        items.sort(key=lambda it: -it["value"])
    elif p.get("sort") == "asc":
        items.sort(key=lambda it: it["value"])
    unit = p.get("unit", "")
    vmax = max([it["value"] for it in items] + [p.get("max", 0)]) or 1
    rows = []
    for it in items:
        hl = " hl" if it.get("highlight") else ""
        pct = max(it["value"] / vmax * 100, 0.4)
        rows.append(
            f'<div class="brow{hl}"><div class="blab"{dattr(it)}>{esc(it["label"])}</div>'
            f'<div class="btrack"><div class="bar" style="width:{pct:.2f}%"{dattr(it)}></div>'
            f'<span class="bval" style="left:calc({pct:.2f}% + 10px)">{esc(num(it["value"]))}{f" <small>{esc(unit)}</small>" if unit else ""}</span></div></div>'
        )
    # The value column's width: with a set 'max', from it too, so two panels that share a scale share the frame.
    valw = max(len(num(v)) for v in [it["value"] for it in items] + ([p["max"]] if "max" in p else [])) * 0.85
    valw += len(unit) * 0.5 + 1.2
    chart = f'<div class="bars" style="--valw:{valw:.1f}em" role="group" aria-label="{esc(p["headline"])}">{"".join(rows)}</div>'
    data = table_html(
        ["Item", f"Value{f' ({unit})' if unit else ''}"],
        [[it["label"], num(it["value"])] for it in items],
        num_cols={1},
        items=items,
    )
    return chart, data


def t_bars(p, W, g):
    items = list(p["items"])
    if p.get("sort") == "desc":
        items.sort(key=lambda it: -it["value"])
    elif p.get("sort") == "asc":
        items.sort(key=lambda it: it["value"])
    unit = p.get("unit", "")
    vmax = max([it["value"] for it in items] + [p.get("max", 0)]) or 1
    lw = min(max(len(it["label"]) for it in items), int(W * 0.45))
    vw = max(len(tfmt(it["value"])) for it in items)
    room = W - lw - vw - 6
    out = []
    stacked = max(len(it["label"]) for it in items) > lw  # long labels go on their own line above the bar
    if stacked:
        room = W - vw - 4
    for it in items:
        n = round(it["value"] / vmax * room)
        mark = g["hl"] if it.get("highlight") else " "
        if stacked:
            out.append(f"{mark}{it['label']}")
            out.append(f" {g['bar'] * n}{' ' * (room - n)} {tfmt(it['value']):>{vw}}")
        else:
            out.append(
                f"{mark}{tcut(it['label'], lw):>{lw}} {g['bar'] * n}{' ' * (room - n)} {tfmt(it['value']):>{vw}}"
            )
    if stacked:
        lw = -1
    if unit:
        out.append(f"{'':>{lw + 1}} Unit: {unit}. Bars start at zero.")
    return out


# ---------- slope: check, HTML, text ----------


def check_slope(p, where, errors, warnings, digest):
    items = listed(p, "items", where, warnings, 10, "lines")
    count_highlights(items, where, warnings)
    unit = p.get("unit", "")
    for it in items:
        digest.append(
            f"    {it.get('label')}: {num(it['before'])} → {num(it['after'])} {unit}".rstrip()
            + ("  [highlight]" if it.get("highlight") else "")
        )
    if not unit:
        warnings.append(f"{where}: no 'unit'; say what the values measure")


def v_slope(p):
    """Each item's change between two states, one line per item."""
    items = sorted(p["items"], key=lambda it: bool(it.get("highlight")))
    unit = p.get("unit", "")
    vals = [v for it in items for v in (it["before"], it["after"])]
    lo, hi = p.get("_range") or (axis_start(p, "y", vals), max(vals))
    top, ph = 44, 300
    x1, x2 = 250, W - 250

    def Y(v):
        return top + ph - (v - lo) / ((hi - lo) or 1) * ph

    body = [
        text_el(x1, 18, [str(p["from"])], 14, 700, C["muted"], "middle"),
        text_el(x2, 18, [str(p["to"])], 14, 700, C["muted"], "middle"),
        f'<line x1="{x1}" y1="{top - 10}" x2="{x1}" y2="{top + ph + 8}" stroke="{C["line"]}" stroke-width="1.5"/>',
        f'<line x1="{x2}" y1="{top - 10}" x2="{x2}" y2="{top + ph + 8}" stroke="{C["line"]}" stroke-width="1.5"/>',
    ]

    def spread(ys):  # keep labels on one side from overlapping
        order = sorted(range(len(ys)), key=lambda k: ys[k])
        out = list(ys)
        for a, b in zip(order, order[1:], strict=False):
            out[b] = max(out[b], out[a] + 20)
        return out

    ly = spread([Y(it["before"]) for it in items])
    ry = spread([Y(it["after"]) for it in items])
    for k, it in enumerate(items):
        hl = it.get("highlight") or len(items) == 1
        color = C["terracotta"] if hl else C["muted"]
        body.append(
            f'<line x1="{x1}" y1="{Y(it["before"]):.1f}" x2="{x2}" y2="{Y(it["after"]):.1f}" stroke="{color}" stroke-width="{3 if hl else 1.75}"/>'
        )
        for x, v in ((x1, it["before"]), (x2, it["after"])):
            body.append(f'<circle cx="{x}" cy="{Y(v):.1f}" r="{5 if hl else 4}" fill="{color}"{dattr(it)}/>')
        weight, fill = (700, C["heading"]) if hl else (500, C["ink"])
        body.append(
            text_el(
                x1 - 12,
                ly[k] + 5,
                [f"{wrap(it['label'], LIMITS['slope_label'], 1)[0]}  {num(it['before'])}"],
                14,
                weight,
                fill,
                "end",
                d=it,
            )
        )
        body.append(
            text_el(
                x2 + 12,
                ry[k] + 5,
                [f"{num(it['after'])}  {wrap(it['label'], LIMITS['slope_label'], 1)[0]}"],
                14,
                weight,
                fill,
                d=it,
            )
        )
    h = max([top + ph + 16] + [y + 12 for y in ly + ry])
    if unit:
        body.append(text_el(W / 2, 18, [unit], 13, 500, C["muted"], "middle"))
    if p.get("y_note"):
        body.append(text_el(W / 2, h + 14, [p["y_note"]], 13, 600, C["ink"], "middle"))
        h += 24
    data = table_html(
        ["Item", f"{p['from']}", f"{p['to']}"],
        [[it["label"], num(it["before"]), num(it["after"])] for it in p["items"]],
        num_cols={1, 2},
        items=p["items"],
    )
    return svg_wrap("".join(body), h + 4, p["headline"]), data


def t_slope(p, W, g):
    items = p["items"]
    unit = p.get("unit", "")
    lw = min(max(len(it["label"]) for it in items), int(W * 0.4))
    out = [f"{'':<{lw + 1}} {p['from']:>8}    {p['to']:<8}  change"]
    for it in sorted(items, key=lambda it: -(it["after"] - it["before"])):
        d = it["after"] - it["before"]
        sign = g["up"] if d > 0 else (g["dn"] if d < 0 else g["same"])
        mark = g["hl"] if it.get("highlight") else " "
        out.append(
            f"{mark}{tcut(it['label'], lw):<{lw}} {tfmt(it['before']):>8} {g['arrow']}  {tfmt(it['after']):<8}  {sign} {'+' if d > 0 else ''}{tfmt(d)}"
        )
    if unit:
        out.append(f"Values in {unit}.")
    return out


# ---------- dots: check, HTML, text ----------


def check_dots(p, where, errors, warnings, digest):
    groups = listed(p, "groups", where, warnings, 6, "groups")
    count_highlights(groups, where, warnings)
    for g in groups:
        vals = g["values"]
        s = sorted(vals)
        med = s[len(s) // 2] if len(s) % 2 else (s[len(s) // 2 - 1] + s[len(s) // 2]) / 2
        digest.append(
            f"    {g.get('label')}: n={len(vals)}, min {num(s[0])}, median {num(med)}, max {num(s[-1])}"
            + ("  [highlight]" if g.get("highlight") else "")
        )
    if not p.get("unit"):
        warnings.append(f"{where}: no 'unit'; say what the values measure")


def v_dots(p):
    """Every value as a dot, stacked where values are close, so the spread is visible."""
    groups, unit = p["groups"], p.get("unit", "")
    allv = [v for g in groups for v in g["values"]]
    ticks = nice_ticks(*(p.get("_range") or (axis_start(p, "x", allv), max(allv))), 5)
    lo, hi = ticks[0], ticks[-1]
    left, right = 170, 20
    pw = W - left - right

    def X(v):
        return left + (v - lo) / ((hi - lo) or 1) * pw

    nbins = 50
    bw = pw / nbins
    r = min(bw / 2 - 0.5, 6)
    stacks = []
    for g in groups:
        bins = {}
        for v in sorted(g["values"]):
            b = min(int((v - lo) / ((hi - lo) or 1) * nbins), nbins - 1)
            bins.setdefault(b, []).append(v)
        stacks.append(bins)
    tallest = max(max(len(v) for v in b.values()) for b in stacks)
    rh = max(60, tallest * 2 * r + 30)
    body, y = [], 10
    for g, bins in zip(groups, stacks, strict=False):
        hl = g.get("highlight")
        base = y + rh - 18
        body.append(
            f'<line x1="{left}" y1="{base + r + 2:.1f}" x2="{left + pw}" y2="{base + r + 2:.1f}" stroke="{C["line"]}" stroke-width="1"/>'
        )
        body.append(
            text_el(
                left - 14,
                base - 4,
                wrap(g["label"], LIMITS["dots_label"] // 2, 2),
                14,
                700 if hl else 500,
                C["heading"] if hl else C["ink"],
                "end",
                gap=17,
                d=g,
            )
        )
        ev = ev_of(g)
        evm = bool(evidence_used(p))
        for b, vs in bins.items():
            cx = left + (b + 0.5) * bw
            for j in range(len(vs)):
                body.append(
                    ev_circle(
                        cx,
                        base - j * 2 * r,
                        r - (0.6 if ev else 0),
                        ev,
                        C["terracotta"] if hl else C["muted"],
                        hl,
                        g,
                        evm,
                    )
                )
        if p.get("marker", "median") == "median":
            s = sorted(g["values"])
            med = s[len(s) // 2] if len(s) % 2 else (s[len(s) // 2 - 1] + s[len(s) // 2]) / 2
            mx = X(med)
            body.append(
                f'<line x1="{mx:.1f}" y1="{y + 4}" x2="{mx:.1f}" y2="{base + r + 8:.1f}" stroke="{C["ink"]}" stroke-width="1.5" stroke-dasharray="3 3"/>'
            )
            body.append(text_el(mx + 6, y + 14, [f"median {num(med)}"], 12.5, 600, C["ink"]))
        y += rh
    for t in ticks:
        body.append(text_el(X(t), y + 16, [num(t)], 13, 500, C["muted"], "middle"))
    if unit:
        body.append(text_el(left + pw, y + 38, [unit], 13, 600, C["muted"], "end"))
    rows = [[g["label"], len(g["values"]), num(min(g["values"])), num(max(g["values"]))] for g in groups]
    data = table_html(["Group", "n", "Min", "Max"], rows, num_cols={1, 2, 3}, items=groups)
    return svg_wrap("".join(body), y + 46, p["headline"]), data


def t_dots(p, W, g):
    groups = p["groups"]
    allv = [v for grp in groups for v in grp["values"]]
    lo, hi = p.get("_range") or (axis_start(p, "x", allv), max(allv))
    lw = min(max(len(grp["label"]) for grp in groups), int(W * 0.3))
    nb = max(W - lw - 4, 20)
    out = []
    for grp in groups:
        counts = [0] * nb
        for v in grp["values"]:
            counts[min(int((v - lo) / ((hi - lo) or 1) * nb), nb - 1)] += 1
        top = max(counts) or 1
        chars = g["spark"]
        strip = "".join(chars[0] if c == 0 else chars[1 + round(c / top * (len(chars) - 2))] for c in counts)
        mark = g["hl"] if grp.get("highlight") else " "
        out.append(f"{mark}{tcut(grp['label'], lw):>{lw}} {g['v']}{strip}")
        med = median(grp["values"])
        pos = min(int((med - lo) / ((hi - lo) or 1) * nb), nb - 1)
        out.append(f" {'':>{lw}} {g['v']}{' ' * pos}{g['up']} median {tfmt(med)}")
    out.append(f" {'':>{lw}} {g['bl']}{g['h'] * nb}")
    left, right = tfmt(lo), tfmt(hi)
    out.append(f" {'':>{lw}}  {left}{' ' * max(nb - len(left) - len(right), 1)}{right}")
    if p.get("unit"):
        out.append(f"Values in {p['unit']}; taller marks mean more values in that range.")
    return out


# ---------- scatter: check, HTML, text ----------


def check_scatter(p, where, errors, warnings, digest):
    pts = listed(p, "points", where, warnings, 200, "points")
    labelled = [pt for pt in pts if pt.get("label")]
    if len(labelled) > 8:
        warnings.append(f"{where}: {len(labelled)} labelled points; label only the few the headline is about")
    count_highlights(pts, where, warnings)
    digest.append(f"    {len(pts)} points; x = {p['x_label']}, y = {p['y_label']}")
    for pt in labelled:
        digest.append(
            f"    {pt['label']}: x={num(pt['x'])}, y={num(pt['y'])}{'  [highlight]' if pt.get('highlight') else ''}"
        )


def v_scatter(p):
    pts = p["points"]
    xs, ys = [pt["x"] for pt in pts], [pt["y"] for pt in pts]
    xt = nice_ticks(*(p.get("_xrange") or (axis_start(p, "x", xs), max(xs))), 5)
    yt = nice_ticks(*(p.get("_yrange") or (axis_start(p, "y", ys), max(ys))), 4)
    left, top, pw, ph = 64, 40, W - 64 - 30, 270

    def X(v):
        return left + (v - xt[0]) / ((xt[-1] - xt[0]) or 1) * pw

    def Y(v):
        return top + ph - (v - yt[0]) / ((yt[-1] - yt[0]) or 1) * ph

    body = []
    for t in yt:
        body.append(f'<line x1="{left}" y1="{Y(t):.1f}" x2="{left + pw}" y2="{Y(t):.1f}" stroke="{C["line"]}"/>')
        body.append(text_el(left - 10, Y(t) + 5, [num(t)], 13, 500, C["muted"], "end"))
    for t in xt:
        body.append(text_el(X(t), top + ph + 22, [num(t)], 13, 500, C["muted"], "middle"))
    body.append(text_el(left + pw, top + ph + 46, [p["x_label"]], 13, 600, C["muted"], "end"))
    body.append(text_el(0, top - 22, [p["y_label"]], 13, 600, C["muted"]))
    for pt in sorted(pts, key=lambda q: bool(q.get("highlight"))):
        hl = pt.get("highlight")
        body.append(
            f'<circle cx="{X(pt["x"]):.1f}" cy="{Y(pt["y"]):.1f}" r="{7 if hl else 5}" fill="{C["terracotta"] if hl else C["muted"]}" fill-opacity="{1 if hl else 0.75}"{dattr(pt)}/>'
        )
        if pt.get("label"):
            anchor = "end" if X(pt["x"]) > left + pw * 0.75 else "start"
            body.append(
                text_el(
                    X(pt["x"]) + (-11 if anchor == "end" else 11),
                    Y(pt["y"]) + 5,
                    [pt["label"]],
                    14,
                    700 if hl else 500,
                    C["heading"],
                    anchor,
                    d=pt,
                )
            )
    data = table_html(
        ["Point", p["x_label"], p["y_label"]],
        [[pt.get("label", ""), num(pt["x"]), num(pt["y"])] for pt in pts],
        num_cols={1, 2},
        items=pts,
    )
    return svg_wrap("".join(body), top + ph + 56, p["headline"]), data


def t_scatter(p, W, g):
    pts = p["points"]
    xs, ys = [q["x"] for q in pts], [q["y"] for q in pts]
    x0 = axis_start(p, "x", xs)
    y0 = axis_start(p, "y", ys)
    cols, rows = min(W - 10, 60), 14
    grid = [[" "] * cols for _ in range(rows)]
    for q in sorted(pts, key=lambda q: bool(q.get("highlight"))):
        c = min(int((q["x"] - x0) / ((max(xs) - x0) or 1) * (cols - 1)), cols - 1)
        r = rows - 1 - min(int((q["y"] - y0) / ((max(ys) - y0) or 1) * (rows - 1)), rows - 1)
        grid[r][c] = g["hl"] if q.get("highlight") else g["pt"]
    yl, yh = tfmt(y0), tfmt(max(ys))
    lab = max(len(yl), len(yh))
    out = [f"{p['y_label']}"]
    for r, row in enumerate(grid):
        tick = yh if r == 0 else (yl if r == rows - 1 else "")
        out.append(f"{tick:>{lab}} {g['v']}{''.join(row)}")
    out.append(f"{'':>{lab}} {g['bl']}{g['h'] * cols}")
    xl, xh = tfmt(x0), tfmt(max(xs))
    out.append(f"{'':>{lab}}  {xl}{' ' * max(cols - len(xl) - len(xh), 1)}{xh}")
    out.append(f"{'':>{lab}}  {p['x_label']}")
    for q in pts:
        if q.get("label"):
            out.append(f"{g['hl'] if q.get('highlight') else g['pt']} {q['label']}: {tfmt(q['x'])}, {tfmt(q['y'])}")
    return out


# ---------- line: check, HTML, text ----------


def spark(values, g, lo=None, hi=None):
    chars = g["spark"]
    lo = min(values) if lo is None else lo
    hi = max(values) if hi is None else hi
    return "".join(chars[1 + round((v - lo) / ((hi - lo) or 1) * (len(chars) - 2))] for v in values)


def check_line(p, where, errors, warnings, digest):
    series = listed(p, "series", where, warnings, LIMITS["series"], "series")
    count_highlights(series, where, warnings)
    for s in series:
        pts = s["points"]
        digest.append(f"    {s.get('name')}: " + ", ".join(f"{x}={num(y)}" for x, y in pts))
    if not p.get("unit"):
        warnings.append(f"{where}: no 'unit'; say what the values measure")


def v_line(p):
    series = p["series"]
    xs_all = [pt[0] for s in series for pt in s["points"]]
    numeric = all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in xs_all)
    if numeric:
        xlo, xhi = min(xs_all), max(xs_all)

        def xpos(x):
            return (x - xlo) / ((xhi - xlo) or 1)

        xticks = sorted(set(xs_all)) if len(set(xs_all)) <= 8 else nice_ticks(xlo, xhi, 5)
    else:
        order = list(dict.fromkeys(xs_all))

        def xpos(x):
            return order.index(x) / ((len(order) - 1) or 1)

        xticks = order
    ys = [pt[1] for s in series for pt in s["points"]]
    ticks = nice_ticks(*(p.get("_range") or (axis_start(p, "y", ys), max(ys))), 4)
    ylo, yhi = ticks[0], ticks[-1]
    unit = p.get("unit", "")
    left, right, top, plot_h = 56, 190, 30, 260
    plot_w = W - left - right

    def X(x):
        return left + xpos(x) * plot_w

    def Y(y):
        return top + plot_h - (y - ylo) / ((yhi - ylo) or 1) * plot_h

    body = []
    for t in ticks:
        body.append(
            f'<line x1="{left}" y1="{Y(t):.1f}" x2="{left + plot_w}" y2="{Y(t):.1f}" stroke="{C["line"]}" stroke-width="1"/>'
        )
        body.append(text_el(left - 10, Y(t) + 5, [num(t)], 13, 500, C["muted"], "end"))
    step = max(1, math.ceil(len(xticks) / 8))
    for x in xticks[::step]:
        tick = (str(int(x)) if float(x).is_integer() else num(x)) if numeric else str(x)  # 2020, not 2,020
        body.append(text_el(X(x), top + plot_h + 22, [tick], 13, 500, C["muted"], "middle"))
    if unit:
        body.append(text_el(0, top - 8, [unit], 13, 600, C["muted"]))
    ends = []
    for s in sorted(series, key=lambda s: bool(s.get("highlight"))):
        hl = s.get("highlight") or len(series) == 1
        color = C["terracotta"] if hl else C["muted"]
        pts = " ".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in s["points"])
        dash = ""
        body.append(
            f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{3 if hl else 1.75}"{dash} stroke-linejoin="round"/>'
        )
        lx, ly = s["points"][-1]
        body.append(f'<circle cx="{X(lx):.1f}" cy="{Y(ly):.1f}" r="{4 if hl else 3}" fill="{color}"/>')
        ends.append([Y(ly), s.get("name", ""), num(ly), hl, color])
    ends.sort()
    for i in range(1, len(ends)):  # keep end labels from overlapping
        ends[i][0] = max(ends[i][0], ends[i - 1][0] + 38)
    for y, name, val, hl, _color in ends:
        body.append(
            text_el(
                left + plot_w + 12,
                y + 4,
                wrap(name, LIMITS["series_name"], 1) + [val + (f" {unit}" if unit else "")],
                14,
                700 if hl else 500,
                C["heading"] if hl else C["ink"],
                gap=17,
            )
        )
    for a in p.get("annotations", []):
        s = next((s for s in series if s.get("name") == a.get("series")), series[0])
        pt = next((pt for pt in s["points"] if pt[0] == a.get("x")), None)
        if pt is None:
            continue
        ax, ay = X(pt[0]), Y(pt[1])
        ty = ay - 34 if ay > top + 50 else ay + 30
        body.append(
            f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{ax:.1f}" y2="{ty + (8 if ty < ay else -12):.1f}" stroke="{C["ink"]}" stroke-width="1"/>'
        )
        body.append(f'<circle cx="{ax:.1f}" cy="{ay:.1f}" r="5" fill="none" stroke="{C["ink"]}" stroke-width="1.5"/>')
        anchor = "end" if ax > left + plot_w * 0.7 else "start"
        body.append(
            text_el(
                ax + (-8 if anchor == "end" else 8),
                ty,
                wrap(a.get("text", ""), 32, 2),
                13,
                500,
                C["ink"],
                anchor,
                italic=True,
                gap=16,
            )
        )
    if p.get("y_note"):
        body.append(text_el(left, top + plot_h + 46, [p["y_note"]], 13, 600, C["ink"]))
    h = top + plot_h + (58 if p.get("y_note") else 34)
    head = ["x"] + [s.get("name", "") for s in series]
    keys = list(dict.fromkeys(xs_all))
    rows = [[x] + [next((num(y) for xx, y in s["points"] if xx == x), "–") for s in series] for x in keys]
    data = table_html([p.get("x_label", "x")] + head[1:], rows, num_cols=set(range(1, len(head))))
    return svg_wrap("".join(body), h, p["headline"]), data


def t_line(p, W, g):
    series = p["series"]
    unit = p.get("unit", "")
    ys = [pt[1] for s in series for pt in s["points"]]
    lo, hi = p.get("_range") or (axis_start(p, "y", ys), max(ys))
    nw = min(max(len(s["name"]) for s in series), 22)
    out = []
    for s in series:
        vals = [pt[1] for pt in s["points"]]
        mark = g["hl"] if s.get("highlight") else " "
        out.append(
            f"{mark}{tcut(s['name'], nw):<{nw}}  {spark(vals, g, lo, hi)}  {tfmt(vals[0])} {g['arrow']} {tfmt(vals[-1])} {unit}".rstrip()
        )
    xs = [pt[0] for pt in series[0]["points"]]
    out.append(f" {'':<{nw}}  {tfmt(xs[0])} … {tfmt(xs[-1])}" + (f"  ({p['x_label']})" if p.get("x_label") else ""))
    for a in p.get("annotations", []):
        out += twrap(f"{g['pt']} at {a.get('x')}: {a.get('text')}", W)
    if p.get("y_note"):
        out += twrap(p["y_note"], W)
    return out


# ---------- timeline: check, HTML, text ----------


def check_timeline(p, where, errors, warnings, digest):
    events = listed(p, "events", where, warnings, LIMITS["timeline"], "events")
    count_highlights(events, where, warnings)
    for e in events:
        digest.append(f"    {e['date']}: {e['label']}{'  [highlight]' if e.get('highlight') else ''}")


def v_timeline(p):
    events = p["events"]
    n = len(events)
    pad = 70
    span = W - 2 * pad
    # Labels alternate above and below the axis, so each label may use the width of two intervals.
    room = span / max(n - 1, 1) * (2 if n > 2 else 1) - 16
    chars = max(int(room / 8.2), 12)
    up_lines = max([len(wrap(e["label"], chars, 3)) for k, e in enumerate(events) if k % 2 == 0] or [1])
    down_lines = max([len(wrap(e["label"], chars, 3)) for k, e in enumerate(events) if k % 2 == 1] or [0])
    axis_y = 50 + up_lines * 18
    body = [f'<line x1="20" y1="{axis_y}" x2="{W - 20}" y2="{axis_y}" stroke="{C["ink"]}" stroke-width="1"/>']
    for i, e in enumerate(events):
        x = pad + (span * i / (n - 1) if n > 1 else span / 2)
        hl = e.get("highlight")
        up = i % 2 == 0
        body.append(dot(x, axis_y, e, hl))
        body.append(
            f'<line x1="{x:.1f}" y1="{axis_y + (-10 if up else 10)}" x2="{x:.1f}" y2="{axis_y + (-24 if up else 24)}" stroke="{C["line"]}" stroke-width="1"/>'
        )
        lines = wrap(e["label"], chars, 3)
        half = max(len(line) for line in lines + [str(e["date"])]) * 4.3
        tx = min(max(x, half + 2), W - half - 2)  # keep the label inside the frame
        if up:
            y0 = axis_y - 30 - len(lines) * 18
            body.append(text_el(tx, y0, [str(e["date"])], 14, 700, C["ink"], "middle"))
            body.append(text_el(tx, y0 + 19, lines, 14, 700 if hl else 500, C["heading"], "middle", gap=18, d=e))
        else:
            body.append(text_el(tx, axis_y + 44, [str(e["date"])], 14, 700, C["ink"], "middle"))
            body.append(text_el(tx, axis_y + 63, lines, 14, 700 if hl else 500, C["heading"], "middle", gap=18, d=e))
    text = "<ul>" + "".join(f"<li{dattr(e)}><b>{esc(e['date'])}</b>: {esc(e['label'])}</li>" for e in events) + "</ul>"
    return svg_wrap("".join(body), axis_y + (50 + down_lines * 18 if down_lines else 12), p["headline"]), text


def t_timeline(p, W, g):
    dw = max(len(str(e["date"])) for e in p["events"])
    out = []
    for k, e in enumerate(p["events"]):
        mark = g["hl"] if e.get("highlight") else g["dot"]
        out.append(f"{str(e['date']):>{dw}} {mark} {e['label']}")
        if k < len(p["events"]) - 1:
            out.append(f"{'':>{dw}} {g['v']}")
    out.append("Events in order; spacing does not show the time between them.")
    return out


# ---------- table: check, HTML, text ----------


def check_table(p, where, errors, warnings, digest):
    rows = listed(p, "rows", where, warnings, LIMITS["rows"], "rows")
    for row in rows:
        digest.append("    " + " | ".join(str(c) for c in row))


def v_table(p):
    cols = p["columns"]
    labels, num_cols = [], set()
    for i, c in enumerate(cols):
        c = c if isinstance(c, dict) else {"label": c}
        labels.append(c["label"] + (f" ({c['unit']})" if c.get("unit") else ""))
        if c.get("align") == "right" or c.get("unit"):
            num_cols.add(i)
    rows = [
        [num(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v for v in row] for row in p["rows"]
    ]
    hl = set(p.get("highlight_rows", []))
    return f'<div class="tablewrap">{table_html(labels, rows, num_cols, {i - 1 for i in hl})}</div>', ""


def t_table(p, W, g):
    cols = [c if isinstance(c, dict) else {"label": c} for c in p["columns"]]
    head = [c["label"] + (f" ({c['unit']})" if c.get("unit") else "") for c in cols]
    right = {i for i, c in enumerate(cols) if c.get("unit") or c.get("align") == "right"}
    return table_lines(head, p["rows"], W, g, right, {i - 1 for i in p.get("highlight_rows", [])})


# ---------- text: check, HTML, text ----------


def check_text(p, where, errors, warnings, digest):
    body = p["body"]
    if isinstance(body, str):
        body = [body]
    words = sum(len(str(b).split()) for b in body)
    if words > 120:
        warnings.append(f"{where}: {words} words; a panel read alone works best with a short text")
    digest.append(f"    {words} words")


def v_text(p):
    body = p["body"] if isinstance(p["body"], list) else [p["body"]]
    return '<div class="prose">' + "".join(f"<p>{rich(b)}</p>" for b in body) + "</div>", ""


def t_text(p, W, g):
    body = p["body"] if isinstance(p["body"], list) else [p["body"]]
    out = []
    for para in body:
        out += twrap(plain(para), W) + [""]
    return out[:-1]


# ---------- svg: check, HTML, text ----------

# Static drawing only. Names are lower case because HTMLParser lowers them. <title> is left out on purpose: newer
# HTMLParsers read its content as text, while a browser drawing SVG reads it as markup, so markup inside could hide.
SVG_ELEMENTS = frozenset(
    (
        "svg g defs desc symbol use path rect circle ellipse line polyline polygon text tspan textpath marker "
        "lineargradient radialgradient stop clippath mask pattern"
    ).split()
)
SVG_ATTRIBUTES = frozenset(
    (
        "id class style lang xml:space xmlns xmlns:xlink role aria-label aria-labelledby aria-describedby aria-hidden "
        "viewbox preserveaspectratio width height x y x1 y1 x2 y2 cx cy r rx ry fx fy d points transform pathlength "
        "fill fill-opacity fill-rule stroke stroke-width stroke-opacity stroke-dasharray stroke-dashoffset stroke-linecap "
        "stroke-linejoin stroke-miterlimit opacity color visibility display vector-effect paint-order shape-rendering "
        "font-family font-size font-weight font-style text-anchor dominant-baseline alignment-baseline baseline-shift "
        "letter-spacing word-spacing text-decoration text-rendering dx dy rotate textlength lengthadjust startoffset "
        "method spacing side href xlink:href marker-start marker-mid marker-end markerwidth markerheight markerunits refx "
        "refy orient offset stop-color stop-opacity gradientunits gradienttransform spreadmethod clip-path clip-rule "
        "clippathunits mask maskunits maskcontentunits patternunits patterncontentunits patterntransform"
    ).split()
)
URL_REF = re.compile(r"url\(\s*(?!['\"]?#)", re.I)  # url(...) that is not a reference to an element in this svg


class _SvgCheck(HTMLParser):
    """Collect every element, attribute or construct in an svg that is not on the allowlist."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.problems = []

    def handle_starttag(self, tag, attrs):
        if tag not in SVG_ELEMENTS:
            self.problems.append(f"element <{tag}>; use shapes, paths, text, groups, gradients, markers and masks only")
            return
        for name, value in attrs:
            value = value or ""
            if name not in SVG_ATTRIBUTES:
                self.problems.append(
                    f"attribute '{name}' on <{tag}>; use geometry, paint, text and marker attributes only"
                )
            elif name in ("href", "xlink:href") and not value.strip().startswith("#"):
                self.problems.append(f"link '{value}' on <{tag}>; only links to an id in this svg, such as '#arrow'")
            elif URL_REF.search(value):
                self.problems.append(
                    f"url() in '{name}' on <{tag}>; only references to an id in this svg, such as 'url(#fade)'"
                )

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_comment(self, data):
        self.problems.append("a comment")

    def handle_decl(self, decl):
        self.problems.append(f"<!{decl}>")

    def unknown_decl(self, data):
        self.problems.append(f"<![{data[:20]}…]>")

    def handle_pi(self, data):
        self.problems.append(f"<?{data[:20]}…>")


def check_svg(p, where, errors, warnings, digest):
    svg = p["svg"].strip()
    if not svg.startswith("<svg") or not svg.endswith("</svg>"):
        errors.append(f"{where}: 'svg' must be one <svg>…</svg> element")
    if "viewBox" not in svg:
        errors.append(f"{where}: the svg needs a viewBox and no fixed width or height")
    parser = _SvgCheck()
    parser.feed(svg)
    parser.close()
    for problem in dict.fromkeys(parser.problems):  # each problem once, in order
        errors.append(f"{where}: the svg must not contain {problem}")
    digest.append(f"    custom svg; alt: {p['alt']}")


def v_svg(p):
    svg = re.sub(r"^<svg", f'<svg role="img" aria-label="{esc(p["alt"])}"', p["svg"].strip(), count=1)
    return svg, f"<p>{esc(p['alt'])}</p>"


def t_svg(p, W, g):
    return twrap("[Diagram] " + p["alt"], W)


# ---------- lanes: check, HTML, text ----------


def check_lanes(p, where, errors, warnings, digest):
    listed(p, "actors", where, warnings, LIMITS["lanes_actors"], "actors")
    steps = listed(p, "steps", where, warnings, LIMITS["lanes_steps"], "steps")
    count_highlights(steps, where, warnings)
    prev = None
    for s in steps:
        hand = f"  (hand-off from {prev})" if prev is not None and prev != s["actor"] else ""
        digest.append(f"    {s['actor']}: {s['label']}{hand}{'  [highlight]' if s.get('highlight') else ''}")
        prev = s["actor"]


def v_lanes(p):
    """Actors as rows, steps in one shared order along them. A hand-off turns between two columns, so it crosses no
    label."""
    actors, steps = [str(a) for a in p["actors"]], p["steps"]
    evm = bool(evidence_used(p))
    left, rh, pad = 170, 92, 10
    n = len(steps)
    cw = (W - left - pad) / max(n, 1)
    chars = max(int((cw - 18) / 7.4), 6)

    def X(k):
        return left + cw * (k + 0.5)

    def Y(actor):
        return 18 + actors.index(str(actor)) * rh + rh - 26

    body = []
    for a in actors:
        y = Y(a)
        body.append(text_el(0, y + 5, wrap(a, 20, 2), 15, 700, C["heading"], gap=18))
        body.append(
            f'<line x1="{left - 10}" y1="{y:.1f}" x2="{W}" y2="{y:.1f}" stroke="{C["line"]}" stroke-width="1"/>'
        )
    for k in range(1, n):
        a, b = steps[k - 1], steps[k]
        x1, y1, x2, y2 = X(k - 1), Y(a["actor"]), X(k), Y(b["actor"])
        hl = b.get("highlight")
        color, width = (C["terracotta"], 2.5) if hl else (C["ink"], 1.5)
        if y1 == y2:
            body.append(
                f'<line x1="{x1 + 8:.1f}" y1="{y1:.1f}" x2="{x2 - 8:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="{width}"/>'
            )
        else:  # a hand-off: along the lane to the column's edge, across to the other lane, then on to the step
            mid = x1 + cw / 2
            body.append(
                f'<path d="M{x1 + 8:.1f} {y1:.1f}H{mid:.1f}V{y2:.1f}" fill="none" stroke="{color}" stroke-width="{width}"/>'
            )
            body.append(arrow(mid, y2, x2 - 9, y2, color))
    for k, s in enumerate(steps):
        hl = s.get("highlight")
        x, y = X(k), Y(s["actor"])
        lines = wrap(s["label"], chars, 3)
        body.append(
            text_el(
                x, y - 16 - 17 * (len(lines) - 1), lines, 13.5, 700 if hl else 500, C["heading"], "middle", gap=17, d=s
            )
        )
        body.append(ev_circle(x, y, 7, ev_of(s), C["muted"], hl, s, evm))
    text = "<ol>" + "".join(f"<li{dattr(s)}>{esc(s['actor'])}: {esc(s['label'])}</li>" for s in steps) + "</ol>"
    return svg_wrap("".join(body), 26 + len(actors) * rh, p["headline"]), text


def t_lanes(p, W, g):
    steps = p["steps"]
    aw = min(max(len(str(a)) for a in p["actors"]), 18)
    out, prev = [], None
    for k, s in enumerate(steps, 1):
        actor = str(s["actor"])
        if prev is not None and actor != prev:
            out.append(f"{'':>{aw}}    {g['down']} hand-off to {actor}")
        mark = g["hl"] if s.get("highlight") else " "
        out += twrap(f"{mark}{tcut(actor, aw):>{aw}} {g['v']} {k}. {s['label']}", W)
        prev = actor
    return out


# ---------- fork: check, HTML, text ----------


def check_fork(p, where, errors, warnings, digest):
    branches = listed(p, "branches", where, warnings, LIMITS["fork_branches"], "branches")
    count_highlights(branches, where, warnings)
    digest.append(f"    {p['input']} → {p['decider']}")
    for b in branches:
        digest.append(
            f"      {b['label']}: {b['outcome']}{(' (' + b['note'] + ')') if b.get('note') else ''}"
            + ("  [highlight]" if b.get("highlight") else "")
        )


def outcome_glyph(x, y, outcome):
    """An outcome's glyph, so the outcome does not rest on colour: ▲ helps, ▼ hurts, ✕ never, = neutral. None is a
    circle, so no outcome looks like an evidence mark."""
    if outcome == "helps":
        return f'<path d="M{x:.1f} {y - 7:.1f}L{x + 7:.1f} {y + 5:.1f}H{x - 7:.1f}Z" fill="{C["moss"]}"/>'
    if outcome == "hurts":
        return f'<path d="M{x:.1f} {y + 7:.1f}L{x + 7:.1f} {y - 5:.1f}H{x - 7:.1f}Z" fill="{C["ink"]}"/>'
    if outcome == "never":
        return f'<path d="M{x - 6:.1f} {y - 6:.1f}l12 12M{x + 6:.1f} {y - 6:.1f}l-12 12" stroke="{C["ink"]}" stroke-width="2.4"/>'
    return f'<path d="M{x - 6:.1f} {y - 3:.1f}h12M{x - 6:.1f} {y + 3:.1f}h12" stroke="{C["ink"]}" stroke-width="1.8"/>'


def v_fork(p):
    """One input meets a decider and forks into two to four branches, each with its outcome."""
    branches = p["branches"]
    evm = bool(evidence_used(p))
    n = len(branches)
    rh = 92
    H = max(n * rh, 170)
    cy = H / 2
    dx = 250  # the decider
    bx = 430  # where the branches end
    body = [
        text_el(
            0, cy - 9 * (len(wrap(p["input"], 20, 3)) - 1) + 5, wrap(p["input"], 20, 3), 16, 700, C["heading"], gap=18
        )
    ]
    body.append(arrow(170, cy, dx - 18, cy, C["ink"]))
    body.append(
        f'<path d="M{dx:.1f} {cy - 14:.1f}L{dx + 14:.1f} {cy:.1f}L{dx:.1f} {cy + 14:.1f}L{dx - 14:.1f} {cy:.1f}Z" fill="{C["cream"]}" stroke="{C["ink"]}" stroke-width="1.5"/>'
    )
    dec = wrap(p["decider"], 22, 2)
    body.append(text_el(dx, cy - 26 - 15 * (len(dec) - 1), dec, 13, 500, C["muted"], "middle", True, 15))
    for k, b in enumerate(branches):
        hl = b.get("highlight")
        by = rh / 2 + k * rh + (H - n * rh) / 2
        color = C["terracotta"] if hl else C["ink"]
        body.append(
            f'<path d="M{dx + 14:.1f} {cy:.1f}C{dx + 90:.1f} {cy:.1f} {bx - 100:.1f} {by:.1f} {bx - 10:.1f} {by:.1f}" fill="none" stroke="{color}" stroke-width="{2.5 if hl else 1.5}"/>'
        )
        body.append(ev_circle(bx, by, 7, ev_of(b), C["muted"], hl, b, evm))
        body.append(outcome_glyph(bx + 26, by, b["outcome"]))
        word = OUTCOMES[b["outcome"]][1]
        body.append(
            text_el(
                bx + 44, by + 5, wrap(b["label"], LIMITS["fork_label"], 1), 15, 700 if hl else 600, C["heading"], d=b
            )
        )
        sub = word + (f": {b['note']}" if b.get("note") else "")
        body.append(text_el(bx + 44, by + 25, wrap(sub, 44, 2), 13, 500, C["muted"], italic=True, gap=16))
    text = (
        f"<p>{esc(p['input'])}, depending on {esc(p['decider'])}:</p><ul>"
        + "".join(
            f"<li{dattr(b)}>{esc(b['label'])}: {OUTCOMES[b['outcome']][1]}{(' — ' + esc(b['note'])) if b.get('note') else ''}</li>"
            for b in branches
        )
        + "</ul>"
    )
    return svg_wrap("".join(body), H + 10, p["headline"]), text


def t_fork(p, W, g):
    out = twrap(f"{p['input']}", W) + twrap(f"  {g['arrow']} {p['decider']}", W)
    branches = p["branches"]
    for k, b in enumerate(branches):
        branch = g["end"] if k == len(branches) - 1 else g["tee"]
        glyph, word = OUTCOMES[b["outcome"]]
        mark = f" {g['hl']}" if b.get("highlight") else ""
        out += twrap(
            f"    {branch}{g['h']} {b['label']}: {g[glyph]} {word}{(', ' + b['note']) if b.get('note') else ''}{mark}",
            W,
        )
    return out


# ---------- registries ----------

PANEL_CHECKS = {
    "effects": check_effects,
    "pairs": check_pairs,
    "map": check_map,
    "concept": check_concept,
    "slope": check_slope,
    "dots": check_dots,
    "scatter": check_scatter,
    "quadrant": check_quadrant,
    "sets": check_sets,
    "tree": check_tree,
    "numbers": check_numbers,
    "units": check_units,
    "matrix": check_matrix,
    "bars": check_bars,
    "line": check_line,
    "table": check_table,
    "flow": check_flow,
    "groups": check_groups,
    "timeline": check_timeline,
    "text": check_text,
    "svg": check_svg,
    "lanes": check_lanes,
    "fork": check_fork,
}


VISUALS = {
    "effects": v_effects,
    "pairs": v_pairs,
    "map": v_map,
    "concept": v_concept,
    "slope": v_slope,
    "dots": v_dots,
    "scatter": v_scatter,
    "quadrant": v_quadrant,
    "sets": v_sets,
    "tree": v_tree,
    "numbers": v_numbers,
    "units": v_units,
    "matrix": v_matrix,
    "bars": v_bars,
    "line": v_line,
    "table": v_table,
    "flow": v_flow,
    "groups": v_groups,
    "timeline": v_timeline,
    "text": v_text,
    "svg": v_svg,
    "lanes": v_lanes,
    "fork": v_fork,
}


TEXT = {
    "effects": t_effects,
    "pairs": t_pairs,
    "numbers": t_numbers,
    "units": t_units,
    "bars": t_bars,
    "line": t_line,
    "table": t_table,
    "matrix": t_matrix,
    "flow": t_flow,
    "map": t_map,
    "concept": t_concept,
    "groups": t_groups,
    "timeline": t_timeline,
    "text": t_text,
    "svg": t_svg,
    "slope": t_slope,
    "dots": t_dots,
    "scatter": t_scatter,
    "quadrant": t_quadrant,
    "sets": t_sets,
    "tree": t_tree,
    "lanes": t_lanes,
    "fork": t_fork,
}


def _tables_match_kinds() -> bool:
    """Every kind needs a check, a visual and a text form; fail at start-up, not later in one output format."""
    for name, table in (("PANEL_CHECKS", PANEL_CHECKS), ("VISUALS", VISUALS), ("TEXT", TEXT)):
        if set(table) != set(KINDS):
            raise RuntimeError(
                f"{name} does not match KINDS: missing {sorted(set(KINDS) - set(table))}, extra {sorted(set(table) - set(KINDS))}"
            )
    return True


TABLES_MATCH_KINDS = _tables_match_kinds()


def visual_of(p, spec):
    """A panel's (visual HTML, data HTML). A map draws the spec's document, so it gets the spec."""
    return v_map(p, spec) if p["kind"] == "map" else VISUALS[p["kind"]](p)


def text_of(p, W, g, spec):
    """A panel's plain-text lines."""
    return t_map(p, W, g, spec) if p["kind"] == "map" else TEXT[p["kind"]](p, W, g)
