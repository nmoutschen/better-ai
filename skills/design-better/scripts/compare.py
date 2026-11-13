#!/usr/bin/env python3
"""Put versions of a screen side by side on one page, at the same screen sizes, so the user can compare them.

Usage:
  python3 compare.py VERSION... --out FILE [--title T] [--question Q] [--width WxH ...] [--open]

VERSION is LABEL=SOURCE or SOURCE. SOURCE is an HTML file, embedded into the page, or an http(s) address, loaded
when the page is viewed. Without a LABEL, versions are labelled A, B, C in order.

Every version is shown side by side, in a frame of each screen size, scaled down by the same amount to fit. Each
version can also be opened at full size. When the two versions are labelled Before and After, the page also offers
a view that switches between them in the same place, which shows small changes at one spot better than looking
from one to the other. The page styles only its own labels: each version keeps the styles it brings.
"""

import argparse
import html
import json
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

FONTS = ("https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400"
         "&family=Space+Grotesk:wght@400;500;700&display=swap")

# The n14n "Journal" tokens, as in research-better's board.html.
CSS = """
:root { --cream:#FFFCF7; --linen:#F2EDE5; --sand:#C4B69C; --terracotta:#E8725C; --umber:#5C4033;
  --moss-dark:#66795A; --ink:#33302B;
  /* ISO 3664 asks for a neutral, matte surround when judging colour: Munsell N8 grey behind the versions. */
  --surround:#C9C9C9; --heading:#1C1A17; --muted:#78736B; --line:#DDD6CA;
  --serif:'Libre Baskerville', Georgia, serif; --sans:'Space Grotesk', -apple-system, sans-serif;
  --saya:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='130' height='75' viewBox='0 0 10 10' preserveAspectRatio='none'%3E%3Cpath fill='%23FFFCF7' fill-opacity='0.22' d='m0-1 4 4 1-1-1-1 1-1 1 1 1-1 1 1-7 7-1-1 1-1-1-1 1-1 1 1 1-1-4-4m0 8 3 3h-3m11 0-4-4-1 1 1 1-1 1-1-1-1 1-1-1 7-7 1 1-1 1 1 1-1 1-1-1-1 1 4 4m0-8-3-3h3'/%3E%3C/svg%3E"); }
* { box-sizing:border-box; }
body { margin:0; background:var(--cream); color:var(--ink); font:400 15px/1.55 var(--sans); -webkit-font-smoothing:antialiased;
  --pad:max(40px, (100% - 110rem) / 2); }
.band { height:10px; background:var(--umber) var(--saya); background-size:13px 7.5px; }
.band--thin { height:6px; }
/* The banner above the versions is an inverted n14n block: umber with cream text. */
header { padding:24px var(--pad) 12px; background:var(--umber); color:var(--cream); }
main { padding:4px var(--pad) 36px; background:var(--surround); color:var(--ink); }
h1 { font:700 28px/1.2 var(--serif); color:var(--cream); margin:0 0 8px; }
.question { font:400 17px/1.6 var(--serif); margin:0 0 16px; max-width:65ch; }
.controls { position:sticky; top:0; z-index:2; background:var(--umber); color:var(--cream);
  padding:10px var(--pad); display:flex; flex-wrap:wrap; gap:8px 28px; align-items:center; }
.seg { display:inline-flex; border:1px solid var(--cream); }
.seg button { border:0; background:transparent; color:var(--cream); padding:7px 14px; cursor:pointer;
  font:700 12px var(--sans); letter-spacing:.08em; text-transform:uppercase; }
.seg button + button { border-left:1px solid var(--cream); }
.seg button[aria-pressed="true"] { background:var(--cream); color:var(--umber); }
.seg[hidden] { display:none; }
/* Scroll together is a separate setting from the view, so it uses moss instead of umber. */
.seg--moss { border-color:var(--moss-dark); }
.seg--moss button { color:var(--cream); }
.seg--moss button[aria-pressed="true"] { background:var(--moss-dark); color:var(--cream); }
.full { border:0; background:none; padding:4px 0; cursor:pointer; font:700 12px var(--sans);
  letter-spacing:.08em; text-transform:uppercase; color:var(--ink); }
:focus-visible { outline:2px solid var(--terracotta); outline-offset:2px; }
.hint { color:var(--cream); font-size:13px; margin:0; }
h2 { font:700 12px var(--sans); letter-spacing:.1em; text-transform:uppercase; color:var(--ink);
  border-top:2px solid var(--ink); padding-top:10px; margin:28px 0 14px; }
.row { display:grid; grid-template-columns:repeat(var(--n), minmax(0, 1fr)); gap:32px; align-items:start; }
/* Frames narrow enough to fit at full size sit next to each other, not spread across the page. */
.row.packed { grid-template-columns:repeat(var(--n), max-content); }
/* With two versions, packed frames sit in the middle of the page. */
.row.packed.pair { justify-content:center; }
main.switch .row.packed.pair { grid-template-columns:max-content; }
figure { margin:0; min-width:0; }
.label { display:flex; justify-content:space-between; align-items:baseline; gap:12px; margin:0 0 8px; }
.label b { font:700 15px/1.3 var(--sans); color:var(--heading); overflow-wrap:anywhere; }
.screen { position:relative; overflow:auto; border:1px solid var(--line); background:#fff; max-width:100%; }
.screen iframe { display:block; border:0; transform-origin:0 0; background:#fff; }
.scaled main .screen { overflow:hidden; }
figcaption { font-size:13px; color:var(--ink); border-top:1px solid var(--ink); margin-top:8px; padding-top:6px; }
/* Switch view: the two frames of a row sit in one place; only the current one shows. */
main.switch .row { grid-template-columns:minmax(0, 1fr); }
main.switch .row { position:relative; }
/* The hidden version stays laid out, so it keeps scrolling with the shown one. */
main.switch figure:not(.current) { position:absolute; top:0; left:0; width:100%; visibility:hidden; }
dialog { border:0; padding:0; max-width:calc(100vw - 32px); max-height:calc(100vh - 32px); background:var(--cream); }
dialog::backdrop { background:rgba(28,26,23,.6); }
dialog .bar { display:flex; justify-content:space-between; align-items:baseline; gap:16px; padding:10px 16px; }
dialog .bar b { font:700 15px var(--sans); color:var(--heading); }
dialog .screen { margin:0 16px 16px; max-height:calc(100vh - 100px); }
.foot { padding:6px var(--pad); font-size:12px; color:var(--muted); }
"""

