"""Render a short visual presentation from a JSON spec, as one self-contained HTML page.

Usage:
  python3 show.py check SPEC                  validate the spec and print every value it will show
  python3 show.py render SPEC --out FILE      check, then write the page (add --open to open it)

SPEC is a JSON file described in templates/spec.md. Panels are shown one at a time, and the reader
steps through them with buttons or the arrow keys. Without JavaScript, or when printed, all panels
are shown in order.

render --format text or md draws the same panels as plain text; --format text --screen-reader writes them as
sentences and value lists, without box drawing, for screen readers. Every layout is computed here, so the agent
never draws a text diagram by hand: language models read text diagrams far better than they construct them.
"""





import argparse
import html
import json
import math
import re
import sys
import textwrap
import webbrowser
from html.parser import HTMLParser
from pathlib import Path


HERE = Path(__file__).resolve().parent  # show.css and show.js, inlined into every page, sit next to this script
KINDS = ("map", "concept", "flow", "groups", "tree", "sets", "matrix", "effects", "pairs", "quadrant", "numbers", "units", "bars", "slope",
         "dots", "scatter", "line", "timeline", "table", "text", "svg")


LIMITS = {"panels": 12, "bars": 12, "series": 4, "flow": 7, "groups": 4, "group_items": 15, "timeline": 8,
          "numbers": 3, "highlights": 2, "headline_chars": 140, "rows": 15, "units": 100, "unit_parts": 3,
          "matrix_rows": 10, "matrix_cols": 5}


MARKS = {"yes": "yes", "no": "no", "up": "higher", "down": "lower", "same": "no difference"}


C = {"cream": "#FFFCF7", "linen": "#F2EDE5", "sand": "#C4B69C", "terracotta": "#E8725C", "moss": "#6B7F5E",
     "umber": "#5C4033", "ink": "#33302B", "heading": "#1C1A17", "muted": "#78736B", "line": "#DDD6CA"}


SANS = "Space Grotesk, -apple-system, sans-serif"


W = 800  # SVG viewBox width


GLYPHS = {
    "unicode": {"h": "─", "v": "│", "tl": "┌", "tr": "┐", "bl": "└", "br": "┘", "arrow": "→", "down": "↓",
                "bar": "█", "half": "▌", "hl": "◆", "dot": "●", "pt": "•", "box": "■", "box2": "▣", "box3": "□",
                "spark": " ▁▂▃▄▅▆▇█", "tee": "├", "end": "└", "up": "▲", "dn": "▼", "yes": "✓", "no": "✗",
                "same": "=", "blank": "·", "cross": "┼", "seg": "━"},
    "ascii": {"h": "-", "v": "|", "tl": "+", "tr": "+", "bl": "+", "br": "+", "arrow": "->", "down": "v",
              "bar": "#", "half": "#", "hl": ">", "dot": "o", "pt": "*", "box": "#", "box2": "+", "box3": ".",
              "spark": " .:-=+*#%@", "tee": "|-", "end": "`-", "up": "^", "dn": "v", "yes": "Y", "no": "N",
              "same": "=", "blank": ".", "cross": "+", "seg": "="},
}


# ---------- shared helpers: HTML and SVG ----------

LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")


def rich(value) -> str:
    """Escape text and turn Markdown links, [label](https://...), into anchors."""
    out, last = [], 0
    text = str(value)
    for m in LINK.finditer(text):
        out.append(esc(text[last:m.start()]))
        out.append(f'<a href="{esc(m.group(2))}" target="_blank" rel="noopener">{esc(m.group(1))}</a>')
        last = m.end()
    out.append(esc(text[last:]))
    return "".join(out)


def plain(value, keep_links=False) -> str:
    """Text output: a link becomes its label followed by the address, or stays Markdown."""
    return str(value) if keep_links else LINK.sub(lambda m: f"{m.group(1)} <{m.group(2)}>", str(value))


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def num(value) -> str:
    """Format a number for a label: no trailing .0, thousands separators."""
    if isinstance(value, float) and not value.is_integer():
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    return f"{int(value):,}"


def wrap(text: str, chars: int, max_lines: int = 3) -> list[str]:
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > chars:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: max(chars - 1, 1)].rstrip() + "…"
    return lines


def text_el(x, y, lines, size=12, weight=500, fill=None, anchor="start", italic=False, gap=None) -> str:
    gap = gap or size * 1.3
    style = ' font-style="italic"' if italic else ""
    spans = "".join(f'<tspan x="{x:.1f}" dy="{0 if i == 0 else gap:.1f}">{esc(l)}</tspan>' for i, l in enumerate(lines))
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{SANS}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill or C["ink"]}" text-anchor="{anchor}"{style}>{spans}</text>')


def nice_ticks(lo: float, hi: float, n: int = 4) -> list[float]:
    if hi == lo:
        hi = lo + 1
    raw = (hi - lo) / n
    mag = 10 ** math.floor(math.log10(raw))
    step = next(s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw)
    start = math.floor(lo / step) * step
    ticks, t = [], start
    while t <= hi + step * 0.001:
        ticks.append(round(t, 10))
        t += step
    if ticks[-1] < hi:
        ticks.append(round(ticks[-1] + step, 10))
    return ticks


def svg_wrap(body: str, height: float, label: str) -> str:
    return (f'<svg viewBox="0 0 {W} {height:.0f}" role="img" aria-label="{esc(label)}" '
            f'xmlns="http://www.w3.org/2000/svg">{body}</svg>')


def table_html(columns, rows, num_cols=frozenset(), highlight=frozenset()) -> str:
    head = "".join(f'<th class="{"n" if i in num_cols else ""}">{esc(c)}</th>' for i, c in enumerate(columns))
    body = "".join(
        f'<tr class="{"hl" if r in highlight else ""}">' +
        "".join(f'<td class="{"n" if i in num_cols else ""}">{esc(c)}</td>' for i, c in enumerate(row)) + "</tr>"
        for r, row in enumerate(rows))
    return f'<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def arrow(x1, y1, x2, y2, color):
    ang = math.atan2(y2 - y1, x2 - x1)
    tip = (x2, y2)
    a = (x2 - 10 * math.cos(ang) + 5 * math.sin(ang), y2 - 10 * math.sin(ang) - 5 * math.cos(ang))
    b = (x2 - 10 * math.cos(ang) - 5 * math.sin(ang), y2 - 10 * math.sin(ang) + 5 * math.cos(ang))
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2 - 9 * math.cos(ang):.1f}" y2="{y2 - 9 * math.sin(ang):.1f}" stroke="{color}" stroke-width="1.5"/>'
            f'<polygon points="{tip[0]:.1f},{tip[1]:.1f} {a[0]:.1f},{a[1]:.1f} {b[0]:.1f},{b[1]:.1f}" fill="{color}"/>')


def node(x, y, w, h, label, hl, chars):
    lines = wrap(label, chars, 3)
    stroke = f' stroke="{C["terracotta"]}" stroke-width="2.5"' if hl else ""
    ty = y + h / 2 - (len(lines) - 1) * 9 + 5
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h}" rx="4" fill="{C["linen"]}"{stroke}/>' +
            text_el(x + w / 2, ty, lines, 15, 700 if hl else 600, C["heading"], "middle", gap=18))


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _as_list(v):
    return v if isinstance(v, list) else ([] if v is None else [v])


# ---------- shared helpers: plain text ----------

def tfmt(v):
    if isinstance(v, float) and not v.is_integer():
        return f"{v:,.2f}".rstrip("0").rstrip(".")
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return f"{int(v):,}"
    return str(v)


def twrap(text, width, indent=""):
    return textwrap.wrap(str(text), width=max(width, 10), initial_indent=indent, subsequent_indent=indent, break_long_words=False, break_on_hyphens=False) or [indent]


def tcut(text, n):
    text = str(text)
    return text if len(text) <= n else text[: max(n - 1, 1)] + "…"


def tbox(lines, width, g, hl=False):
    """A box around lines; a highlighted box gets a marker in its top-left corner."""
    inner = width - 4
    top = g["tl"] + (g["hl"] if hl else g["h"]) + g["h"] * (width - 3) + g["tr"]
    out = [top] + [f'{g["v"]} {tcut(l, inner):<{inner}} {g["v"]}' for l in lines] + [g["bl"] + g["h"] * (width - 2) + g["br"]]
    return out


