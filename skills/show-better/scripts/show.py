"""Render a short visual introduction to a document from a JSON spec, as a slide page or as text.

Usage:
  python3 show.py check SPEC                  validate the spec and print every value it will show
  python3 show.py render SPEC --out FILE      check, then write the page (--open to open it, --serve to serve it)
  python3 show.py wait DIR [--timeout S]
  python3 show.py reply DIR TEXT [--to ID]
  python3 show.py status DIR seen|asked|working|done|accepted ID...
  python3 show.py pending DIR

SPEC is a JSON file described in templates/spec.md. The page shows one 16:9 slide at a time, with a strip above that
groups the slides under the story's parts. The reader moves with the buttons, the strip or the arrow keys, and clicks
a label or a mark to see its detail. Export downloads the slides alone as one presentation.

`render --serve` serves the page on 127.0.0.1 and keeps running. The page then shows a conversation with the agent:
the user comments on any part of a slide in Comment mode or writes a message. Each action is a JSON-RPC call from the
page (comment, delete, note, accept, reopen); the script appends it to answers.jsonl next to the page and prints it to
stdout as one JSON line. Running `render` again with the same --out, without --serve, updates the served page: the open
page loads the new slides once the user is not typing. `wait` blocks until the page receives actions the agent has not
seen, prints them and exits. `reply` shows the agent's reply in the page, `status` marks each item seen, asked, working,
done or accepted, and `pending` lists what is not finished. Opened as a file, the page shows the slides without the
conversation: that is the copy to publish.

render --format text or md draws the same slides as plain text; --format text --screen-reader writes them as
sentences and value lists, without box drawing, for screen readers. Every layout is computed here, so the agent
never draws a text diagram by hand: language models read text diagrams far better than they construct them.

show.html, page.css, show.css, page.js and show.js, next to this script, are the page; the script fills in the
slides. page.py, also next to it, holds the conversation with the agent.
"""

import argparse
import contextlib
import html
import http.server
import json
import math
import re
import sys
import textwrap
import webbrowser
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent  # show.html, page.css, show.css, page.js and show.js sit next to this script
sys.path.insert(0, str(HERE))  # page.py, the conversation every page that talks to the agent shares, sits here too
import page  # noqa: E402

KINDS = (
    "map",
    "concept",
    "flow",
    "groups",
    "tree",
    "sets",
    "matrix",
    "effects",
    "pairs",
    "quadrant",
    "numbers",
    "units",
    "bars",
    "slope",
    "dots",
    "scatter",
    "line",
    "timeline",
    "table",
    "text",
    "svg",
    "lanes",
    "fork",
)
TEMPLATES = ("visual", "compare", "statement", "title")
OVERVIEW_KINDS = ("flow", "timeline", "concept", "groups")  # kinds that can be the deck's overview
SHARED_SCALE = ("bars", "dots", "slope", "line", "scatter")  # in a compare, both sides of one of these share a scale
EVIDENCE = ("strong", "moderate", "weak", "stated")
EVIDENCE_WORDS = {"strong": "strong evidence", "moderate": "moderate evidence", "weak": "weak evidence"}
MARKED_KINDS = ("dots", "effects", "fork", "lanes")  # one mark per item: an item's evidence sets the mark's fill
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
        if CUTS is not None:
            CUTS.append((str(text), chars * max_lines))
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
    if len(text) > n and CUTS is not None:
        CUTS.append((text, n))
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
        warnings.append(
            f"{len(panels)} panels: more than {LIMITS['panels']} is long for one introduction; split it or cut panels"
        )
    if spec.get("kicker"):
        warnings.append("'kicker' is not shown: put the reader's question in 'question', the opening slide's kicker")
    if not spec.get("question"):
        warnings.append("no 'question': the opening slide asks the reader's question, and the title answers it")
    digest.append(f"TITLE: {spec.get('title', '')}")
    for key in ("question", "summary", "source"):
        if spec.get(key):
            digest.append(f"{key.upper()}: {spec[key]}")
    doc = spec.get("document")
    if doc is not None:
        if not isinstance(doc, dict) or not doc.get("title"):
            errors.append("'document' needs a 'title', and may have an 'address' and 'sections'")
        else:
            address = doc.get("address")
            if address is not None and not re.match(r"https?://\S+$", str(address)):
                errors.append("document: 'address' must be the document's http(s) URL")
            secs = doc.get("sections")
            if secs is not None and (
                not isinstance(secs, list)
                or not secs
                or not all(isinstance(x, dict) and x.get("id") is not None and x.get("label") for x in secs)
            ):
                errors.append("document: 'sections' needs a list of sections, each with an 'id' and a 'label'")
                secs = None
            digest.append(
                f"DOCUMENT: {doc['title']}{(' <' + str(address) + '>') if address else ''}"
                + (" — " + " · ".join(f"{x['id']} {x['label']}" for x in secs) if secs else "")
            )
            for x in secs or []:
                if len(str(x.get("gist", ""))) > 50:
                    warnings.append(
                        f"document: the gist of '{x['label']}' is {len(x['gist'])} characters; keep it under 50, a few words"
                    )
    overview = None  # (panel number, its labels) once a panel sets overview
    for i, p in enumerate(panels, 1):
        where = f"panel {i}"
        if not isinstance(p, dict):
            errors.append(f"{where}: must be an object")
            continue
        for old in ("note", "read"):
            if old in p:
                errors.append(
                    f"{where}: '{old}' is no longer used: move it into 'source', the one line at the foot of each slide "
                    "that says what the slide rests on and where to read it"
                )
        template = p.get("template", "visual")
        if template not in TEMPLATES:
            errors.append(f"{where}: template must be one of {', '.join(TEMPLATES)}")
            continue
        head = str(p.get("headline", "")).strip()
        if not head:
            errors.append(f"{where}: missing 'headline' (a full sentence that states the panel's point)")
        else:
            if len(head.split()) < 4 or not re.search(r"[.!?]$", head):
                warnings.append(
                    f"{where}: headline '{head}' does not read as a full sentence; state the point, not the topic"
                )
            if len(head) > LIMITS["headline_chars"]:
                warnings.append(
                    f"{where}: headline is {len(head)} characters; keep it under {LIMITS['headline_chars']}"
                )
        part = p.get("part")
        if part is not None and not isinstance(part, str):
            errors.append(f"{where}: 'part' must be a short question, such as 'Does it arrive?'")
        elif part and len(part) > LIMITS["part_chars"]:
            warnings.append(
                f"{where}: part '{part}' is {len(part)} characters; keep it under {LIMITS['part_chars']}, two to five words"
            )
        label = template.upper() + (f" {str(p.get('kind', '')).upper()}" if template == "visual" else "")
        digest.append(f"\n[{i}] {label}: {head}")
        if part:
            digest.append(f"    part: {part}")
        try:
            if template == "visual":
                check_kind(p, where, spec, errors, warnings, digest)
            elif template == "compare":
                check_compare(p, where, spec, errors, warnings, digest)
            elif template == "statement":
                check_statement(p, where, errors, warnings, digest)
            else:
                check_title(p, where, len(panels), errors, digest)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            errors.append(f"{where}: malformed {template} data ({exc})")
        check_source(p, where, spec, errors, warnings, digest)
        check_details(p, where, errors, digest)
        if p.get("overview"):
            if overview:
                errors.append(f"{where}: only one panel may set 'overview'; panel {overview[0]} already does")
            elif template != "visual" or p.get("kind") not in OVERVIEW_KINDS:
                errors.append(f"{where}: the overview must be a visual panel of kind {', '.join(OVERVIEW_KINDS)}")
            else:
                try:
                    overview = (i, overview_labels(p))
                    digest.append("    overview: later panels may mark their place in it with 'focus'")
                except (TypeError, KeyError, AttributeError):
                    pass  # the kind's own check has reported the malformed data
        if p.get("focus") is not None:
            focus = _as_list(p["focus"])
            if overview is None:
                errors.append(f"{where}: 'focus' needs an earlier panel with \"overview\": true")
            else:
                for lab in focus:
                    if lab not in overview[1]:
                        errors.append(
                            f"{where}: focus '{lab}' is not a label in the overview (panel {overview[0]}): "
                            + ", ".join(overview[1])
                        )
                digest.append(f"    where we are: {', '.join(map(str, focus))}")
    check_style(spec, errors, digest)
    if not errors:
        check_cuts(spec, warnings)
    return errors, warnings, digest


