"""The compare page: the versions of a screen at the same screen sizes, from a unit's `canvas.json`.

`serve` (the shared page module) shows it live; `render` writes the same page as one file, `index.html`, in the unit.
The page builds its frames from the data `load` returns, so what the unit holds is never put into the page's markup.
A version's HTML is read from the unit, and the files it links by a relative path, when they are in the unit, are
embedded in it, so the page needs no other file.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import posixpath
import re
from typing import Any

from .. import cli, page, paths, resources
from ..paths import Refused, Unit
from ..skill import Skill
from .checks import version_path

SIZE = re.compile(r"^(\d{3,4})(?:x(\d{3,4}))?$")
# `src` of any element, and `href` of a <link> (a style sheet, an icon): files that a version needs to look right. A link
# to another page (<a href>) is left alone.
SRC = re.compile(r"""(\bsrc\s*=\s*)(["'])([^"'#?]+)(?:[?#][^"']*)?\2""", re.I)
LINK = re.compile(r"<link\b[^>]*>", re.I)
HREF = re.compile(r"""(\bhref\s*=\s*)(["'])([^"'#?]+)(?:[?#][^"']*)?\2""", re.I)
STYLE = re.compile(r"(<style\b[^>]*>)(.*?)(</style>)", re.I | re.S)
URL = re.compile(r"""url\(\s*(["']?)([^"')]+)\1\s*\)""", re.I)
REMOTE = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//|#)", re.I)
MAX_EMBED = 5_000_000  # bytes of one embedded file; a larger one stays a link
DEFAULTS = ("1280x800", "375x700")


def sizes(widths: list[str]) -> list[dict]:
    """The screen sizes of `canvas.json`: width, height and the name the page shows for each."""
    found = []
    for text in widths:
        match = SIZE.match(text)
        w = int(match.group(1))
        h = int(match.group(2)) if match.group(2) else (800 if w >= 768 else 700)
        found.append({"w": w, "h": h, "name": "Desktop" if w >= 1024 else "Tablet" if w >= 600 else "Mobile"})
    return found


def read_head(unit: Unit) -> dict:
    """`canvas.json` as a dict. A unit without a valid head has no page to show: the refusal says how to make one."""
    try:
        raw = paths.read_bytes(unit, "canvas.json")
    except FileNotFoundError:
        raise Refused(
            f"{unit.label}: there is no canvas.json. Make the unit first: create {unit.label} --by <your name>"
        ) from None
    try:
        head = json.loads(raw.decode("utf-8"))
    except (ValueError, RecursionError):
        head = None
    if not isinstance(head, dict):
        raise Refused(f"{unit.label}/canvas.json is not a JSON object. Fix it, then run check {unit.label}")
    return head


def _embed(unit: Unit, folder: str, link: str, warnings: set, seen: tuple = ()) -> str | None:
    """The `data:` address of the file a relative `link` (from a file in `folder`) names, if it is a file of the unit."""
    if REMOTE.match(link) or "\0" in link:
        return None
    path = version_path(posixpath.normpath(posixpath.join(folder, link)))
    try:
        if path is None:
            raise FileNotFoundError(link)
        data = paths.read_bytes(unit, path)
    except (FileNotFoundError, IsADirectoryError, NotADirectoryError, Refused):
        warnings.add(link)
        return None
    if len(data) > MAX_EMBED:
        warnings.add(link)
        return None
    kind = mimetypes.guess_type(path)[0] or "application/octet-stream"
    if kind == "text/css" and path not in seen:  # a style sheet's own url() are relative to the sheet
        text = _urls(unit, posixpath.dirname(path), data.decode("utf-8", "replace"), warnings, (*seen, path))
        data = text.encode("utf-8")
    if kind in ("text/css", "text/javascript", "application/javascript", "text/html"):
        kind += ";charset=utf-8"
    return f"data:{kind};base64,{base64.b64encode(data).decode('ascii')}"


def _urls(unit: Unit, folder: str, css: str, warnings: set, seen: tuple = ()) -> str:
    def swap(match):
        found = _embed(unit, folder, match.group(2), warnings, seen)
        return f'url("{found}")' if found else match.group(0)

    return URL.sub(swap, css)


def embed_links(unit: Unit, file: str, doc: str, warnings: set) -> str:
    """The version's HTML with the files it links by a relative path, when they are in the unit, embedded."""
    folder = posixpath.dirname(file)

    def source(match):
        found = _embed(unit, folder, match.group(3).strip(), warnings)
        return f"{match.group(1)}{match.group(2)}{found}{match.group(2)}" if found else match.group(0)

    def link(match):
        tag = match.group(0)
        return HREF.sub(lambda m: source(m), tag)

    def style(match):
        return match.group(1) + _urls(unit, folder, match.group(2), warnings) + match.group(3)

    doc = LINK.sub(link, doc)
    doc = SRC.sub(source, doc)
    return STYLE.sub(style, doc)


def version_data(unit: Unit, version: dict, warnings: list) -> dict:
    """One version as the page loads it: `srcdoc` (its HTML) for a file, `src` for an address."""
    label = version["label"]
    if "address" in version:
        warnings.append(f"{version['address']} is loaded when the page is viewed: it shows only while that address answers.")
        return {"label": label, "src": version["address"]}
    file = version["file"]
    path = version_path(file)
    try:
        if path is None:
            raise Refused(f"{file} is not a path inside the unit")
        doc = paths.read_bytes(unit, path).decode("utf-8", "replace")
    except (FileNotFoundError, IsADirectoryError, Refused):
        warnings.append(f"{file} is not a file of the unit.")
        return {"label": label, "srcdoc": f"<p style='font:16px sans-serif;padding:1em'>{_escape(file)} is not a file of the unit.</p>"}
    missed: set = set()
    doc = embed_links(unit, path, doc, missed)
    for link in sorted(missed):
        warnings.append(f"{file} links {link}, which is not a file of the unit: the page may not show it.")
    return {"label": label, "srcdoc": doc}


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def data_of(unit: Unit) -> tuple[dict, list]:
    """What the page shows, and what to warn about."""
    head = read_head(unit)
    warnings: list = []
    versions = [version_data(unit, v, warnings) for v in head.get("versions", []) if isinstance(v, dict) and "label" in v]
    widths = [w for w in head.get("widths", []) if isinstance(w, str) and SIZE.match(w)] or list(DEFAULTS)
    data = {
        "title": head.get("title") or "Versions",
        "question": head.get("question") or "",
        "sizes": sizes(widths),
        "versions": versions,
    }
    return data, warnings


def load(unit: Unit) -> dict:
    """`/data`: a head or a version that cannot be read is an `error` the page shows, never a failed request."""
    try:
        data, _ = data_of(unit)
    except Refused as error:
        return {"error": str(error), "title": "Versions", "question": "", "sizes": [], "versions": []}
    return data


def revision(unit: Unit) -> str:
    """What the page reloads on: the head, and each version's file."""
    parts = []
    try:
        head = read_head(unit)
    except Refused:
        return "missing"
    parts.append(json.dumps(head, sort_keys=True))
    for version in head.get("versions", []):
        path = version_path(version.get("file")) if isinstance(version, dict) else None
        if path is None:
            continue
        try:
            stat = unit.target(path).stat()
        except (OSError, Refused):
            parts.append(f"{path}:missing")
        else:
            parts.append(f"{path}:{stat.st_mtime_ns}:{stat.st_size}")
    return page.revision_of(*parts)


SPEC = page.PageSpec(
    title="Versions",
    agent="agent",
    main="design/canvas.html",
    load=load,
    events="canvas-events.schema.json",
    assets={"/canvas.css": "design/canvas.css", "/canvas.js": "design/canvas.js"},
    css=("/canvas.css",),
    js=("/canvas.js",),
    capabilities=("pins", "accept", "approve"),
    methods=("verdict",),
    empty="Nothing yet. Click any part of a version to comment on it, or write to the agent below.",
    revision=revision,
)


def register(skill: Skill) -> None:
    page.register(skill, SPEC)


# ---------------------------------------------------------------- render


def _script_json(value: Any) -> str:
    return json.dumps(value).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def static_page(data: dict) -> str:
    """The page as one file: the shell with its style sheets and scripts inlined, and the data it would fetch."""
    text = page.shell(SPEC)
    for url, name in SPEC.table().items():
        body = resources.read_text(name)
        if "</script" in body.lower() or "</style" in body.lower():
            raise ValueError(f"{name} holds a closing tag that would end its element")
        if url.endswith(".css"):
            tag, new = f'<link href="{url}" rel="stylesheet">', f"<style>\n{body}\n</style>"
        else:
            tag, new = f'<script src="{url}"></script>', f"<script>\n{body}\n</script>"
        if tag not in text:
            raise ValueError(f"the shell does not link {url}")
        text = text.replace(tag, new, 1)
    marker = '<script type="application/json" id="page-config">'
    return text.replace(marker, f'<script type="application/json" id="page-data">{_script_json(data)}</script>\n{marker}', 1)


def _render_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("unit", help="the unit to render, such as .design/pay-screen")


@cli.verb(
    "render",
    help="write the compare page as one file, index.html, in the unit; prints its path",
    arguments=_render_arguments,
    skills=("design-better",),
)
def render(args: argparse.Namespace, run: cli.Run) -> int:
    unit = paths.resolve_unit(args.unit, run.skill)
    data, warnings = data_of(unit)
    paths.write_atomic(unit, "index.html", static_page(data).encode("utf-8"))
    for warning in warnings:
        run.err(f"warning: {warning}")
    run.out(str(unit.target("index.html")))
    return 0
