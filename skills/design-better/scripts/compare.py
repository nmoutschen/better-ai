#!/usr/bin/env python3
"""Put versions of a screen side by side on one page, at the same screen sizes, so the user can compare them.

Usage:
  python3 compare.py VERSION... --out FILE [--title T] [--question Q] [--width WxH ...] [--open] [--serve [--port N]]
  python3 compare.py --wait DIR [--timeout S]
  python3 compare.py --reply DIR TEXT [--to COMMENT_ID]

VERSION is LABEL=SOURCE or SOURCE. SOURCE is an HTML file, embedded into the page, or an http(s) address, loaded
when the page is viewed. Without a LABEL, versions are labelled A, B, C in order.

The page fills one window: the versions sit side by side at one screen size at a time, each scaled to fit and
scrolling inside its own frame. Each can be shown alone at full width. The page also offers a view that switches
between the versions in the same place, which shows small changes at one spot better than looking from one to the
other; side by side suits comparing whole screens. The page styles only its own controls: each version keeps the styles it brings.

On the page, the user gives each version a thumbs up or down, chooses one, and in comment mode clicks any part of
a version to comment on it. With --serve, the script serves the page on 127.0.0.1 and keeps running. Each action is a
JSON-RPC call from the page (choose, verdict, comment, delete, note); the script appends it to answers.jsonl next to
the page and prints it to stdout as one JSON line, so a harness that streams a command's output delivers it to the
agent as it arrives. Writing the page again with the same --out, without --serve, updates the served page: the open
page offers to load the new versions. --wait blocks until the served page receives actions the agent has not seen
yet, prints them and exits, for harnesses that only notify when a command ends. --reply shows the agent's reply in
the page's conversation panel, which lists everything the user sent and every reply, and survives a reload. Without a server, Copy all copies
the feedback as text for the user to paste in the chat. Comments work on versions embedded from files only.
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
THUMB_UP = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 10v11H3V10zM7 10l4-8a3 3 0 0 1 3 3v4h6a2 2 0 0 1 2 2.3'
            'l-1.4 8A2 2 0 0 1 18.6 21H7"/></svg>')
THUMB_DOWN = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M17 14V3h4v11zM17 14l-4 8a3 3 0 0 1-3-3v-4H4a2 2 0 0 1-2-2.3'
              'l1.4-8A2 2 0 0 1 5.4 3H17"/></svg>')
def icon(path: str) -> str:
    return f'<svg viewBox="0 0 24 24" aria-hidden="true">{path}</svg>'


ICONS = {
    "Desktop": icon('<rect x="2" y="4" width="20" height="13" rx="1"/><path d="M8 21h8M12 17v4"/>'),
    "Tablet": icon('<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M11 18h2"/>'),
    "Mobile": icon('<rect x="7" y="2" width="10" height="20" rx="2"/><path d="M11 18h2"/>'),
    "comment": icon('<path d="M4 4h16v12H9l-5 4z"/>'),
    "together": icon('<path d="M7 3v18M17 3v18M4 7l3-4 3 4M14 17l3 4 3-4M7 12h10"/>'),
    "side": icon('<rect x="3" y="4" width="8" height="16"/><rect x="13" y="4" width="8" height="16"/>'),
    "switch": icon('<rect x="5" y="4" width="14" height="16"/><path d="M9 12h6M13 9l3 3-3 3"/>'),
}
# Backgrounds behind the versions: untinted, because a tinted surround shifts what looks neutral. Near-white is the
# default, as in design tools; dark is for versions meant for a dark context. A mid-grey is left out: judgment is
# sharpest near the surround's own lightness, so mid-grey favours mid-tones.
BACKGROUNDS = (("Light", "#F5F5F5"), ("Dark", "#1E1E1E"))
METHODS = ("choose", "verdict", "comment", "delete", "note")
MAX_BODY = 200_000
LOCAL_ORIGIN = re.compile(r"^http://(127\.0\.0\.1|localhost):\d+$")

FONTS = ("https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400"
         "&family=Space+Grotesk:wght@400;500;700&display=swap")

# The n14n "Journal" tokens, as in research-better's board.html.
CSS = """
:root { --cream:#FFFCF7; --linen:#F2EDE5; --sand:#C4B69C; --terracotta:#E8725C; --umber:#5C4033;
  --moss-dark:#66795A; --ink:#33302B;
  --surround:#F5F5F5; --heading:#1C1A17; --muted:#78736B; --line:#DDD6CA;
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
.seg button.ico { padding:5px 9px; display:inline-flex; align-items:center; opacity:.8; }
.seg button.ico[aria-pressed="true"] { opacity:1; }
.seg button.sw span { width:16px; height:16px; border:1px solid var(--sand); display:block; }
.seg button.sw[aria-pressed="true"] span { outline:2px solid var(--umber); outline-offset:1px; }
main.on-dark .label b, main.on-dark .full { color:var(--cream); }
main.on-dark .vbtn { color:var(--cream); border-color:var(--cream); }
.crumb { display:block; }
.crumb .path { display:block; font:400 12px/1.4 var(--sans); color:var(--muted); }
.crumb .el { display:block; font:400 15px/1.4 var(--serif); color:var(--heading); margin-top:2px; }
.crumb .role { font:700 11px var(--sans); letter-spacing:.08em; text-transform:uppercase; color:var(--umber); margin-right:8px; }
.seg button.ico svg { width:18px; height:18px; fill:none; stroke:currentColor; stroke-width:1.8; stroke-linejoin:round; stroke-linecap:round; }
body.app .controls { gap:8px 12px; }
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
.foot { padding:6px var(--pad); font-size:12px; color:var(--muted); }
/* Feedback: verdicts and Choose in each version's label, comments pinned on the versions, the list after them. */
.label .acts { display:flex; gap:6px; align-items:center; flex-wrap:wrap; justify-content:flex-end; }
.vbtn { border:1px solid var(--ink); background:transparent; color:var(--ink); height:30px; min-width:30px; padding:0 8px;
  cursor:pointer; display:inline-flex; align-items:center; justify-content:center; gap:6px; font:700 12px var(--sans);
  letter-spacing:.08em; text-transform:uppercase; }
.vbtn svg { width:16px; height:16px; fill:none; stroke:currentColor; stroke-width:2; }
.vbtn[data-verdict="up"][aria-pressed="true"] { background:var(--moss-dark); border-color:var(--moss-dark); color:var(--cream); }
.vbtn[data-verdict="down"][aria-pressed="true"] { background:var(--terracotta); border-color:var(--terracotta); color:var(--heading); }
.vbtn.pickv[aria-pressed="true"] { background:var(--umber); border-color:var(--umber); color:var(--cream); }
.seg--terra { border-color:var(--terracotta); }
.seg--terra button[aria-pressed="true"] { background:var(--terracotta); color:var(--heading); }
.pop { position:fixed; z-index:5; width:min(22rem, calc(100vw - 24px)); background:var(--cream); color:var(--ink);
  border:2px solid var(--ink); box-shadow:0 8px 24px rgba(28,26,23,.25); padding:12px; }
.pop[hidden] { display:none; }
.pop .target { margin:0 0 8px; font-size:13px; color:var(--muted); overflow-wrap:anywhere; }
.pop .verdicts { display:flex; gap:6px; margin-bottom:8px; }
.pop textarea, .notes textarea { width:100%; min-height:4.5em; font:400 15px/1.5 var(--sans); color:var(--ink); background:#fff;
  border:1px solid var(--sand); padding:8px 10px; resize:vertical; }
.pop .row2 { display:flex; gap:8px; align-items:center; margin-top:8px; }
.btn { border:0; background:var(--umber); color:var(--cream); padding:8px 16px; cursor:pointer;
  font:700 12px var(--sans); letter-spacing:.08em; text-transform:uppercase; }
.btn--quiet { background:transparent; color:var(--ink); border:1px solid var(--ink); }
.notes { background:var(--cream); color:var(--ink); padding:28px var(--pad) 32px; border-top:2px solid var(--ink); }
.notes h2 { border:0; padding:0; margin:0 0 12px; }
.notes ol { margin:0 0 16px; padding:0; list-style:none; max-width:80ch; }
.notes li { display:grid; grid-template-columns:2rem 1fr auto; gap:4px 10px; align-items:start; padding:10px 0;
  border-top:1px solid var(--line); }
.notes .n { display:inline-flex; width:24px; height:24px; border-radius:50%; background:var(--terracotta); color:var(--heading);
  font:700 12px var(--sans); align-items:center; justify-content:center; }
.notes .what { font-size:13px; color:var(--muted); }
.notes .empty { margin:0 0 16px; }
.notes label { display:block; font-size:14px; margin:8px 0 4px; }
.notes .general { max-width:65ch; }
.notes .send { display:flex; flex-wrap:wrap; gap:12px 20px; align-items:center; margin-top:12px; }
.status { margin:0; font-size:14px; }
.status.error { color:#9A3B2A; font-weight:700; }
.pop .remove { margin-left:auto; }
.pop .remove[hidden] { display:none; }
.toast { position:fixed; z-index:6; left:50%; bottom:24px; transform:translateX(-50%); max-width:min(36rem, calc(100vw - 32px));
  background:var(--umber); color:var(--cream); padding:12px 20px; font:700 15px/1.4 var(--sans);
  box-shadow:0 8px 24px rgba(28,26,23,.3); }
.toast.ok { background:var(--moss-dark); }
.toast.error { background:#9A3B2A; }
.toast[hidden] { display:none; }
/* App layout: one window, no page scroll. The top bar holds the question and the controls; the versions fill the
   space left of the comments, and each render scrolls inside its own frame. */
html { height:100%; }
body.app { height:100%; display:flex; flex-direction:column; overflow:hidden; }
body.app > header { flex:none; display:flex; flex-wrap:wrap; gap:10px 32px; align-items:center; justify-content:space-between;
  padding:12px 20px; }
body.app h1 { font-size:20px; margin:0; }
body.app .question { font-size:15px; line-height:1.4; margin:4px 0 0; }
body.app .controls { position:static; padding:0; background:none; }
.work { flex:1; min-height:0; display:grid; grid-template-columns:minmax(0, 1fr) minmax(16rem, 22rem); }
body.app main { min-height:0; overflow:hidden; padding:12px 20px 10px; display:flex; flex-direction:column; }
main > section { flex:1; min-height:0; display:flex; flex-direction:column; }
main > section[hidden] { display:none; }
body.app .row { flex:1; min-height:0; align-items:stretch; gap:20px; }
body.app figure { display:flex; flex-direction:column; min-height:0; position:relative; }
.stage { flex:1; min-height:0; display:flex; justify-content:center; align-items:flex-start; }
body.app .screen { overflow:hidden; flex:none; }
main.switch figure:not(.current) { position:absolute; inset:0; }
main.focus .row { grid-template-columns:minmax(0, 1fr); }
main.focus figure.aside { display:none; }
body.app .notes { overflow:hidden; border-top:0; border-left:2px solid var(--ink); padding:16px 0 0; display:flex; flex-direction:column; min-height:0; }
body.app .notes h2, body.app .notes .empty { padding:0 20px; }
.notes .thread { flex:1; min-height:0; overflow:auto; list-style:none; margin:0; padding:0 20px 12px; max-width:none; }
.thread > li { display:block; margin:0 0 12px; }
.thread > li.msg { padding:10px 12px; background:#fff; border:1px solid var(--line); }
.thread > li.msg.agent { background:var(--linen); border-color:var(--sand); border-left:4px solid var(--moss-dark); }
.msg.deleted { opacity:.55; }
.msg .head { display:flex; gap:8px; align-items:center; margin-bottom:4px; font-size:12px; color:var(--muted); }
.msg .who { font-weight:700; color:var(--heading); }
.msg.agent .who { color:var(--moss-dark); }
.msg .re { font-style:italic; }
.msg .body { margin:4px 0 0; white-space:pre-wrap; }
.msg .link { margin-left:auto; border:0; background:none; padding:0; cursor:pointer; font:inherit; color:var(--ink); text-decoration:underline; }
.sys { font-size:12px; color:var(--muted); text-align:center; }
.composer { border-top:1px solid var(--line); padding:12px 20px 14px; background:var(--cream); }
.composer textarea { min-height:3.2em; }
.copy[hidden] { display:none; }
.update { position:fixed; left:0; right:0; top:0; }
/* A quiet toolbar: cream with ink, so the chrome draws less attention than the versions. */
body.app > header { background:var(--cream); color:var(--ink); border-bottom:1px solid var(--line); }
body.app h1 { color:var(--heading); }
body.app .question { color:var(--ink); }
body.app .seg { border-color:var(--line); }
body.app .seg button { color:var(--ink); }
body.app .seg button + button { border-left-color:var(--line); }
body.app .seg button[aria-pressed="true"] { background:var(--ink); color:var(--cream); }
body.app .seg button.sw[aria-pressed="true"] { background:transparent; }
body.app .hint { color:var(--muted); }
/* A thin neutral outline on each frame keeps the background from changing how the version's own edges read. */
body.app .screen { border:1px solid #BDBDBD; }
main.on-dark .screen { border-color:#5A5A5A; }
@media (max-width:900px) {
  body.app { height:auto; overflow:auto; }
  .work { grid-template-columns:1fr; }
  body.app main { height:85vh; }
  body.app .notes { border-left:0; border-top:2px solid var(--ink); }
}
.update { position:sticky; top:0; z-index:3; background:var(--moss-dark); color:var(--cream); padding:10px var(--pad);
  display:flex; gap:16px; align-items:center; }
.update[hidden] { display:none; }
.update button { border:1px solid var(--cream); background:transparent; color:var(--cream); padding:6px 12px; cursor:pointer;
  font:700 12px var(--sans); letter-spacing:.08em; text-transform:uppercase; }
"""

JS = r"""
(function () {
  var main = document.querySelector('main'), hint = document.querySelector('.hint');
  var labels = JSON.parse(main.dataset.labels), current = 0;
  var viewButtons = document.querySelectorAll('[data-view]'), pickButtons = document.querySelectorAll('[data-pick]');
  var pick = document.querySelector('.pick'), together = document.querySelector('#together');
  together.addEventListener('click', function () { together.setAttribute('aria-pressed', String(together.getAttribute('aria-pressed') !== 'true')); });
  // Each render fills the space it has: scaled down to fit the width, and as tall as the stage, so it scrolls inside
  // its own frame while the page itself does not scroll.
  function fit() {
    document.querySelectorAll('main > section:not([hidden]) .stage').forEach(function (stage) {
      var frame = stage.querySelector('iframe'), box = stage.firstElementChild, w = +frame.getAttribute('width');
      var sw = stage.clientWidth, sh = stage.clientHeight;
      if (sw <= 0 || sh <= 0) return;
      var scale = Math.min(1, (sw - 2) / w);
      frame.style.width = w + 'px';
      frame.style.height = Math.floor((sh - 2) / scale) + 'px';
      frame.style.transform = 'scale(' + scale + ')';
      box.style.width = Math.ceil(w * scale + 2) + 'px';
      box.style.height = sh + 'px';
      try { frame.contentDocument.documentElement.style.setProperty('--db-s', String(1 / scale)); } catch (e) {}
      if (typeof movePins === 'function') movePins(frame);
    });
  }
  // Background behind the versions, kept for the next visit.
  function setBg(c) {
    main.style.setProperty('--surround', c);
    main.classList.toggle('on-dark', c === '#1E1E1E');
    document.querySelectorAll('.sw').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.bg === c)); });
    try { localStorage.setItem('compare-bg', c); } catch (e) {}
  }
  document.querySelectorAll('.sw').forEach(function (b) { b.addEventListener('click', function () { setBg(b.dataset.bg); }); });
  try { var savedBg = localStorage.getItem('compare-bg'); if (savedBg && document.querySelector('.sw[data-bg="' + savedBg + '"]')) setBg(savedBg); } catch (e) {}
  // Screen size: one size at a time, chosen in the top bar.
  document.querySelectorAll('button[data-size]').forEach(function (b) {
    b.addEventListener('click', function () {
      document.querySelectorAll('button[data-size]').forEach(function (o) { o.setAttribute('aria-pressed', String(o === b)); });
      document.querySelectorAll('main > section').forEach(function (sec) { sec.hidden = sec.dataset.size !== b.dataset.size; });
      fit();
    });
  });
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
    hint.textContent = hint.dataset.side;
    show(current);
  }
  viewButtons.forEach(function (b) { b.addEventListener('click', function () { view(b.dataset.view); }); });
  pickButtons.forEach(function (b) { b.addEventListener('click', function () { show(+b.dataset.pick); }); });
  document.addEventListener('keydown', function (e) {
    if (!main.classList.contains('switch')) return;
    if (e.key === ' ' || e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
      if (e.target.tagName === 'BUTTON' && e.key === ' ') return;
      show((current + 1) % labels.length); e.preventDefault();
    }
  });
  // Full size: one version fills the viewer, the others step aside; the same button brings them back.
  var focused = null;
  function focusOn(i) {
    focused = focused === i ? null : i;
    main.classList.toggle('focus', focused !== null);
    document.querySelectorAll('main figure').forEach(function (f) { f.classList.toggle('aside', focused !== null && +f.dataset.i !== focused); });
    document.querySelectorAll('figure .full').forEach(function (b) { b.textContent = focused === null ? 'Full size' : 'Back to all'; });
    fit();
  }
  document.querySelectorAll('figure .full').forEach(function (b) {
    b.addEventListener('click', function () { focusOn(+b.closest('figure').dataset.i); });
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && focused !== null && pop.hidden) focusOn(focused);
  });
  document.body.classList.add('scaled');
  window.addEventListener('resize', fit);
  view('side');

  // Feedback. Every action is sent as it happens, as one JSON-RPC call, and the server keeps a log of them with the
  // agent's replies. The page streams that log: it rebuilds the conversation and the pins from it, so a reload or new
  // versions lose nothing. State changes are also applied at once, and applying the same event twice changes nothing.
  var served = location.protocol === 'http:', rpcId = 0, seq = 0, items = [], verdicts = {}, choice = null, log = [];
  var status = document.querySelector('.notes .status');
  function say(text, error) { status.textContent = text; status.classList.toggle('error', !!error); }
  // Every action shows a toast at the bottom of the window: sending, then sent or failed.
  var toast = document.querySelector('.toast'), toastTimer = null;
  function flash(text, kind) {
    clearTimeout(toastTimer);
    toast.textContent = text; toast.className = 'toast ' + (kind || ''); toast.hidden = false;
    if (kind !== 'error' && kind !== 'busy') toastTimer = setTimeout(function () { toast.hidden = true; }, 2500);
  }
  function send(method, params, what, done) {
    var event = Object.assign({ action: method, at: new Date().toISOString().slice(0, 19) }, params);
    apply(event, true);
    if (!served) { log.push(event); renderThread(); flash(what + ' saved on this page. Use Copy all to paste it in the chat.', 'ok');
                   if (done) done(); return; }
    flash('Sending ' + what.toLowerCase() + '…', 'busy');
    fetch('/rpc', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jsonrpc: '2.0', id: ++rpcId, method: method, params: params }) })
      .then(function (r) { return r.json(); })
      .then(function (r) { if (r.error) throw new Error(r.error.message);
        flash('✓ ' + what + ' sent to the agent', 'ok'); say(''); if (done) done(); })
      .catch(function () { flash('Not sent: ' + what.toLowerCase() + '. The page lost its connection to the agent.', 'error');
        say('Not sent. The page lost its connection to the agent: copy your message into the chat.', true); });
  }
  function apply(e, fresh) {
    if (e.action === 'comment') {
      var it = byId(e.id);
      if (!it) {
        it = { id: e.id, n: e.n || seq + 1, version: e.version, screen: e.screen, target: e.target || {}, spot: e.spot || { fx: 0.5, fy: 0.5 } };
        seq = Math.max(seq, it.n); items.push(it);
        document.querySelectorAll('iframe[data-i="' + labels.indexOf(it.version) + '"]').forEach(function (f) { placePin(f, it, fresh); });
      }
      it.verdict = e.verdict || null; it.comment = e.comment || null;
    } else if (e.action === 'delete') {
      items = items.filter(function (x) { return x.id !== e.id; });
      document.querySelectorAll('iframe').forEach(function (f) { try { var p = f.contentDocument.querySelector('.db-pin[data-id="' + e.id + '"]'); if (p) p.remove(); } catch (x) {} });
    } else if (e.action === 'choose') { choice = e.version || null; syncVersionButtons(); }
    else if (e.action === 'verdict') { verdicts[e.version] = e.verdict || null; syncVersionButtons(); }
  }
  function byId(id) { return items.filter(function (x) { return x.id === id; })[0]; }
  function syncVersionButtons() {
    document.querySelectorAll('.vbtn[data-v]').forEach(function (b) {
      var v = labels[+b.dataset.v];
      b.setAttribute('aria-pressed', String(b.classList.contains('pickv') ? choice === v : verdicts[v] === b.dataset.verdict));
    });
  }
  document.querySelectorAll('.vbtn[data-v]').forEach(function (b) {
    b.addEventListener('click', function () {
      var v = labels[+b.dataset.v];
      if (b.classList.contains('pickv')) { var c = choice === v ? null : v;
        send('choose', { version: c }, c ? 'Choice of ' + v : 'Choice withdrawn'); }
      else { var d = verdicts[v] === b.dataset.verdict ? null : b.dataset.verdict;
        send('verdict', { version: v, verdict: d }, d ? (d === 'up' ? 'Thumbs up' : 'Thumbs down') + ' for ' + v : 'Verdict on ' + v + ' withdrawn'); }
    });
  });

  // Comment mode: hovering a version outlines the element under the pointer; a click opens the comment box for it.
  var modeBtn = document.querySelector('#comment'), commenting = true, pop = document.querySelector('.pop'), draft = null;
  function setMode(on) {
    commenting = on; modeBtn.setAttribute('aria-pressed', String(on)); main.classList.toggle('commenting', on);
    document.querySelectorAll('iframe').forEach(function (f) { try { f.contentDocument.documentElement.classList.toggle('db-commenting', on); } catch (e) {} });
  }
  main.classList.add('commenting');
  modeBtn.addEventListener('click', function () { setMode(!commenting); });
  document.addEventListener('keydown', function (e) {
    if ((e.key === 'c' || e.key === 'C') && !/INPUT|TEXTAREA/.test(e.target.tagName) && !e.metaKey && !e.ctrlKey) setMode(!commenting);
    if (e.key === 'Escape' && !pop.hidden) closePop();
  });
  function selectorOf(el) {
    var parts = [];
    while (el && el.nodeType === 1 && el.tagName !== 'BODY' && el.tagName !== 'HTML') {
      if (el.id) { parts.unshift('#' + CSS.escape(el.id)); break; }
      var tag = el.tagName.toLowerCase(), n = 1, sib = el;
      while ((sib = sib.previousElementSibling)) if (sib.tagName === el.tagName) n++;
      parts.unshift(tag + ':nth-of-type(' + n + ')');
      el = el.parentElement;
    }
    return parts.join(' > ') || 'body';
  }
  // What a click points at, in enough detail for the agent to find it without the user picking an exact element:
  // the element and its parents, the words under the pointer, an image's source, and where the click fell.
  function brief(x) {
    var t = (x.getAttribute('aria-label') || x.getAttribute('alt') || x.getAttribute('placeholder') ||
             x.innerText || x.value || '').replace(/\s+/g, ' ').trim();
    return { tag: x.tagName.toLowerCase(), id: x.id || null, cls: (x.getAttribute('class') || '').trim() || null, text: t.slice(0, 120) };
  }
  function wordsAt(doc, x, y) {
    var r = doc.caretRangeFromPoint ? doc.caretRangeFromPoint(x, y) : null;
    if (!r && doc.caretPositionFromPoint) { var c = doc.caretPositionFromPoint(x, y); if (c) { r = doc.createRange(); r.setStart(c.offsetNode, c.offset); } }
    if (!r || r.startContainer.nodeType !== 3) return null;
    var text = r.startContainer.textContent, i = r.startOffset, a = i, b = i;
    while (a > 0 && !/[.!?\n]/.test(text[a - 1])) a--;
    while (b < text.length && !/[.!?\n]/.test(text[b])) b++;
    return text.slice(a, b + 1).replace(/\s+/g, ' ').trim().slice(0, 200) || null;
  }
  // Where the clicked element sits, in words: version › parents › the element and what it says.
  var ROLE = { h1: 'Heading', h2: 'Heading', h3: 'Heading', h4: 'Heading', h5: 'Heading', h6: 'Heading', p: 'Paragraph',
    img: 'Image', svg: 'Image', picture: 'Image', button: 'Button', a: 'Link', input: 'Field', textarea: 'Field', select: 'Menu',
    label: 'Label', table: 'Table', tr: 'Row', td: 'Cell', th: 'Column heading', ul: 'List', ol: 'List', li: 'List item',
    header: 'Header', footer: 'Footer', nav: 'Navigation', main: 'Main', aside: 'Sidebar', section: 'Section',
    article: 'Article', form: 'Form', figure: 'Figure', figcaption: 'Caption', blockquote: 'Quote', span: 'Text' };
  // Two lines: the path to the element, small and muted, then what the element is and what it says.
  function crumb(version, t) {
    var path = [version];
    (t.parents || []).slice().reverse().forEach(function (x) {
      if (/^(tbody|thead|tfoot)$/.test(x.tag)) return;
      path.push(ROLE[x.tag] || (x.id ? '#' + x.id : 'Block'));
    });
    var said = t.image ? (t.image.alt || 'no alt text') : (t.words || t.text || '');
    var box = document.createElement('span'), a = document.createElement('span'), b = document.createElement('span'), r = document.createElement('span');
    box.className = 'crumb'; a.className = 'path'; b.className = 'el'; r.className = 'role';
    a.textContent = path.join(' › ');
    r.textContent = ROLE[t.tag] || 'Block';
    b.append(r, said ? '“' + said.slice(0, 90) + (said.length > 90 ? '…' : '') + '”' : '');
    box.append(a, b);
    return box;
  }
  function describe(el, cx, cy) {
    var doc = el.ownerDocument, win = doc.defaultView, r = el.getBoundingClientRect(), d = brief(el);
    // The nearest heading above the element in reading order, or the element itself if it is a heading.
    var heading = null;
    doc.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(function (x) {
      if (x === el || x.contains(el) || (x.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING)) heading = x.innerText.trim();
    });
    var parents = [], up = el.parentElement;
    while (up && up.tagName !== 'BODY' && parents.length < 4) { parents.push(brief(up)); up = up.parentElement; }
    var img = el.tagName === 'IMG' ? el : null, image = null;
    if (img) image = { src: (img.currentSrc || img.getAttribute('src') || '').slice(0, 300), alt: img.getAttribute('alt') };
    else { var bg = win.getComputedStyle(el).backgroundImage; if (bg && bg !== 'none') image = { src: bg.slice(0, 300), alt: null }; }
    return { selector: selectorOf(el), tag: d.tag, text: d.text, heading: heading, words: wordsAt(doc, cx, cy), image: image,
             parents: parents, point: { x: Math.round(cx + win.scrollX), y: Math.round(cy + win.scrollY) },
             box: { x: Math.round(r.left + win.scrollX), y: Math.round(r.top + win.scrollY), w: Math.round(r.width), h: Math.round(r.height) } };
  }
  var PIN_CSS = 'html.db-commenting, html.db-commenting *{cursor:crosshair!important}' +
    '.db-pin{position:absolute;z-index:2147483647;width:24px;height:24px;margin:-12px 0 0 -12px;border-radius:50%;' +
    'background:#E8725C;color:#1C1A17;font:700 12px/24px sans-serif;text-align:center;box-shadow:0 0 0 2px #FFFCF7;cursor:pointer;transform:scale(var(--db-s,1))}' +
    '.db-pin.db-new{animation:db-pulse 1.2s ease-out 2}' +
    '@keyframes db-pulse{0%{box-shadow:0 0 0 2px #FFFCF7,0 0 0 0 rgba(232,114,92,.9)}100%{box-shadow:0 0 0 2px #FFFCF7,0 0 0 18px rgba(232,114,92,0)}}';
  function instrument(frame) {
    var doc; try { doc = frame.contentDocument; } catch (e) { return; }
    if (!doc || !doc.body || doc.documentElement.dataset.dbReady) return;
    doc.documentElement.dataset.dbReady = '1';
    var style = doc.createElement('style'); style.textContent = PIN_CSS; doc.head.appendChild(style);
    doc.documentElement.classList.toggle('db-commenting', commenting);
    doc.addEventListener('click', function (e) {
      var pin = e.target.closest && e.target.closest('.db-pin');
      if (pin) {
        // A pin opens its comment, to read, change or delete it, whether or not comment mode is on.
        e.preventDefault(); e.stopPropagation();
        var found = items.filter(function (x) { return x.id === pin.dataset.id; })[0];
        if (found) openPop(frame, null, null, e.clientX, e.clientY, found);
        return;
      }
      if (!commenting) return;
      e.preventDefault(); e.stopPropagation();
      var el = e.target, r = el.getBoundingClientRect();
      openPop(frame, el, { fx: (e.clientX - r.left) / Math.max(1, r.width), fy: (e.clientY - r.top) / Math.max(1, r.height) }, e.clientX, e.clientY);
    }, true);
    items.forEach(function (it) { placePin(frame, it); });
    fit();
  }
  document.querySelectorAll('main iframe').forEach(function (frame) {
    frame.addEventListener('load', function () { instrument(frame); });
    try { if (frame.contentDocument.readyState === 'complete') instrument(frame); } catch (e) {}
  });
  function openPop(frame, el, at, cx, cy, existing) {
    var box = frame.getBoundingClientRect(), scale = box.width / +frame.getAttribute('width');
    draft = existing ? { item: existing, version: existing.version, target: existing.target, verdict: existing.verdict }
      : { version: labels[+frame.dataset.i], screen: frame.getAttribute('width') + 'x' + frame.getAttribute('height'),
          target: describe(el, cx, cy), spot: at, verdict: null };
    pop.querySelector('.target').replaceChildren(crumb(draft.version, draft.target));
    pop.querySelector('textarea').value = existing ? existing.comment || '' : '';
    pop.querySelectorAll('.vbtn').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.verdict === draft.verdict)); });
    pop.querySelector('.remove').hidden = !existing;
    pop.querySelector('.ok').textContent = existing ? 'Update' : 'Send';
    pop.hidden = false;
    var x = box.left + cx * scale + 12, y = box.top + cy * scale + 12;
    pop.style.left = Math.max(12, Math.min(x, innerWidth - pop.offsetWidth - 12)) + 'px';
    pop.style.top = Math.max(12, Math.min(y, innerHeight - pop.offsetHeight - 12)) + 'px';
    pop.querySelector('textarea').focus();
  }
  function closePop() { pop.hidden = true; draft = null; }
  pop.querySelectorAll('.vbtn').forEach(function (b) {
    b.addEventListener('click', function () {
      draft.verdict = draft.verdict === b.dataset.verdict ? null : b.dataset.verdict;
      pop.querySelectorAll('.vbtn').forEach(function (o) { o.setAttribute('aria-pressed', String(o.dataset.verdict === draft.verdict)); });
    });
  });
  pop.querySelector('.cancel').addEventListener('click', closePop);
  pop.querySelector('.remove').addEventListener('click', function () { var it = draft && draft.item; closePop(); if (it) removeItem(it); });
  pop.querySelector('textarea').addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submitComment(); }
  });
  pop.querySelector('.ok').addEventListener('click', submitComment);
  function submitComment() {
    var text = pop.querySelector('textarea').value.trim();
    if (!draft || (!text && !draft.verdict)) { pop.querySelector('textarea').focus(); return; }
    var it = draft.item, id = it ? it.id : 'c' + (seq + 1) + '-' + Date.now().toString(36), n = it ? it.n : seq + 1;
    var params = it ? { id: id, n: n, version: it.version, screen: it.screen, target: it.target, spot: it.spot }
                    : { id: id, n: n, version: draft.version, screen: draft.screen, target: draft.target, spot: draft.spot };
    params.verdict = draft.verdict; params.comment = text || null;
    closePop();
    // An update reuses the comment's id, so the agent replaces the earlier version of it.
    send('comment', params, 'Comment ' + n + (it ? ' (updated)' : ''));
  }
  function removeItem(it) { send('delete', { id: it.id, n: it.n }, 'Deletion of comment ' + it.n); }
  function movePins(frame) {
    var doc; try { doc = frame.contentDocument; } catch (e) { return; }
    if (!doc) return;
    doc.querySelectorAll('.db-pin').forEach(function (pin) {
      var it = items.filter(function (x) { return x.id === pin.dataset.id; })[0];
      var el = it && doc.querySelector(it.target.selector); if (!el) return;
      var r = el.getBoundingClientRect(), win = frame.contentWindow;
      pin.style.left = (r.left + win.scrollX + it.spot.fx * r.width) + 'px';
      pin.style.top = (r.top + win.scrollY + it.spot.fy * r.height) + 'px';
    });
  }
  function placePin(frame, it, fresh) {
    if (labels[+frame.dataset.i] !== it.version) return;
    var doc; try { doc = frame.contentDocument; } catch (e) { return; }
    if (!doc || !doc.documentElement.dataset.dbReady || doc.querySelector('.db-pin[data-id="' + it.id + '"]')) return;
    var el; try { el = doc.querySelector(it.target.selector); } catch (e) { return; }
    if (!el) return;
    var r = el.getBoundingClientRect(), win = frame.contentWindow, pin = doc.createElement('span');
    pin.className = 'db-pin' + (fresh ? ' db-new' : ''); pin.dataset.id = it.id; pin.textContent = it.n;
    pin.title = 'Comment ' + it.n + ': open to change or delete';
    pin.style.left = (r.left + win.scrollX + it.spot.fx * r.width) + 'px';
    pin.style.top = (r.top + win.scrollY + it.spot.fy * r.height) + 'px';
    doc.body.appendChild(pin);
  }
  // The conversation: everything sent and every reply, in order. A comment shows once, in its latest state.
  var thread = document.querySelector('.thread');
  function el(tag, cls, text) { var x = document.createElement(tag); if (cls) x.className = cls; if (text != null) x.textContent = text; return x; }
  function time(at) { return (at || '').slice(11, 16); }
  function renderThread() {
    var stick = thread.scrollHeight - thread.scrollTop - thread.clientHeight < 40;
    var entries = [], firsts = {};
    log.forEach(function (e) {
      if (e.action === 'comment' || e.action === 'delete') {
        var c = firsts[e.id];
        if (!c) { if (e.action === 'delete') return; c = firsts[e.id] = { kind: 'comment', e: e, edited: false, deleted: false }; entries.push(c); }
        else if (e.action === 'delete') c.deleted = true;
        else { c.e = e; c.edited = true; c.deleted = false; }
      } else entries.push({ kind: e.action, e: e });
    });
    thread.replaceChildren();
    document.querySelector('.notes .empty').hidden = entries.length > 0;
    entries.forEach(function (c) {
      var e = c.e, li;
      if (c.kind === 'comment') {
        li = el('li', 'msg me comment' + (c.deleted ? ' deleted' : ''));
        var head = el('div', 'head'); head.append(el('span', 'n', e.n || '?'), el('span', 'who', 'You'), el('span', 'when', time(e.at) + (c.edited ? ', edited' : '')));
        var it = byId(e.id);
        if (it && !c.deleted) {
          var del = el('button', 'link', 'Delete'); del.type = 'button'; del.setAttribute('aria-label', 'Delete comment ' + e.n);
          del.addEventListener('click', function () { removeItem(it); }); head.append(del);
        }
        li.append(head, crumb(e.version, e.target || {}));
        var said = (e.verdict ? (e.verdict === 'up' ? 'Good' : 'Not good') + (e.comment ? ': ' : '') : '') + (e.comment || '');
        li.append(el('p', 'body', c.deleted ? 'Deleted' : said));
      } else if (c.kind === 'note') {
        li = el('li', 'msg me'); var h = el('div', 'head'); h.append(el('span', 'who', 'You'), el('span', 'when', time(e.at)));
        li.append(h, el('p', 'body', e.note));
      } else if (c.kind === 'reply') {
        li = el('li', 'msg agent'); var h2 = el('div', 'head'); h2.append(el('span', 'who', 'Agent'), el('span', 'when', time(e.at)));
        var to = e.to && log.filter(function (x) { return x.id === e.to; })[0];
        if (to) h2.append(el('span', 're', 'on comment ' + (to.n || '?')));
        li.append(h2, el('p', 'body', e.text));
      } else if (c.kind === 'choose' || c.kind === 'verdict') {
        var t = c.kind === 'choose' ? (e.version ? 'You chose ' + e.version : 'You withdrew your choice')
              : (e.verdict ? (e.verdict === 'up' ? 'Thumbs up for ' : 'Thumbs down for ') + e.version : 'You withdrew your verdict on ' + e.version);
        li = el('li', 'sys', t + ', ' + time(e.at));
      } else return;
      thread.appendChild(li);
    });
    if (stick) thread.scrollTop = thread.scrollHeight;
  }
  function asText() {
    var lines = [];
    if (choice) lines.push('I choose ' + choice + '.');
    labels.forEach(function (v) { if (verdicts[v]) lines.push(v + ': ' + (verdicts[v] === 'up' ? 'good' : 'not good') + '.'); });
    items.forEach(function (it) {
      var t = it.target || {};
      lines.push(it.n + '. ' + it.version + ', ' + (t.words || t.text ? '"' + (t.words || t.text).slice(0, 60) + '"' : t.selector) + ': ' +
                 (it.verdict ? (it.verdict === 'up' ? 'good' : 'not good') + (it.comment ? ', ' : '') : '') + (it.comment || ''));
    });
    log.forEach(function (e) { if (e.action === 'note') lines.push(e.note); });
    return lines.join('\n');
  }
  var noteBox = document.querySelector('#note'), noteBtn = document.querySelector('.notes .send .btn'), copyBtn = document.querySelector('.notes .copy');
  copyBtn.hidden = served;
  copyBtn.addEventListener('click', function () {
    navigator.clipboard.writeText(asText()).then(function () { say('Copied. Paste it in the chat with the agent.'); },
      function () { say('Could not copy. Select the conversation and copy it by hand.', true); });
  });
  function sendNote() {
    var note = noteBox.value.trim();
    if (!note) { noteBox.focus(); return; }
    send('note', { note: note }, 'Message', function () { noteBox.value = ''; });
  }
  noteBtn.addEventListener('click', sendNote);
  noteBox.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendNote(); } });
  if (served) (function stream(after) {
    fetch('/events?after=' + after).then(function (r) { return r.json(); }).then(function (r) {
      r.events.forEach(function (e) { log.push(e); apply(e, false); });
      if (r.events.length) renderThread();
      stream(r.total);
    }).catch(function () { setTimeout(function () { stream(after); }, 2000); });
  })(0);
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