def check_style(spec, errors, digest):
    style = spec.get("style")
    if style is None:
        return
    if not isinstance(style, dict):
        errors.append('\'style\' must be an object, such as {"point": "#0055AA", "serif": "Georgia, serif"}')
        return
    for k, v in style.items():
        if k not in STYLE_KEYS:
            errors.append(f"style: '{k}' is not a slide variable; use {', '.join(STYLE_KEYS)}")
        elif k in ("serif", "sans"):
            if not (isinstance(v, str) and FONT_STACK.fullmatch(v)):
                errors.append(f"style: '{k}' must be a font stack, such as \"'Inter', sans-serif\"")
        elif not (isinstance(v, str) and COLOUR.fullmatch(v.strip())):
            errors.append(f"style: '{k}' must be a CSS colour, such as #1C1A17 or rgb(28, 26, 23)")
    digest.append("STYLE: " + ", ".join(f"{k}={v}" for k, v in style.items()))


def check_cuts(spec, warnings):
    """Render each slide and warn about every label its drawing cuts with an ellipsis: the same limits as the page."""
    global CUTS
    ov = overview_of(spec)
    total = len(spec["panels"]) + 1
    for i, p in enumerate(spec["panels"], 1):
        CUTS = []
        # A malformed panel is reported by its own check.
        with contextlib.suppress(TypeError, ValueError, KeyError, AttributeError, IndexError):
            slide_panel(spec, p, i, total, ov)
        cuts, CUTS = CUTS, None
        for text, n in dict.fromkeys(cuts):
            warnings.append(
                f"panel {i}: '{text}' is cut to fit the drawing; shorten it to about {n} characters, or move the rest into a detail"
            )


def check_kind(p, where, spec, errors, warnings, digest):
    """Check a visual's kind and its data: a visual panel, or one side of a compare."""
    kind = p.get("kind")
    if kind not in KINDS:
        errors.append(f"{where}: kind must be one of {', '.join(KINDS)}")
        return
    if kind == "map":
        check_map(p, where, errors, warnings, digest, spec)
    else:
        PANEL_CHECKS[kind](p, where, errors, warnings, digest)


def check_compare(p, where, spec, errors, warnings, digest):
    sides = []
    for side in ("a", "b"):
        s = p.get(side)
        if not isinstance(s, dict) or not s.get("label"):
            errors.append(f"{where}: '{side}' needs a 'label' and a 'kind' with that kind's fields")
            continue
        digest.append(f"    {side.upper()}: {s['label']} ({s.get('kind')})")
        check_kind(s, f"{where}, side {side}", spec, errors, warnings, digest)
        sides.append(s.get("kind"))
    if len(sides) == 2 and sides[0] == sides[1] and sides[0] in SHARED_SCALE:
        digest.append("    both sides drawn on one scale")


def check_statement(p, where, errors, warnings, digest):
    for key in ("figure", "sentence"):
        if not p.get(key):
            errors.append(f"{where}: a statement needs '{key}'")
    if len(str(p.get("figure", ""))) > 14:
        warnings.append(f"{where}: figure '{p.get('figure')}' is long; a statement shows one short figure")
    if not p.get("compare"):
        warnings.append(
            f"{where}: no 'compare': a figure alone does not say whether it is large; give what it is compared to, "
            "such as 'against 89% before', or use another template"
        )
    digest.append(f"    {p.get('figure')} {p.get('sentence')}" + (f" ({p['compare']})" if p.get("compare") else ""))


def check_title(p, where, n_panels, errors, digest):
    if p.get("body") is not None and not isinstance(p["body"], str):
        errors.append(f"{where}: 'body' must be a string")
    if p.get("body"):
        digest.append(f"    {p['body']}")
    actions = p.get("actions") or []
    if not isinstance(actions, list):
        errors.append(f"{where}: 'actions' must be a list")
        return
    for k, a in enumerate(actions, 1):
        target = a.get("panel") if isinstance(a, dict) else None
        if not isinstance(a, dict) or not a.get("text") or not isinstance(target, int) or isinstance(target, bool):
            errors.append(f"{where}: each action needs 'text' and 'panel', the number of the panel it points to")
            continue
        if not 1 <= target <= n_panels:
            errors.append(f"{where}: action '{a['text']}' points to panel {target}; there are {n_panels} panels")
            continue
        digest.append(f"    {k}. {a['text']} → panel {target} (slide {target + 1})")


def check_source(p, where, spec, errors, warnings, digest):
    src = p.get("source")
    if not src:
        warnings.append(f"{where}: no 'source': say what the slide's claim rests on, and where to read it")
        return
    if isinstance(src, dict):
        if not src.get("text") and not src.get("section"):
            errors.append(f"{where}: 'source' needs 'text', and may have 'section'")
            return
        if src.get("section") and not (spec.get("document") or {}).get("address"):
            warnings.append(
                f"{where}: source section '{src['section']}' is shown without a link: the 'document' has no 'address'"
            )
        digest.append(
            f"    source: {src.get('text', '')}" + (f" [read: {src['section']}]" if src.get("section") else "")
        )
    elif isinstance(src, str):
        digest.append(f"    source: {src}")
    else:
        errors.append(f"{where}: 'source' must be a string or an object with 'text' and 'section'")


