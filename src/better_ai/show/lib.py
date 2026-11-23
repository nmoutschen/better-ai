"""What every kind of slide shares: the limits, the palette, the glyphs and the helpers for HTML, SVG and plain text."""

import html
import json
import math
import re
import textwrap

from .. import resources

# The spec schema lists the kinds once. It is read as plain JSON: the hooks it names are not registered yet.
KINDS = tuple(json.loads(resources.read_text("show/schemas/spec.schema.json"))["$defs"]["kind"]["enum"])
SHARED_SCALE = ("bars", "dots", "slope", "line", "scatter")  # in a compare, both sides of one of these share a scale
EVIDENCE_WORDS = {"strong": "strong evidence", "moderate": "moderate evidence", "weak": "weak evidence"}
OUTCOMES = {"helps": ("up", "helps"), "hurts": ("dn", "hurts"), "never": ("x", "never"), "neutral": ("same", "neutral")}


LIMITS = {
    "panels": 12,
    "bars": 12,
    "series": 4,
    "flow": 7,
    "groups": 4,
    "group_items": 15,
    "timeline": 8,
    "numbers": 3,
    "highlights": 2,
    "headline_chars": 140,
    "rows": 15,
    "units": 100,
    "unit_parts": 3,
    "matrix_rows": 10,
    "matrix_cols": 5,
    "part_chars": 28,
    "lanes_actors": 5,
    "lanes_steps": 10,
    "fork_branches": 4,
    # Characters a label may use before the drawing cuts it with an ellipsis; check warns past them.
    "quadrant_label": 26,
    "slope_label": 22,
    "dots_label": 40,
    "series_name": 20,
    "fork_label": 34,
}


MARKS = {"yes": "yes", "no": "no", "up": "higher", "down": "lower", "same": "no difference"}


C = {
    "cream": "#FFFCF7",
    "linen": "#F2EDE5",
    "sand": "#C4B69C",
    "terracotta": "#E8725C",
    "moss": "#6B7F5E",
    "umber": "#5C4033",
    "ink": "#33302B",
    "heading": "#1C1A17",
    "muted": "#78736B",
    "line": "#DDD6CA",
}


SANS = "Space Grotesk, -apple-system, sans-serif"


W = 800  # SVG viewBox width


GLYPHS = {
    "unicode": {
        "h": "─",
        "v": "│",
        "tl": "┌",
        "tr": "┐",
        "bl": "└",
        "br": "┘",
        "arrow": "→",
        "down": "↓",
        "bar": "█",
        "half": "▌",
        "hl": "◆",
        "dot": "●",
        "pt": "•",
        "box": "■",
        "box2": "▣",
        "box3": "□",
        "spark": " ▁▂▃▄▅▆▇█",
        "tee": "├",
        "end": "└",
        "up": "▲",
        "dn": "▼",
        "yes": "✓",
        "no": "✗",
        "same": "=",
        "blank": "·",
        "cross": "┼",
        "seg": "━",
        "x": "✕",
    },
    "ascii": {
        "h": "-",
        "v": "|",
        "tl": "+",
        "tr": "+",
        "bl": "+",
        "br": "+",
        "arrow": "->",
        "down": "v",
        "bar": "#",
        "half": "#",
        "hl": ">",
        "dot": "o",
        "pt": "*",
        "box": "#",
        "box2": "+",
        "box3": ".",
        "spark": " .:-=+*#%@",
        "tee": "|-",
        "end": "`-",
        "up": "^",
        "dn": "v",
        "yes": "Y",
        "no": "N",
        "same": "=",
        "blank": ".",
        "cross": "+",
        "seg": "=",
        "x": "x",
    },
}


# ---------- shared helpers: HTML and SVG ----------

LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")


def rich(value) -> str:
    """Escape text and turn Markdown links, [label](https://...), into anchors."""
    out, last = [], 0
    text = str(value)
    for m in LINK.finditer(text):
        out.append(esc(text[last : m.start()]))
        out.append(f'<a href="{esc(m.group(2))}" target="_blank" rel="noopener">{esc(m.group(1))}</a>')
        last = m.end()
    out.append(esc(text[last:]))
    return "".join(out)


