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

On the page, the user gives each version a thumbs up or down, chooses one, and in comment mode clicks any part of
a version to comment on it. With --serve, the script serves the page on 127.0.0.1 and keeps running. Each action is a
JSON-RPC call from the page (choose, verdict, comment, delete, note); the script appends it to answers.jsonl next to
the page and prints it to stdout as one JSON line, so a harness that streams a command's output delivers it to the
agent as it arrives. Writing the page again with the same --out, without --serve, updates the served page: the open
page offers to load the new versions. --wait blocks until the served page receives actions the agent has not seen
yet, prints them and exits, for harnesses that only notify when a command ends. Without a server, Copy all copies
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
METHODS = ("choose", "verdict", "comment", "delete", "note")
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
main.commenting .screen { outline:3px solid var(--terracotta); outline-offset:2px; }
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
      try { frame.contentDocument.documentElement.style.setProperty('--db-s', String(1 / scale)); } catch (e) {}
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

  // Feedback. Every action is sent as it happens, as one JSON-RPC call: the agent gets each verdict, choice and
  // comment with what it points at, and the latest verdict or choice for a version replaces earlier ones.
  var served = location.protocol === 'http:', rpcId = 0, seq = 0, items = [], verdicts = {}, choice = null;
  var status = document.querySelector('.notes .status');
  function say(text, error) { status.textContent = text; status.classList.toggle('error', !!error); }
  function send(method, params) {
    if (!served) { say('Saved on this page. Use Copy all to paste your feedback in the chat.'); return; }
    fetch('/rpc', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jsonrpc: '2.0', id: ++rpcId, method: method, params: params }) })
      .then(function (r) { return r.json(); })
      .then(function (r) { if (r.error) throw new Error(r.error.message);
        say('Sent at ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + '. The agent gets it at its next step.'); })
      .catch(function () { say('Not sent: the page lost its connection to the agent. Use Copy all and paste it in the chat.', true); });
  }
  function syncVersionButtons() {
    document.querySelectorAll('.vbtn[data-v]').forEach(function (b) {
      var v = labels[+b.dataset.v];
      b.setAttribute('aria-pressed', String(b.classList.contains('pickv') ? choice === v : verdicts[v] === b.dataset.verdict));
    });
  }
  document.querySelectorAll('.vbtn[data-v]').forEach(function (b) {
    b.addEventListener('click', function () {
      var v = labels[+b.dataset.v];
      if (b.classList.contains('pickv')) { choice = choice === v ? null : v; send('choose', { version: choice }); }
      else { verdicts[v] = verdicts[v] === b.dataset.verdict ? null : b.dataset.verdict; send('verdict', { version: v, verdict: verdicts[v] }); }
      syncVersionButtons();
    });
  });

  // Comment mode: hovering a version outlines the element under the pointer; a click opens the comment box for it.
  var modeBtn = document.querySelector('#comment'), commenting = false, pop = document.querySelector('.pop'), draft = null;
  function setMode(on) {
    commenting = on; modeBtn.setAttribute('aria-pressed', String(on)); main.classList.toggle('commenting', on);
    if (!on) document.querySelectorAll('main iframe').forEach(function (f) { try { clearHover(f.contentDocument); } catch (e) {} });
  }
  modeBtn.addEventListener('click', function () { setMode(!commenting); });
  document.addEventListener('keydown', function (e) {
    if ((e.key === 'c' || e.key === 'C') && !/INPUT|TEXTAREA/.test(e.target.tagName) && !e.metaKey && !e.ctrlKey) setMode(!commenting);
    if (e.key === 'Escape' && !pop.hidden) closePop();
  });
  function clearHover(doc) { var h = doc.querySelector('[data-db-hover]'); if (h) h.removeAttribute('data-db-hover'); }
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
  function describe(el) {
    var text = (el.getAttribute('aria-label') || el.getAttribute('alt') || el.getAttribute('placeholder') ||
                el.innerText || el.value || '').replace(/\s+/g, ' ').trim();
    var heading = null, h = el.closest('section, article, main, body');
    while (h && !heading) { var x = h.querySelector('h1, h2, h3, h4'); if (x && x !== el) heading = x.innerText.trim(); h = h.parentElement && h.parentElement.closest('section, article, main, body'); }
    return { selector: selectorOf(el), tag: el.tagName.toLowerCase(), text: text.slice(0, 120), heading: heading };
  }
  var PIN_CSS = '[data-db-hover]{outline:2px solid #E8725C!important;outline-offset:2px;cursor:crosshair!important}' +
    '.db-pin{position:absolute;z-index:2147483647;width:24px;height:24px;margin:-12px 0 0 -12px;border-radius:50%;' +
    'background:#E8725C;color:#1C1A17;font:700 12px/24px sans-serif;text-align:center;box-shadow:0 0 0 2px #FFFCF7;pointer-events:none;transform:scale(var(--db-s,1))}';
  function instrument(frame) {
    var doc; try { doc = frame.contentDocument; } catch (e) { return; }
    if (!doc || !doc.body || doc.documentElement.dataset.dbReady) return;
    doc.documentElement.dataset.dbReady = '1';
    var style = doc.createElement('style'); style.textContent = PIN_CSS; doc.head.appendChild(style);
    doc.addEventListener('mouseover', function (e) { if (!commenting) return; clearHover(doc); e.target.setAttribute('data-db-hover', ''); }, true);
    doc.addEventListener('click', function (e) {
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
  function openPop(frame, el, at, cx, cy) {
    var fig = frame.closest('figure'), box = frame.getBoundingClientRect(), scale = box.width / +frame.getAttribute('width');
    draft = { frame: frame, version: labels[+fig.dataset.i], screen: frame.getAttribute('width') + 'x' + frame.getAttribute('height'),
              target: describe(el), at: at, verdict: null };
    pop.querySelector('.target').textContent = draft.version + ': ' + (draft.target.text || '<' + draft.target.tag + '>');
    pop.querySelector('textarea').value = '';
    pop.querySelectorAll('.vbtn').forEach(function (b) { b.setAttribute('aria-pressed', 'false'); });
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
  pop.querySelector('textarea').addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submitComment(); }
  });
  pop.querySelector('.ok').addEventListener('click', submitComment);
  function submitComment() {
    var text = pop.querySelector('textarea').value.trim();
    if (!draft || (!text && !draft.verdict)) { pop.querySelector('textarea').focus(); return; }
    var it = { id: 'c' + (++seq), n: seq, version: draft.version, screen: draft.screen, target: draft.target,
               at: draft.at, verdict: draft.verdict, comment: text || null };
    items.push(it); closePop(); renderList();
    document.querySelectorAll('main figure[data-i="' + labels.indexOf(it.version) + '"] iframe').forEach(function (f) { placePin(f, it); });
    send('comment', { id: it.id, version: it.version, screen: it.screen, target: it.target, verdict: it.verdict, comment: it.comment });
  }
  function placePin(frame, it) {
    if (labels[+frame.closest('figure').dataset.i] !== it.version) return;
    var doc; try { doc = frame.contentDocument; } catch (e) { return; }
    var el = doc && doc.querySelector(it.target.selector); if (!el) return;
    var r = el.getBoundingClientRect(), win = frame.contentWindow, pin = doc.createElement('span');
    pin.className = 'db-pin'; pin.dataset.id = it.id; pin.textContent = it.n;
    pin.style.left = (r.left + win.scrollX + it.at.fx * r.width) + 'px';
    pin.style.top = (r.top + win.scrollY + it.at.fy * r.height) + 'px';
    doc.body.appendChild(pin);
  }
  function renderList() {
    var list = document.querySelector('.notes ol'); list.replaceChildren();
    document.querySelector('.notes .empty').hidden = items.length > 0;
    items.forEach(function (it) {
      var li = document.createElement('li'), n = document.createElement('span'), body = document.createElement('div'),
          del = document.createElement('button');
      n.className = 'n'; n.textContent = it.n;
      var what = document.createElement('div'); what.className = 'what';
      what.textContent = it.version + ', ' + (it.target.text ? '“' + it.target.text.slice(0, 60) + '”' : '<' + it.target.tag + '>');
      var say_ = document.createElement('div');
      say_.textContent = (it.verdict ? (it.verdict === 'up' ? 'Good' : 'Not good') + (it.comment ? ': ' : '') : '') + (it.comment || '');
      body.append(what, say_);
      del.type = 'button'; del.className = 'btn btn--quiet'; del.textContent = 'Delete';
      del.setAttribute('aria-label', 'Delete comment ' + it.n);
      del.addEventListener('click', function () {
        items = items.filter(function (x) { return x !== it; }); renderList();
        document.querySelectorAll('main iframe').forEach(function (f) { try { var p = f.contentDocument.querySelector('.db-pin[data-id="' + it.id + '"]'); if (p) p.remove(); } catch (e) {} });
        send('delete', { id: it.id });
      });
      li.append(n, body, del); list.appendChild(li);
    });
  }
  function asText() {
    var lines = [];
    if (choice) lines.push('I choose ' + choice + '.');
    labels.forEach(function (v) { if (verdicts[v]) lines.push(v + ': ' + (verdicts[v] === 'up' ? 'good' : 'not good') + '.'); });
    items.forEach(function (it) {
      lines.push(it.n + '. ' + it.version + ', ' + (it.target.text ? '"' + it.target.text.slice(0, 60) + '"' : it.target.selector) + ': ' +
                 (it.verdict ? (it.verdict === 'up' ? 'good' : 'not good') + (it.comment ? ', ' : '') : '') + (it.comment || ''));
    });
    var note = document.querySelector('#note').value.trim(); if (note) lines.push(note);
    return lines.join('\n');
  }
  var noteBtn = document.querySelector('.notes .send .btn');
  if (!served) noteBtn.textContent = 'Copy all';
  noteBtn.addEventListener('click', function () {
    if (!served) {
      navigator.clipboard.writeText(asText()).then(function () { say('Copied. Paste it in the chat with the agent.'); },
        function () { say('Could not copy. Select the list and copy it by hand.', true); });
      return;
    }
    var note = document.querySelector('#note').value.trim();
    if (!note) return say('Write a note first.', true);
    send('note', { note: note });
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
            f'<figure data-i="{i}"><div class="label"><b>{esc(label)}</b><span class="acts">'
            f'<button type="button" class="vbtn" data-v="{i}" data-verdict="up" aria-pressed="false" aria-label="Good: {esc(label)}">{THUMB_UP}</button>'
            f'<button type="button" class="vbtn" data-v="{i}" data-verdict="down" aria-pressed="false" aria-label="Not good: {esc(label)}">{THUMB_DOWN}</button>'
            f'<button type="button" class="vbtn pickv" data-v="{i}" aria-pressed="false">Choose</button>'
            f'<button type="button" class="full">Full size</button></span></div>'
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
        side_hint = "Press C to switch comments on or off."
    else:
        side_hint = "Press C to switch comments on or off."
    controls += ('<div class="seg seg--terra"><button type="button" id="comment" aria-pressed="false">Comment</button></div>'
                 '<div class="seg seg--moss"><button type="button" id="together" aria-pressed="true">'
                 'Scroll together</button></div>')
    question_html = f'<p class="question">{esc(question)}</p>' if question else ""
    notes = ('<section class="notes" aria-labelledby="notes-h"><h2 id="notes-h">Your comments</h2>'
             '<p class="empty">No comments yet. Press Comment, then click any part of a version.</p><ol></ol>'
             '<div class="general"><label for="note">Note to the agent</label><textarea id="note"></textarea></div>'
             '<div class="send"><button type="button" class="btn">Send note</button><p class="status" role="status"></p></div></section>')
    pop = ('<div class="pop" role="dialog" aria-label="Comment" hidden><p class="target"></p><div class="verdicts">'
           f'<button type="button" class="vbtn" data-verdict="up" aria-pressed="false" aria-label="Good">{THUMB_UP}</button>'
           f'<button type="button" class="vbtn" data-verdict="down" aria-pressed="false" aria-label="Not good">{THUMB_DOWN}</button></div>'
           '<textarea aria-label="Comment"></textarea><div class="row2"><button type="button" class="btn ok">Send</button>'
           '<button type="button" class="btn btn--quiet cancel">Cancel</button></div></div>')
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
{notes}
{pop}
<div class="band band--thin"></div>
<p class="foot">design-better by n14n.dev</p>
<dialog aria-label="Full size"><div class="bar"><b></b><button type="button" class="full close">Close</button></div><div class="screen"></div></dialog>
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