def check_details(p, where, errors, digest):
    for lab, d in collect_details(p):
        if not isinstance(d, dict) or not d.get("text"):
            errors.append(f"{where}: the detail of '{lab}' needs 'text', and may have 'source' and 'evidence'")
            continue
        if d.get("evidence") is not None and d["evidence"] not in EVIDENCE:
            errors.append(f"{where}: the evidence of '{lab}' must be one of {', '.join(EVIDENCE)}")
        digest.append(
            f"    detail, {lab}: {d['text']}"
            + (f" ({d['source']})" if d.get("source") else "")
            + (f" [{d['evidence']}]" if d.get("evidence") else "")
        )


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
        warnings.append(
            f"{where}: {n} highlighted items; emphasis works when it marks the one or two that carry the point"
        )


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
                warnings.append(
                    f"{where}: the gist of '{sec.get('label')}' is {len(sec['gist'])} characters; keep it under 50, a few words"
                )
    for s in secs:
        if not isinstance(s, dict) or not s.get("label"):
            errors.append(f"{where}: each section needs a 'label'")
            continue
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
            errors.append(
                f"{where}: edge {e['from']} → {e['to']} needs a 'label' that says how they relate, such as 'causes' or 'is part of'"
            )
            continue
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
    steps = need_list(p, "steps", where, errors, LIMITS["flow"], warnings, "steps")
    count_highlights(steps, where, warnings)
    if not p.get("arrow"):
        errors.append(f"{where}: missing 'arrow': state what every arrow means, such as 'then' or 'sends data to'")
    for s in steps:
        if not s.get("label"):
            errors.append(f"{where}: every step needs a 'label'")
        digest.append(
            f"    → {s.get('label')}{'  [highlight]' if s.get('highlight') else ''}"
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
    groups = need_list(p, "groups", where, errors, LIMITS["groups"], warnings, "groups")
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
                errors.append(
                    f"{where}: the children of '{n['label']}' sum to {num(total)}, more than its value {num(n['value'])}"
                )
        digest.append(
            "    "
            + "  " * depth
            + f"{n.get('label')}{(' = ' + num(n['value'])) if _is_num(n.get('value')) else ''}"
            + ("  [highlight]" if n.get("highlight") else "")
        )
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
            mark = _mark(c)
            if mark is not None and mark not in MARKS:
                errors.append(f"{where}: row '{r['label']}' has mark '{mark}'; use one of {', '.join(MARKS)}, or null")
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
        if isinstance(r, dict) and isinstance(r.get("cells"), list):
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
    rows = need_list(p, "rows", where, errors, 12, warnings, "findings")
    count_highlights(rows, where, warnings)
    for r in rows:
        if not isinstance(r, dict) or not r.get("label") or r.get("effect") not in EFFECTS:
            errors.append(f"{where}: each row needs a 'label' and an 'effect' of {', '.join(EFFECTS)}")
            continue
        g = f"{r['group']} / " if r.get("group") else ""
        digest.append(
            f"    {g}{r['label']}{(' on ' + r['outcome']) if r.get('outcome') else ''}: {EFFECT_WORDS[r['effect']]}"
            + ("  [highlight]" if r.get("highlight") else "")
        )
    if rows and not any(isinstance(r, dict) and r.get("outcome") for r in rows):
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
    heads = p.get("columns")
    if not (isinstance(heads, list) and len(heads) == 2):
        errors.append(f'{where}: \'columns\' needs two headings, such as ["Helps when", "Hurts or no gain when"]')
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
                    errors.append(
                        f"{where}: '{r['label']}': each entry in '{side}' needs a 'label', and an optional 'effect' of {', '.join(EFFECTS)}"
                    )
        if not (r.get("left") or r.get("right")):
            errors.append(f"{where}: '{r['label']}' has nothing in 'left' or 'right'")
        digest.append(
            f"    {r['label']}: "
            + " | ".join(
                ", ".join(
                    f"{c.get('label')}{(' [' + EFFECT_WORDS.get(c.get('effect'), '') + ']') if c.get('effect') else ''}"
                    for c in r.get(side) or []
                    if isinstance(c, dict)
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
    items = need_list(p, "items", where, errors, 10, warnings, "items")
    count_highlights(items, where, warnings)
    for ax in ("x", "y"):
        a = p.get(ax)
        if not isinstance(a, dict) or not a.get("label") or not a.get("low") or not a.get("high"):
            errors.append(
                f'{where}: \'{ax}\' needs \'label\', \'low\' and \'high\', such as {{"label": "Effort", "low": "small", "high": "large"}}'
            )
    if not p.get("basis"):
        errors.append(
            f"{where}: a quadrant needs 'basis': where the positions come from (measured values, or the document's own judgment)"
        )
    for it in items:
        if not (_is_num(it.get("x")) and _is_num(it.get("y")) and 0 <= it["x"] <= 1 and 0 <= it["y"] <= 1):
            errors.append(f"{where}: '{it.get('label')}' needs 'x' and 'y' between 0 and 1")
            continue
        digest.append(
            f"    {it.get('label')}: x={it['x']}, y={it['y']}{'  [highlight]' if it.get('highlight') else ''}"
        )
    digest.append(f"    basis: {p.get('basis')}")


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
    items = need_list(p, "figures", where, errors, LIMITS["numbers"], warnings, "figures")
    for it in items:
        if "value" not in it or "label" not in it:
            errors.append(f"{where}: each figure needs 'value' and 'label'")
            continue
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
    items = need_list(p, "items", where, errors, LIMITS["bars"], warnings, "bars")
    count_highlights(items, where, warnings)
    unit = p.get("unit", "")
    for it in items:
        v = it.get("value")
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            errors.append(f"{where}: bar '{it.get('label')}' needs a numeric 'value'")
            continue
        if v < 0:
            errors.append(
                f"{where}: bar '{it.get('label')}' is negative; bars start at zero, so use a table or an 'svg' panel"
            )
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
    items = need_list(p, "items", where, errors, 10, warnings, "lines")
    count_highlights(items, where, warnings)
    for k in ("from", "to"):
        if not p.get(k):
            errors.append(
                f"{where}: a slope needs '{k}', the label of the {'first' if k == 'from' else 'second'} state, such as '2020'"
            )
    unit = p.get("unit", "")
    for it in items:
        if not _is_num(it.get("before")) or not _is_num(it.get("after")):
            errors.append(f"{where}: '{it.get('label')}' needs numeric 'before' and 'after'")
            continue
        digest.append(
            f"    {it.get('label')}: {num(it['before'])} → {num(it['after'])} {unit}".rstrip()
            + ("  [highlight]" if it.get("highlight") else "")
        )
    if p.get("y_from_zero") is False and not p.get("y_note"):
        errors.append(f"{where}: 'y_from_zero' is false, so add 'y_note' stating where the scale starts and why")
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
    groups = need_list(p, "groups", where, errors, 6, warnings, "groups")
    count_highlights(groups, where, warnings)
    for g in groups:
        vals = g.get("values") if isinstance(g, dict) else None
        if not isinstance(vals, list) or not vals or not all(_is_num(v) for v in vals):
            errors.append(
                f"{where}: group '{g.get('label') if isinstance(g, dict) else g}' needs a non-empty list of numeric 'values'"
            )
            continue
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
    cols = need_list(p, "columns", where, errors)
    rows = need_list(p, "rows", where, errors, LIMITS["rows"], warnings, "rows")
    for r, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != len(cols):
            errors.append(
                f"{where}: row {r + 1} has {len(row) if isinstance(row, list) else '?'} cells for {len(cols)} columns"
            )
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
    svg = str(p.get("svg", "")).strip()
    if not svg.startswith("<svg") or not svg.endswith("</svg>"):
        errors.append(f"{where}: 'svg' must be one <svg>…</svg> element")
    if "viewBox" not in svg:
        errors.append(f"{where}: the svg needs a viewBox and no fixed width or height")
    parser = _SvgCheck()
    parser.feed(svg)
    parser.close()
    for problem in dict.fromkeys(parser.problems):  # each problem once, in order
        errors.append(f"{where}: the svg must not contain {problem}")
    if not p.get("alt"):
        errors.append(f"{where}: an 'svg' panel needs 'alt': a description of its essential information")
    digest.append(f"    custom svg; alt: {p.get('alt', '')}")


def v_svg(p):
    svg = re.sub(r"^<svg", f'<svg role="img" aria-label="{esc(p["alt"])}"', p["svg"].strip(), count=1)
    return svg, f"<p>{esc(p['alt'])}</p>"


def t_svg(p, W, g):
    return twrap("[Diagram] " + p["alt"], W)


# ---------- lanes: check, HTML, text ----------


def check_lanes(p, where, errors, warnings, digest):
    actors = need_list(p, "actors", where, errors, LIMITS["lanes_actors"], warnings, "actors")
    steps = need_list(p, "steps", where, errors, LIMITS["lanes_steps"], warnings, "steps")
    count_highlights(steps, where, warnings)
    names = set(map(str, actors))
    prev = None
    for s in steps:
        if not isinstance(s, dict) or not s.get("label") or str(s.get("actor")) not in names:
            errors.append(f"{where}: each step needs a 'label' and an 'actor' from 'actors'")
            continue
        hand = f"  (hand-off from {prev})" if prev is not None and prev != str(s["actor"]) else ""
        digest.append(f"    {s['actor']}: {s['label']}{hand}{'  [highlight]' if s.get('highlight') else ''}")
        prev = str(s["actor"])


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
    for key in ("input", "decider"):
        if not p.get(key):
            errors.append(f"{where}: a fork needs '{key}'")
    branches = need_list(p, "branches", where, errors, LIMITS["fork_branches"], warnings, "branches")
    if len(branches) < 2:
        errors.append(f"{where}: a fork needs two to four branches")
    count_highlights(branches, where, warnings)
    digest.append(f"    {p.get('input')} → {p.get('decider')}")
    for b in branches:
        if not isinstance(b, dict) or not b.get("label") or b.get("outcome") not in OUTCOMES:
            errors.append(f"{where}: each branch needs a 'label' and an 'outcome' of {', '.join(OUTCOMES)}")
            continue
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

# Every kind needs a check, a visual and a text form; fail at start-up, not later in one output format.
for _name, _table in (("PANEL_CHECKS", PANEL_CHECKS), ("VISUALS", VISUALS), ("TEXT", TEXT)):
    if set(_table) != set(KINDS):
        raise RuntimeError(
            f"{_name} does not match KINDS: missing {sorted(set(KINDS) - set(_table))}, extra {sorted(set(_table) - set(KINDS))}"
        )


def visual_of(p, spec):
    """A panel's (visual HTML, data HTML). A map draws the spec's document, so it gets the spec."""
    return v_map(p, spec) if p["kind"] == "map" else VISUALS[p["kind"]](p)


def text_of(p, W, g, spec):
    """A panel's plain-text lines."""
    return t_map(p, W, g, spec) if p["kind"] == "map" else TEXT[p["kind"]](p, W, g)


# ---------- page ----------

TEMPLATE = (HERE / "show.html").read_text(encoding="utf-8")
# page.css is the look shared with design-better's canvas and research-better's board; show.css adds what only this
# page shows: the slides, the strip and the presentation.
CSS = (HERE / "page.css").read_text(encoding="utf-8") + (HERE / "show.css").read_text(encoding="utf-8")
# page.js is the conversation shared with the other pages that talk to the agent; show.js is this page alone.
JS = (HERE / "page.js").read_text(encoding="utf-8") + (HERE / "show.js").read_text(encoding="utf-8")
HTML_KINDS = ("bars", "numbers", "table", "text")  # drawn in HTML, so they reflow on a narrow screen
# Every other kind is an 800-wide drawing: on a phone its text would shrink below reading size, so the page shows its
# text version there instead.
NARROW_KINDS = tuple(k for k in KINDS if k not in HTML_KINDS)
# CSS variables of a slide, by the colour names the drawings use. A project's `style` sets them.
THEME = {
    "cream": "--s-bg",
    "linen": "--s-tint",
    "sand": "--s-sand",
    "terracotta": "--s-point",
    "moss": "--s-good",
    "umber": "--s-actor",
    "ink": "--s-ink",
    "heading": "--s-head",
    "muted": "--s-muted",
    "line": "--s-line",
}
HEX_VAR = {C[name].lower(): f"var({var}, {C[name]})" for name, var in THEME.items()}
STYLE_KEYS = {
    "background": "--s-bg",
    "tint": "--s-tint",
    "ink": "--s-ink",
    "heading": "--s-head",
    "muted": "--s-muted",
    "line": "--s-line",
    "point": "--s-point",
    "serif": "--s-serif",
    "sans": "--s-sans",
}
COLOUR = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})|(?:rgb|rgba|hsl|hsla)\([0-9.,%\s/]+\)")
FONT_STACK = re.compile(r"[A-Za-z0-9 ,'\"-]+")
START_TAG = re.compile(r"<([a-zA-Z][\w:-]*)((?:\s+[^\s=>/]+(?:=\"[^\"]*\")?)*)\s*(/?)>")
PAINT = re.compile(r'\s(fill|stroke|stop-color|font-family)="([^"]*)"')


def themed(markup: str) -> str:
    """Draw with the slide's variables: each palette colour and the sans font in a tag becomes var(--s-...) in its
    style, so a project's style restyles the drawings too. Other values stay as they are."""

    def fix(m):
        attrs, decls = m.group(2), []

        def take(a):
            name, value = a.group(1), a.group(2)
            if name == "font-family" and "Space Grotesk" in value:
                decls.append(f"font-family:var(--s-sans, {SANS})")
                return ""
            if value.lower() in HEX_VAR:
                decls.append(f"{name}:{HEX_VAR[value.lower()]}")
                return ""
            return a.group(0)

        attrs = PAINT.sub(take, attrs)
        if not decls:
            return m.group(0)
        style = re.search(r'\sstyle="([^"]*)"', attrs)
        if style:
            attrs = attrs.replace(style.group(0), f' style="{style.group(1).rstrip(";")};{";".join(decls)}"')
        else:
            attrs += f' style="{";".join(decls)}"'
        return f"<{m.group(1)}{attrs}{m.group(3)}>"

    return START_TAG.sub(fix, markup)


def style_css(spec) -> str:
    """The project's slide style, as CSS variables on .slide; the frame keeps the better-ai look."""
    style = spec.get("style") or {}
    decls = [f"{STYLE_KEYS[k]}:{v}" for k, v in style.items() if k in STYLE_KEYS]
    return f".slide {{ {'; '.join(decls)}; }}" if decls else ""


OPENING_PART = "The question"


def slug(text) -> str:
    """The anchor GitHub gives a heading: lower case, punctuation dropped, spaces as hyphens."""
    return re.sub(r"[^\w\- ]", "", str(text).strip().lower()).replace(" ", "-")


def section_link(spec, section):
    """Where to read a section: a link when the document has an address, else the section's name."""
    address = (spec.get("document") or {}).get("address")
    if not address:
        return esc(section), plain(section)
    url = str(address).split("#")[0] + "#" + slug(section)
    return f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(section)}</a>', f"{section} <{url}>"


def source_parts(spec, src):
    """A slide's source as (text, section)."""
    if isinstance(src, dict):
        return src.get("text", ""), src.get("section")
    return src or "", None


def source_html(spec, src):
    text, section = source_parts(spec, src)
    if not text and not section:
        return ""
    read = f' <span class="read">Read: {section_link(spec, section)[0]}{stop(section)}</span>' if section else ""
    return f'<p class="src">{rich(text)}{read}</p>'


def source_text(spec, src, markdown=False):
    text, section = source_parts(spec, src)
    if not text and not section:
        return ""
    out = plain(text, markdown)
    if section:
        address = (spec.get("document") or {}).get("address")
        if markdown and address:
            out += f" Read: [{section}]({str(address).split('#')[0]}#{slug(section)}){stop(section)}"
        else:
            out += f" Read: {section_link(spec, section)[1]}{stop(section)}"
    return out.strip()


def overview_of(spec):
    return next((p for p in spec["panels"] if isinstance(p, dict) and p.get("overview")), None)


def mini_overview(ov, focus):
    """A small copy of the overview with the slide's items marked: orientation only, not a control."""
    focus = set(map(str, _as_list(focus)))
    kind = ov["kind"]
    MW = 340
    body, edges = [], []
    if kind == "groups":
        nodes = [
            (g["label"], g["label"] in focus or any(str(it) in focus for it in g.get("items") or []))
            for g in ov["groups"]
        ]
    else:
        nodes = [(lab, lab in focus) for lab in overview_labels(ov)]
    n = len(nodes)
    if kind == "concept":
        order, _ = _layers(ov["nodes"], ov["edges"])
        by_id = {x["id"]: x["label"] for x in ov["nodes"]}
        rows = max(len(col) for col in order)
        H = 22 * rows + 26
        pos = {}
        for k, col in enumerate(order):
            x = 14 + (MW - 28) * (k / max(len(order) - 1, 1))
            for j, i in enumerate(col):
                pos[by_id[i]] = (x, 12 + (H - 34) * ((j + 0.5) / len(col)))
        for e in ov["edges"]:
            (x1, y1), (x2, y2) = pos[by_id[e["from"]]], pos[by_id[e["to"]]]
            edges.append(
                f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{C["sand"]}" stroke-width="1"/>'
            )
        points = [(lab, on, *pos[lab]) for lab, on in nodes]
        labelled = [pt for pt in points if pt[1]]
    else:
        H = 46
        xs = [14 + (MW - 28) * (k / max(n - 1, 1)) if n > 1 else MW / 2 for k in range(n)]
        points = [(lab, on, x, 12) for (lab, on), x in zip(nodes, xs, strict=True)]
        if kind != "groups":
            edges.append(
                f'<line x1="{xs[0]:.1f}" y1="12" x2="{xs[-1]:.1f}" y2="12" stroke="{C["sand"]}" stroke-width="1.2"/>'
            )
        labelled = points if n <= 4 else [pt for pt in points if pt[1]]
    for _lab, on, x, y in points:
        if kind == "groups":
            body.append(
                f'<rect x="{x - 5:.1f}" y="{y - 5:.1f}" width="10" height="10" fill="{C["terracotta"] if on else C["cream"]}" stroke="{C["terracotta"] if on else C["muted"]}" stroke-width="1.5"/>'
            )
        else:
            body.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{6 if on else 4.5}" fill="{C["terracotta"] if on else C["cream"]}" stroke="{C["terracotta"] if on else C["muted"]}" stroke-width="1.5"/>'
            )
    if kind == "concept":  # nodes sit close together: name the marked ones in one line under the drawing
        names = ", ".join(lab for lab, on, _x, _y in labelled)
        body.append(text_el(MW / 2, H - 4, [tcut(names, 42)], 13.5, 700, C["heading"], "middle"))
    else:
        # Neighbouring labels join into one, centred under its marks, and each is cut to the room up to the next.
        runs = []
        for pt in labelled:
            if runs and points.index(pt) == points.index(runs[-1][-1]) + 1 and pt[1] and runs[-1][-1][1]:
                runs[-1].append(pt)
            else:
                runs.append([pt])
        centres = [sum(q[2] for q in r) / len(r) for r in runs]
        for j, r in enumerate(runs):
            left = centres[j] - (centres[j - 1] if j else -centres[j])
            right = (centres[j + 1] if j + 1 < len(runs) else 2 * MW - centres[j]) - centres[j]
            x, anchor, room = centres[j], "middle", min(left, right)
            if x < 40:  # at the left edge: the label runs right, up to half the gap to the next label
                anchor, room = "start", right / 2
            elif x > MW - 40:
                anchor, room = "end", left / 2
            text = ", ".join(q[0] for q in r)
            on = any(q[1] for q in r)
            body.append(
                text_el(
                    x,
                    34,
                    [tcut(text, max(int(room / 7.8), 4))],
                    13.5,
                    700 if on else 500,
                    C["heading"] if on else C["muted"],
                    anchor,
                )
            )
    marked = [lab for lab, on in nodes if on]
    label = "Where this slide sits in the overview: " + ", ".join(marked)
    return (
        f'<svg class="where" viewBox="0 0 {MW} {H}" role="img" aria-label="{esc(label)}" xmlns="http://www.w3.org/2000/svg">'
        + "".join(edges)
        + "".join(body)
        + "</svg>"
    )