def plain(value, keep_links=False) -> str:
    """Text output: a link becomes its label followed by the address, or stays Markdown."""
    return str(value) if keep_links else LINK.sub(lambda m: f"{m.group(1)} <{m.group(2)}>", str(value))


def stop(text) -> str:
    """The full stop after a sentence's last words, unless they already end one: no "arrive?." or "2026.."."""
    return "" if str(text).rstrip()[-1:] in (".", "?", "!") else "."


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def num(value) -> str:
    """Format a number for a label: no trailing .0, thousands separators."""
    if isinstance(value, float) and not value.is_integer():
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    return f"{int(value):,}"


# While `check` renders the slides, the labels the drawings cut with an ellipsis, so it can warn about each.
CUTS: list | None = None


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
        found = CUTS  # another thread may end the collection between the test and the append
        if found is not None:
            found.append((str(text), chars * max_lines))
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: max(chars - 1, 1)].rstrip() + "…"
    return lines


def text_el(x, y, lines, size=12, weight=500, fill=None, anchor="start", italic=False, gap=None, d=None) -> str:
    """SVG text, one tspan per line. d is the item the text labels, so a click on it opens the item's detail."""
    gap = gap or size * 1.3
    style = ' font-style="italic"' if italic else ""
    style += dattr(d) if d is not None else ""
    spans = "".join(
        f'<tspan x="{x:.1f}" dy="{0 if i == 0 else gap:.1f}">{esc(line)}</tspan>' for i, line in enumerate(lines)
    )
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{SANS}" font-size="{size}" font-weight="{weight}" '
        f'fill="{fill or C["ink"]}" text-anchor="{anchor}"{style}>{spans}</text>'
    )


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
    return (
        f'<svg viewBox="0 0 {W} {height:.0f}" role="img" aria-label="{esc(label)}" '
        f'xmlns="http://www.w3.org/2000/svg">{body}</svg>'
    )


def table_html(columns, rows, num_cols=frozenset(), highlight=frozenset(), items=None) -> str:
    """A table; items, one per row, lets a row open its item's detail."""
    head = "".join(f'<th class="{"n" if i in num_cols else ""}">{esc(c)}</th>' for i, c in enumerate(columns))
    body = "".join(
        f'<tr class="{"hl" if r in highlight else ""}"{dattr(items[r]) if items and r < len(items) else ""}>'
        + "".join(f'<td class="{"n" if i in num_cols else ""}">{esc(c)}</td>' for i, c in enumerate(row))
        + "</tr>"
        for r, row in enumerate(rows)
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def arrow(x1, y1, x2, y2, color, width=1.2):
    """A thin connector with a small arrowhead at its end."""
    ang = math.atan2(y2 - y1, x2 - x1)
    a = (x2 - 7 * math.cos(ang) + 3.5 * math.sin(ang), y2 - 7 * math.sin(ang) - 3.5 * math.cos(ang))
    b = (x2 - 7 * math.cos(ang) - 3.5 * math.sin(ang), y2 - 7 * math.sin(ang) + 3.5 * math.cos(ang))
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2 - 6 * math.cos(ang):.1f}" y2="{y2 - 6 * math.sin(ang):.1f}" stroke="{color}" stroke-width="{width}"/>'
        f'<polygon points="{x2:.1f},{y2:.1f} {a[0]:.1f},{a[1]:.1f} {b[0]:.1f},{b[1]:.1f}" fill="{color}"/>'
    )


def dot(cx, cy, item=None, hl=False):
    """A node's mark: a small muted dot, or, for the point of the slide, a larger terracotta one."""
    if hl:
        return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="6" fill="{C["terracotta"]}"{dattr(item)}/>'
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3.5" fill="{C["muted"]}"{dattr(item)}/>'


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def axis_start(p, axis, values):
    """Where a value axis starts: at zero, unless the panel sets '<axis>_from_zero' to false."""
    return min(values) if p.get(f"{axis}_from_zero") is False else min(0, min(values))


def _as_list(v):
    return v if isinstance(v, list) else ([] if v is None else [v])


# ---------- shared helpers: plain text ----------