JS = """
(function () {
  var main = document.querySelector('main'), hint = document.querySelector('.hint');
  var labels = JSON.parse(main.dataset.labels), current = 0;
  var viewButtons = document.querySelectorAll('[data-view]'), pickButtons = document.querySelectorAll('[data-pick]');
  var pick = document.querySelector('.pick'), together = document.querySelector('#together');
  together.addEventListener('click', function () { together.setAttribute('aria-pressed', String(together.getAttribute('aria-pressed') !== 'true')); });
  function fit() {
    document.querySelectorAll('main .row').forEach(function (row) {
      var frames = row.querySelectorAll('figure:not([hidden]) iframe'), n = main.classList.contains('switch') ? 1 : frames.length;
      var w = +frames[0].getAttribute('width');
      row.classList.toggle('packed', n * w + (n - 1) * 32 + n * 2 <= row.clientWidth);
      row.classList.toggle('pair', labels.length === 2);
    });
    document.querySelectorAll('main .screen').forEach(function (box) {
      var frame = box.firstElementChild, w = +frame.getAttribute('width'), h = +frame.getAttribute('height');
      var row = box.closest('.row'), packed = row.classList.contains('packed');
      var room = packed ? w + 2 : box.parentElement.clientWidth;
      if (room <= 0) return;
      var scale = Math.min(1, (room - 2) / w);
      frame.style.transform = 'scale(' + scale + ')';
      box.style.width = Math.ceil(w * scale + 2) + 'px';
      box.style.height = Math.ceil(h * scale + 2) + 'px';
      box.parentElement.querySelector('figcaption').textContent =
        w + ' × ' + h + ' px, ' + (scale < 1 ? 'shown at ' + Math.round(scale * 100) + '%' : 'actual size');
    });
  }
  // Scrolling: frames of one screen size scroll together. The position is matched between elements with the
  // same id in both versions, such as headings, so versions of different length stay on the same section.
  // This works only for versions embedded from files; a page loaded from an address cannot be followed.
  var quietUntil = new WeakMap();
  function tops(win, ids) {
    var doc = win.document, end = doc.documentElement.scrollHeight;
    var marks = [{ id: '', top: 0 }];
    ids.forEach(function (id) {
      var el = doc.getElementById(id);
      if (el) marks.push({ id: id, top: el.getBoundingClientRect().top + win.scrollY });
    });
    marks.push({ id: '', top: end });
    return marks;
  }
  function sharedIds(a, b) {
    return Array.prototype.map.call(a.document.querySelectorAll('[id]'), function (el) { return el.id; })
      .filter(function (id) { return id && b.document.getElementById(id); });
  }
  function match(from, to) {
    try {
      var src = from.contentWindow, dst = to.contentWindow, ids = sharedIds(src, dst);
      var a = tops(src, ids), b = tops(dst, ids), y = src.scrollY, k = 0;
      while (k < a.length - 2 && a[k + 1].top <= y) k++;
      var p = (y - a[k].top) / Math.max(1, a[k + 1].top - a[k].top);
      quietUntil.set(to, Date.now() + 150);
      dst.scrollTo(0, b[k].top + p * (b[k + 1].top - b[k].top));
    } catch (e) {}
  }
  function follow(frame) {
    if (together.getAttribute('aria-pressed') !== 'true' || (quietUntil.get(frame) || 0) > Date.now()) return;
    frame.closest('.row').querySelectorAll('iframe').forEach(function (other) { if (other !== frame) match(frame, other); });
  }
  function bind(frame) {
    try { frame.contentWindow.addEventListener('scroll', function () { follow(frame); }); } catch (e) { together.parentElement.hidden = true; }
  }
  var bound = new WeakSet();
  function bindOnce(frame) {
    var win; try { win = frame.contentWindow; } catch (e) { return; }
    if (!win || bound.has(win)) return;
    bound.add(win); bind(frame);
  }
  document.querySelectorAll('main iframe').forEach(function (frame) {
    frame.addEventListener('load', function () { bindOnce(frame); });
    try { if (frame.contentDocument.readyState === 'complete' && frame.contentDocument.body.childElementCount) bindOnce(frame); } catch (e) {}
  });
  function show(i) {
    var previous = current;
    current = i;
    document.querySelectorAll('main figure').forEach(function (f) { f.classList.toggle('current', +f.dataset.i === i); });
    pickButtons.forEach(function (b) { b.setAttribute('aria-pressed', String(+b.dataset.pick === i)); });
    fit();
    if (main.classList.contains('switch') && previous !== i) document.querySelectorAll('main .row').forEach(function (row) {
      match(row.querySelector('figure[data-i="' + previous + '"] iframe'), row.querySelector('figure[data-i="' + i + '"] iframe'));
    });
  }
  function view(name) {
    main.classList.toggle('switch', name === 'switch');
    viewButtons.forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.view === name)); });
    if (pick) pick.hidden = name !== 'switch';
    hint.textContent = name === 'switch' ? 'Press Space to switch between ' + labels.join(' and ') + '.' : hint.dataset.side;
    show(current);
  }
  viewButtons.forEach(function (b) { b.addEventListener('click', function () { view(b.dataset.view); }); });
  pickButtons.forEach(function (b) { b.addEventListener('click', function () { show(+b.dataset.pick); }); });
  document.addEventListener('keydown', function (e) {
    if (!main.classList.contains('switch') || document.querySelector('dialog[open]')) return;
    if (e.key === ' ' || e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
      if (e.target.tagName === 'BUTTON' && e.key === ' ') return;
      show((current + 1) % labels.length); e.preventDefault();
    }
  });
  var dialog = document.querySelector('dialog');
  document.querySelectorAll('figure .full').forEach(function (b) {
    b.addEventListener('click', function () {
      var src = b.closest('figure').querySelector('iframe'), copy = src.cloneNode(false);
      copy.style.transform = '';
      dialog.querySelector('.bar b').textContent = src.title;
      var box = dialog.querySelector('.screen'); box.replaceChildren(copy);
      box.style.width = ''; box.style.height = '';
      dialog.showModal();
    });
  });
  dialog.querySelector('.close').addEventListener('click', function () { dialog.close(); });
  document.body.classList.add('scaled');
  window.addEventListener('resize', fit);
  view('side');
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
    labels = [label for label, _ in loaded]
    before_after = [label.lower() for label in labels] == ["before", "after"]
    rows = []
    for w, h in sizes:
        figures = "".join(
            f'<figure data-i="{i}"><div class="label"><b>{esc(label)}</b>'
            f'<button type="button" class="full">Full size</button></div>'
            f'<div class="screen"><iframe title="{esc(label)}, {w} × {h} px" width="{w}" height="{h}" '
            f'{attr}></iframe></div><figcaption>{w} × {h} px</figcaption></figure>'
            for i, (label, attr) in enumerate(loaded))
        rows.append(f'<section><h2>Screen {w} × {h} px</h2><div class="row" style="--n:{len(loaded)}">{figures}</div></section>')
    controls = ""
    if before_after:
        controls += ('<div class="seg" role="group" aria-label="View">'
                     '<button type="button" data-view="side" aria-pressed="true">Side by side</button>'
                     '<button type="button" data-view="switch" aria-pressed="false">Switch in place</button></div>'
                     '<div class="seg pick" role="group" aria-label="Version shown" hidden>'
                     + "".join(f'<button type="button" data-pick="{i}" aria-pressed="false">{esc(label)}</button>'
                               for i, label in enumerate(labels)) + '</div>')
        side_hint = ""
    else:
        side_hint = "Every version has the same screen size and scale. Full size shows one version at its real size."
    controls += ('<div class="seg seg--moss"><button type="button" id="together" aria-pressed="true">'
                 'Scroll together</button></div>')
    question_html = f'<p class="question">{esc(question)}</p>' if question else ""
    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<link href="{FONTS}" rel="stylesheet">
<style>{CSS}</style></head>
<body><div class="band"></div>
<header><h1>{esc(title)}</h1>{question_html}</header>
<div class="controls">{controls}<p class="hint" data-side="{esc(side_hint)}">{esc(side_hint)}</p></div>
<main data-labels="{esc(json.dumps(labels))}">{"".join(rows)}</main>
<div class="band band--thin"></div>
<p class="foot">design-better by n14n.dev</p>
<dialog aria-label="Full size"><div class="bar"><b></b><button type="button" class="full close">Close</button></div><div class="screen"></div></dialog>
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