def where_text(ov, focus, sep=" › "):
    if not ov or focus is None:
        return ""
    return f"Where we are: {', '.join(map(str, _as_list(focus)))} (in the overview: {sep.join(overview_labels(ov))})"


def details_html(p):
    """Each item's detail, hidden and numbered as in keyed(); the page shows one under the visual when the reader
    clicks a label, mark or row that carries its number."""
    out = []
    for k, lab, d in keyed_details(p):
        if not isinstance(d, dict):
            continue
        foot = [(rich(d["source"]), plain(d["source"]))] if d.get("source") else []
        if d.get("evidence"):
            foot.append((f"Evidence: {esc(d['evidence'])}", d["evidence"]))
        out.append(
            f'<div class="dt" data-k="{k}" data-label="{esc(lab)}"><b>{esc(lab)}</b><p>{rich(d.get("text", ""))}</p>'
            + (f'<p class="dsrc">{" ".join(f + stop(t) for f, t in foot)}</p>' if foot else "")
            + "</div>"
        )
    return f'<div class="dts" hidden>{"".join(out)}</div>' if out else ""


def share_scale(a, b):
    """Copies of two compare sides of the same numeric kind, set to draw on one scale."""
    kind = a.get("kind")
    if kind != b.get("kind") or kind not in SHARED_SCALE:
        return a, b
    a, b = dict(a), dict(b)
    if kind == "bars":
        a["max"] = b["max"] = max(
            [it["value"] for s in (a, b) for it in s["items"]] + [a.get("max", 0), b.get("max", 0)]
        )
    elif kind == "dots":
        vals = [v for s in (a, b) for g in s["groups"] for v in g["values"]]
        a["_range"] = b["_range"] = (min(axis_start(s, "x", vals) for s in (a, b)), max(vals))
    elif kind in ("slope", "line"):
        if kind == "slope":
            vals = [v for s in (a, b) for it in s["items"] for v in (it["before"], it["after"])]
        else:
            vals = [pt[1] for s in (a, b) for ser in s["series"] for pt in ser["points"]]
        a["_range"] = b["_range"] = (min(axis_start(s, "y", vals) for s in (a, b)), max(vals))
    else:
        xs = [pt["x"] for s in (a, b) for pt in s["points"]]
        ys = [pt["y"] for s in (a, b) for pt in s["points"]]
        a["_xrange"] = b["_xrange"] = (min(axis_start(s, "x", xs) for s in (a, b)), max(xs))
        a["_yrange"] = b["_yrange"] = (min(axis_start(s, "y", ys) for s in (a, b)), max(ys))
    return a, b