def screen_name(w: int, h: int) -> str:
    return "Desktop" if w >= 1024 else "Tablet" if w >= 600 else "Mobile"


def render(versions: list, sizes: list, title: str, question: str) -> tuple:
    warnings = []
    loaded = [(label, frame_source(source, warnings)) for label, source in versions]
    labels = [label for label, _ in loaded]
    before_after = [label.lower() for label in labels] == ["before", "after"]
    rows = []
    for k, (w, h) in enumerate(sizes):
        # With two versions, choosing one says all a verdict would; verdicts help only to sort three or more.
        figures = "".join(
            f'<figure data-i="{i}"><div class="label"><b>{esc(label)}</b><span class="acts">'
            + (f'<button type="button" class="vbtn" data-v="{i}" data-verdict="up" aria-pressed="false" aria-label="Good: {esc(label)}">{THUMB_UP}</button>'
               f'<button type="button" class="vbtn" data-v="{i}" data-verdict="down" aria-pressed="false" aria-label="Not good: {esc(label)}">{THUMB_DOWN}</button>'
               if len(loaded) > 2 else '') +
            f'<button type="button" class="vbtn pickv" data-v="{i}" aria-pressed="false">Choose</button>'
            f'<button type="button" class="full">Full size</button></span></div>'
            f'<div class="stage"><div class="screen"><iframe data-i="{i}" title="{esc(label)}, {w} × {h} px" width="{w}" height="{h}" '
            f'{attr}></iframe></div></div></figure>'
            for i, (label, attr) in enumerate(loaded))
        rows.append(f'<section data-size="{k}" aria-label="Screen {w} × {h} px"{" hidden" if k else ""}>'
                    f'<div class="row" style="--n:{len(loaded)}">{figures}</div></section>')
    names = [screen_name(w, h) for w, h in sizes]
    if len(set(names)) < len(names):
        names = [f"{w} × {h}" for w, h in sizes]
    sizes_html = ('<div class="seg" role="group" aria-label="Screen">' + "".join(
        f'<button type="button" class="ico" data-size="{k}" aria-pressed="{str(k == 0).lower()}" title="{esc(n)}, {w} × {h} px" '
        f'aria-label="{esc(n)}, {w} × {h} px">{ICONS.get(n) or esc(n)}</button>'
        for k, ((w, h), n) in enumerate(zip(sizes, names))) + '</div>') if len(sizes) > 1 else ""
    controls = sizes_html
    if len(labels) > 1:
        controls += ('<div class="seg" role="group" aria-label="View">'
                     f'<button type="button" class="ico" data-view="side" aria-pressed="true" title="Side by side" aria-label="Side by side">{ICONS["side"]}</button>'
                     f'<button type="button" class="ico" data-view="switch" aria-pressed="false" title="Switch in place (Space)" aria-label="Switch in place">{ICONS["switch"]}</button></div>'
                     '<div class="seg pick" role="group" aria-label="Version shown" hidden>'
                     + "".join(f'<button type="button" data-pick="{i}" aria-pressed="false">{esc(label)}</button>'
                               for i, label in enumerate(labels)) + '</div>')
    side_hint = ""
    controls += (f'<div class="seg"><button type="button" class="ico" id="comment" aria-pressed="true" title="Comment (C)" aria-label="Comment">{ICONS["comment"]}</button>'
                 f'<button type="button" class="ico" id="together" aria-pressed="true" title="Scroll versions together" aria-label="Scroll versions together">{ICONS["together"]}</button></div>'
                 '<div class="seg" role="group" aria-label="Background">' + "".join(
                     f'<button type="button" class="ico sw" data-bg="{c}" aria-pressed="{str(c == BACKGROUNDS[0][1]).lower()}" '
                     f'title="{n} background" aria-label="{n} background"><span style="background:{c}"></span></button>'
                     for n, c in BACKGROUNDS) + '</div>')
    question_html = f'<p class="question">{esc(question)}</p>' if question else ""
    notes = ('<aside class="notes" aria-labelledby="notes-h"><h2 id="notes-h">Conversation</h2>'
             '<p class="empty">Nothing yet. Click any part of a version to comment on it, or write to the agent below.</p>'
             '<ol class="thread" aria-live="polite"></ol>'
             '<div class="composer"><label for="note">Message to the agent</label><textarea id="note"></textarea>'
             '<div class="send"><button type="button" class="btn">Send</button>'
             '<button type="button" class="btn btn--quiet copy">Copy all</button>'
             '<p class="status" role="status"></p></div></div></aside>')
    pop = ('<div class="pop" role="dialog" aria-label="Comment" hidden><p class="target"></p><div class="verdicts">'
           f'<button type="button" class="vbtn" data-verdict="up" aria-pressed="false" aria-label="Good">{THUMB_UP}</button>'
           f'<button type="button" class="vbtn" data-verdict="down" aria-pressed="false" aria-label="Not good">{THUMB_DOWN}</button></div>'
           '<textarea aria-label="Comment"></textarea><div class="row2"><button type="button" class="btn ok">Send</button>'
           '<button type="button" class="btn btn--quiet cancel">Cancel</button>'
           '<button type="button" class="btn btn--quiet remove" hidden>Delete</button></div></div>'
           '<div class="toast" role="status" aria-live="polite" hidden></div>')
    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<link href="{FONTS}" rel="stylesheet">
