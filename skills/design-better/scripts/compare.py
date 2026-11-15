#!/usr/bin/env python3
"""Put versions of a screen side by side on one page, at the same screen sizes, so the user can compare them.

Usage:
  python3 compare.py VERSION... --out FILE [--title T] [--question Q] [--width WxH ...] [--open] [--serve [--port N]]
  python3 compare.py --wait DIR [--timeout S]

VERSION is LABEL=SOURCE or SOURCE. SOURCE is an HTML file, embedded into the page, or an http(s) address, loaded
when the page is viewed. Without a LABEL, versions are labelled A, B, C in order.

Every version is shown side by side, in a frame of each screen size, scaled down by the same amount to fit. Each
version can also be opened at full size. When the two versions are labelled Before and After, the page also offers
a view that switches between them in the same place, which shows small changes at one spot better than looking
from one to the other. The page styles only its own labels: each version keeps the styles it brings.
"""

import argparse
import html
import http.server
import threading
import time
import urllib.request
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
MAX_BODY = 200_000
LOCAL_ORIGIN = re.compile(r"^http://(127\.0\.0\.1|localhost):\d+$")

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
/* The answer form: a cream block after the versions, in the page's own type. */
.answer { background:var(--cream); color:var(--ink); padding:28px var(--pad) 32px; border-top:2px solid var(--ink); }
.answer h2 { border:0; padding:0; margin:0 0 6px; }
.answer .ask { font:400 17px/1.6 var(--serif); margin:0 0 18px; max-width:65ch; }
.answer .opts { display:grid; grid-template-columns:repeat(auto-fit, minmax(16rem, 1fr)); gap:16px 32px; }
.answer fieldset { border:0; border-top:1px solid var(--ink); margin:0; padding:10px 0 0; min-width:0; }
.answer legend { font:700 15px var(--sans); color:var(--heading); padding:0; }
.answer label { display:block; font-size:14px; margin:8px 0 4px; }
.answer .choose { display:flex; gap:8px; align-items:center; margin:8px 0 0; font-size:15px; }
.answer input[type="radio"] { accent-color:var(--umber); width:18px; height:18px; margin:0; }
.answer textarea { width:100%; min-height:5.5em; font:400 15px/1.5 var(--sans); color:var(--ink); background:#fff;
  border:1px solid var(--sand); padding:8px 10px; resize:vertical; }
.answer .general { margin-top:20px; max-width:65ch; }
.answer .send { display:flex; flex-wrap:wrap; gap:12px 20px; align-items:center; margin-top:18px; }
.answer .send button { border:0; background:var(--umber); color:var(--cream); padding:10px 20px; cursor:pointer;
  font:700 13px var(--sans); letter-spacing:.08em; text-transform:uppercase; }