def visual_html(p, spec):
    """A visual's HTML and its text version, which screen readers get in place of the drawing."""
    visual, data = visual_of(p, spec)
    visual, data = themed(visual), themed(data)
    if p["kind"] in NARROW_KINDS:  # on narrow screens show the text version instead of a shrunken drawing
        visual = f'<div class="wide">{visual}</div><div class="narrow" aria-hidden="true">{data}</div>'
    return visual, data


def slide_open(spec, total):
    doc = spec.get("document") or {}
    src = rich(spec["source"]) if spec.get("source") else ""
    if doc.get("title"):
        name = (
            f'<a href="{esc(doc["address"])}" target="_blank" rel="noopener">{esc(doc["title"])}</a>'
            if doc.get("address")
            else esc(doc["title"])
        )
        src += f'{" " if src else ""}<span class="read">Introduces {name}{stop(doc["title"])}</span>'
    return (
        f'<section class="slide t-title t-open" data-part="{esc(OPENING_PART)}" data-headline="{esc(spec["title"])}" '
        f'aria-roledescription="slide" aria-label="1 of {total}">'
        + (f'<p class="kicker">{esc(spec["question"])}</p>' if spec.get("question") else "")
        + f'<h2 class="title">{esc(spec["title"])}</h2>'
        + (f'<p class="summary">{rich(spec["summary"])}</p>' if spec.get("summary") else "")
        + (f'<p class="src">{src}</p>' if src else "")
        + "</section>"
    )