<style>{CSS}</style></head>
<body class="app"><div class="update" role="status" hidden>The agent sent new versions. <button type="button">Load them</button></div>
<div class="band band--thin"></div>
<header><div class="ttl"><h1>{esc(title)}</h1>{question_html}</div>
<div class="controls">{controls}<p class="hint" data-side="{esc(side_hint)}">{esc(side_hint)}</p></div></header>
<div class="work"><main data-labels="{esc(json.dumps(labels))}" data-question="{esc(question)}">{"".join(rows)}</main>
{notes}</div>
{pop}
<script>{JS}</script>
</body></html>
"""
    return page, warnings


def clean(value, depth=0):
    """Keep only JSON values a page can legitimately send, with long text cut, so the log stays readable."""
    if isinstance(value, str):
        return value[:5000]
    if isinstance(value, bool) or value is None or isinstance(value, (int, float)):
        return value
    if depth < 4 and isinstance(value, dict):
        return {str(k)[:100]: clean(v, depth + 1) for k, v in list(value.items())[:50]}
    if depth < 4 and isinstance(value, list):
        return [clean(v, depth + 1) for v in value[:50]]
    return None


def serve(page: Path, port: int, open_browser: bool) -> None:
    """Serve the page from disk, so a rewrite shows on reload, and record each answer the page sends."""
    log, cursor = page.parent / "answers.jsonl", page.parent / ".answers-seen"
    lock = threading.Lock()

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
            if self.path.startswith("/events?after="):
                # Long poll for the page: every logged event after the first `after`, including the agent's replies.
                after, deadline = int(self.path.split("=", 1)[1] or 0), time.time() + 20
                while count() <= after and time.time() < deadline:
                    time.sleep(0.25)
                lines = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
                events = []
                for line in lines[after:]:
                    try:
                        events.append(json.loads(line))
                    except ValueError:
                        events.append({})
                return self.reply(200, json.dumps({"total": len(lines), "events": events}).encode(), "application/json")
            if self.path.startswith("/wait?after="):
                # Long poll for --wait: answer as soon as there are more than `after` answers, or after 25 s.
                after = int(self.path.split("=", 1)[1] or 0)
                deadline = time.time() + 25
                while count() <= after and time.time() < deadline:
                    time.sleep(0.25)
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
            if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or msg.get("method") not in METHODS \
                    or not isinstance(msg.get("params"), dict):
                return self.rpc(msg.get("id") if isinstance(msg, dict) else None,
                                error={"code": -32601, "message": "Unknown method"})
            event = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "action": msg["method"], **clean(msg["params"])}
            line = json.dumps(event, ensure_ascii=False)
            with lock:
                with log.open("a", encoding="utf-8") as f:
                    f.write(line + "\n")
                print(line, flush=True)
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
            lines = [line for line in log.read_text(encoding="utf-8").splitlines()[seen:total] if '"action": "reply"' not in line]
            cursor.write_text(str(total), encoding="utf-8")
            if not lines:
                seen = total
                continue
            print("\n".join(lines), flush=True)
            return 0
    print("No new answer before the timeout.", flush=True)
    return 2


def reply(folder: Path, text: str, to: str | None) -> None:
    """Show the agent's reply in the served page's conversation. The page streams it from answers.jsonl."""
    if not (folder / ".server").exists():
        sys.exit(f"error: no page is served from {folder}. Start it with --serve first.")
    event = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "action": "reply", "text": text[:5000], "to": to}
    with (folder / "answers.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    print("Reply shown in the page.")


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
    parser.add_argument("--reply", nargs=2, metavar=("DIR", "TEXT"), help="show a reply from the agent in the page served from DIR")
    parser.add_argument("--to", metavar="ID", help="with --reply: the id of the comment the reply answers")
    args = parser.parse_args()

    if args.wait:
        sys.exit(wait(Path(args.wait).expanduser().resolve(), args.timeout))
    if args.reply:
        return reply(Path(args.reply[0]).expanduser().resolve(), args.reply[1], args.to)
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