.answer .status { margin:0; font-size:14px; }
.answer .status.error { color:#9A3B2A; font-weight:700; }
.update { position:sticky; top:0; z-index:3; background:var(--moss-dark); color:var(--cream); padding:10px var(--pad);
  display:flex; gap:16px; align-items:center; }
.update[hidden] { display:none; }
.update button { border:1px solid var(--cream); background:transparent; color:var(--cream); padding:6px 12px; cursor:pointer;
  font:700 12px var(--sans); letter-spacing:.08em; text-transform:uppercase; }
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

  // The answer: one message per Send, with the choice and every note, so the agent gets the whole answer at once.
  var form = document.querySelector('form.answer'), status = form.querySelector('.status');
  var served = location.protocol === 'http:', rpcId = 0;
  if (!served) form.querySelector('.send button').textContent = 'Copy answer';
  function answer() {
    var data = new FormData(form), notes = {};
    labels.forEach(function (l, i) { var t = (data.get('note-' + i) || '').trim(); if (t) notes[l] = t; });
    return { question: main.dataset.question, versions: labels, choice: data.get('choice') || null,
             notes: notes, note: (data.get('note') || '').trim() || null };
  }
  function asText(a) {
    var lines = [];
    if (a.choice) lines.push('I choose ' + a.choice + '.');
    a.versions.forEach(function (l) { if (a.notes[l]) lines.push(l + ': ' + a.notes[l]); });
    if (a.note) lines.push(a.note);
    return lines.join('\\n');
  }
  function say(text, error) { status.textContent = text; status.classList.toggle('error', !!error); }
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var a = answer();
    if (!a.choice && !a.note && !Object.keys(a.notes).length) return say('Choose a version or write a note first.', true);
    if (!served) {
      navigator.clipboard.writeText(asText(a)).then(function () { say('Copied. Paste it in the chat with the agent.'); },
        function () { say('Could not copy. Select your notes and copy them by hand.', true); });
      return;
    }
    fetch('/rpc', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jsonrpc: '2.0', id: ++rpcId, method: 'answer', params: a }) })
      .then(function (r) { return r.json(); })
      .then(function (r) {
        if (r.error) throw new Error(r.error.message);
        say('Sent at ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) +
            '. The agent gets it at its next step. You can change your answer and send it again.');
      })
      .catch(function () { say('Not sent: the page lost its connection to the agent. Copy your notes into the chat instead.', true); });
  });
  // New versions from the agent: offer to load them instead of reloading, so typed notes are not lost.
  if (served) {
    var rev = null, bar = document.querySelector('.update');
    bar.querySelector('button').addEventListener('click', function () { location.reload(); });
    (function poll() {
      fetch('/rev').then(function (r) { return r.text(); }).then(function (t) {
        if (rev === null) rev = t; else if (t !== rev) bar.hidden = false;
      }).catch(function () {}).then(function () { setTimeout(poll, 2000); });
    })();
  }
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
    fieldsets = "".join(
        f'<fieldset><legend>{esc(label)}</legend>'
        f'<label class="choose"><input type="radio" name="choice" value="{esc(label)}"> Choose {esc(label)}</label>'
        f'<label for="note-{i}">What is wrong with {esc(label)}?</label>'
        f'<textarea id="note-{i}" name="note-{i}"></textarea></fieldset>'
        for i, label in enumerate(labels))
    form = (f'<form class="answer"><h2>Your answer</h2>'
            f'<p class="ask">{esc(question) if question else "Which version do you choose, and what is wrong with each one?"}</p>'
            f'<div class="opts">{fieldsets}</div>'
            f'<div class="general"><label for="note">Anything else</label><textarea id="note" name="note"></textarea></div>'
            f'<div class="send"><button type="submit">Send to the agent</button><p class="status" role="status"></p></div></form>')
    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<link href="{FONTS}" rel="stylesheet">