def slide_panel(spec, p, i, total, ov):
    """One panel as a slide, laid out by its template."""
    t = p.get("template", "visual")
    n = i + 1
    part = esc(p.get("part") or "")
    head = esc(p["headline"])
    attrs = (
        f'class="slide t-{t}" data-part="{part}" data-headline="{head}" '
        f'aria-roledescription="slide" aria-label="{n} of {total}"'
    )
    src = source_html(spec, p.get("source"))
    p = keyed(p)
    if t == "title":
        kicker = p.get("part") or spec.get("question") or ""
        actions = "".join(
            f'<li><span>{esc(a["text"])}</span> <a href="#{a["panel"] + 1}" data-go="{a["panel"] + 1}">slide {a["panel"] + 1}</a></li>'
            for a in p.get("actions") or []
        )
        return (
            f"<section {attrs}>"
            + (f'<p class="kicker">{esc(kicker)}</p>' if kicker else "")
            + f'<h2 class="title">{head}</h2>'
            + (f'<p class="body">{rich(p["body"])}</p>' if p.get("body") else "")
            + (f'<ol class="actions">{actions}</ol>' if actions else "")
            + src
            + "</section>"
        )
    mini = themed(mini_overview(ov, p["focus"])) if ov is not None and p.get("focus") is not None else ""
    top = f'<div class="ptop"><span class="part">{part}</span>{mini}</div><h2 class="headline">{head}</h2>'
    if t == "statement":
        middle = (
            f'<div class="big"><p class="stat">{esc(p["figure"])}</p><p class="say">{rich(p["sentence"])}</p>'
            + (f'<p class="against">{rich(p["compare"])}</p>' if p.get("compare") else "")
            + "</div>"
        )
        return f"<section {attrs}>{top}{middle}{src}</section>"
    if t == "compare":
        a, b = share_scale({**p["a"], "headline": p["a"]["label"]}, {**p["b"], "headline": p["b"]["label"]})
        (va, da), (vb, db) = visual_html(a, spec), visual_html(b, spec)
        # Two drawings side by side would each shrink to half the slide and their text below reading size, so they
        # stack, at full width and on their shared scale. Kinds drawn in HTML sit side by side in one frame.
        side = a["kind"] in HTML_KINDS and b["kind"] in HTML_KINDS
        frame = ""
        if a["kind"] == b["kind"] == "bars":  # one label column, so both tracks have one length and one scale
            longest = max(len(str(it["label"])) for q in (a, b) for it in q["items"])
            frame = f' style="--labw:{min(longest * 0.56, 11):.1f}em"'
        used = evidence_used(a) | evidence_used(b)
        sides = "".join(
            f'<figure><figcaption{dattr(q)}>{esc(q["label"])}</figcaption><div class="vis">{v}</div>'
            f'<div class="sr">{d}</div></figure>'
            for q, v, d in ((a, va, da), (b, vb, db))
        )
        key = f'<p class="key">{themed(evidence_key(used))}</p>' if used else ""
        return (
            f'<section {attrs}>{top}<div class="compare{"" if side else " stacked"}"{frame}>{sides}</div>{key}'
            f'<div class="detail" hidden></div>{src}{details_html(p)}</section>'
        )
    visual, data = visual_html(p, spec)
    used = evidence_used(p)
    key = f'<p class="key">{themed(evidence_key(used))}</p>' if used else ""
    return (
        f'<section {attrs}>{top}<div class="vis">{visual}</div>{key}<div class="detail" hidden></div>'
        f'{src}{details_html(p)}<div class="sr">{data}</div></section>'
    )


