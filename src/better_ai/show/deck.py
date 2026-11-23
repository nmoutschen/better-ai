"""The deck: a spec checked, drawn as a slide page, as plain text, and as sentences for a screen reader."""

from __future__ import annotations

import contextlib
import functools
import re
from html.parser import HTMLParser
from pathlib import Path

from .. import resources, schema
from . import lib
from .kinds import PANEL_CHECKS, _layers, check_map, evidence_key, evidence_used, text_of, visual_of
from .lib import (
    GLYPHS,
    KINDS,
    LIMITS,
    SANS,
    SHARED_SCALE,
    C,
    _as_list,
    axis_start,
    collect_details,
    dattr,
    esc,
    keyed,
    keyed_details,
    overview_labels,
    plain,
    rich,
    stop,
    tcut,
    text_el,
    twrap,
)

# ---------- validation ----------


def without_nulls(value):
    """The value with each object field that holds null left out: an optional field set to null means the same as one
    that is not there. A null inside a list, such as an empty cell, stays."""
    if isinstance(value, dict):
        return {k: without_nulls(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [without_nulls(v) for v in value]
    return value


@functools.lru_cache(maxsize=1)
def schemas() -> dict[str, dict]:
    """The schemas of a run of show-better: the shared ones and the package's own."""
    return schema.load_schemas(*resources.schema_sources("show"))


def spec_problems(spec) -> list[tuple[str, str]]:
    """(field, message) of each problem the spec's schema finds, its cross-checks (`show_spec`) included."""
    docs = schemas()
    context = schema.Context(Path.cwd(), "spec.json", {})
    return [(p.field, p.message) for p in schema.validate_instance(spec, docs["spec.schema.json"], docs, context)]


def worded(field: str, message: str) -> str:
    """The message for a field, with an old `note` or `read` on a panel saying where its text goes now."""
    old = re.fullmatch(r"panels\[\d+\]\.(note|read)", field)
    if not old:
        return message
    return (
        f"'{old[1]}' is no longer used: move it into 'source', the one line at the foot of each slide "
        "that says what the slide rests on and where to read it"
    )


def shape_errors(spec) -> list[str]:
    """What the schema finds wrong with the spec's shape, one line each, the field first."""
    found = []
    for field, message in dict.fromkeys(spec_problems(spec)):
        found.append(f"{field}: {worded(field, message)}")
    return found


def guarded(function, spec: dict) -> tuple[list[str], list[str], list[str]]:
    """What `function` answers for the spec; whatever the spec holds, errors and never a traceback."""
    try:
        return function(spec)
    except RecursionError:
        return ["(record): is nested too deeply to check"], [], []
    except Exception as error:
        return [f"(record): could not be checked: {type(error).__name__}"], [], []


def check(spec: dict) -> tuple[list[str], list[str], list[str]]:
    """Return (errors, warnings, digest lines). The shape is the schema's; the rest needs the rendering's knowledge."""
    return guarded(check_spec, spec)


def inspect(spec: dict) -> tuple[list[str], list[str], list[str]]:
    """The same for a spec whose shape was checked and which holds no nulls."""
    return guarded(inspect_spec, spec)


def check_spec(spec: dict) -> tuple[list[str], list[str], list[str]]:
    spec = without_nulls(spec)
    errors = shape_errors(spec)
    if errors:
        return errors, [], []
    return inspect_spec(spec)


def inspect_spec(spec: dict) -> tuple[list[str], list[str], list[str]]:
    """What the drawing knows about a spec whose shape is right: (errors, warnings, digest lines). `spec` has no nulls."""
    errors, warnings, digest = [], [], []
    panels = spec["panels"]
    if len(panels) > LIMITS["panels"]:
        warnings.append(
            f"{len(panels)} panels: more than {LIMITS['panels']} is long for one introduction; split it or cut panels"
        )
    if spec.get("kicker"):
        warnings.append("'kicker' is not shown: put the reader's question in 'question', the opening slide's kicker")
    if not spec.get("question"):
        warnings.append("no 'question': the opening slide asks the reader's question, and the title answers it")
    digest.append(f"TITLE: {spec['title']}")
    for key in ("question", "summary", "source"):
        if spec.get(key):
            digest.append(f"{key.upper()}: {spec[key]}")
    doc = spec.get("document")
    if doc:
        address = doc.get("address")
        secs = doc.get("sections")
        digest.append(
            f"DOCUMENT: {doc['title']}{(' <' + address + '>') if address else ''}"
            + (" — " + " · ".join(f"{x['id']} {x['label']}" for x in secs) if secs else "")
        )
        for x in secs or []:
            if len(str(x.get("gist", ""))) > 50:
                warnings.append(
                    f"document: the gist of '{x['label']}' is {len(x['gist'])} characters; keep it under 50, a few words"
                )
    for i, p in enumerate(panels, 1):
        where = f"panel {i}"
        template = p.get("template", "visual")
        head = p["headline"].strip()
        if len(head.split()) < 4 or not re.search(r"[.!?]$", head):
            warnings.append(
                f"{where}: headline '{head}' does not read as a full sentence; state the point, not the topic"
            )
        if len(head) > LIMITS["headline_chars"]:
            warnings.append(f"{where}: headline is {len(head)} characters; keep it under {LIMITS['headline_chars']}")
        part = p.get("part")
        if part and len(part) > LIMITS["part_chars"]:
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
                check_statement(p, where, warnings, digest)
            else:
                check_title(p, where, errors, digest)
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            errors.append(f"{where}: malformed {template} data ({exc})")
        check_source(p, where, spec, warnings, digest)
        check_details(p, digest)
        if p.get("overview"):
            digest.append("    overview: later panels may mark their place in it with 'focus'")
        if p.get("focus") is not None:
            digest.append(f"    where we are: {', '.join(map(str, _as_list(p['focus'])))}")
    if spec.get("style"):
        digest.append("STYLE: " + ", ".join(f"{k}={v}" for k, v in spec["style"].items()))
    if not errors:
        check_cuts(spec, warnings)
    return errors, warnings, digest


def check_cuts(spec, warnings):
    """Render each slide and warn about every label its drawing cuts with an ellipsis: the same limits as the page."""
    ov = overview_of(spec)
    total = len(spec["panels"]) + 1
    for i, p in enumerate(spec["panels"], 1):
        lib.CUTS = []
        # A malformed panel is reported by its own check.
        with contextlib.suppress(TypeError, ValueError, KeyError, AttributeError, IndexError):
            slide_panel(spec, p, i, total, ov)
        cuts, lib.CUTS = lib.CUTS, None
        for text, n in dict.fromkeys(cuts):
            warnings.append(
                f"panel {i}: '{text}' is cut to fit the drawing; shorten it to about {n} characters, or move the rest into a detail"
            )


def check_kind(p, where, spec, errors, warnings, digest):
    """Check a visual's data against what its drawing needs: a visual panel, or one side of a compare."""
    kind = p["kind"]
    if kind == "map":
        check_map(p, where, errors, warnings, digest, spec)
    else:
        PANEL_CHECKS[kind](p, where, errors, warnings, digest)


def check_compare(p, where, spec, errors, warnings, digest):
    sides = []
    for side in ("a", "b"):
        s = p[side]
        digest.append(f"    {side.upper()}: {s['label']} ({s['kind']})")
        check_kind(s, f"{where}, side {side}", spec, errors, warnings, digest)
        sides.append(s["kind"])
    if sides[0] == sides[1] and sides[0] in SHARED_SCALE:
        digest.append("    both sides drawn on one scale")


def check_statement(p, where, warnings, digest):
    if len(str(p["figure"])) > 14:
        warnings.append(f"{where}: figure '{p['figure']}' is long; a statement shows one short figure")
    if not p.get("compare"):
        warnings.append(
            f"{where}: no 'compare': a figure alone does not say whether it is large; give what it is compared to, "
            "such as 'against 89% before', or use another template"
        )
    digest.append(f"    {p['figure']} {p['sentence']}" + (f" ({p['compare']})" if p.get("compare") else ""))


def check_title(p, where, errors, digest):
    if p.get("body"):
        digest.append(f"    {p['body']}")
    for k, a in enumerate(p.get("actions") or [], 1):
        target = a["panel"]
        digest.append(f"    {k}. {a['text']} → panel {target} (slide {target + 1})")


def check_source(p, where, spec, warnings, digest):
    src = p.get("source")
    if not src:
        warnings.append(f"{where}: no 'source': say what the slide's claim rests on, and where to read it")
        return
    if isinstance(src, dict):
        if src.get("section") and not (spec.get("document") or {}).get("address"):
            warnings.append(
                f"{where}: source section '{src['section']}' is shown without a link: the 'document' has no 'address'"
            )
        digest.append(
            f"    source: {src.get('text', '')}" + (f" [read: {src['section']}]" if src.get("section") else "")
        )
    else:
        digest.append(f"    source: {src}")


def check_details(p, digest):
    for lab, d in collect_details(p):
        if not isinstance(d, dict):
            continue  # a detail where no kind has one is not drawn
        digest.append(
            f"    detail, {lab}: {d.get('text')}"
            + (f" ({d['source']})" if d.get("source") else "")
            + (f" [{d['evidence']}]" if d.get("evidence") else "")
        )


# ---------- page ----------

# The page opened as a file: the copy to read or publish. page.css is the look every live page shares; show.css adds
# what only this page shows: the slides, the strip and the presentation. page.js is the conversation shared with the
# other pages; show.js is this page alone.
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


def slides_html(spec: dict) -> str:
    """The opening slide and one slide per panel, as HTML."""
    panels = spec["panels"]
    total = len(panels) + 1
    ov = overview_of(spec)
    return "".join([slide_open(spec, total)] + [slide_panel(spec, p, i, total, ov) for i, p in enumerate(panels, 1)])


def render(spec: dict) -> str:
    """The page opened as a file: the slides without the conversation."""
    main = resources.read_text("show/main.html").replace(
        '<div class="stage"></div>', f'<div class="stage">{slides_html(spec)}</div>'
    )
    fill = {
        "{{CSS}}": resources.read_text("page/page.css") + resources.read_text("show/show.css"),
        "{{STYLE}}": style_css(spec),
        "{{PAGE_JS}}": resources.read_text("page/page.js"),
        "{{SHOW_JS}}": resources.read_text("show/show.js"),
        "{{LANG}}": esc(spec.get("lang", "en")),
        "{{TITLE}}": esc(spec["title"]),
        "{{QUESTION}}": f'<p class="question">{esc(spec["question"])}</p>' if spec.get("question") else "",
        "{{MAIN}}": main,
    }
    # One pass, so a placeholder inside the content is not filled in.
    return re.sub(r"\{\{[A-Z_]+\}\}", lambda m: fill.get(m.group(0), m.group(0)), resources.read_text("show/page.html"))


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