<style>{CSS}</style></head>
<body><div class="update" role="status" hidden>The agent sent new versions. <button type="button">Load them</button></div>
<div class="band"></div>
<header><h1>{esc(title)}</h1>{question_html}</header>
<div class="controls">{controls}<p class="hint" data-side="{esc(side_hint)}">{esc(side_hint)}</p></div>
<main data-labels="{esc(json.dumps(labels))}" data-question="{esc(question)}">{"".join(rows)}</main>
{form}
<div class="band band--thin"></div>
<p class="foot">design-better by n14n.dev</p>
<dialog aria-label="Full size"><div class="bar"><b></b><button type="button" class="full close">Close</button></div><div class="screen"></div></dialog>
<script>{JS}</script>
</body></html>
"""
    return page, warnings


def serve(page: Path, port: int, open_browser: bool) -> None:
    """Serve the page from disk, so a rewrite shows on reload, and record each answer the page sends."""
    log, cursor = page.parent / "answers.jsonl", page.parent / ".answers-seen"
    lock, arrived = threading.Lock(), threading.Condition()

    def count() -> int:
        return sum(1 for _ in log.open(encoding="utf-8")) if log.exists() else 0

    class Handler(http.server.BaseHTTPRequestHandler):
        def local(self) -> bool:
            # Only answer requests addressed to this machine, so a web page cannot reach it via DNS rebinding.
            return (self.headers.get("Host") or "").rsplit(":", 1)[0] in ("127.0.0.1", "localhost")

        def reply(self, code: int, body: bytes, kind: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def rpc(self, rid, result=None, error=None) -> None:
            body = {"jsonrpc": "2.0", "id": rid}
            body.update({"error": error} if error else {"result": result})
            self.reply(200, json.dumps(body).encode(), "application/json")

        def do_GET(self):
            if not self.local():
                return self.send_error(403)
            if self.path in ("/", "/index.html"):
                return self.reply(200, page.read_bytes(), "text/html; charset=utf-8")
            if self.path == "/rev":
                return self.reply(200, str(page.stat().st_mtime_ns).encode(), "text/plain")
            if self.path.startswith("/wait?after="):
                # Long poll for --wait: answer as soon as there are more than `after` answers, or after 25 s.
                after = int(self.path.split("=", 1)[1] or 0)
                with arrived:
                    arrived.wait_for(lambda: count() > after, timeout=25)
                return self.reply(200, str(count()).encode(), "text/plain")
            self.send_error(404)

        def do_POST(self):
            # Only this page may send answers: same host, and a JSON body that a cross-site form cannot send.
            if not self.local() or self.path != "/rpc" or not LOCAL_ORIGIN.match(self.headers.get("Origin", "")):
                return self.send_error(403)
            if not (self.headers.get("Content-Type") or "").startswith("application/json"):
                return self.send_error(415)
            size = int(self.headers.get("Content-Length") or 0)
            if not 0 < size <= MAX_BODY:
                return self.send_error(413)
            try:
                msg = json.loads(self.rfile.read(size))
            except ValueError:
                return self.rpc(None, error={"code": -32700, "message": "Parse error"})
            if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or msg.get("method") != "answer" \
                    or not isinstance(msg.get("params"), dict):
                return self.rpc(msg.get("id") if isinstance(msg, dict) else None,
                                error={"code": -32601, "message": "Only the answer method exists"})
            p = msg["params"]
            event = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "action": "answer",
                     "question": str(p.get("question") or ""), "choice": p.get("choice"),
                     "notes": {str(k): str(v)[:5000] for k, v in (p.get("notes") or {}).items()},
                     "note": str(p["note"])[:5000] if p.get("note") else None}
            line = json.dumps(event, ensure_ascii=False)
            with lock:
                with log.open("a", encoding="utf-8") as f:
                    f.write(line + "\n")
                print(line, flush=True)
            with arrived:
                arrived.notify_all()
            self.rpc(msg.get("id"), result="saved")

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    (page.parent / ".server").write_text(url, encoding="utf-8")
    cursor.write_text(str(count()), encoding="utf-8")
    print(f"Serving {page} at {url}. Each answer the user sends is printed here as one JSON line.", flush=True)
    if open_browser and not webbrowser.open(url):
        print("Could not open a browser on this machine. If the user's browser runs on another machine, this address does not reach it.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        (page.parent / ".server").unlink(missing_ok=True)


def wait(folder: Path, timeout: float) -> int:
    """Print the answers the agent has not seen yet, waiting for the served page to receive one."""
    log, cursor, address = folder / "answers.jsonl", folder / ".answers-seen", folder / ".server"
    if not address.exists():
        sys.exit(f"error: no page is served from {folder}. Start it with --serve first.")
    seen = int(cursor.read_text() or 0) if cursor.exists() else 0
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{address.read_text().strip()}wait?after={seen}", timeout=30) as r:
                total = int(r.read())
        except OSError:
            sys.exit("error: the page's server is not answering. Is it still running?")
        if total > seen:
            lines = log.read_text(encoding="utf-8").splitlines()[seen:total]
            print("\n".join(lines), flush=True)
            cursor.write_text(str(total), encoding="utf-8")
            return 0
    print("No new answer before the timeout.", flush=True)
    return 2


def main() -> None:
    parser = argparse.ArgumentParser(description="Put versions of a screen side by side on one page.")
    parser.add_argument("versions", nargs="*", metavar="VERSION", help="LABEL=SOURCE or SOURCE: an HTML file or an http(s) address")
    parser.add_argument("--out", help="the HTML page to write")
    parser.add_argument("--title", default="Compare versions", help="the page heading")
    parser.add_argument("--question", default="", help="what the user should decide, shown under the heading")
    parser.add_argument("--width", action="append", metavar="WxH",
                        help=f"a screen size to show every version at; repeat for more (default: {' and '.join(DEFAULT_WIDTHS)})")
    parser.add_argument("--open", action="store_true", help="open the page in the default browser")
    parser.add_argument("--serve", action="store_true", help="serve the page on 127.0.0.1 and record the user's answers")
    parser.add_argument("--port", type=int, default=0, help="port to serve on (default: any free port)")
    parser.add_argument("--wait", metavar="DIR", help="wait for new answers to the page served from DIR, print them and exit")
    parser.add_argument("--timeout", type=float, default=3600, help="seconds --wait waits (default: 3600)")
    args = parser.parse_args()

    if args.wait:
        sys.exit(wait(Path(args.wait).expanduser().resolve(), args.timeout))
    if not args.versions or not args.out:
        parser.error("give at least one VERSION and --out")

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
    if args.serve:
        return serve(out.resolve(), args.port, args.open)
    if args.open and not webbrowser.open(out.resolve().as_uri()):
        print("Could not open a browser on this machine. Give the user the path instead.")


if __name__ == "__main__":
    main()