def median(vals):
    s = sorted(vals)
    return s[len(s) // 2] if len(s) % 2 else (s[len(s) // 2 - 1] + s[len(s) // 2]) / 2


def table_lines(header, rows, W, g, right=frozenset(), hl=frozenset()):
    rows = [[tfmt(c) for c in r] for r in rows]
    n = len(header)
    widths = [max(len(str(header[i])), *(len(r[i]) for r in rows)) for i in range(n)]
    while sum(widths) + 3 * n + 1 > W and max(widths) > 8:
        widths[widths.index(max(widths))] -= 1
    sep = "  "

    def line(cells, mark=" "):
        return mark + sep.join(tcut(c, w).rjust(w) if i in right else tcut(c, w).ljust(w) for i, (c, w) in enumerate(zip(cells, widths)))
    out = [line([str(h).upper() for h in header]), " " + sep.join(g["h"] * w for w in widths)]
    for k, r in enumerate(rows):
        out.append(line(r, g["hl"] if k in hl else " "))
    return out


# ---------- validation ----------

def check(spec: dict) -> tuple[list[str], list[str], list[str]]:
    """Return (errors, warnings, digest lines)."""
    errors, warnings, digest = [], [], []
    if not isinstance(spec, dict):
        return ["the spec must be a JSON object"], [], []
    for key in ("title", "panels"):
        if not spec.get(key):
            errors.append(f"missing '{key}'")
    panels = spec.get("panels") or []
    if not isinstance(panels, list):
        return errors + ["'panels' must be a list"], warnings, digest
    if len(panels) > LIMITS["panels"]:
        warnings.append(f"{len(panels)} panels: more than {LIMITS['panels']} is long for one introduction; split it or cut panels")
    digest.append(f"TITLE: {spec.get('title', '')}")
    if spec.get("summary"):
        digest.append(f"SUMMARY: {spec['summary']}")
    doc = spec.get("document")
    if doc is not None:
        secs = doc.get("sections") if isinstance(doc, dict) else None
        if not isinstance(secs, list) or not secs or not all(isinstance(x, dict) and x.get("id") is not None and x.get("label") for x in secs):
            errors.append("'document' needs 'sections', each with an 'id' and a 'label'")
        else:
            digest.append(f"DOCUMENT: {doc.get('title', '')} — " + " · ".join(f"{x['id']} {x['label']}" for x in secs))
            for x in secs:
                if len(str(x.get("gist", ""))) > 50:
                    warnings.append(f"document: the gist of '{x['label']}' is {len(x['gist'])} characters; keep it under 50, a few words")
    for i, p in enumerate(panels, 1):
        where = f"panel {i}"
        if not isinstance(p, dict):
            errors.append(f"{where}: must be an object")
            continue
        kind, head = p.get("kind"), str(p.get("headline", "")).strip()
        if kind not in KINDS:
            errors.append(f"{where}: kind must be one of {', '.join(KINDS)}")
            continue
        if not head:
            errors.append(f"{where}: missing 'headline' (a full sentence that states the panel's point)")
        else:
            if len(head.split()) < 4 or not re.search(r"[.!?]$", head):
                warnings.append(f"{where}: headline '{head}' does not read as a full sentence; state the point, not the topic")
            if len(head) > LIMITS["headline_chars"]:
                warnings.append(f"{where}: headline is {len(head)} characters; keep it under {LIMITS['headline_chars']}")
        digest.append(f"\n[{i}] {kind.upper()}: {head}")
        try:
            if kind == "map":
                check_map(p, where, errors, warnings, digest, spec)
            else:
                PANEL_CHECKS[kind](p, where, errors, warnings, digest)
            if p.get("part") is not None and not spec.get("document"):
                warnings.append(f"{where}: 'part' is set but there is no top-level 'document' to show it in")
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            errors.append(f"{where}: malformed {kind} data ({exc})")
        if p.get("note"):
            digest.append(f"    note: {p['note']}")
    return errors, warnings, digest


def need_list(p, key, where, errors, limit=None, warnings=None, what="items"):
    items = p.get(key)
    if not isinstance(items, list) or not items:
        errors.append(f"{where}: '{key}' must be a non-empty list")
        return []
    if limit and len(items) > limit and warnings is not None:
        warnings.append(f"{where}: {len(items)} {what}; more than {limit} is hard to read in one panel")
    return items


def count_highlights(items, where, warnings):
    n = sum(1 for it in items if isinstance(it, dict) and it.get("highlight"))
    if n > LIMITS["highlights"]:
        warnings.append(f"{where}: {n} highlighted items; emphasis works when it marks the one or two that carry the point")


# ---------- map: check, HTML, text ----------

def check_map(p, where, errors, warnings, digest, spec=None):
    secs = p.get("sections") or (spec or {}).get("document", {}).get("sections")
    if not isinstance(secs, list) or not secs:
        errors.append(f"{where}: a map needs 'sections', or a top-level 'document' with 'sections'")
        return
    if len(secs) > 9:
        warnings.append(f"{where}: {len(secs)} sections; group them into at most 9 parts")
    if p.get("sections"):
        for sec in secs:
            if isinstance(sec, dict) and len(str(sec.get("gist", ""))) > 50:
                warnings.append(f"{where}: the gist of '{sec.get('label')}' is {len(sec['gist'])} characters; keep it under 50, a few words")
    for s in secs:
        if not isinstance(s, dict) or not s.get("label"):
            errors.append(f"{where}: each section needs a 'label'")
            continue
        digest.append(f"    {s.get('id', '')} {s['label']}{(' — ' + s['gist']) if s.get('gist') else ''}"
                      f"{'  [highlight]' if s.get('highlight') or s.get('id') in _as_list(p.get('highlight')) else ''}")


def v_map(p, spec=None):
    """The document's parts in order: the organizer the reader returns to."""
    secs = p.get("sections") or spec["document"]["sections"]
    hl_ids = set(_as_list(p.get("highlight")))
    n = len(secs)
    body = []
    stroke = lambda hl: f' stroke="{C["terracotta"]}" stroke-width="2.5"' if hl else ""
    if n <= 5:  # a row of parts, each with its gist inside the box
        gap = 14
        bw = (W - gap * (n - 1)) / n
        glines = {k: wrap(sec.get("gist", ""), int(bw / 7.4), 3) if sec.get("gist") else [] for k, sec in enumerate(secs)}
        llines = {k: wrap(sec["label"], int(bw / 9), 2) for k, sec in enumerate(secs)}
        bh = 26 + 19 * max(len(v) for v in llines.values()) + 17 * max(len(v) for v in glines.values())
        for k, sec in enumerate(secs):
            x = k * (bw + gap)
            hl = sec.get("highlight") or sec.get("id") in hl_ids
            body.append(f'<rect x="{x:.1f}" y="1" width="{bw:.1f}" height="{bh}" rx="4" fill="{C["linen"]}"{stroke(hl)}/>')
            body.append(text_el(x + 14, 30, llines[k], 16, 700, C["heading"], gap=19))
            if glines[k]:
                body.append(text_el(x + 14, 30 + 19 * len(llines[k]) + 6, glines[k], 13, 500, C["muted"], gap=17))
        h = bh + 2
    else:  # one row per part: id, label, and its gist on the same line
        rh = 50
        for k, sec in enumerate(secs):
            y = k * rh
            hl = sec.get("highlight") or sec.get("id") in hl_ids
            body.append(f'<rect x="1" y="{y + 1}" width="{W - 2}" height="{rh - 8}" rx="4" fill="{C["linen"]}"{stroke(hl)}/>')
            body.append(text_el(18, y + 28, wrap(sec["label"], 34, 1), 16, 700, C["heading"]))
            if sec.get("gist"):
                body.append(text_el(370, y + 28, wrap(sec["gist"], 52, 1), 14, 500, C["muted"]))
        h = n * rh - 6
    text = "<ol>" + "".join(f"<li><b>{esc(sec['label'])}</b>{(': ' + esc(sec['gist'])) if sec.get('gist') else ''}</li>" for sec in secs) + "</ol>"
    return svg_wrap("".join(body), h + 2, p["headline"]), text


def t_map(p, W, g, spec=None):
    secs = p.get("sections") or spec["document"]["sections"]
    hl_ids = set(p.get("highlight") if isinstance(p.get("highlight"), list) else [p.get("highlight")])
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
    nodes = need_list(p, "nodes", where, errors, 12, warnings, "concepts")
    edges = need_list(p, "edges", where, errors)
    ids = {n.get("id") for n in nodes if isinstance(n, dict)}
    for n in nodes:
        if not isinstance(n, dict) or not n.get("id") or not n.get("label"):
            errors.append(f"{where}: each node needs an 'id' and a 'label'")
    count_highlights(nodes, where, warnings)
    labels = {n.get("id"): n.get("label") for n in nodes if isinstance(n, dict)}
    for e in edges:
        if not isinstance(e, dict) or e.get("from") not in ids or e.get("to") not in ids:
            errors.append(f"{where}: each edge needs 'from' and 'to' that name node ids")
            continue
        if not e.get("label"):
            errors.append(f"{where}: edge {e['from']} → {e['to']} needs a 'label' that says how they relate, such as 'causes' or 'is part of'")
            continue
        if len(e["label"]) > 40:
            warnings.append(f"{where}: relation '{e['label']}' is {len(e['label'])} characters; keep relations to a few words and put conditions in the note")
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
        body.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{2.2 if hl else 1.5}" marker-end="url(#ah{"h" if hl else ""})"/>')
        lab = wrap(e["label"], 24 if e in long_edges else lab_chars, 4)
        lw = max(len(l) for l in lab) * 7.2 + 10
        my -= (len(lab) - 1) * 8  # centre a multi-line label on its edge
        labels.append(f'<rect x="{mx - lw / 2:.1f}" y="{my - 13:.1f}" width="{lw:.1f}" height="{len(lab) * 16 + 6}" rx="3" fill="{C["cream"]}"/>'
                      + text_el(mx, my + 1, lab, 13, 600 if hl else 500, C["umber"] if hl else C["muted"], "middle", True, 16))
    for i, (x, y, w, h) in box.items():
        n = by_id[i]
        hl = n.get("highlight")
        body.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h}" rx="4" fill="{C["linen"]}"'
                    + (f' stroke="{C["terracotta"]}" stroke-width="2.5"' if hl else f' stroke="{C["sand"]}" stroke-width="1"') + "/>")
        body.append(text_el(x + w / 2, y + 26, lines_of[i], 15, 700 if hl else 600, C["heading"], "middle", gap=18))
    defs = (f'<defs><marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="{C["ink"]}"/></marker>'
            f'<marker id="ahh" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="{C["terracotta"]}"/></marker></defs>')
    text = "<ul>" + "".join(f"<li>{esc(by_id[e['from']]['label'])} <i>{esc(e['label'])}</i> {esc(by_id[e['to']]['label'])}</li>" for e in edges) + "</ul>"
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
            out += twrap(f"{branch}{g['h']} {e['label']} {g['arrow']} {t['label']}{' ' + g['hl'] if t.get('highlight') else ''}", W - 2, "  ")
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
        for lab, hl in zip(labels, hls):
            boxes.append(tbox(twrap(lab, bw - 4), bw, g, hl))
        h = max(len(b) for b in boxes)
        for b in boxes:
            while len(b) < h:
                b.insert(-1, f'{g["v"]}{" " * (bw - 2)}{g["v"]}')
        mid = h // 2
        for row in range(h):
            out.append("".join(b[row] + ((" " + g["arrow"] + " ") if (k < n - 1 and row == mid) else (" " * aw if k < n - 1 else ""))
                               for k, b in enumerate(boxes)))
        for k, note in enumerate(notes):
            if note:
                out += twrap(f"{k + 1}. {note}", W)
    else:
        width = min(W, 48)
        for k, (lab, note, hl) in enumerate(zip(labels, notes, hls)):
            out += tbox(twrap(lab, width - 4) + (twrap(note, width - 4) if note else []), width, g, hl)
            if k < n - 1:
                out.append(" " * (width // 2) + g["down"])
    out.append(f"{g['arrow']} means: {arrow_word}")
    return out


def check_flow(p, where, errors, warnings, digest):
    steps = need_list(p, "steps", where, errors, LIMITS["flow"], warnings, "steps")
    count_highlights(steps, where, warnings)
    if not p.get("arrow"):
        errors.append(f"{where}: missing 'arrow': state what every arrow means, such as 'then' or 'sends data to'")
    for s in steps:
        if not s.get("label"):
            errors.append(f"{where}: every step needs a 'label'")
        digest.append(f"    → {s.get('label')}{'  [highlight]' if s.get('highlight') else ''}" + (f" ({s['note']})" if s.get("note") else ""))


def v_flow(p):
    steps = p["steps"]
    n = len(steps)
    body = []
    if n <= 5:  # one row, left to right
        gap = 44
        bw = (W - gap * (n - 1)) / n
        bh = 76
        for i, s in enumerate(steps):
            x = i * (bw + gap)
            body.append(node(x, 10, bw, bh, s["label"], s.get("highlight"), int(bw / 9)))
            if s.get("note"):
                body.append(text_el(x + bw / 2, 10 + bh + 24, wrap(s["note"], int(bw / 7.4), 3), 13, 500, C["muted"], "middle", True, 17))
            if i < n - 1:
                body.append(arrow(x + bw + 4, 10 + bh / 2, x + bw + gap - 4, 10 + bh / 2, C["ink"]))
        h = 10 + bh + (82 if any(s.get("note") for s in steps) else 14)
    else:  # one column, top to bottom
        bw, bh, gap = 320, 56, 30
        for i, s in enumerate(steps):
            y = 6 + i * (bh + gap)
            body.append(node(0, y, bw, bh, s["label"], s.get("highlight"), 34))
            if s.get("note"):
                body.append(text_el(bw + 22, y + bh / 2 + 5, wrap(s["note"], 54, 2), 14, 500, C["muted"], italic=True, gap=17))
            if i < n - 1:
                body.append(arrow(bw / 2, y + bh + 3, bw / 2, y + bh + gap - 3, C["ink"]))
        h = 6 + n * (bh + gap) - gap + 8
    legend = f'<p class="legend"><span class="arrow">→</span> {esc(p["arrow"])}</p>'
    steps_text = "<ol>" + "".join(f"<li>{esc(s['label'])}{(' — ' + esc(s['note'])) if s.get('note') else ''}</li>" for s in steps) + "</ol>"
    return svg_wrap("".join(body), h, p["headline"]) + legend, steps_text


def t_flow(p, W, g):
    st = p["steps"]
    return flow_boxes([s["label"] for s in st], [s.get("note") for s in st], [s.get("highlight") for s in st], W, g, p["arrow"])


# ---------- groups: check, HTML, text ----------

def check_groups(p, where, errors, warnings, digest):
    groups = need_list(p, "groups", where, errors, LIMITS["groups"], warnings, "groups")
    count_highlights(groups, where, warnings)
    total = 0
    for g in groups:
        items = g.get("items") or []
        total += len(items)
        digest.append(f"    {g.get('label')}: {', '.join(map(str, items))}{'  [highlight]' if g.get('highlight') else ''}")
    if total > LIMITS["group_items"]:
        warnings.append(f"{where}: {total} items in groups; more than {LIMITS['group_items']} nodes is hard to read")


def v_groups(p):
    groups = p["groups"]
    n = len(groups)
    gap = 24
    gw = (W - gap * (n - 1)) / n
    ih, igap, pad = 46, 10, 14
    rows = max(len(g.get("items") or []) for g in groups)
    gh = 42 + rows * (ih + igap) + pad
    body = []
    for i, g in enumerate(groups):
        x = i * (gw + gap)
        hl = g.get("highlight")
        stroke = C["terracotta"] if hl else C["sand"]
        body.append(f'<rect x="{x + 1:.1f}" y="1" width="{gw - 2:.1f}" height="{gh}" fill="none" stroke="{stroke}" stroke-width="{2 if hl else 1.25}" stroke-dasharray="6 4"/>')
        body.append(text_el(x + 14, 27, wrap(str(g.get("label", "")).upper(), int(gw / 10), 1), 13, 700, C["umber"] if hl else C["muted"]))
        for j, item in enumerate(g.get("items") or []):
            body.append(node(x + pad, 42 + j * (ih + igap), gw - 2 * pad, ih, item, False, int((gw - 2 * pad) / 8.6)))
    text = "<ul>" + "".join(f"<li><b>{esc(g.get('label', ''))}</b>: {esc(', '.join(map(str, g.get('items') or [])))}</li>" for g in groups) + "</ul>"
    return svg_wrap("".join(body), gh + 4, p["headline"]), text


def t_groups(p, W, g):
    out = []
    for grp in p["groups"]:
        out += tbox([grp["label"].upper()] + [f"{g['pt']} {it}" for it in grp.get("items") or []], min(W, 48), g, grp.get("highlight"))
    return out


# ---------- tree: check, HTML, text ----------

def check_tree(p, where, errors, warnings, digest):
    root = p.get("root")
    if not isinstance(root, dict) or not root.get("label"):
        errors.append(f"{where}: a tree needs 'root' with a 'label' and optional 'children'")
        return
    count = [0]
    hl = [0]

    def walk(n, depth):
        count[0] += 1
        hl[0] += 1 if n.get("highlight") else 0
        if depth > 3:
            errors.append(f"{where}: '{n.get('label')}' is deeper than 4 levels; cut the tree or split it")
            return
        kids = n.get("children") or []
        if "value" in n and not _is_num(n["value"]):
            errors.append(f"{where}: '{n.get('label')}' has a non-numeric 'value'")
        if kids and "value" in n and all(_is_num(k.get("value")) for k in kids):
            total = sum(k["value"] for k in kids)
            if abs(total - n["value"]) > 1e-9 * max(1, abs(n["value"])) and total > n["value"]:
                errors.append(f"{where}: the children of '{n['label']}' sum to {num(total)}, more than its value {num(n['value'])}")
        digest.append("    " + "  " * depth + f"{n.get('label')}{(' = ' + num(n['value'])) if _is_num(n.get('value')) else ''}"
                      + ("  [highlight]" if n.get("highlight") else ""))
        for k in kids:
            if not isinstance(k, dict) or not k.get("label"):
                errors.append(f"{where}: every node needs a 'label'")
                continue
            walk(k, depth + 1)
    walk(root, 0)
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
    colx = lambda d: 0 if d == 0 else rootw + (d - 1) * cw
    colw = lambda d: rootw if d == 0 else cw
    H = 420
    body, rows = [], []
    unit = p.get("unit", "")

    def draw(n, d, y, h, path):
        hl = n.get("highlight")
        x, w = colx(d), colw(d)
        body.append(f'<rect x="{x + 1:.1f}" y="{y + 1:.1f}" width="{w - 2:.1f}" height="{max(h - 2, 0.5):.1f}" fill="{C["terracotta"] if hl else (C["linen"] if d else C["sand"])}"/>')
        if h >= 22:
            lines = wrap(n["label"], int(w / 8), max(1, min(3, int((h - 6) / 17))))
            if _is_num(n.get("value")) and h >= 22 + 17 * len(lines):
                lines = lines + [num(n["value"]) + (f" {unit}" if unit else "")]
            body.append(text_el(x + 10, y + 19, lines, 13.5, 700 if hl else 500, C["heading"], gap=17))
        rows.append([" / ".join(path + [n["label"]]), num(val(n))])
        kids = n.get("children") or []
        tot = sum(val(k) for k in kids) or 1
        yy = y
        for k in kids:
            kh = h * val(k) / max(val(n), tot)
            draw(k, d + 1, yy, kh, path + [n["label"]])
            yy += kh
    draw(root, 0, 0, H, [])
    data = table_html(["Node", f"Value{f' ({unit})' if unit else ''}"], rows, num_cols={1})
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
    sets = need_list(p, "sets", where, errors, 6, warnings, "sets")
    regions = need_list(p, "regions", where, errors, 12, warnings, "regions")
    names = set(map(str, sets))
    for r in regions:
        ins = r.get("in") if isinstance(r, dict) else None
        if not isinstance(ins, list) or not ins or not all(str(s) in names for s in ins):
            errors.append(f"{where}: each region needs 'in', a list of set names from 'sets'")
            continue
        if not r.get("label") and "count" not in r:
            errors.append(f"{where}: region {ins} needs a 'label' or a 'count'")
        digest.append(f"    in {' & '.join(ins)}: {r.get('label', '')} {('(' + num(r['count']) + ')') if 'count' in r else ''}".rstrip()
                      + ("  [highlight]" if r.get("highlight") else ""))
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
        if hl:
            body.append(f'<rect x="{x + 1:.1f}" y="4" width="{cw - 2:.1f}" height="{top + len(sets) * rh:.1f}" fill="{C["linen"]}"/>')
        lab = wrap(r.get("label", ""), int(cw / 7.2), 3)
        body.append(text_el(x + cw / 2, 20, lab, 12.5, 700 if hl else 500, C["heading"], "middle", gap=16))
        if "count" in r:
            body.append(text_el(x + cw / 2, 20 + len(lab) * 16 + 4, [num(r["count"])], 14, 700, C["umber"] if hl else C["ink"], "middle"))
    for i, s in enumerate(sets):
        y = top + i * rh
        body.append(text_el(left - 14, y + rh / 2 + 5, wrap(s, 20, 1), 14, 600, C["heading"], "end"))
        body.append(f'<line x1="{left}" y1="{y + rh / 2:.1f}" x2="{W}" y2="{y + rh / 2:.1f}" stroke="{C["line"]}" stroke-width="1"/>')
        if not any(s in r["in"] for r in regions):
            body.append(f'<rect x="{left + 8}" y="{y + rh / 2 - 10:.1f}" width="86" height="20" fill="{C["cream"]}"/>')
            body.append(text_el(left + 12, y + rh / 2 + 5, ["none found"], 13, 600, C["umber"], italic=True))
        j = 0
        while j < n:  # merge adjacent columns into one bar
            if s in regions[order[j]]["in"]:
                start = j
                while j + 1 < n and s in regions[order[j + 1]]["in"]:
                    j += 1
                for jj in range(start, j + 1):
                    hl = regions[order[jj]].get("highlight")
                    body.append(f'<rect x="{left + jj * cw + (3 if jj == start else 0):.1f}" y="{y + rh / 2 - 7:.1f}" width="{cw - (3 if jj == start else 0) - (3 if jj == j else 0):.1f}" height="14" fill="{C["terracotta"] if hl else C["moss"]}"/>')
            j += 1
    rows = [[r.get("label", ""), " & ".join(r["in"]), num(r["count"]) if "count" in r else ""] for r in regions]
    data = table_html(["Region", "In sets", "Count"], rows, num_cols={2})
    return svg_wrap("".join(body), top + len(sets) * rh + 8, p["headline"]), data


def t_sets(p, W, g):
    sets = [str(s) for s in p["sets"]]
    regions = p["regions"]
    order = sorted(range(len(regions)), key=lambda k: [0 if s in regions[k]["in"] else 1 for s in sets])
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
        out += twrap(f"{j + 1}{'*' if r.get('highlight') else ''} {r.get('label', '')}{cnt}: in {' & '.join(r['in'])}", W)
    return out


# ---------- matrix: check, HTML, text ----------

def _label(col):
    return col.get("label", "") if isinstance(col, dict) else str(col)


def mark_svg(mark, hl):
    """A cell mark whose shape carries the meaning; colour only repeats it."""
    ring = f'<circle cx="24" cy="24" r="22.5" fill="none" stroke="{C["terracotta"]}" stroke-width="3"/>' if hl else ""
    shapes = {
        "yes": f'<circle cx="24" cy="24" r="16" fill="{C["moss"]}"/><path d="M16.5 24.5l5 5 10-11" fill="none" stroke="{C["cream"]}" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>',
        "no": f'<circle cx="24" cy="24" r="15" fill="none" stroke="{C["muted"]}" stroke-width="2"/><path d="M18.5 18.5l11 11M29.5 18.5l-11 11" stroke="{C["muted"]}" stroke-width="2.6" stroke-linecap="round"/>',
        "up": f'<path d="M24 9 L39 35 H9 Z" fill="{C["moss"]}"/>',
        "down": f'<path d="M24 39 L39 13 H9 Z" fill="{C["umber"]}"/>',
        "same": f'<circle cx="24" cy="24" r="15" fill="none" stroke="{C["sand"]}" stroke-width="2.5"/><path d="M17 20.5h14M17 27.5h14" stroke="{C["ink"]}" stroke-width="2.6" stroke-linecap="round"/>',
    }
    if mark is None:
        return f'<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M18 24h12" stroke="{C["line"]}" stroke-width="2.5" stroke-linecap="round"/>{ring}</svg>'
    return f'<svg viewBox="0 0 48 48" aria-hidden="true">{shapes[mark]}{ring}</svg>'


def check_matrix(p, where, errors, warnings, digest):
    cols = need_list(p, "columns", where, errors, LIMITS["matrix_cols"], warnings, "columns")
    rows = need_list(p, "rows", where, errors, LIMITS["matrix_rows"], warnings, "rows")
    n_hl = 0
    for r in rows:
        cells = r.get("cells") if isinstance(r, dict) else None
        if not isinstance(cells, list) or len(cells) != len(cols) or not r.get("label"):
            errors.append(f"{where}: each row needs a 'label' and one cell per column ({len(cols)})")
            continue
        out = []
        for c in cells:
            mark = c.get("mark") if isinstance(c, dict) else c
            if mark is not None and mark not in MARKS:
                errors.append(f"{where}: row '{r['label']}' has mark '{mark}'; use one of {', '.join(MARKS)}, or null")
            n_hl += 1 if isinstance(c, dict) and c.get("highlight") else 0
            out.append(mark or "–")
        n_hl += 1 if r.get("highlight") else 0
        group = f"{r['group']} / " if r.get("group") else ""
        digest.append(f"    {group}{r['label']}: " + ", ".join(f"{_label(col)}={m}" for col, m in zip(cols, out)))
    if n_hl > LIMITS["highlights"]:
        warnings.append(f"{where}: {n_hl} highlighted rows or cells; emphasis works when it marks the one or two that carry the point")
    if len(cols) == 1:
        warnings.append(f"{where}: a matrix with one column is a list of marks; use 'pairs' if each item comes in a good and a bad form, or 'effects' for a list of findings")
    measured = {}
    for r in rows:
        if isinstance(r, dict) and isinstance(r.get("cells"), list):
            key = r.get("group") or r.get("label")
            measured.setdefault(key, set()).update(k for k, c in enumerate(r["cells"]) if (c.get("mark") if isinstance(c, dict) else c))
    keys = [k for k in measured if measured[k]]
    for a in range(len(keys)):
        for b in range(a + 1, len(keys)):
            if not measured[keys[a]] & measured[keys[b]]:
                warnings.append(f"{where}: '{keys[a]}' and '{keys[b]}' share no measured column, so they measure different things; use 'effects', which names each row's outcome, or separate panels")


def v_matrix(p):
    """Rows by columns of marks, so the pattern of where effects fall is seen at once."""
    cols = [c if isinstance(c, dict) else {"label": c} for c in p["columns"]]
    words = {**MARKS, **(p.get("legend") or {})}
    blank = p.get("blank", "not measured")
    n = len(cols)
    out = [f'<div class="matrix" style="--mcols:{n}" role="table" aria-label="{esc(p["headline"])}">',
           '<div class="mrow mhead" role="row"><span role="columnheader"></span>' +
           "".join(f'<span role="columnheader" class="{"hl" if c.get("highlight") else ""}">{esc(c["label"])}</span>' for c in cols) + "</div>"]
    used, group, rows_text = [], None, []
    for r in p["rows"]:
        if r.get("group") and r["group"] != group:
            group = r["group"]
            out.append(f'<div class="mgroup" role="row"><span role="rowheader">{esc(group)}</span></div>')
        cells = []
        for c, col in zip(r["cells"], cols):
            mark = c.get("mark") if isinstance(c, dict) else c
            hl = isinstance(c, dict) and c.get("highlight")
            word = words.get(mark, blank) if mark else blank
            if mark not in used:
                used.append(mark)
            text = c.get("text") if isinstance(c, dict) and c.get("text") else ""
            cells.append(f'<span role="cell" class="mcell{" hl" if hl else ""}" title="{esc(word)}">{mark_svg(mark, hl)}'
                         f'<span class="sr">{esc(col["label"])}: {esc(word)}</span>'
                         f'{f"<small>{esc(text)}</small>" if text else ""}</span>')
        out.append(f'<div class="mrow{" hl" if r.get("highlight") else ""}" role="row"><span role="rowheader" class="mlab">{esc(r["label"])}</span>{"".join(cells)}</div>')
        rows_text.append([(f"{r['group']}: " if r.get("group") else "") + r["label"]] +
                         [words.get(c.get("mark") if isinstance(c, dict) else c, blank) if (c.get("mark") if isinstance(c, dict) else c) else blank for c in r["cells"]])
    out.append("</div>")
    legend = "".join(f'<span>{mark_svg(m, False)}{esc(words.get(m, blank) if m else blank)}</span>' for m in [m for m in MARKS if m in used] + ([None] if None in used else []))
    out.append(f'<p class="mlegend">{legend}</p>')
    return "".join(out), table_html([""] + [c["label"] for c in cols], rows_text)


def t_matrix(p, W, g):
    cols = [c if isinstance(c, dict) else {"label": c} for c in p["columns"]]
    sym = {"yes": g["yes"], "no": g["no"], "up": g["up"], "down": g["dn"], "same": g["same"], None: g["blank"]}
    words = {"yes": "yes", "no": "no", "up": "higher", "down": "lower", "same": "no difference", **(p.get("legend") or {})}
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
            m = c.get("mark") if isinstance(c, dict) else c
            used.append(m)
            s = sym[m]
            if isinstance(c, dict) and c.get("highlight"):
                s = f"[{s}]"
            cells.append(s.center(cw))
        mark = g["hl"] if r.get("highlight") else " "
        out.append(f"{mark}{tcut(r['label'], lw - 2):<{lw - 1}}" + "".join(cells))
    legend = [f"{sym[m]} {words.get(m, p.get('blank', 'not measured')) if m else p.get('blank', 'not measured')}"
              for m in ["yes", "no", "up", "down", "same", None] if m in used]
    out += [""] + twrap("   ".join(legend), W)
    return out


# ---------- effects and pairs: shared mark ----------

EFFECTS = ("up", "down", "same")
EFFECT_WORDS = {"up": "raises", "down": "lowers", "same": "no clear effect"}


def mark_shape(cx, cy, m):
    """An effect mark inside an SVG: the shape carries the meaning, colour only repeats it."""
    if m == "up":
        return f'<path d="M{cx:.1f} {cy - 12:.1f} L{cx + 13:.1f} {cy + 10:.1f} H{cx - 13:.1f} Z" fill="{C["moss"]}"/>'
    if m == "down":
        return f'<path d="M{cx:.1f} {cy + 12:.1f} L{cx + 13:.1f} {cy - 10:.1f} H{cx - 13:.1f} Z" fill="{C["umber"]}"/>'
    return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="11" fill="none" stroke="{C["sand"]}" stroke-width="2.5"/>'
            f'<path d="M{cx - 5.5:.1f} {cy - 3:.1f}h11M{cx - 5.5:.1f} {cy + 3:.1f}h11" stroke="{C["ink"]}" stroke-width="2.2"/>')


def effect_legend(used, g=None):
    marks = {"up": "▲", "down": "▼", "same": "="} if g is None else {"up": g["up"], "down": g["dn"], "same": g["same"]}
    return "   ".join(f"{marks[m]} {EFFECT_WORDS[m]}" for m in EFFECTS if m in used)


# ---------- effects: check, HTML, text ----------

def check_effects(p, where, errors, warnings, digest):
    rows = need_list(p, "rows", where, errors, 12, warnings, "findings")
    count_highlights(rows, where, warnings)
    for r in rows:
        if not isinstance(r, dict) or not r.get("label") or r.get("effect") not in EFFECTS:
            errors.append(f"{where}: each row needs a 'label' and an 'effect' of {', '.join(EFFECTS)}")
            continue
        g = f"{r['group']} / " if r.get("group") else ""
        digest.append(f"    {g}{r['label']}{(' on ' + r['outcome']) if r.get('outcome') else ''}: {EFFECT_WORDS[r['effect']]}"
                      + ("  [highlight]" if r.get("highlight") else ""))
    if rows and not any(isinstance(r, dict) and r.get("outcome") for r in rows):
        warnings.append(f"{where}: no row names its 'outcome'; when every finding has the same outcome and each item comes in a good and a bad form, use 'pairs'")


def v_effects(p):
    """One row per finding, its mark placed in a lowers / no clear effect / raises column; each row names its outcome."""
    rows = p["rows"]
    heads = p.get("columns") or ["Lowers", "No clear effect", "Raises"]
    left = 360
    zw = (W - left) / 3
    zone = {"down": 0, "same": 1, "up": 2}
    body = [f'<rect x="{left + zw:.1f}" y="0" width="{zw:.1f}" height="__H__" fill="{C["linen"]}"/>']
    for k, h in enumerate(heads):
        body.append(text_el(left + zw * k + zw / 2, 20, [h.upper()], 12, 700, C["muted"], "middle"))
    y, group = 40, None
    for r in rows:
        if r.get("group") and r["group"] != group:
            group = r["group"]
            y += 22
            body.append(text_el(0, y, [group.upper()], 12.5, 700, C["umber"]))
            y += 8
        hl = r.get("highlight")
        lab = wrap(r["label"], 40, 2)
        out = wrap("on " + r["outcome"], 46, 2) if r.get("outcome") else []
        rh = 14 + 19 * len(lab) + 16 * len(out)
        body.append(text_el(0, y + 18, lab, 16, 700 if hl else 600, C["heading"], gap=19))
        if out:
            body.append(text_el(0, y + 18 + 19 * len(lab) - 2, out, 13, 500, C["muted"], italic=True, gap=16))
        body.append(mark_shape(left + zw * zone[r["effect"]] + zw / 2, y + rh / 2, r["effect"]))
        body.append(f'<line x1="0" y1="{y + rh:.1f}" x2="{W}" y2="{y + rh:.1f}" stroke="{C["line"]}"/>')
        y += rh
    H = y + 8
    text = "<ul>" + "".join(f"<li>{esc(r.get('group', ''))}{': ' if r.get('group') else ''}{esc(r['label'])}"
                            f"{(' on ' + esc(r['outcome'])) if r.get('outcome') else ''}: {EFFECT_WORDS[r['effect']]}</li>" for r in rows) + "</ul>"
    return svg_wrap("".join(body).replace("__H__", f"{H:.0f}"), H, p["headline"]), text


def t_effects(p, W, g):
    heads = p.get("columns") or ["Lowers", "No clear effect", "Raises"]
    sym = {"up": g["up"], "down": g["dn"], "same": g["same"]}
    zone = {"down": 0, "same": 1, "up": 2}
    cw = 10
    lw = max(W - 3 * cw - 2, 20)
    hl = [twrap(h, cw - 1) for h in heads]
    out = [" " * (lw + 1) + "".join((h[k] if k < len(h) else "").center(cw) for h in hl) for k in range(max(map(len, hl)))]
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
        out += [f" {l}" for l in lines[1:]]
    return out + ["", effect_legend({r["effect"] for r in p["rows"]}, g)]


# ---------- pairs: check, HTML, text ----------

def check_pairs(p, where, errors, warnings, digest):
    heads = p.get("columns")
    if not (isinstance(heads, list) and len(heads) == 2):
        errors.append(f"{where}: 'columns' needs two headings, such as [\"Helps when\", \"Hurts or no gain when\"]")
    else:
        digest.append(f"    columns: {heads[0]} | {heads[1]}")
    rows = need_list(p, "rows", where, errors, 7, warnings, "items")
    count_highlights(rows, where, warnings)
    for r in rows:
        if not isinstance(r, dict) or not r.get("label"):
            errors.append(f"{where}: each row needs a 'label'")
            continue
        for side in ("left", "right"):
            for c in r.get(side) or []:
                if not isinstance(c, dict) or not c.get("label") or c.get("effect") not in EFFECTS + (None,):
                    errors.append(f"{where}: '{r['label']}': each entry in '{side}' needs a 'label', and an optional 'effect' of {', '.join(EFFECTS)}")
        if not (r.get("left") or r.get("right")):
            errors.append(f"{where}: '{r['label']}' has nothing in 'left' or 'right'")
        digest.append(f"    {r['label']}: " + " | ".join(
            ", ".join(f"{c.get('label')}{(' [' + EFFECT_WORDS.get(c.get('effect'), '') + ']') if c.get('effect') else ''}" for c in r.get(side) or [] if isinstance(c, dict)) or "–"
            for side in ("left", "right")))


def v_pairs(p):
    """One row per item, its two contrasting forms side by side."""
    heads = p["columns"]
    left = 240
    cw = (W - left) / 2
    body = [text_el(left + 40, 20, [heads[0].upper()], 12, 700, C["muted"]), text_el(left + cw + 40, 20, [heads[1].upper()], 12, 700, C["muted"]),
            f'<line x1="0" y1="32" x2="{W}" y2="32" stroke="{C["line"]}" stroke-width="2"/>']
    y = 40
    for r in p["rows"]:
        hl = r.get("highlight")
        sides = [r.get("left") or [], r.get("right") or []]
        lines = [[wrap(c["label"], int((cw - 50) / 8), 2) for c in s] for s in sides]
        heights = [sum(10 + 19 * len(l) for l in s) for s in lines]
        lab = wrap(r["label"], 24, 3)
        rh = max(heights + [19 * len(lab)]) + 16
        body.append(text_el(0, y + 26, lab, 16, 700, C["heading"] if not hl else C["umber"], gap=19))
        for k, (s, ls) in enumerate(zip(sides, lines)):
            yy = y + 8
            x = left + cw * k
            for c, l in zip(s, ls):
                h = 10 + 19 * len(l)
                if c.get("effect"):
                    body.append(mark_shape(x + 16, yy + h / 2, c["effect"]))
                body.append(text_el(x + 40, yy + 18, l, 15, 600 if hl else 500, C["ink"], gap=19))
                yy += h
        body.append(f'<line x1="0" y1="{y + rh:.1f}" x2="{W}" y2="{y + rh:.1f}" stroke="{C["line"]}"/>')
        y += rh
    text = table_html(["", heads[0], heads[1]], [[r["label"]] + ["; ".join(c["label"] + (f" ({EFFECT_WORDS[c['effect']]})" if c.get("effect") else "") for c in r.get(s) or []) or "–"
                                                   for s in ("left", "right")] for r in p["rows"]])
    return svg_wrap("".join(body), y + 6, p["headline"]), text


def t_pairs(p, W, g):
    heads = p["columns"]
    sym = {"up": g["up"], "down": g["dn"], "same": g["same"], None: " "}
    lw = 18
    cw = (W - lw - 2) // 2
    ha, hb = twrap(heads[0].upper(), cw - 2), twrap(heads[1].upper(), cw - 2)
    out = [" " * lw + "  " + (ha[k] if k < len(ha) else "").ljust(cw) + (hb[k] if k < len(hb) else "") for k in range(max(len(ha), len(hb)))]
    out = [l.rstrip() for l in out] + [g["h"] * W]
    used = set()
    for r in p["rows"]:
        cols = []
        for s in (r.get("left") or [], r.get("right") or []):
            lines = []
            for c in s:
                used.add(c.get("effect"))
                w = twrap(c["label"], cw - 4)
                lines.append(f"{sym[c.get('effect')]} {w[0]}")
                lines += [f"  {l}" for l in w[1:]]
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
    items = need_list(p, "items", where, errors, 10, warnings, "items")
    count_highlights(items, where, warnings)
    for ax in ("x", "y"):
        a = p.get(ax)
        if not isinstance(a, dict) or not a.get("label") or not a.get("low") or not a.get("high"):
            errors.append(f"{where}: '{ax}' needs 'label', 'low' and 'high', such as {{\"label\": \"Effort\", \"low\": \"small\", \"high\": \"large\"}}")
    if not p.get("basis"):
        errors.append(f"{where}: a quadrant needs 'basis': where the positions come from (measured values, or the document's own judgment)")
    for it in items:
        if not (_is_num(it.get("x")) and _is_num(it.get("y")) and 0 <= it["x"] <= 1 and 0 <= it["y"] <= 1):
            errors.append(f"{where}: '{it.get('label')}' needs 'x' and 'y' between 0 and 1")
            continue
        digest.append(f"    {it.get('label')}: x={it['x']}, y={it['y']}{'  [highlight]' if it.get('highlight') else ''}")
    digest.append(f"    basis: {p.get('basis')}")


def v_quadrant(p):
    """Items placed on two judged dimensions, with the four regions named."""
    left, top, pw, ph = 40, 30, W - 80, 400
    X = lambda v: left + v * pw
    Y = lambda v: top + ph - v * ph
    body = [f'<rect x="{left}" y="{top}" width="{pw}" height="{ph}" fill="none" stroke="{C["line"]}" stroke-width="1.5"/>',
            f'<line x1="{left + pw / 2}" y1="{top}" x2="{left + pw / 2}" y2="{top + ph}" stroke="{C["sand"]}" stroke-width="1.5"/>',
            f'<line x1="{left}" y1="{top + ph / 2}" x2="{left + pw}" y2="{top + ph / 2}" stroke="{C["sand"]}" stroke-width="1.5"/>']
    q = p.get("quadrants") or {}
    corners = {"top_left": (left + 12, top + 24, "start"), "top_right": (left + pw - 12, top + 24, "end"),
               "bottom_left": (left + 12, top + ph - 12, "start"), "bottom_right": (left + pw - 12, top + ph - 12, "end")}
    for k, (x, y, a) in corners.items():
        if q.get(k):
            body.append(text_el(x, y, [q[k].upper()], 12.5, 700, C["muted"], a))
    xa, ya = p["x"], p["y"]
    body.append(text_el(left, top + ph + 22, [f"← {xa['low']}"], 13, 500, C["muted"]))
    body.append(text_el(left + pw, top + ph + 22, [f"{xa['high']} →"], 13, 500, C["muted"], "end"))
    body.append(text_el(left + pw / 2, top + ph + 22, [xa["label"]], 13, 700, C["ink"], "middle"))
    body.append(f'<text x="{left - 14}" y="{top + ph / 2}" font-family="{SANS}" font-size="13" font-weight="700" fill="{C["ink"]}" text-anchor="middle" transform="rotate(-90 {left - 14} {top + ph / 2})">{esc(ya["label"])}</text>')
    body.append(text_el(left - 6, top - 10, [f"↑ {ya['high']}"], 13, 500, C["muted"]))
    body.append(text_el(left - 6, top + ph + 40, [f"↓ {ya['low']}"], 13, 500, C["muted"]))
    placed = []
    for it in sorted(p["items"], key=lambda i: bool(i.get("highlight"))):
        hl = it.get("highlight")
        cx, cy = X(it["x"]), Y(it["y"])
        body.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{8 if hl else 6}" fill="{C["terracotta"] if hl else C["moss"]}"/>')
        anchor = "end" if cx > left + pw * 0.72 else "start"
        ty = cy + 5
        for (px, py) in placed:  # nudge labels that would sit on top of each other
            if abs(px - cx) < 160 and abs(py - ty) < 18:
                ty = py + 18
        placed.append((cx, ty))
        body.append(text_el(cx + (-13 if anchor == "end" else 13), ty, wrap(it["label"], 26, 1), 14, 700 if hl else 500, C["heading"], anchor))
    rows = [[it["label"], f"{it['x']:.2f}", f"{it['y']:.2f}"] for it in p["items"]]
    data = f"<p>{esc(p['basis'])}</p>" + table_html(["Item", xa["label"] + " (0–1)", ya["label"] + " (0–1)"], rows, num_cols={1, 2})
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
        for l, r in zip(L, R):
            out.append(f" {l:<{half}}{g['v']} {r}")
        if a == "top_left":
            out.append(" " + g["h"] * half + g["cross"] + g["h"] * half)
    out.append(f"{g['dn']} {ya['low']}")
    out.append(f"{xa['label']}: {xa['low']} (left) {g['arrow']} {xa['high']} (right)")
    out += twrap(f"Positions: {p['basis']}", W)
    return out


# ---------- numbers: check, HTML, text ----------

def check_numbers(p, where, errors, warnings, digest):
    items = need_list(p, "figures", where, errors, LIMITS["numbers"], warnings, "figures")
    for it in items:
        if "value" not in it or "label" not in it:
            errors.append(f"{where}: each figure needs 'value' and 'label'")
            continue
        digest.append(f"    {it['value']} — {it['label']}")


def v_numbers(p):
    cells = "".join(
        f'<div class="fig{" hl" if it.get("highlight") else ""}"><div class="val">{esc(it["value"])}</div>'
        f'<div class="lab">{esc(it["label"])}</div></div>' for it in p["figures"])
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
    parts = need_list(p, "parts", where, errors, LIMITS["unit_parts"], warnings, "parts")
    count_highlights(parts, where, warnings)
    total = 0
    for it in parts:
        n = it.get("count") if isinstance(it, dict) else None
        if not isinstance(n, int) or isinstance(n, bool) or n < 1 or not it.get("label"):
            errors.append(f"{where}: each part needs a 'label' and a whole-number 'count' of at least 1")
            continue
        total += n
        digest.append(f"    {n} {it['label']}{'  [highlight]' if it.get('highlight') else ''}")
    if total > LIMITS["units"]:
        errors.append(f"{where}: {total} units; above {LIMITS['units']} the marks cannot be counted, so use 'bars' or 'numbers'")
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
    size = min(72, (W - gap * (cols - 1)) / cols)
    # Fill and shape both mark the part, so colour is not the only signal: highlighted parts are solid
    # terracotta, the others solid moss, then outlined.
    styles, plain = [], [("moss", None), (None, "muted"), ("linen", "sand")]
    for it in parts:
        styles.append(("terracotta", None) if it.get("highlight") else plain.pop(0) if plain else ("linen", "sand"))
    body, k, spans = [], 0, []
    for it, (fill, stroke) in zip(parts, styles):
        start = k
        for _ in range(it["count"]):
            r, c = divmod(k, cols)
            x, y = c * (size + gap), r * (size + gap)
            attrs = f'fill="{C[fill]}"' if fill else 'fill="none"'
            if stroke:
                attrs += f' stroke="{C[stroke]}" stroke-width="2"'
            inset = 1 if stroke else 0
            body.append(f'<rect x="{x + inset:.1f}" y="{y + inset:.1f}" width="{size - 2 * inset:.1f}" height="{size - 2 * inset:.1f}" rx="3" {attrs}/>')
            k += 1
        spans.append((start, k - 1, it))
    h = nrows * (size + gap) - gap
    if nrows == 1:  # label each part under its own marks
        y = h + 18
        for a, b, it in spans:
            x1, x2 = a * (size + gap), b * (size + gap) + size
            body.append(f'<path d="M{x1 + 1:.1f} {y - 8} V{y} H{x2 - 1:.1f} V{y - 8}" fill="none" stroke="{C["ink"]}" stroke-width="1.25"/>')
            hl = it.get("highlight")
            mid = (x1 + x2) / 2
            lines = wrap(f'{it["count"]} {it["label"]}', max(int((x2 - x1) / 8.5), 10), 3)
            half = max(len(l) for l in lines) * 4.6
            mid = min(max(mid, half), W - half)
            body.append(text_el(mid, y + 24, lines, 17, 700 if hl else 500, C["heading"], "middle", gap=21))
        h = y + 24 + 21 * max(len(wrap(f'{it["count"]} {it["label"]}', max(int(((b - a + 1) * (size + gap) - gap) / 8.5), 10), 3)) for a, b, it in spans)
    else:  # a legend below the grid
        y = h + 28
        for (fill, stroke), it in zip(styles, parts):
            attrs = (f'fill="{C[fill]}"' if fill else 'fill="none"') + (f' stroke="{C[stroke]}" stroke-width="2"' if stroke else "")
            body.append(f'<rect x="1" y="{y - 15}" width="18" height="18" rx="2" {attrs}/>')
            body.append(text_el(30, y, [f'{it["count"]} {it["label"]}'], 17, 700 if it.get("highlight") else 500, C["heading"]))
            y += 28
        h = y - 10
    if unit:
        body.append(text_el(W, h + 26, [f"Each mark is one of {total} {unit}"], 14, 500, C["muted"], "end"))
        h += 34
    data = table_html(["Part", f"Count{f' ({unit})' if unit else ''}"], [[it["label"], it["count"]] for it in parts] + [["Total", total]], num_cols={1})
    return svg_wrap("".join(body), h + 4, p["headline"]), data


def t_units(p, W, g):
    marks = []
    plain = [g["box2"], g["box3"]]
    for it in p["parts"]:
        marks.append(g["box"] if it.get("highlight") else (plain.pop(0) if plain else g["box3"]))
    total = sum(it["count"] for it in p["parts"])
    per_row = 20 if total > 20 else total
    cells = "".join(m * it["count"] for m, it in zip(marks, p["parts"]))
    out = [" ".join(cells[i:i + per_row]) for i in range(0, len(cells), per_row)]
    out.append("")
    for m, it in zip(marks, p["parts"]):
        out += twrap(f"{m} {it['count']} {it['label']}", W)
    if p.get("unit"):
        out.append(f"Each mark is one of {total} {p['unit']}.")
    return out


# ---------- bars: check, HTML, text ----------

def check_bars(p, where, errors, warnings, digest):
    items = need_list(p, "items", where, errors, LIMITS["bars"], warnings, "bars")
    count_highlights(items, where, warnings)
    unit = p.get("unit", "")
    for it in items:
        v = it.get("value")
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            errors.append(f"{where}: bar '{it.get('label')}' needs a numeric 'value'")
            continue
        if v < 0:
            errors.append(f"{where}: bar '{it.get('label')}' is negative; bars start at zero, so use a table or an 'svg' panel")
        digest.append(f"    {it.get('label')}: {num(v)}{(' ' + unit) if unit else ''}{'  [highlight]' if it.get('highlight') else ''}")
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
        rows.append(f'<div class="brow{hl}"><div class="blab">{esc(it["label"])}</div>'
                    f'<div class="btrack"><div class="bar" style="width:{pct:.2f}%"></div>'
                    f'<span class="bval" style="left:calc({pct:.2f}% + 10px)">{esc(num(it["value"]))}{f" <small>{esc(unit)}</small>" if unit else ""}</span></div></div>')
    valw = max(len(num(it["value"])) for it in items) * 0.85 + len(unit) * 0.5 + 1.2
    chart = f'<div class="bars" style="--valw:{valw:.1f}em" role="img" aria-label="{esc(p["headline"])}">{"".join(rows)}</div>'
    data = table_html(["Item", f"Value{f' ({unit})' if unit else ''}"], [[it["label"], num(it["value"])] for it in items], num_cols={1})
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
            out.append(f"{mark}{tcut(it['label'], lw):>{lw}} {g['bar'] * n}{' ' * (room - n)} {tfmt(it['value']):>{vw}}")
    if stacked:
        lw = -1
    if unit:
        out.append(f"{'':>{lw + 1}} Unit: {unit}. Bars start at zero.")
    return out


# ---------- slope: check, HTML, text ----------

def check_slope(p, where, errors, warnings, digest):
    items = need_list(p, "items", where, errors, 10, warnings, "lines")
    count_highlights(items, where, warnings)
    for k in ("from", "to"):
        if not p.get(k):
            errors.append(f"{where}: a slope needs '{k}', the label of the {'first' if k == 'from' else 'second'} state, such as '2020'")
    unit = p.get("unit", "")
    for it in items:
        if not _is_num(it.get("before")) or not _is_num(it.get("after")):
            errors.append(f"{where}: '{it.get('label')}' needs numeric 'before' and 'after'")
            continue
        digest.append(f"    {it.get('label')}: {num(it['before'])} → {num(it['after'])} {unit}".rstrip() + ("  [highlight]" if it.get("highlight") else ""))
    if p.get("y_from_zero") is False and not p.get("y_note"):
        errors.append(f"{where}: 'y_from_zero' is false, so add 'y_note' stating where the scale starts and why")
    if not unit:
        warnings.append(f"{where}: no 'unit'; say what the values measure")


def v_slope(p):
    """Each item's change between two states, one line per item."""
    items = sorted(p["items"], key=lambda it: bool(it.get("highlight")))
    unit = p.get("unit", "")
    vals = [v for it in items for v in (it["before"], it["after"])]
    lo = min(vals) if p.get("y_from_zero") is False else min(0, min(vals))
    hi = max(vals)
    top, ph = 44, 300
    x1, x2 = 250, W - 250
    Y = lambda v: top + ph - (v - lo) / ((hi - lo) or 1) * ph
    body = [text_el(x1, 18, [str(p["from"])], 14, 700, C["muted"], "middle"), text_el(x2, 18, [str(p["to"])], 14, 700, C["muted"], "middle"),
            f'<line x1="{x1}" y1="{top - 10}" x2="{x1}" y2="{top + ph + 8}" stroke="{C["line"]}" stroke-width="1.5"/>',
            f'<line x1="{x2}" y1="{top - 10}" x2="{x2}" y2="{top + ph + 8}" stroke="{C["line"]}" stroke-width="1.5"/>']

    def spread(ys):  # keep labels on one side from overlapping
        order = sorted(range(len(ys)), key=lambda k: ys[k])
        out = list(ys)
        for a, b in zip(order, order[1:]):
            out[b] = max(out[b], out[a] + 20)
        return out
    ly = spread([Y(it["before"]) for it in items])
    ry = spread([Y(it["after"]) for it in items])
    for k, it in enumerate(items):
        hl = it.get("highlight") or len(items) == 1
        color = C["terracotta"] if hl else C["muted"]
        body.append(f'<line x1="{x1}" y1="{Y(it["before"]):.1f}" x2="{x2}" y2="{Y(it["after"]):.1f}" stroke="{color}" stroke-width="{3 if hl else 1.75}"/>')
        for x, v in ((x1, it["before"]), (x2, it["after"])):
            body.append(f'<circle cx="{x}" cy="{Y(v):.1f}" r="{5 if hl else 4}" fill="{color}"/>')
        weight, fill = (700, C["heading"]) if hl else (500, C["ink"])
        body.append(text_el(x1 - 12, ly[k] + 5, [f'{wrap(it["label"], 22, 1)[0]}  {num(it["before"])}'], 14, weight, fill, "end"))
        body.append(text_el(x2 + 12, ry[k] + 5, [f'{num(it["after"])}  {wrap(it["label"], 22, 1)[0]}'], 14, weight, fill))
    h = max([top + ph + 16] + [y + 12 for y in ly + ry])
    if unit:
        body.append(text_el(W / 2, 18, [unit], 13, 500, C["muted"], "middle"))
    if p.get("y_note"):
        body.append(text_el(W / 2, h + 14, [p["y_note"]], 13, 600, C["umber"], "middle"))
        h += 24
    data = table_html(["Item", f"{p['from']}", f"{p['to']}"], [[it["label"], num(it["before"]), num(it["after"])] for it in p["items"]], num_cols={1, 2})
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
        out.append(f"{mark}{tcut(it['label'], lw):<{lw}} {tfmt(it['before']):>8} {g['arrow']}  {tfmt(it['after']):<8}  {sign} {'+' if d > 0 else ''}{tfmt(d)}")
    if unit:
        out.append(f"Values in {unit}.")
    return out


# ---------- dots: check, HTML, text ----------

def check_dots(p, where, errors, warnings, digest):
    groups = need_list(p, "groups", where, errors, 6, warnings, "groups")
    count_highlights(groups, where, warnings)
    for g in groups:
        vals = g.get("values") if isinstance(g, dict) else None
        if not isinstance(vals, list) or not vals or not all(_is_num(v) for v in vals):
            errors.append(f"{where}: group '{g.get('label') if isinstance(g, dict) else g}' needs a non-empty list of numeric 'values'")
            continue
        s = sorted(vals)
        med = s[len(s) // 2] if len(s) % 2 else (s[len(s) // 2 - 1] + s[len(s) // 2]) / 2
        digest.append(f"    {g.get('label')}: n={len(vals)}, min {num(s[0])}, median {num(med)}, max {num(s[-1])}"
                      + ("  [highlight]" if g.get("highlight") else ""))
    if not p.get("unit"):
        warnings.append(f"{where}: no 'unit'; say what the values measure")


def v_dots(p):
    """Every value as a dot, stacked where values are close, so the spread is visible."""
    groups, unit = p["groups"], p.get("unit", "")
    allv = [v for g in groups for v in g["values"]]
    ticks = nice_ticks(min(allv) if p.get("x_from_zero") is False else min(0, min(allv)), max(allv), 5)
    lo, hi = ticks[0], ticks[-1]
    left, right = 170, 20
    pw = W - left - right
    X = lambda v: left + (v - lo) / ((hi - lo) or 1) * pw
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
    for g, bins in zip(groups, stacks):
        hl = g.get("highlight")
        base = y + rh - 18
        body.append(f'<line x1="{left}" y1="{base + r + 2:.1f}" x2="{left + pw}" y2="{base + r + 2:.1f}" stroke="{C["line"]}" stroke-width="1"/>')
        body.append(text_el(left - 14, base - 4, wrap(g["label"], 20, 2), 14, 700 if hl else 500, C["heading"] if hl else C["ink"], "end", gap=17))
        for b, vs in bins.items():
            cx = left + (b + 0.5) * bw
            for j in range(len(vs)):
                body.append(f'<circle cx="{cx:.1f}" cy="{base - j * 2 * r:.1f}" r="{r:.1f}" fill="{C["terracotta"] if hl else C["moss"]}"/>')
        if p.get("marker", "median") == "median":
            s = sorted(g["values"])
            med = s[len(s) // 2] if len(s) % 2 else (s[len(s) // 2 - 1] + s[len(s) // 2]) / 2
            mx = X(med)
            body.append(f'<line x1="{mx:.1f}" y1="{y + 4}" x2="{mx:.1f}" y2="{base + r + 8:.1f}" stroke="{C["ink"]}" stroke-width="1.5" stroke-dasharray="3 3"/>')
            body.append(text_el(mx + 6, y + 14, [f"median {num(med)}"], 12.5, 600, C["ink"]))
        y += rh
    for t in ticks:
        body.append(text_el(X(t), y + 16, [num(t)], 13, 500, C["muted"], "middle"))
    if unit:
        body.append(text_el(left + pw, y + 38, [unit], 13, 600, C["muted"], "end"))
    rows = [[g["label"], len(g["values"]), num(min(g["values"])), num(max(g["values"]))] for g in groups]
    data = table_html(["Group", "n", "Min", "Max"], rows, num_cols={1, 2, 3})
    return svg_wrap("".join(body), y + 46, p["headline"]), data


def t_dots(p, W, g):
    groups = p["groups"]
    allv = [v for grp in groups for v in grp["values"]]
    lo = min(allv) if p.get("x_from_zero") is False else min(0, min(allv))
    hi = max(allv)
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
    pts = need_list(p, "points", where, errors, 200, warnings, "points")
    for k in ("x_label", "y_label"):
        if not p.get(k):
            errors.append(f"{where}: a scatter needs '{k}' naming what the axis measures")
    bad = [pt for pt in pts if not (isinstance(pt, dict) and _is_num(pt.get("x")) and _is_num(pt.get("y")))]
    if bad:
        errors.append(f"{where}: {len(bad)} point(s) lack numeric 'x' and 'y'")
    labelled = [pt for pt in pts if isinstance(pt, dict) and pt.get("label")]
    if len(labelled) > 8:
        warnings.append(f"{where}: {len(labelled)} labelled points; label only the few the headline is about")
    count_highlights(pts, where, warnings)
    digest.append(f"    {len(pts)} points; x = {p.get('x_label')}, y = {p.get('y_label')}")
    for pt in labelled:
        digest.append(f"    {pt['label']}: x={num(pt['x'])}, y={num(pt['y'])}{'  [highlight]' if pt.get('highlight') else ''}")


def v_scatter(p):
    pts = p["points"]
    xs, ys = [pt["x"] for pt in pts], [pt["y"] for pt in pts]
    xt = nice_ticks(min(xs) if p.get("x_from_zero") is False else min(0, min(xs)), max(xs), 5)
    yt = nice_ticks(min(ys) if p.get("y_from_zero") is False else min(0, min(ys)), max(ys), 4)
    left, top, pw, ph = 64, 40, W - 64 - 30, 360
    X = lambda v: left + (v - xt[0]) / ((xt[-1] - xt[0]) or 1) * pw
    Y = lambda v: top + ph - (v - yt[0]) / ((yt[-1] - yt[0]) or 1) * ph
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
        body.append(f'<circle cx="{X(pt["x"]):.1f}" cy="{Y(pt["y"]):.1f}" r="{7 if hl else 5}" fill="{C["terracotta"] if hl else C["moss"]}" fill-opacity="{1 if hl else 0.75}"/>')
        if pt.get("label"):
            anchor = "end" if X(pt["x"]) > left + pw * 0.75 else "start"
            body.append(text_el(X(pt["x"]) + (-11 if anchor == "end" else 11), Y(pt["y"]) + 5, [pt["label"]], 14, 700 if hl else 500, C["heading"], anchor))
    data = table_html(["Point", p["x_label"], p["y_label"]], [[pt.get("label", ""), num(pt["x"]), num(pt["y"])] for pt in pts], num_cols={1, 2})
    return svg_wrap("".join(body), top + ph + 56, p["headline"]), data


def t_scatter(p, W, g):
    pts = p["points"]
    xs, ys = [q["x"] for q in pts], [q["y"] for q in pts]
    x0 = min(xs) if p.get("x_from_zero") is False else min(0, min(xs))
    y0 = min(ys) if p.get("y_from_zero") is False else min(0, min(ys))
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
    series = need_list(p, "series", where, errors, LIMITS["series"], warnings, "series")
    count_highlights(series, where, warnings)
    for s in series:
        pts = s.get("points")
        if not isinstance(pts, list) or len(pts) < 2:
            errors.append(f"{where}: series '{s.get('name')}' needs at least 2 points as [x, y] pairs")
            continue
        ys = [pt[1] for pt in pts]
        if not all(isinstance(y, (int, float)) and not isinstance(y, bool) for y in ys):
            errors.append(f"{where}: series '{s.get('name')}' has non-numeric y values")
            continue
        digest.append(f"    {s.get('name')}: " + ", ".join(f"{x}={num(y)}" for x, y in pts))
    if p.get("y_from_zero") is False and not p.get("y_note"):
        errors.append(f"{where}: 'y_from_zero' is false, so add 'y_note' stating where the axis starts and why")
    if not p.get("unit"):
        warnings.append(f"{where}: no 'unit'; say what the values measure")


def v_line(p):
    series = p["series"]
    xs_all = [pt[0] for s in series for pt in s["points"]]
    numeric = all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in xs_all)
    if numeric:
        xlo, xhi = min(xs_all), max(xs_all)
        xpos = lambda x: (x - xlo) / ((xhi - xlo) or 1)
        xticks = sorted(set(xs_all)) if len(set(xs_all)) <= 8 else nice_ticks(xlo, xhi, 5)
    else:
        order = list(dict.fromkeys(xs_all))
        xpos = lambda x: order.index(x) / ((len(order) - 1) or 1)
        xticks = order
    ys = [pt[1] for s in series for pt in s["points"]]
    lo = min(ys) if p.get("y_from_zero") is False else min(0, min(ys))
    ticks = nice_ticks(lo, max(ys), 4)
    ylo, yhi = ticks[0], ticks[-1]
    unit = p.get("unit", "")
    left, right, top, plot_h = 56, 190, 30, 260
    plot_w = W - left - right
    X = lambda x: left + xpos(x) * plot_w
    Y = lambda y: top + plot_h - (y - ylo) / ((yhi - ylo) or 1) * plot_h
    body = []
    for t in ticks:
        body.append(f'<line x1="{left}" y1="{Y(t):.1f}" x2="{left + plot_w}" y2="{Y(t):.1f}" stroke="{C["line"]}" stroke-width="1"/>')
        body.append(text_el(left - 10, Y(t) + 5, [num(t)], 13, 500, C["muted"], "end"))
    step = max(1, math.ceil(len(xticks) / 8))
    for x in xticks[::step]:
        body.append(text_el(X(x), top + plot_h + 22, [num(x) if numeric else str(x)], 13, 500, C["muted"], "middle"))
    if unit:
        body.append(text_el(0, top - 8, [unit], 13, 600, C["muted"]))
    ends = []
    for s in sorted(series, key=lambda s: bool(s.get("highlight"))):
        hl = s.get("highlight") or len(series) == 1
        color = C["terracotta"] if hl else C["muted"]
        pts = " ".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in s["points"])
        dash = "" if hl else ' stroke-dasharray="5 3"'
        body.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{3 if hl else 1.75}"{dash} stroke-linejoin="round"/>')
        lx, ly = s["points"][-1]
        body.append(f'<circle cx="{X(lx):.1f}" cy="{Y(ly):.1f}" r="{4 if hl else 3}" fill="{color}"/>')
        ends.append([Y(ly), s.get("name", ""), num(ly), hl, color])
    ends.sort()
    for i in range(1, len(ends)):  # keep end labels from overlapping
        ends[i][0] = max(ends[i][0], ends[i - 1][0] + 38)
    for y, name, val, hl, color in ends:
        body.append(text_el(left + plot_w + 12, y + 4, wrap(name, 20, 1) + [val + (f" {unit}" if unit else "")], 14,
                            700 if hl else 500, C["heading"] if hl else C["ink"], gap=17))
    for a in p.get("annotations", []):
        s = next((s for s in series if s.get("name") == a.get("series")), series[0])
        pt = next((pt for pt in s["points"] if pt[0] == a.get("x")), None)
        if pt is None:
            continue
        ax, ay = X(pt[0]), Y(pt[1])
        ty = ay - 34 if ay > top + 50 else ay + 30
        body.append(f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{ax:.1f}" y2="{ty + (8 if ty < ay else -12):.1f}" stroke="{C["ink"]}" stroke-width="1"/>')
        body.append(f'<circle cx="{ax:.1f}" cy="{ay:.1f}" r="5" fill="none" stroke="{C["ink"]}" stroke-width="1.5"/>')
        anchor = "end" if ax > left + plot_w * 0.7 else "start"
        body.append(text_el(ax + (-8 if anchor == "end" else 8), ty, wrap(a.get("text", ""), 32, 2), 13, 500, C["ink"], anchor, italic=True, gap=16))
    if p.get("y_note"):
        body.append(text_el(left, top + plot_h + 46, [p["y_note"]], 13, 600, C["umber"]))
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
    lo = min(ys) if p.get("y_from_zero") is False else min(0, min(ys))
    nw = min(max(len(s["name"]) for s in series), 22)
    out = []
    for s in series:
        vals = [pt[1] for pt in s["points"]]
        mark = g["hl"] if s.get("highlight") else " "
        out.append(f"{mark}{tcut(s['name'], nw):<{nw}}  {spark(vals, g, lo, max(ys))}  {tfmt(vals[0])} {g['arrow']} {tfmt(vals[-1])} {unit}".rstrip())
    xs = [pt[0] for pt in series[0]["points"]]
    out.append(f" {'':<{nw}}  {tfmt(xs[0])} … {tfmt(xs[-1])}" + (f"  ({p['x_label']})" if p.get("x_label") else ""))
    for a in p.get("annotations", []):
        out += twrap(f"{g['pt']} at {a.get('x')}: {a.get('text')}", W)
    if p.get("y_note"):
        out += twrap(p["y_note"], W)
    return out


# ---------- timeline: check, HTML, text ----------

def check_timeline(p, where, errors, warnings, digest):
    events = need_list(p, "events", where, errors, LIMITS["timeline"], warnings, "events")
    count_highlights(events, where, warnings)
    for e in events:
        if not e.get("date") or not e.get("label"):
            errors.append(f"{where}: every event needs 'date' and 'label'")
        digest.append(f"    {e.get('date')}: {e.get('label')}{'  [highlight]' if e.get('highlight') else ''}")


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
    body = [f'<line x1="20" y1="{axis_y}" x2="{W - 20}" y2="{axis_y}" stroke="{C["ink"]}" stroke-width="1.5"/>']
    for i, e in enumerate(events):
        x = pad + (span * i / (n - 1) if n > 1 else span / 2)
        hl = e.get("highlight")
        up = i % 2 == 0
        color = C["terracotta"] if hl else C["moss"]
        body.append(f'<circle cx="{x:.1f}" cy="{axis_y}" r="{8 if hl else 6}" fill="{color}"/>')
        body.append(f'<line x1="{x:.1f}" y1="{axis_y + (-10 if up else 10)}" x2="{x:.1f}" y2="{axis_y + (-24 if up else 24)}" stroke="{C["line"]}" stroke-width="1"/>')
        lines = wrap(e["label"], chars, 3)
        half = max(len(l) for l in lines + [str(e["date"])]) * 4.3
        tx = min(max(x, half + 2), W - half - 2)  # keep the label inside the frame
        if up:
            y0 = axis_y - 30 - len(lines) * 18
            body.append(text_el(tx, y0, [str(e["date"])], 14, 700, C["umber"], "middle"))
            body.append(text_el(tx, y0 + 19, lines, 14, 700 if hl else 500, C["heading"], "middle", gap=18))
        else:
            body.append(text_el(tx, axis_y + 44, [str(e["date"])], 14, 700, C["umber"], "middle"))
            body.append(text_el(tx, axis_y + 63, lines, 14, 700 if hl else 500, C["heading"], "middle", gap=18))
    text = "<ul>" + "".join(f"<li><b>{esc(e['date'])}</b>: {esc(e['label'])}</li>" for e in events) + "</ul>"
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
    cols = need_list(p, "columns", where, errors)
    rows = need_list(p, "rows", where, errors, LIMITS["rows"], warnings, "rows")
    for r, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != len(cols):
            errors.append(f"{where}: row {r + 1} has {len(row) if isinstance(row, list) else '?'} cells for {len(cols)} columns")
            continue
        digest.append("    " + " | ".join(str(c) for c in row))


def v_table(p):
    cols = p["columns"]
    labels, num_cols = [], set()
    for i, c in enumerate(cols):
        c = c if isinstance(c, dict) else {"label": c}
        labels.append(c["label"] + (f" ({c['unit']})" if c.get("unit") else ""))
        if c.get("align") == "right" or c.get("unit"):
            num_cols.add(i)
    rows = [[num(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v for v in row] for row in p["rows"]]
    hl = set(p.get("highlight_rows", []))
    return f'<div class="tablewrap">{table_html(labels, rows, num_cols, {i - 1 for i in hl})}</div>', ""


def t_table(p, W, g):
    cols = [c if isinstance(c, dict) else {"label": c} for c in p["columns"]]
    head = [c["label"] + (f" ({c['unit']})" if c.get("unit") else "") for c in cols]
    right = {i for i, c in enumerate(cols) if c.get("unit") or c.get("align") == "right"}
    return table_lines(head, p["rows"], W, g, right, {i - 1 for i in p.get("highlight_rows", [])})


# ---------- text: check, HTML, text ----------

def check_text(p, where, errors, warnings, digest):
    body = p.get("body")
    if isinstance(body, str):
        body = [body]
    if not body:
        errors.append(f"{where}: 'body' must be a string or a list of paragraphs")
        return
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

def check_svg(p, where, errors, warnings, digest):
    svg = str(p.get("svg", "")).strip()
    if not svg.startswith("<svg") or not svg.endswith("</svg>"):
        errors.append(f"{where}: 'svg' must be one <svg>…</svg> element")
    if "viewBox" not in svg:
        errors.append(f"{where}: the svg needs a viewBox and no fixed width or height")
    if re.search(r"<script|[\s/]on\w+\s*=|javascript:|<foreignObject|href\s*=\s*[\"']?(https?:|//)", svg, re.I):
        errors.append(f"{where}: the svg must not contain scripts, event handlers, foreignObject or external links")
    if not p.get("alt"):
        errors.append(f"{where}: an 'svg' panel needs 'alt': a description of its essential information")
    digest.append(f"    custom svg; alt: {p.get('alt', '')}")


def v_svg(p):
    svg = re.sub(r"^<svg", f'<svg role="img" aria-label="{esc(p["alt"])}"', p["svg"].strip(), count=1)
    return svg, f"<p>{esc(p['alt'])}</p>"


def t_svg(p, W, g):
    return twrap("[Diagram] " + p["alt"], W)


# ---------- registries ----------

PANEL_CHECKS = {"effects": check_effects, "pairs": check_pairs, "map": check_map, "concept": check_concept, "slope": check_slope, "dots": check_dots,
                "scatter": check_scatter, "quadrant": check_quadrant, "sets": check_sets, "tree": check_tree,
                "numbers": check_numbers, "units": check_units, "matrix": check_matrix, "bars": check_bars, "line": check_line, "table": check_table,
                "flow": check_flow, "groups": check_groups, "timeline": check_timeline, "text": check_text,
                "svg": check_svg}


VISUALS = {"effects": v_effects, "pairs": v_pairs, "map": v_map, "concept": v_concept, "slope": v_slope, "dots": v_dots, "scatter": v_scatter,
           "quadrant": v_quadrant, "sets": v_sets, "tree": v_tree, "numbers": v_numbers, "units": v_units, "matrix": v_matrix, "bars": v_bars, "line": v_line, "table": v_table, "flow": v_flow,
           "groups": v_groups, "timeline": v_timeline, "text": v_text, "svg": v_svg}


TEXT = {"effects": t_effects, "pairs": t_pairs, "numbers": t_numbers, "units": t_units, "bars": t_bars, "line": t_line, "table": t_table, "matrix": t_matrix,
        "flow": t_flow, "map": t_map, "concept": t_concept, "groups": t_groups, "timeline": t_timeline, "text": t_text,
        "svg": t_svg, "slope": t_slope, "dots": t_dots, "scatter": t_scatter, "quadrant": t_quadrant, "sets": t_sets, "tree": t_tree}


# ---------- page ----------

CSS = (HERE / "show.css").read_text(encoding="utf-8")


JS = (HERE / "show.js").read_text(encoding="utf-8")


def doc_strip(spec, p):
    """Where this panel sits in the document it introduces: the same map on every panel keeps the reader oriented."""
    doc = spec.get("document")
    if not doc or p.get("part") is None:
        return ""
    parts = set(map(str, _as_list(p["part"])))
    current = ' aria-current="true"'
    cells = "".join(f'<li class="{"on" if str(s["id"]) in parts else ""}"{current if str(s["id"]) in parts else ""}>'
                    f'{esc(s["label"])}</li>' for s in doc["sections"])
    return f'<nav class="docstrip" aria-label="Where this is in the document"><ol>{cells}</ol></nav>'


def read_next(p):
    return f'<p class="readnext"><span>Read in the document</span> {rich(p["read"])}</p>' if p.get("read") else ""


def render(spec: dict) -> str:
    panels = spec["panels"]
    sections, toc = [], []
    for i, p in enumerate(panels, 1):
        visual, data = v_map(p, spec) if p["kind"] == "map" else VISUALS[p["kind"]](p)
        if p["kind"] in ("flow", "groups", "timeline", "map", "concept", "sets", "quadrant", "tree", "effects", "pairs"):  # on narrow screens show the text version instead of a shrunken svg
            visual = f'<div class="wide">{visual}</div><div class="narrow" aria-hidden="true">{data}</div>'

        note = p.get("note")
        note_html = ""
        if note:
            paras = note if isinstance(note, list) else [note]
            note_html = '<aside class="note">' + "".join(f"<p>{rich(t)}</p>" for t in paras) + "</aside>"
        data_html = f'<details class="data"><summary>{"Data" if p["kind"] in ("bars", "line", "units", "slope", "dots", "scatter", "tree", "sets") else "As text"}</summary><div>{data}</div></details>' if data else ""
        sections.append(
            f'<section class="panel page" id="p{i}" aria-labelledby="h{i}"><div class="count">{i} of {len(panels)}</div>'
            f'{doc_strip(spec, p)}<h2 id="h{i}" tabindex="-1">{esc(p["headline"])}</h2>'
            f'<div class="body{" has-note" if note_html else ""}"><figure>{visual}{data_html}</figure>{note_html}</div>'
            f'{read_next(p)}</section>')
        toc.append(f'<li><a href="#p{i}">{esc(p["headline"])}</a></li>')
    source = f'<p class="source">{rich(spec["source"])}</p>' if spec.get("source") else ""
    summary = f'<p class="summary">{rich(spec["summary"])}</p>' if spec.get("summary") else ""
    kicker = f'<div class="kicker">{esc(spec["kicker"])}</div>' if spec.get("kicker") else ""
    return f"""<!DOCTYPE html>
<html lang="{esc(spec.get('lang', 'en'))}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(spec['title'])}</title>
<link href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head>
<body><div class="band"></div>
<div class="wrap"><header class="top page" id="cover">{kicker}<h1 tabindex="-1">{esc(spec['title'])}</h1>{summary}{source}
<nav class="toc" aria-label="Panels"><ol>{''.join(toc)}</ol></nav></header>
<div class="slim"><a href="#cover">{esc(spec['title'])}</a></div>
<div class="controls" role="group" aria-label="Move between panels"><button class="prev" type="button" aria-keyshortcuts="ArrowLeft Shift+Space">← Back</button>
<span class="pos" aria-live="polite"></span><button class="next" type="button" aria-keyshortcuts="ArrowRight Space">Next →</button><span class="dots" aria-hidden="true"></span>
<button class="all" type="button"></button></div>
<main>{''.join(sections)}</main>
</div>
<div class="band band--thin"></div>
<footer class="foot"><span>{rich(spec.get("source", ""))}</span><span>show-better by <a href="https://n14n.dev/" target="_blank" rel="noopener">n14n.dev</a></span></footer>
<script>{JS}</script></body></html>"""


# ---------- plain text ----------

def doc_line(spec, p, g, W=72):
    doc = spec.get("document")
    if not doc or p.get("part") is None:
        return []
    parts = set(map(str, p["part"] if isinstance(p["part"], list) else [p["part"]]))
    secs = doc["sections"]
    here = [f"{k + 1} of {len(secs)}, {s['label']}" for k, s in enumerate(secs) if str(s["id"]) in parts]
    return twrap("In the document: part " + "; part ".join(here), W, "")


def render_text(spec, width=72, ascii=False, markdown=False):
    g = GLYPHS["ascii" if ascii else "unicode"]
    W = width
    out = []
    n = len(spec["panels"])
    if markdown:
        out += [f"# {spec['title']}", ""]
        if spec.get("summary"):
            out += [spec["summary"], ""]
    else:
        out += twrap(spec["title"].upper(), W) + [g["h"] * min(W, len(spec["title"]) + 4)]
        if spec.get("summary"):
            out += twrap(spec["summary"], W)
        out.append("")
    for i, p in enumerate(spec["panels"], 1):
        visual = t_map(p, W, g, spec) if p["kind"] == "map" else TEXT[p["kind"]](p, W, g)
        strip = doc_line(spec, p, g, W)
        if markdown:
            out += [f"## {i}. {p['headline']}", ""] + ([f"*{' '.join(strip)}*", ""] if strip else [])
            out += ["```text"] + visual + ["```", ""] if p["kind"] not in ("text",) else visual + [""]
        else:
            rule = f"{g['h'] * 2} {i}/{n} " + g["h"] * max(W - len(f'{i}/{n}') - 4, 0)
            out += [rule] + strip + twrap(p["headline"], W) + [""] + visual
        note = p.get("note")
        if note:
            for para in (note if isinstance(note, list) else [note]):
                out += ([""] if not markdown else []) + (twrap(plain(para), W - 4, f"{g['v']}   ") if not markdown else ["> " + para])
        if p.get("read"):
            out += ["", f"Read in the document: {plain(p['read'], markdown)}"]
        out.append("")
    if spec.get("source"):
        out += twrap(plain(spec["source"], markdown), W)
    return "\n".join(l.rstrip() for l in out) + "\n"


# ---------- screen-reader text ----------

class _Linear(HTMLParser):
    """Read a panel's HTML data as lines: a table row becomes one sentence, a list item one line."""

    def __init__(self):
        super().__init__()
        self.lines, self.buf, self.lists = [], [], []
        self.table = None  # {"head": [...], "rows": [(cells, hl)], "row": [...], "hl": bool, "cell": [...] or None, "in_head": bool}

    def flush(self, prefix=""):
        text = re.sub(r"\s+", " ", "".join(self.buf)).strip()
        self.buf = []
        if text:
            self.lines.append(prefix + text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            self.flush()
            self.table = {"head": [], "rows": [], "row": [], "hl": False, "cell": None, "in_head": False}
        elif self.table is not None:
            if tag == "thead":
                self.table["in_head"] = True
            elif tag == "tr":
                self.table["row"], self.table["hl"] = [], "hl" in (a.get("class") or "").split()
            elif tag in ("td", "th"):
                self.table["cell"] = []
        elif tag in ("ol", "ul"):
            self.flush()
            self.lists.append([tag, 0])
        elif tag == "li":
            self.flush()
        elif tag in ("p", "div", "br"):
            self.flush()

    def handle_endtag(self, tag):
        t = self.table
        if t is not None:
            if tag in ("td", "th") and t["cell"] is not None:
                t["row"].append(re.sub(r"\s+", " ", "".join(t["cell"])).strip())
                t["cell"] = None
            elif tag == "tr":
                if t["in_head"]:
                    t["head"] = t["row"]
                else:
                    t["rows"].append((t["row"], t["hl"]))
            elif tag == "thead":
                t["in_head"] = False
            elif tag == "table":
                head = t["head"]
                for cells, hl in t["rows"]:
                    named = [f"{h}: {c}" if h else c for h, c in zip(head[1:], cells[1:]) if c]
                    label = cells[0] if cells else ""
                    line = f"{label}. {'; '.join(named)}" if label and named else (label or "; ".join(named))
                    self.lines.append(line + (" (highlighted)" if hl else ""))
                self.table = None
            return
        if tag == "li" and self.lists:
            kind = self.lists[-1]
            kind[1] += 1
            self.flush(f"{kind[1]}. " if kind[0] == "ol" else "- ")
        elif tag in ("ol", "ul") and self.lists:
            self.lists.pop()
        elif tag in ("p", "div"):
            self.flush()

    def handle_data(self, data):
        if self.table is not None:
            if self.table["cell"] is not None:
                self.table["cell"].append(data)
        else:
            self.buf.append(data)


def linear_lines(fragment):
    parser = _Linear()
    parser.feed(fragment)
    parser.close()
    parser.flush()
    return parser.lines


def highlighted(p, spec=None):
    """Labels of the highlighted items in a panel, so a reader who cannot see the colour still knows the point."""
    found = []
    if p["kind"] == "map":
        ids = set(map(str, _as_list(p.get("highlight"))))
        secs = p.get("sections") or (spec or {}).get("document", {}).get("sections", [])
        return [s["label"] for s in secs if str(s.get("id")) in ids or s.get("highlight")]

    def walk(o):
        if isinstance(o, dict):
            if o.get("highlight") is True:
                lab = o.get("label") or o.get("name") or o.get("value")
                if lab is not None:
                    found.append(str(lab))
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk({k: v for k, v in p.items() if k != "highlight"})
    return found


def render_screen_reader(spec, width=72):
    """Plain sentences and value lists, with no box drawing, bars, rules or symbols that a screen reader reads aloud."""
    W, n = width, len(spec["panels"])
    out = twrap(spec["title"], W)
    if spec.get("summary"):
        out += twrap(plain(spec["summary"]), W)
    out.append("")
    for i, p in enumerate(spec["panels"], 1):
        out += twrap(f"Panel {i} of {n}: {p['headline']}", W) + doc_line(spec, p, GLYPHS["ascii"], W)
        if p["kind"] == "numbers":
            body = [f"{f['value']}: {f['label']}" + (" (highlighted)" if f.get("highlight") else "") for f in p["figures"]]
        elif p["kind"] == "text":
            body = [plain(b) for b in _as_list(p.get("body"))]
        else:
            visual, data = v_map(p, spec) if p["kind"] == "map" else VISUALS[p["kind"]](p)
            body = linear_lines(data or visual)
        for line in body:
            out += twrap(line, W)
        hl = highlighted(p, spec) if p["kind"] not in ("numbers", "table") else []
        if hl:
            out += twrap("Highlighted: " + ", ".join(hl) + ".", W)
        for para in _as_list(p.get("note")):
            out += twrap("Note: " + plain(para), W)
        if p.get("read"):
            out += twrap(f"Read in the document: {plain(p['read'])}", W)
        out.append("")
    if spec.get("source"):
        out += twrap(plain(spec["source"]), W)
    return "\n".join(l.rstrip() for l in out) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a short visual presentation from a JSON spec.")
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("check", help="validate a spec and print every value it will show")
    c.add_argument("spec")
    r = sub.add_parser("render", help="check a spec, then write the page (html) or print it as text (text, md)")
    r.add_argument("spec")
    r.add_argument("--format", choices=("html", "text", "md"), default="html",
                   help="html: a page to open; text: plain text for a terminal; md: Markdown with text diagrams in code blocks")
    r.add_argument("--out", help="file to write; required for html, otherwise the text is printed")
    r.add_argument("--open", action="store_true", help="open the page in the default browser")
    r.add_argument("--width", type=int, default=72, help="text width in characters (text and md)")
    r.add_argument("--ascii", action="store_true", help="use only ASCII characters (text and md)")
    r.add_argument("--screen-reader", action="store_true",
                   help="text only: sentences and value lists, without box drawing, bars or rules that a screen reader reads aloud")
    args = parser.parse_args()
    try:
        spec = json.loads(Path(args.spec).expanduser().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        sys.exit(f"error: cannot read {args.spec}: {exc}")
    errors, warnings, digest = check(spec)
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    for e in errors:
        print(f"error: {e}", file=sys.stderr)
    if args.command == "check" or errors:
        print("\n".join(digest))
        sys.exit(1 if errors else 0)
    if args.format != "html":
        if args.screen_reader and args.format != "text":
            sys.exit("error: --screen-reader works with --format text")
        text = (render_screen_reader(spec, args.width) if args.screen_reader
                else render_text(spec, args.width, args.ascii, args.format == "md"))
        if args.out:
            Path(args.out).expanduser().write_text(text, encoding="utf-8")
            print(f"wrote {Path(args.out).expanduser().resolve()}", file=sys.stderr)
        else:
            print(text, end="")
        return
    if not args.out:
        sys.exit("error: --out is required for --format html")
    out = Path(args.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(spec), encoding="utf-8")
    print("\n".join(digest))
    print(f"\nwrote {out.resolve()}")
    if args.open and not webbrowser.open(out.resolve().as_uri()):
        print("could not open a browser on this machine: if the user's browser runs on another machine, this path does not reach it")


if __name__ == "__main__":
    main()
