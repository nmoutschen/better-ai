#!/usr/bin/env python3
"""Put versions of a screen side by side on one page, at the same screen widths, so the user can compare them.

Usage:
  python3 compare.py VERSION... --out FILE [--title T] [--question Q] [--width WxH ...] [--open]

VERSION is LABEL=SOURCE or SOURCE. SOURCE is an HTML file, embedded into the page, or an http(s) address, loaded
when the page is viewed. Without a LABEL, versions are labelled A, B, C in order. For a before and after, pass
Before=old.html After=new.html.

Each version is shown in a frame of the given screen size, scaled down to fit, so that every version gets the same
width, the same height and the same scale. The reader can switch from all versions side by side to one at a time,
with buttons or the arrow keys, to see small differences. The page styles only its own labels: each version keeps
the styles it brings.
"""

import argparse
import html
import re
import sys
import webbrowser
from pathlib import Path

DEFAULT_WIDTHS = ("1280x800", "375x700")
SIZE = re.compile(r"^(\d{3,4})(?:x(\d{3,4}))?$")
URL = re.compile(r"^https?://", re.I)
# A relative href or src: not absolute, not a fragment, not a data: or mailto: link.
RELATIVE_REF = re.compile(r"""(?:href|src)\s*=\s*["'](?![a-z][a-z0-9+.-]*:|//|#)[^"']+["']""", re.I)
HEAD = re.compile(r"<head[^>]*>", re.I)

CSS = """
:root { --cream:#FFFCF7; --linen:#F2EDE5; --umber:#5C4033; --terracotta:#E8725C; --ink:#33302B; --heading:#1C1A17;
  --muted:#78736B; --line:#DDD6CA; --sans:'Space Grotesk', -apple-system, 'Segoe UI', sans-serif; }
* { box-sizing:border-box; }
body { margin:0; background:var(--cream); color:var(--ink); font:400 15px/1.5 var(--sans); }
.band { height:8px; background:var(--umber); }
header, main { padding:0 max(24px, (100% - 110rem) / 2); }
header { padding-top:20px; padding-bottom:4px; }
h1 { font:700 24px/1.25 var(--sans); color:var(--heading); margin:0 0 4px; }
.question { margin:0 0 12px; max-width:70ch; }
.views { display:flex; flex-wrap:wrap; gap:6px; align-items:center; margin:0 0 4px; }
.views span { color:var(--muted); font-size:13px; margin-right:4px; }
.views button { font:500 14px var(--sans); color:var(--ink); background:var(--linen); border:1px solid var(--line);
  padding:4px 12px; cursor:pointer; }
.views button[aria-pressed="true"] { background:var(--umber); border-color:var(--umber); color:var(--cream); }
.views button:focus-visible { outline:2px solid var(--terracotta); outline-offset:2px; }
.hint { color:var(--muted); font-size:13px; margin:0 0 8px; }
h2 { font:700 12px var(--sans); letter-spacing:.1em; text-transform:uppercase; color:var(--muted);
  border-top:2px solid var(--line); padding-top:10px; margin:20px 0 10px; }
.row { display:grid; grid-template-columns:repeat(var(--n), minmax(0, 1fr)); gap:24px; align-items:start; }
main.single .row { grid-template-columns:minmax(0, 1fr); }
main.single figure:not(.current) { display:none; }
figure { margin:0; min-width:0; }
figcaption { font:700 14px var(--sans); color:var(--heading); margin:0 0 6px; overflow-wrap:anywhere; }
figcaption small { font-weight:400; color:var(--muted); margin-left:6px; }
.screen { overflow:auto; border:1px solid var(--line); background:#fff; max-width:100%; }
.screen iframe { display:block; border:0; transform-origin:0 0; background:#fff; }
.scaled .screen { overflow:hidden; }
"""

JS = """
(function () {
  var main = document.querySelector('main'), buttons = document.querySelectorAll('.views button');
  var figures = function (i) { return document.querySelectorAll('figure[data-i="' + i + '"]'); };
  var count = buttons.length - 1, view = -1;
  function fit() {
    document.querySelectorAll('.screen').forEach(function (box) {
      var frame = box.firstElementChild, w = +frame.getAttribute('width'), h = +frame.getAttribute('height');
      var room = box.parentElement.clientWidth - 2;
      if (room <= 0) return;
      var scale = Math.min(1, room / w);
      frame.style.transform = 'scale(' + scale + ')';
      box.style.width = Math.ceil(w * scale + 2) + 'px';
      box.style.height = Math.ceil(h * scale + 2) + 'px';
      var note = box.parentElement.querySelector('figcaption small');
      if (note) note.textContent = scale < 1 ? 'shown at ' + Math.round(scale * 100) + '%' : 'actual size';
    });
  }
  function show(i) {
    view = i;
    main.classList.toggle('single', i >= 0);
    document.querySelectorAll('figure').forEach(function (f) { f.classList.remove('current'); });
    if (i >= 0) figures(i).forEach(function (f) { f.classList.add('current'); });
    buttons.forEach(function (b) { b.setAttribute('aria-pressed', String(+b.dataset.view === i)); });
    fit();
  }
  buttons.forEach(function (b) { b.addEventListener('click', function () { show(+b.dataset.view); }); });
  document.addEventListener('keydown', function (e) {
    if (e.target.closest && e.target.closest('iframe, input, textarea')) return;
    if (e.key === 'ArrowRight') { show(view < 0 ? 0 : (view + 1) % count); e.preventDefault(); }
    if (e.key === 'ArrowLeft') { show(view < 0 ? count - 1 : (view - 1 + count) % count); e.preventDefault(); }
    if (e.key === 'Escape') show(-1);
  });
  document.body.classList.add('scaled');
  window.addEventListener('resize', fit);
  fit();
})();
"""


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def parse_version(arg: str, index: int) -> tuple:
    """LABEL=SOURCE or SOURCE. The part before '=' is a label only if it does not look like a path or an address."""
    label, sep, rest = arg.partition("=")
    if sep and rest and "/" not in label and ":" not in label and not label.lower().endswith((".html", ".htm")):
        return label.strip(), rest.strip()
    return chr(ord("A") + index), arg.strip()