def render(spec: dict) -> str:
    panels = spec["panels"]
    total = len(panels) + 1
    ov = overview_of(spec)
    slides = [slide_open(spec, total)] + [slide_panel(spec, p, i, total, ov) for i, p in enumerate(panels, 1)]
    fill = {
        "{{CSS}}": CSS,
        "{{STYLE}}": style_css(spec),
        "{{JS}}": JS,
        "{{LANG}}": esc(spec.get("lang", "en")),
        "{{TITLE}}": esc(spec["title"]),
        "{{QUESTION}}": f'<p class="question">{esc(spec["question"])}</p>' if spec.get("question") else "",
        "{{SLIDES}}": "".join(slides),
    }
    # One pass, so a placeholder inside the content is not filled in.
    return re.sub(r"\{\{[A-Z_]+\}\}", lambda m: fill.get(m.group(0), m.group(0)), TEMPLATE)


# ---------- plain text ----------


def panel_text(p, spec, W, g, markdown):
    """The body of one slide in text: its visual or visuals, figure or actions."""
    t = p.get("template", "visual")

    def block(q):
        lines = text_of(q, W, g, spec)
        return lines if not markdown or q["kind"] == "text" else ["```text"] + lines + ["```"]

    if t == "visual":
        return block(p)
    if t == "compare":
        a, b = share_scale(p["a"], p["b"])
        out = []
        for side, s in (("A", a), ("B", b)):
            out += ([f"**{side}: {s['label']}**", ""] if markdown else [f"{side}: {s['label']}", ""]) + block(s) + [""]
        return out[:-1]
    if t == "statement":
        out = [f"**{p['figure']}**" if markdown else str(p["figure"])] + twrap(plain(p["sentence"], markdown), W)
        return out + (twrap(plain(p["compare"], markdown), W) if p.get("compare") else [])
    out = twrap(plain(p["body"], markdown), W) if p.get("body") else []
    actions = p.get("actions") or []
    if actions:
        out += [""] if out else []
        out += [f"{k}. {a['text']} (slide {a['panel'] + 1})" for k, a in enumerate(actions, 1)]
    return out


def detail_lines(p, W, markdown, prefix="Detail"):
    out = []
    for lab, d in collect_details(p):
        if isinstance(d, dict):
            extra = [plain(d["source"], markdown)] if d.get("source") else []
            if d.get("evidence"):
                extra.append(f"evidence: {d['evidence']}")
            line = f"{prefix}, {lab}: {plain(d.get('text', ''), markdown)}" + (
                f" ({'; '.join(extra)})" if extra else ""
            )
            out += ["- " + line] if markdown else twrap(line, W)
    return out


def render_text(spec, width=72, ascii=False, markdown=False):
    g = GLYPHS["ascii" if ascii else "unicode"]
    W = width
    panels = spec["panels"]
    total = len(panels) + 1
    ov = overview_of(spec)
    out = []
    doc = spec.get("document") or {}
    if markdown:
        out += ([f"*{spec['question']}*", ""] if spec.get("question") else []) + [f"# {spec['title']}", ""]
        if spec.get("summary"):
            out += [spec["summary"], ""]
        if spec.get("source"):
            out += [spec["source"], ""]
        if doc.get("title"):
            name = f"[{doc['title']}]({doc['address']})" if doc.get("address") else doc["title"]
            out += [f"Introduces {name}{stop(doc['title'])}", ""]
    else:
        if spec.get("question"):
            out += twrap(spec["question"], W)
        out += twrap(spec["title"].upper(), W) + [g["h"] * min(W, len(spec["title"]) + 4)]
        if spec.get("summary"):
            out += twrap(plain(spec["summary"]), W)
        if spec.get("source"):
            out += twrap(plain(spec["source"]), W)
        if doc.get("title"):
            out += twrap(
                f"Introduces {doc['title']}" + (f" <{doc['address']}>." if doc.get("address") else stop(doc["title"])),
                W,
            )
        out.append("")
    for i, p in enumerate(panels, 1):
        n = i + 1
        where = where_text(ov, p.get("focus"), " > " if ascii else " › ")
        if markdown:
            out += [f"## {n}. {p['headline']}", ""]
            if p.get("part"):
                out += [f"*{p['part']}*", ""]
            if where:
                out += [f"*{where}*", ""]
        else:
            rule = f"{g['h'] * 2} {n}/{total} " + (f"{p['part']} " if p.get("part") else "")
            out += (
                [rule + g["h"] * max(W - len(rule), 0)] + (twrap(where, W) if where else []) + twrap(p["headline"], W)
            )
            out.append("")
        out += panel_text(p, spec, W, g, markdown)
        details = detail_lines(p, W, markdown)
        if details:
            out += [""] + details
        src = source_text(spec, p.get("source"), markdown)
        if src:
            out += (
                ["", ("> " if markdown else "") + "Source: " + src] if markdown else [""] + twrap("Source: " + src, W)
            )
        out.append("")
    return "\n".join(line.rstrip() for line in out) + "\n"


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
        elif tag == "li" or tag in ("p", "div", "br"):
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
                    named = [f"{h}: {c}" if h else c for h, c in zip(head[1:], cells[1:], strict=False) if c]
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


def sr_visual(p, spec):
    """A visual as sentences and value lists, with its highlighted items named."""
    if p["kind"] == "numbers":
        body = [f"{f['value']}: {f['label']}" + (" (highlighted)" if f.get("highlight") else "") for f in p["figures"]]
    elif p["kind"] == "text":
        body = [plain(b) for b in _as_list(p.get("body"))]
    else:
        visual, data = visual_of(p, spec)
        body = linear_lines(data or visual)
    hl = highlighted(p, spec) if p["kind"] not in ("numbers", "table") else []
    return body + (["Highlighted: " + ", ".join(hl) + "."] if hl else [])