def tfmt(v):
    return num(v) if _is_num(v) else str(v)


def twrap(text, width, indent=""):
    return textwrap.wrap(
        str(text),
        width=max(width, 10),
        initial_indent=indent,
        subsequent_indent=indent,
        break_long_words=False,
        break_on_hyphens=False,
    ) or [indent]


def tcut(text, n):
    text = str(text)
    found = CUTS
    if len(text) > n and found is not None:
        found.append((text, n))
    return text if len(text) <= n else text[: max(n - 1, 1)] + "…"


def tbox(lines, width, g, hl=False):
    """A box around lines; a highlighted box gets a marker in its top-left corner."""
    inner = width - 4
    top = g["tl"] + (g["hl"] if hl else g["h"]) + g["h"] * (width - 3) + g["tr"]
    out = (
        [top]
        + [f"{g['v']} {tcut(line, inner):<{inner}} {g['v']}" for line in lines]
        + [g["bl"] + g["h"] * (width - 2) + g["br"]]
    )
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
        return mark + sep.join(
            tcut(c, w).rjust(w) if i in right else tcut(c, w).ljust(w)
            for i, (c, w) in enumerate(zip(cells, widths, strict=False))
        )

    out = [line([str(h).upper() for h in header]), " " + sep.join(g["h"] * w for w in widths)]
    for k, r in enumerate(rows):
        out.append(line(r, g["hl"] if k in hl else " "))
    return out


def collect_details(p):
    """Every (label, detail) in a panel: any item with a 'label' may carry a 'detail'."""
    found = []

    def walk(o):
        if isinstance(o, dict):
            if o.get("label") and "detail" in o:
                found.append((str(o["label"]), o["detail"]))
            for k, v in o.items():
                if k != "detail":
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(p)
    return found


def dattr(item):
    """The attribute that ties a drawn label, mark or row to its item's detail: the detail's number in the slide."""
    k = item.get("_dk") if isinstance(item, dict) else None
    return f' data-d="{k}"' if k is not None else ""


def keyed(p):
    """A copy of a panel in which each item with a detail carries _dk, its detail's number, in collect_details order,
    so two items with the same label keep their own details."""
    n = [0]

    def walk(o):
        if isinstance(o, dict):
            out = dict(o)
            if o.get("label") and "detail" in o:
                out["_dk"] = n[0]
                n[0] += 1
            for k, v in o.items():
                if k != "detail":
                    out[k] = walk(v)
            return out
        if isinstance(o, list):
            return [walk(v) for v in o]
        return o

    return walk(p)


def keyed_details(p):
    """(number, label, detail) for each item of a keyed panel or side."""
    found = []

    def walk(o):
        if isinstance(o, dict):
            if "_dk" in o:
                found.append((o["_dk"], str(o["label"]), o["detail"]))
            for k, v in o.items():
                if k != "detail":
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(p)
    return found


def ev_of(item):
    """An item's evidence strength, or None."""
    d = item.get("detail") if isinstance(item, dict) else None
    return d.get("evidence") if isinstance(d, dict) and d.get("evidence") in EVIDENCE_WORDS else None


def overview_labels(p):
    """The labels a later panel's 'focus' may name."""
    kind = p["kind"]
    if kind == "flow":
        return [s["label"] for s in p["steps"]]
    if kind == "timeline":
        return [e["label"] for e in p["events"]]
    if kind == "concept":
        return [n["label"] for n in p["nodes"]]
    return [x for g in p["groups"] for x in [g["label"], *map(str, g.get("items") or [])]]


def listed(p, key, where, warnings, limit=None, what="items"):
    """The list the schema guarantees, with a warning when it is longer than one panel can show."""
    items = p[key]
    if limit and len(items) > limit:
        warnings.append(f"{where}: {len(items)} {what}; more than {limit} is hard to read in one panel")
    return items


def count_highlights(items, where, warnings):
    n = sum(1 for it in items if isinstance(it, dict) and it.get("highlight"))
    if n > LIMITS["highlights"]:
        warnings.append(
            f"{where}: {n} highlighted items; emphasis works when it marks the one or two that carry the point"
        )