def parse_size(text: str) -> tuple:
    m = SIZE.match(text.strip().lower())
    if not m:
        sys.exit(f"error: --width {text!r} is not WIDTH or WIDTHxHEIGHT in pixels, such as 375 or 375x700")
    w = int(m.group(1))
    return w, int(m.group(2)) if m.group(2) else (800 if w >= 768 else 700)


def frame_source(source: str, warnings: list) -> str:
    """The iframe attribute that loads one version: src for an address, srcdoc for a file."""
    if URL.match(source):
        warnings.append(f"{source} is loaded when the page is viewed: it shows only while that address answers.")
        return f'src="{esc(source)}"'
    path = Path(source).expanduser()
    if not path.is_file():
        sys.exit(f"error: {source} is not a file or an http(s) address")
    doc = path.read_text(encoding="utf-8", errors="replace")
    if RELATIVE_REF.search(doc):
        warnings.append(f"{source} links files by relative path: the page shows them only on this machine.")
        base = f'<base href="{esc(path.resolve().parent.as_uri())}/">'
        m = HEAD.search(doc)
        doc = doc[:m.end()] + base + doc[m.end():] if m else base + doc
    return f'srcdoc="{esc(doc)}"'


def render(versions: list, sizes: list, title: str, question: str) -> tuple:
    warnings = []
    loaded = [(label, frame_source(source, warnings)) for label, source in versions]
    buttons = ['<button type="button" data-view="-1" aria-pressed="true">Side by side</button>']
    buttons += [f'<button type="button" data-view="{i}" aria-pressed="false">{esc(label)}</button>'
                for i, (label, _) in enumerate(loaded)]
    rows = []
    for w, h in sizes:
        figures = "".join(
            f'<figure data-i="{i}"><figcaption>{esc(label)}<small></small></figcaption>'
            f'<div class="screen"><iframe title="{esc(label)}, {w} by {h} pixels" width="{w}" height="{h}" '
            f'loading="lazy" {attr}></iframe></div></figure>'
            for i, (label, attr) in enumerate(loaded))
        rows.append(f'<section><h2>Screen {w} × {h} px</h2><div class="row" style="--n:{len(loaded)}">{figures}</div></section>')
    question_html = f'<p class="question">{esc(question)}</p>' if question else ""
    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<style>{CSS}</style></head>
<body><div class="band"></div>
<header><h1>{esc(title)}</h1>{question_html}
<div class="views" role="group" aria-label="View"><span>View</span>{"".join(buttons)}</div>
<p class="hint">Left and right arrow keys step through the versions one at a time; Escape shows them side by side.</p>
</header>
<main>{"".join(rows)}</main>
<script>{JS}</script>
</body></html>
"""
    return page, warnings


def main() -> None:
    parser = argparse.ArgumentParser(description="Put versions of a screen side by side on one page.")
    parser.add_argument("versions", nargs="+", metavar="VERSION", help="LABEL=SOURCE or SOURCE: an HTML file or an http(s) address")
    parser.add_argument("--out", required=True, help="the HTML page to write")
    parser.add_argument("--title", default="Compare versions", help="the page heading")
    parser.add_argument("--question", default="", help="what the user should decide, shown under the heading")
    parser.add_argument("--width", action="append", metavar="WxH",
                        help=f"a screen size to show every version at; repeat for more (default: {' and '.join(DEFAULT_WIDTHS)})")
    parser.add_argument("--open", action="store_true", help="open the page in the default browser")
    args = parser.parse_args()

    if len(args.versions) > 26:
        sys.exit("error: at most 26 versions")
    versions = [parse_version(arg, i) for i, arg in enumerate(args.versions)]
    labels = [label for label, _ in versions]
    if len(set(labels)) != len(labels):
        sys.exit("error: two versions have the same label")
    sizes = [parse_size(s) for s in (args.width or DEFAULT_WIDTHS)]

    page, warnings = render(versions, sizes, args.title, args.question)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)
    print(f"wrote {out}")
    if args.open and not webbrowser.open(out.resolve().as_uri()):
        print("Could not open a browser on this machine. Give the user the path instead.")


if __name__ == "__main__":
    main()