def render_screen_reader(spec, width=72):
    """Plain sentences and value lists, with no box drawing, bars, rules or symbols that a screen reader reads aloud."""
    W, panels = width, spec["panels"]
    total = len(panels) + 1
    ov = overview_of(spec)
    doc = spec.get("document") or {}
    out = twrap(f"Slide 1 of {total}.", W)
    if spec.get("question"):
        out += twrap(f"Question: {spec['question']}", W)
    out += twrap(spec["title"], W)
    for key in ("summary", "source"):
        if spec.get(key):
            out += twrap(plain(spec[key]), W)
    if doc.get("title"):
        out += twrap(
            f"Introduces {doc['title']}" + (f" <{doc['address']}>." if doc.get("address") else stop(doc["title"])), W
        )
    out.append("")
    for i, p in enumerate(panels, 1):
        t = p.get("template", "visual")
        out += twrap(
            f"Slide {i + 1} of {total}" + (f", {p['part']}" if p.get("part") else "") + f": {p['headline']}", W
        )
        where = where_text(ov, p.get("focus"), ", then ")
        if where:
            out += twrap(where + ".", W)
        if t == "visual":
            body = sr_visual(p, spec)
        elif t == "compare":
            a, b = share_scale({**p["a"], "headline": p["a"]["label"]}, {**p["b"], "headline": p["b"]["label"]})
            body = []
            for side, s in (("First", a), ("Second", b)):
                body += [f"{side}, {s['label']}:"] + sr_visual(s, spec)
        elif t == "statement":
            body = [f"{p['figure']}: {plain(p['sentence'])}"] + ([plain(p["compare"])] if p.get("compare") else [])
        else:
            body = ([plain(p["body"])] if p.get("body") else []) + [
                f"{k}. {a['text']}, slide {a['panel'] + 1}." for k, a in enumerate(p.get("actions") or [], 1)
            ]
        for line in body + detail_lines(p, W, False):
            out += twrap(line, W)
        src = source_text(spec, p.get("source"))
        if src:
            out += twrap(f"Source: {src}", W)
        out.append("")
    return "\n".join(line.rstrip() for line in out) + "\n"


# ---------- The conversation: answers.jsonl, one JSON event per line, next to the page ----------

LOG, SEEN, ADDRESS = "answers.jsonl", ".answers-seen", ".server"
METHODS = ("comment", "delete", "note", "accept", "reopen")  # what the page may send
ITEMS = ("comment", "note")  # what the agent tracks with status


def conversation(folder: Path) -> page.Conversation:
    return page.Conversation(folder, LOG, SEEN, ADDRESS, ITEMS, "agent", "render SPEC --out FILE --serve")


# ---------- render --serve ----------


def serve(path: Path, port: int, open_browser: bool) -> None:
    """Serve the page from disk, so a new render shows on reload, and record each action the page sends."""
    conv = conversation(path.parent)

    class Handler(page.Handler):
        conversation = conv
        methods = METHODS

        def do_GET(self):
            if not self.local():
                return self.send_error(403)
            if self.conversation_get():
                return None
            if self.path in ("/", "/index.html") or self.path.startswith("/?"):
                return self.send(200, path.read_bytes(), "text/html; charset=utf-8")
            if self.path == "/rev":
                return self.send(200, str(path.stat().st_mtime_ns).encode(), "text/plain")
            self.send_error(404)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    conv.address.write_text(url, encoding="utf-8")
    conv.seen.write_text(str(len(conv.lines())), encoding="utf-8")
    print(f"Serving {path} at {url}. Each action the user takes is printed here as one JSON line.", flush=True)
    if open_browser and not webbrowser.open(url):
        print(
            "Could not open a browser on this machine. If the user's browser runs on another machine, "
            "this address does not reach it.",
            flush=True,
        )
    page.stop_like_ctrl_c()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        conv.address.unlink(missing_ok=True)


# ---------- Command line ----------


def render_command(args) -> None:
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
        if args.serve:
            sys.exit("error: --serve works with --format html")
        text = (
            render_screen_reader(spec, args.width)
            if args.screen_reader
            else render_text(spec, args.width, args.ascii, args.format == "md")
        )
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
    print(f"\nwrote {out.resolve()}", flush=True)
    if args.serve:
        serve(out.resolve(), args.port, args.open)
    elif args.open and (out.parent / ADDRESS).exists():
        print("The page is already served: the open page loads the new slides once the user is not typing.")
    elif args.open and not webbrowser.open(out.resolve().as_uri()):
        print(
            "Could not open a browser on this machine: if the user's browser runs on another machine, this path does not reach it."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a short visual introduction to a document from a JSON spec.")
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("check", help="validate a spec and print every value it will show")
    c.add_argument("spec")
    r = sub.add_parser("render", help="check a spec, then write the page (html) or print it as text (text, md)")
    r.add_argument("spec")
    r.add_argument(
        "--format",
        choices=("html", "text", "md"),
        default="html",
        help="html: a page to open; text: plain text for a terminal; md: Markdown with text diagrams in code blocks",
    )
    r.add_argument("--out", help="file to write; required for html, otherwise the text is printed")
    r.add_argument("--open", action="store_true", help="open the page in the default browser")
    r.add_argument("--serve", action="store_true", help="serve the page on 127.0.0.1 and record the user's actions")
    r.add_argument("--port", type=int, default=0, help="port to serve on (default: any free port)")
    r.add_argument("--width", type=int, default=72, help="text width in characters (text and md)")
    r.add_argument("--ascii", action="store_true", help="use only ASCII characters (text and md)")
    r.add_argument(
        "--screen-reader",
        action="store_true",
        help="text only: sentences and value lists, without box drawing, bars or rules that a screen reader reads aloud",
    )
    w = sub.add_parser("wait", help="wait for the user's next actions on the served page, print them and exit")
    w.add_argument("dir")
    w.add_argument("--timeout", type=float, default=3600, help="seconds to wait (default: 3600)")
    rp = sub.add_parser("reply", help="show a reply from the agent in the served page")
    rp.add_argument("dir")
    rp.add_argument("text")
    rp.add_argument("--to", metavar="ID", help="the id of the comment or message the reply answers")
    t = sub.add_parser(
        "status",
        help="mark items as seen, asked (waiting for the user), working or done; "
        "accepted only when the user accepted in words",
    )
    t.add_argument("dir")
    t.add_argument("state", choices=page.STATES)
    t.add_argument("ids", nargs="+", metavar="ID")
    pd = sub.add_parser("pending", help="list the items that are not done or accepted")
    pd.add_argument("dir")
    args = parser.parse_args()

    if args.command in ("check", "render"):
        return render_command(args)
    folder = Path(args.dir).expanduser().resolve()
    if args.command == "wait":
        sys.exit(conversation(folder).wait(args.timeout))
    elif args.command == "reply":
        conversation(folder).reply(args.text, args.to)
    elif args.command == "status":
        conversation(folder).set_status(args.state, args.ids)
    else:
        conversation(folder).pending()


if __name__ == "__main__":
    main()
