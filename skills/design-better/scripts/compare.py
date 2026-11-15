#!/usr/bin/env python3
"""Put versions of a screen side by side on one page, at the same screen sizes, so the user can compare them.

Usage:
  python3 compare.py VERSION... --out FILE [--title T] [--question Q] [--width WxH ...] [--open] [--serve [--port N]]
  python3 compare.py --wait DIR [--timeout S]
  python3 compare.py --reply DIR TEXT [--to COMMENT_ID]
  python3 compare.py --status DIR seen|asked|working|done|accepted ID...
  python3 compare.py --pending DIR

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
    "settings": icon('<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>'),
    "use": icon('<path d="M5 3l14 8-6 2-3 6z"/>'),
    "free": icon('<path d="M7 3v18M17 3v18M4 7l3-4 3 4M14 17l3 4 3-4"/>'),
    "together": icon('<path d="M7 3v18M17 3v18M4 7l3-4 3 4M14 17l3 4 3-4M7 12h10"/>'),
    "side": icon('<rect x="3" y="4" width="8" height="16"/><rect x="13" y="4" width="8" height="16"/>'),
    "switch": icon('<rect x="5" y="4" width="14" height="16"/><path d="M9 12h6M13 9l3 3-3 3"/>'),
}
# Backgrounds behind the versions: untinted, because a tinted surround shifts what looks neutral. Near-white is the
# default, as in design tools; dark is for versions meant for a dark context. A mid-grey is left out: judgment is
# sharpest near the surround's own lightness, so mid-grey favours mid-tones.
BACKGROUNDS = (("Light", "#F5F5F5"), ("Dark", "#1E1E1E"))
METHODS = ("choose", "verdict", "comment", "delete", "note", "accept", "reopen", "decide")
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
.seg button.sw .chip { width:14px; height:14px; border:1px solid var(--sand); display:block; }
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
/* The top bar stays umber, the n14n brand block; each control pairs its icon with a short label. Pickers (one of
   several) are segmented and fill the chosen option; switches (on or off) have no fill and a box that is ticked. */
body.app .seg button.ico { gap:6px; font:700 11px var(--sans); letter-spacing:.06em; text-transform:uppercase; padding:6px 10px; }
/* Experiment: in the bar, each two-option setting is one button that shows the current option; a click switches. */
/* Both options share one cell, so the button keeps the width of the longer one; the first option is cream, the
   second umber, so the colour also tells which is on. */
.controls > .seg.cycle { display:inline-grid; }
.controls > .seg.cycle button { grid-area:1 / 1; justify-content:center; border:0; }
.controls > .seg.cycle button[aria-pressed="false"] { visibility:hidden; }
.controls > .seg.cycle button:first-child[aria-pressed="true"] { background:var(--cream); color:var(--umber); }
.controls > .seg.cycle button:last-child[aria-pressed="true"] { background:transparent; color:var(--cream); }
.more { position:relative; }
.morebtn { display:inline-flex; align-items:center; gap:5px; border:1px solid var(--cream); background:transparent; color:var(--cream);
  padding:6px 10px; cursor:pointer; font:700 11px var(--sans); letter-spacing:.06em; text-transform:uppercase; }
.morebtn svg { width:18px; height:18px; fill:none; stroke:currentColor; stroke-width:1.8; }
.morebtn[aria-expanded="true"] { background:var(--cream); color:var(--umber); }
.menu { position:absolute; right:0; top:calc(100% + 6px); z-index:4; background:var(--umber); border:1px solid var(--cream);
  padding:10px 12px 12px; box-shadow:0 8px 24px rgba(28,26,23,.3); display:grid; gap:4px; min-width:12rem; }
.menu[hidden] { display:none; }
.menu-h { margin:4px 0 2px; font:700 10px var(--sans); letter-spacing:.08em; text-transform:uppercase; color:var(--cream); opacity:.8; }
.thread > li.msg .body { font-size:14px; line-height:1.45; }
body.app main .pick { align-self:flex-start; margin:0 0 10px; border-color:var(--ink); }
body.app main .pick button { color:var(--ink); }
body.app main .pick button + button { border-left-color:var(--ink); }
body.app main .pick button[aria-pressed="true"] { background:var(--ink); color:var(--cream); }
main.on-dark .pick, main.on-dark .pick button + button { border-color:var(--cream); }
main.on-dark .pick button { color:var(--cream); }
main.on-dark .pick button[aria-pressed="true"] { background:var(--cream); color:var(--heading); }
.thread .reply { margin:10px -12px -10px; padding:8px 12px 10px 12px; background:var(--linen); border-top:1px solid var(--line);
  border-left:4px solid var(--moss-dark); }
.thread .reply .who { color:var(--moss-dark); }
.thread .reply .body { font-size:14px; line-height:1.45; margin:2px 0 0; }
.thread > li.msg.agent .reply { margin:-10px -12px; border:0; background:none; }
.progress { white-space:nowrap; display:inline-flex; align-items:center; gap:6px; font:700 10px var(--sans); letter-spacing:.08em;
  text-transform:uppercase; color:var(--muted); }
.progress .bars { display:inline-flex; gap:2px; }
.progress .bars i { width:10px; height:4px; background:var(--line); }
.progress.seen .bars i.on { background:var(--sand); }
.progress.working { color:var(--umber); }
.progress.asked { color:var(--umber); }
.progress.asked .bars i.on { background:var(--umber); }
.progress.working .bars i.on { background:var(--terracotta); }
.progress.working .bars i.on:last-of-type { animation:pulse-bar 1.2s ease-in-out infinite; }
.progress.done { color:var(--moss-dark); }
.progress.done .bars i.on { background:var(--moss-dark); }
.progress.accepted { color:var(--moss-dark); }
.progress.accepted .bars i.on { background:var(--moss-dark); }
.progress.accepted::after { content:"\\2713"; font-size:12px; }
.progress.reopened { color:#9A3B2A; }
.progress.reopened .bars i { background:var(--terracotta); opacity:.5; }
.thread .reply.mine { background:#fff; border-left-color:var(--terracotta); }
.thread .reply.mine .who { color:var(--heading); }
.why { margin-top:10px; }
/* A reply above pulls its bottom edge down by the item's padding; give that space back. */
.thread .reply + .why { margin-top:20px; }
.why textarea { width:100%; min-height:3em; font:400 14px/1.45 var(--sans); border:1px solid var(--sand); padding:6px 8px; }
.why .row2 { display:flex; gap:8px; margin-top:6px; }
.notes-top { display:flex; justify-content:space-between; align-items:center; gap:12px; padding:0 20px; margin-bottom:12px; }
body.app .notes .notes-top h2 { padding:0; margin:0; }
.notes .filter { border-color:var(--ink); }
.notes .filter button { color:var(--ink); padding:4px 10px; font-size:11px; }
.notes .filter button + button { border-left-color:var(--ink); }
.notes .filter button[aria-pressed="true"] { background:var(--ink); color:var(--cream); }
.thread > li.locatable { cursor:pointer; }
.thread > li.locatable:hover { border-color:var(--sand); }
.thread .reply.mine.answer-note { border-left-color:var(--umber); }
.btn--sm { padding:3px 10px; font-size:10px; }
.msg .head { flex-wrap:wrap; row-gap:2px; }
.thread .foot { display:flex; flex-wrap:wrap; gap:4px 8px; align-items:center; margin:2px 0 -6px; }
/* A reply pulls its bottom edge 10px down; 12px leaves the same 2px gap as without one. */
.thread .reply + .foot { margin-top:12px; }
.thread .reply:has(+ .foot) { padding-bottom:2px; }
/* Inside an item, the item's own left edge already marks it: a reply shows by its background and label, not a second bar. */
.thread > li.msg .reply, .thread > li.msg .reply.mine { border-left:0; padding-left:16px; }
.thread .foot .answer { margin-left:auto; }
.thread .foot .mini:first-of-type { margin-left:auto; }
/* The item's left edge carries its state too, so it reads at a glance in a long thread. */
.thread > li.msg[data-state] { border-left-width:4px; }
.thread > li.msg[data-state="seen"] { border-left-color:var(--sand); }
.thread > li.msg[data-state="asked"] { border-left-color:var(--umber); }
.thread > li.msg[data-state="working"] { border-left-color:var(--terracotta); }
.thread > li.msg[data-state="done"], .thread > li.msg[data-state="accepted"] { border-left-color:var(--moss-dark); }
.thread > li.msg[data-state="reopened"] { border-left-color:#9A3B2A; }
.decide { border:1px solid var(--sand); background:#fff; padding:8px 10px; margin-bottom:10px; }
.decide .menu-h { color:var(--muted); margin:0 0 6px; }
.dopt { display:flex; align-items:center; gap:6px; font-size:14px; margin:4px 0; cursor:pointer; }
.dopt input { accent-color:var(--umber); }
.carry .menu-h { margin-top:8px; }
.carried { margin:2px 0; font-size:13px; color:var(--ink); }
.msg.decision { border-left:4px solid var(--umber); }
.msg .with { color:var(--muted); }
.mini { width:22px; height:20px; padding:0; border:1px solid var(--line); background:#fff; color:var(--ink); cursor:pointer;
  font:700 12px/18px var(--sans); }
.mini:hover { border-color:var(--ink); }
@keyframes pulse-bar { 50% { opacity:.35; } }
@media (prefers-reduced-motion: reduce) { .progress .bars i { animation:none !important; } }
.msg .answered { font:700 10px var(--sans); letter-spacing:.08em; text-transform:uppercase; color:var(--moss-dark); }
/* In the conversation, where a comment points is a small quote above the user's words, so every message reads alike. */
.thread .crumb { margin:2px 0 0; padding-left:8px; border-left:2px solid var(--line); }
.thread .crumb .path { font-size:11px; }
.thread .crumb .el { font:400 13px/1.4 var(--sans); color:var(--muted); margin-top:0; }
.thread .crumb .role { font-size:10px; color:var(--muted); margin-right:6px; }
.verdict { display:inline-block; font:700 10px var(--sans); letter-spacing:.08em; text-transform:uppercase; padding:1px 6px;
  margin-right:8px; vertical-align:1px; }
.verdict.up { background:var(--moss-dark); color:var(--cream); }
.verdict.down { background:var(--terracotta); color:var(--heading); }
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
  // In the bar, a two-option setting shows only its current option; clicking it picks the other one.
  document.querySelectorAll('.controls > .seg.cycle').forEach(function (seg) {
    seg.addEventListener('click', function (e) {
      var b = e.target.closest('button'); if (!b || b.getAttribute('aria-pressed') !== 'true' || seg.dataset.cycling) return;
      var other = Array.prototype.filter.call(seg.querySelectorAll('button'), function (x) { return x !== b; })[0];
      if (!other) return;
      e.stopImmediatePropagation(); seg.dataset.cycling = '1'; other.click(); delete seg.dataset.cycling; other.focus();
    }, true);
  });
  // Every setting in the toolbar is one segmented choice between options; the chosen one is filled.
  var pick = document.querySelector('.pick'), linked = true, scrollSeg = document.querySelector('[aria-label="Scroll"]');
  function choose(attr, value) {
    document.querySelectorAll('button[' + attr + ']').forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute(attr) === value)); });
  }
  document.querySelectorAll('button[data-scroll]').forEach(function (b) {
    b.addEventListener('click', function () { linked = b.dataset.scroll === 'linked'; choose('data-scroll', b.dataset.scroll); });
  });
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
  // The Display menu opens under its button and closes on a click outside it or on Escape.
  var moreBtn = document.querySelector('.morebtn'), menu = document.querySelector('.menu');
  function openMenu(on) { menu.hidden = !on; moreBtn.setAttribute('aria-expanded', String(on)); }
  moreBtn.addEventListener('click', function (e) { e.stopPropagation(); openMenu(menu.hidden); });
  document.addEventListener('click', function (e) { if (!menu.hidden && !menu.contains(e.target)) openMenu(false); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !menu.hidden) { openMenu(false); moreBtn.focus(); } });
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
    if (!linked || (quietUntil.get(frame) || 0) > Date.now()) return;
    frame.closest('.row').querySelectorAll('iframe').forEach(function (other) { if (other !== frame) match(frame, other); });
  }
  function bind(frame) {
    try { frame.contentWindow.addEventListener('scroll', function () { follow(frame); }); } catch (e) { if (scrollSeg) scrollSeg.hidden = true; }
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
    document.querySelectorAll('figure .full').forEach(function (b) { b.textContent = name === 'switch' ? 'Side by side' : 'Full size'; });
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
  // Full size is the switch view opened on that version: one version fills the viewer, the tabs pick another,
  // and the same button, now Side by side, brings the others back.
  document.querySelectorAll('figure .full').forEach(function (b) {
    b.addEventListener('click', function () {
      if (main.classList.contains('switch')) view('side');
      else { current = +b.closest('figure').dataset.i; view('switch'); }
    });
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && main.classList.contains('switch') && pop.hidden && !e.target.closest('textarea')) view('side');
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
  var commenting = true, pop = document.querySelector('.pop'), draft = null;
  function setMode(on) {
    commenting = on; choose('data-mode', on ? 'comment' : 'use'); main.classList.toggle('commenting', on);
    document.querySelectorAll('iframe').forEach(function (f) { try { f.contentDocument.documentElement.classList.toggle('db-commenting', on); } catch (e) {} });
  }
  main.classList.add('commenting');
  document.querySelectorAll('button[data-mode]').forEach(function (b) {
    b.addEventListener('click', function () { setMode(b.dataset.mode === 'comment'); });
  });
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
    // A pin shows its comment's progress in the colours of the conversation panel.
    '.db-pin[data-state=seen]{background:#C4B69C}' +
    '.db-pin[data-state=asked]{background:#FFFCF7;color:#5C4033;box-shadow:0 0 0 2px #5C4033}' +
    '.db-pin[data-state=working]{background:#E8725C;animation:db-pulse 1.4s ease-out infinite}' +
    '.db-pin[data-state=done]{background:#66795A;color:#FFFCF7}' +
    // An accepted comment's pin goes away; showing it from the conversation brings it back for a moment.
    '.db-pin[data-state=accepted]{display:none;background:#66795A;color:#FFFCF7}' +
    '.db-pin.db-flash{display:block!important;animation:db-pulse .9s ease-out 3!important}' +
    '.db-pin[data-state=reopened]{background:#E8725C;box-shadow:0 0 0 2px #FFFCF7,0 0 0 4px #9A3B2A}' +
    '@media (prefers-reduced-motion: reduce){.db-pin{animation:none!important}}' +
    '@keyframes db-pulse{0%{box-shadow:0 0 0 2px #FFFCF7,0 0 0 0 rgba(232,114,92,.9)}100%{box-shadow:0 0 0 2px #FFFCF7,0 0 0 18px rgba(232,114,92,0)}}';
  function instrument(frame) {
    var doc; try { doc = frame.contentDocument; } catch (e) { return; }
    if (!doc || !doc.body || doc.documentElement.dataset.dbReady) return;
    doc.documentElement.dataset.dbReady = '1';
    var style = doc.createElement('style'); style.textContent = PIN_CSS; doc.head.appendChild(style);
    doc.documentElement.classList.toggle('db-commenting', commenting);
    doc.addEventListener('click', function (e) {
      if (!menu.hidden) openMenu(false);
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
    pin.dataset.state = pinState[it.id] || 'new';
    pin.title = 'Comment ' + it.n + ': open to change or delete';
    pin.style.left = (r.left + win.scrollX + it.spot.fx * r.width) + 'px';
    pin.style.top = (r.top + win.scrollY + it.spot.fy * r.height) + 'px';
    doc.body.appendChild(pin);
  }
  // The conversation: everything sent and every reply, in order. A comment shows once, in its latest state.
  var thread = document.querySelector('.thread');
  function el(tag, cls, text) { var x = document.createElement(tag); if (cls) x.className = cls; if (text != null) x.textContent = text; return x; }
  function time(at) { return (at || '').slice(11, 16); }
  // A reply that names the message it answers is shown under that message, so the user sees what was answered.
  function replyBlock(e) {
    var mine = e.action === 'reopen' || e.action === 'note', r = el('div', mine ? 'reply mine' + (e.action === 'note' ? ' answer-note' : '') : 'reply'), h = el('div', 'head');
    h.append(el('span', 'who', mine ? 'You' : 'Agent'), el('span', 'when', time(e.at)));
    if (e.action === 'reopen') h.append(el('span', 'progress reopened', 'Reopened'));
    r.append(h, el('p', 'body', e.action === 'reopen' ? e.reason : e.action === 'note' ? e.note : e.text));
    return r;
  }
  var filter = 'open';
  document.querySelectorAll('[data-filter]').forEach(function (b) {
    b.addEventListener('click', function () {
      filter = b.dataset.filter;
      document.querySelectorAll('[data-filter]').forEach(function (o) { o.setAttribute('aria-pressed', String(o === b)); });
      renderThread();
    });
  });
  var STEPS = ['seen', 'working', 'done', 'accepted'],
      LABEL = { seen: 'Seen', asked: 'Waiting for you', working: 'Working on it', done: 'Done', accepted: 'Accepted', reopened: 'Reopened' };
  // Reopening asks why, in a small box under the item; the reason goes with the reopen.
  function reasonBox(li, id, answer) {
    if (li.querySelector('.why')) return li.querySelector('.why textarea').focus();
    var box = el('div', 'why'), ta = el('textarea'), row = el('div', 'row2'),
        ok = el('button', 'btn', answer ? 'Send' : 'Reopen'), no = el('button', 'btn btn--quiet', 'Cancel');
    ta.setAttribute('aria-label', answer ? 'Your answer' : 'Why reopen it?'); ta.placeholder = answer ? 'Your answer' : 'What is still wrong?';
    ok.type = no.type = 'button';
    function go() {
      var r = ta.value.trim(); if (!r) return ta.focus();
      if (answer) send('note', { id: 'm-' + Date.now().toString(36), to: id, note: r }, 'Answer');
      else send('reopen', { to: id, reason: r }, 'Reopening');
      box.remove();
    }
    ok.addEventListener('click', go); no.addEventListener('click', function () { box.remove(); });
    ta.addEventListener('keydown', function (k) { if (k.key === 'Enter' && !k.shiftKey) { k.preventDefault(); go(); } if (k.key === 'Escape') box.remove(); });
    row.append(ok, no); box.append(ta, row); li.append(box); ta.focus();
  }
  function renderThread() {
    var stick = thread.scrollHeight - thread.scrollTop - thread.clientHeight < 40;
    var entries = [], byKey = {}, state = {};
    log.forEach(function (e) {
      if (e.action === 'status') state[e.to] = e.status;
      else if (e.action === 'accept') state[e.to] = 'accepted';
      else if (e.action === 'reopen') state[e.to] = 'reopened';
    });
    log.forEach(function (e, i) {
      if (e.action === 'comment' || e.action === 'delete') {
        var c = byKey[e.id];
        if (!c) { if (e.action === 'delete') return; c = byKey[e.id] = { kind: 'comment', e: e, edited: false, deleted: false, replies: [] }; entries.push(c); }
        else if (e.action === 'delete') c.deleted = true;
        else { c.e = e; c.edited = true; c.deleted = false; }
      } else if ((e.action === 'reply' || (e.action === 'reopen' && e.reason) || (e.action === 'note' && e.to)) && e.to && byKey[e.to]) byKey[e.to].replies.push(e);
      else if (e.action === 'accept' || e.action === 'reopen' || e.action === 'status') return;
      else { var n = { kind: e.action, e: e, replies: [] }; if (e.id) byKey[e.id] = n; entries.push(n); }
    });
    // Open: only the user's comments and messages that are not yet accepted, with what was said under them.
    var open = entries.filter(function (c) { return (c.kind === 'comment' || c.kind === 'note' || c.kind === 'decide') && c.e.id && !c.deleted && state[c.e.id] !== 'accepted'; });
    var openBtn = document.querySelector('[data-filter="open"]');
    openBtn.textContent = 'Open (' + open.length + ')';
    if (filter === 'open') entries = open;
    thread.replaceChildren();
    document.querySelector('.notes .empty').hidden = entries.length > 0 || filter === 'open';
    entries.forEach(function (c) {
      var e = c.e, li, head;
      // Progress on the user's item: three short bars fill as the agent sees it, works on it and finishes it.
      function answered(h) {
        var st = state[e.id];
        if (!st) { if (c.replies.length) h.append(el('span', 'answered', 'Answered')); return; }
        var k = st === 'asked' ? 0 : STEPS.indexOf(st), chip = el('span', 'progress ' + st), bars = el('span', 'bars');
        for (var j = 0; j < 4; j++) bars.append(el('i', j <= k ? 'on' : ''));
        chip.append(bars, el('span', '', LABEL[st]));
        h.append(chip);
        // Once the agent marks an item done, two small equal buttons beside the state let the user accept or reopen it.
        if (st === 'done') {
          [['accept', '\u2713', 'Accept'], ['reopen', '\u21BA', 'Reopen']].forEach(function (a) {
            var b = el('button', 'mini', a[1]); b.type = 'button'; b.title = a[2]; b.setAttribute('aria-label', a[2]);
            b.addEventListener('click', function () {
              if (a[0] === 'accept') return send('accept', { to: e.id }, 'Acceptance');
              reasonBox(h.closest('li'), e.id);
            });
            h.append(b);
          });
        }
      }
      if (c.kind === 'comment') {
        li = el('li', 'msg me comment' + (c.deleted ? ' deleted' : ''));
        head = el('div', 'head'); head.append(el('span', 'n', e.n || '?'), el('span', 'who', 'You'), el('span', 'when', time(e.at) + (c.edited ? ', edited' : '')));
        var it = byId(e.id);
        if (it && !c.deleted) {
          var del = el('button', 'link', 'Delete'); del.type = 'button'; del.setAttribute('aria-label', 'Delete comment ' + e.n);
          del.addEventListener('click', function () { removeItem(it); }); head.append(del);
        }
        li.append(head, crumb(e.version, e.target || {}));
        li.classList.add('locatable'); li.title = 'Show where this comment is';
        li.addEventListener('click', function (ev) { if (!ev.target.closest('button, textarea, .why')) reveal(e); });
        var body = el('p', 'body');
        if (c.deleted) body.textContent = 'Deleted';
        else {
          if (e.verdict) body.append(el('span', 'verdict ' + e.verdict, e.verdict === 'up' ? 'Good' : 'Not good'));
          if (e.comment) body.append(e.comment);
        }
        li.append(body);
      } else if (c.kind === 'note') {
        li = el('li', 'msg me'); head = el('div', 'head'); head.append(el('span', 'who', 'You'), el('span', 'when', time(e.at)));
        li.append(head, el('p', 'body', e.note));
      } else if (c.kind === 'decide') {
        li = el('li', 'msg me decision'); head = el('div', 'head'); head.append(el('span', 'who', 'You decided'), el('span', 'when', time(e.at)));
        var d = el('p', 'body'); d.append(el('strong', '', e.label || e.option));
        if (e.carries && e.carries.length) d.append(el('span', 'with', ' with comments ' + e.carries.map(function (id) { var x = log.filter(function (y) { return y.id === id; })[0]; return x && x.n ? x.n : '?'; }).join(', ')));
        li.append(head, d); if (e.note) li.append(el('p', 'body', e.note));
      } else if (c.kind === 'reply') {
        li = el('li', 'msg agent'); li.append(replyBlock(e));
      } else if (c.kind === 'choose' || c.kind === 'verdict') {
        var t = c.kind === 'choose' ? (e.version ? 'You chose ' + e.version : 'You withdrew your choice')
              : (e.verdict ? (e.verdict === 'up' ? 'Thumbs up for ' : 'Thumbs down for ') + e.version : 'You withdrew your verdict on ' + e.version);
        li = el('li', 'sys', t + ', ' + time(e.at));
      } else return;
      c.replies.forEach(function (r) { li.append(replyBlock(r)); });
      // The state and what the user can do with it close the item, after the latest reply, where the eye ends.
      if (c.kind === 'comment' || c.kind === 'note' || c.kind === 'decide') {
        var foot = el('div', 'foot'); answered(foot);
        if (state[e.id] === 'asked') {
          var ans = el('button', 'btn btn--sm answer', 'Answer'); ans.type = 'button';
          ans.addEventListener('click', function () { reasonBox(li, e.id, true); });
          foot.append(ans);
        }
        if (foot.childNodes.length) li.append(foot);
        if (state[e.id]) li.dataset.state = state[e.id];
      }
      thread.appendChild(li);
    });
    if (filter === 'open' && !entries.length) thread.appendChild(el('li', 'sys', 'Nothing open: you accepted everything.'));
    if (stick) thread.scrollTop = thread.scrollHeight;
    pinState = state; syncPins();
  }
  // Show a comment where it was made: its screen size, its version, scrolled to its pin, which flashes.
  function reveal(e) {
    var sec = Array.prototype.filter.call(document.querySelectorAll('main > section'), function (x) {
      var f = x.querySelector('iframe'); return f && f.getAttribute('width') + 'x' + f.getAttribute('height') === e.screen;
    })[0];
    if (sec && sec.hidden) { var sb = document.querySelector('button[data-size="' + sec.dataset.size + '"]'); if (sb) sb.click(); }
    var i = labels.indexOf(e.version); if (i < 0) return;
    if (main.classList.contains('switch')) show(i);
    var frame = (sec || main).querySelector('iframe[data-i="' + i + '"]'); if (!frame) return;
    var doc; try { doc = frame.contentDocument; } catch (x) { return; }
    var pin = doc.querySelector('.db-pin[data-id="' + e.id + '"]'); if (!pin) return;
    pin.classList.remove('db-flash'); void pin.offsetWidth; pin.classList.add('db-flash');
    frame.contentWindow.scrollTo({ top: Math.max(0, parseFloat(pin.style.top) - frame.contentWindow.innerHeight / 3), behavior: 'smooth' });
    setTimeout(function () { pin.classList.remove('db-flash'); }, 2800);
  }
  var pinState = {}, STATE_WORD = { asked: 'waiting for you', seen: 'seen', working: 'being worked on', done: 'done, waiting for you', accepted: 'accepted', reopened: 'reopened' };
  function syncPins() {
    document.querySelectorAll('iframe').forEach(function (f) {
      try { f.contentDocument.querySelectorAll('.db-pin').forEach(function (pin) {
        var st = pinState[pin.dataset.id] || 'new', it = byId(pin.dataset.id);
        pin.dataset.state = st;
        pin.title = 'Comment ' + (it ? it.n : '') + ': ' + (STATE_WORD[st] || 'new') + '. Click to open it.';
      }); } catch (e) {}
    });
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
    send('note', { id: 'm-' + Date.now().toString(36), note: note }, 'Message', function () { noteBox.value = ''; });
  }
  // Decide: one confirmed decision, sent with the open comments that come with it and the message as its note.
  // The Send button becomes Confirm while the decision panel is open, so the same place sends both.
  var decideBtn = document.querySelector('.decide-btn'), panel = document.querySelector('.decide'), deciding = false;
  var beforeAfter = labels.length === 2 && labels[0].toLowerCase() === 'before' && labels[1].toLowerCase() === 'after';
  var OPTIONS = beforeAfter ? [['Ship After', 'After'], ['Keep Before', 'Before']]
    : labels.map(function (l) { return ['Build ' + l, l]; }).concat([['Combine versions (say how below)', 'combine']]);
  OPTIONS.push(['None of these (say why below)', 'none']);
  function openItems() {
    return items.filter(function (it) { return pinState[it.id] !== 'accepted' && pinState[it.id] !== 'done'; });
  }
  function setDeciding(on) {
    deciding = on; panel.hidden = !on; decideBtn.setAttribute('aria-expanded', String(on));
    decideBtn.textContent = on ? 'Cancel' : 'Decide\u2026';
    noteBtn.textContent = on ? 'Confirm decision' : 'Send';
    if (!on) return;
    var box = panel.querySelector('.dopts'); box.replaceChildren();
    OPTIONS.forEach(function (o, k) {
      var lab = el('label', 'dopt'), r = el('input'); r.type = 'radio'; r.name = 'decision'; r.value = o[1]; if (!k) r.checked = true;
      lab.append(r, ' ' + o[0]); box.append(lab);
    });
    var open = openItems(), carry = panel.querySelector('.carry'); carry.replaceChildren();
    if (open.length) {
      carry.append(el('p', 'menu-h', 'Comes with your open comments'));
      open.forEach(function (it) { carry.append(el('p', 'carried', it.n + '. ' + (it.comment || (it.verdict === 'up' ? 'Good' : 'Not good')))); });
    }
    noteBox.focus();
  }
  decideBtn.addEventListener('click', function () { setDeciding(!deciding); });
  function sendDecision() {
    var pick = panel.querySelector('input[name="decision"]:checked'), note = noteBox.value.trim();
    if ((pick.value === 'combine' || pick.value === 'none') && !note) { say('Say how to combine them, or why none fits, in the message.', true); return noteBox.focus(); }
    var label = pick.parentElement.textContent.trim();
    send('decide', { id: 'd-' + Date.now().toString(36), option: pick.value, label: label,
                     carries: openItems().map(function (it) { return it.id; }), note: note || null },
         'Decision', function () { noteBox.value = ''; setDeciding(false); });
  }
  noteBtn.addEventListener('click', function () { if (deciding) sendDecision(); else sendNote(); });
  noteBox.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey && !deciding) { e.preventDefault(); sendNote(); } });
  renderThread();
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

            f'<button type="button" class="full">Full size</button></span></div>'
            f'<div class="stage"><div class="screen"><iframe data-i="{i}" title="{esc(label)}, {w} × {h} px" width="{w}" height="{h}" '
            f'{attr}></iframe></div></div></figure>'
            for i, (label, attr) in enumerate(loaded))
        rows.append(f'<section data-size="{k}" aria-label="Screen {w} × {h} px"{" hidden" if k else ""}>'
                    f'<div class="row" style="--n:{len(loaded)}">{figures}</div></section>')
    names = [screen_name(w, h) for w, h in sizes]
    if len(set(names)) < len(names):
        names = [f"{w} × {h}" for w, h in sizes]
    sizes_html = ('<div class="seg cycle" role="group" aria-label="Screen">' + "".join(
        f'<button type="button" class="ico" data-size="{k}" aria-pressed="{str(k == 0).lower()}" title="{esc(n)}, {w} × {h} px" '
        f'aria-label="{esc(n)}, {w} × {h} px">{ICONS.get(n, "")}<span>{esc(n)}</span></button>'
        for k, ((w, h), n) in enumerate(zip(sizes, names))) + '</div>') if len(sizes) > 1 else ""
    controls = sizes_html
    if len(labels) > 1:
        controls += ('<div class="seg cycle" role="group" aria-label="View">'
                     f'<button type="button" class="ico" data-view="side" aria-pressed="true" title="Side by side" aria-label="Side by side">{ICONS["side"]}<span>Side by side</span></button>'
                     f'<button type="button" class="ico" data-view="switch" aria-pressed="false" title="Switch in place (Space)" aria-label="Switch in place">{ICONS["switch"]}<span>Switch</span></button></div>')
    # In switch view, the version shown is picked from tabs inside the viewer, so the toolbar keeps its layout.
    tabs = ('<div class="seg pick" role="group" aria-label="Version shown" hidden>'
            + "".join(f'<button type="button" data-pick="{i}" aria-pressed="false">{esc(label)}</button>'
                      for i, label in enumerate(labels)) + '</div>') if len(labels) > 1 else ""
    side_hint = ""
    controls += ('<div class="seg cycle" role="group" aria-label="Mode">'
                 f'<button type="button" class="ico" data-mode="comment" aria-pressed="true" title="Click a version to comment on it (C)">{ICONS["comment"]}<span>Comment</span></button>'
                 f'<button type="button" class="ico" data-mode="use" aria-pressed="false" title="Use the versions as pages (C)">{ICONS["use"]}<span>Use</span></button></div>'
                 # Settings changed rarely sit in a Display menu, so the bar keeps to what is used on every visit.
                 + '<div class="more"><button type="button" class="morebtn" aria-expanded="false" aria-haspopup="true">'
                 f'{ICONS["settings"]}<span>Display</span></button><div class="menu" hidden>'
                 + ('<p class="menu-h">Scroll</p><div class="seg" role="group" aria-label="Scroll">'
                    f'<button type="button" class="ico" data-scroll="linked" aria-pressed="true" title="Versions scroll together">{ICONS["together"]}<span>Linked</span></button>'
                    f'<button type="button" class="ico" data-scroll="free" aria-pressed="false" title="Each version scrolls on its own">{ICONS["free"]}<span>Free</span></button></div>'
                    if len(labels) > 1 else '') +
                 '<p class="menu-h">Background</p><div class="seg" role="group" aria-label="Background">' + "".join(
                     f'<button type="button" class="ico sw" data-bg="{c}" aria-pressed="{str(c == BACKGROUNDS[0][1]).lower()}" '
                     f'title="{n} background" aria-label="{n} background"><span class="chip" style="background:{c}"></span><span>{n}</span></button>'
                     for n, c in BACKGROUNDS) + '</div></div></div>')
    question_html = f'<p class="question">{esc(question)}</p>' if question else ""
    notes = ('<aside class="notes" aria-labelledby="notes-h"><div class="notes-top"><h2 id="notes-h">Conversation</h2>'
             '<div class="seg filter" role="group" aria-label="Show"><button type="button" data-filter="all" aria-pressed="false">All</button>'
             '<button type="button" data-filter="open" aria-pressed="true">Open</button></div></div>'
             '<p class="empty">Nothing yet. Click any part of a version to comment on it, or write to the agent below.</p>'
             '<ol class="thread" aria-live="polite"></ol>'
             '<div class="composer"><div class="decide" hidden><p class="menu-h">Your decision</p><div class="dopts" role="radiogroup" aria-label="Decision"></div>'
             '<div class="carry"></div></div>'
             '<label for="note">Message to the agent</label><textarea id="note"></textarea>'
             '<div class="send"><button type="button" class="btn">Send</button>'
             '<button type="button" class="btn btn--quiet decide-btn" aria-expanded="false">Decide…</button>'
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
<div class="work"><main data-labels="{esc(json.dumps(labels))}" data-question="{esc(question)}">{tabs}{"".join(rows)}</main>
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
            lines = [line for line in log.read_text(encoding="utf-8").splitlines()[seen:total] if '"action": "reply"' not in line and '"action": "status"' not in line]
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


STATES = ("seen", "asked", "working", "done", "accepted")


def read_log(folder: Path) -> list:
    log = folder / "answers.jsonl"
    events = []
    for line in (log.read_text(encoding="utf-8").splitlines() if log.exists() else []):
        try:
            events.append(json.loads(line))
        except ValueError:
            pass
    return events


def set_status(folder: Path, state: str, ids: list) -> None:
    """Mark the user's comments or messages as seen, being worked on, or done; the page shows it on each one."""
    if state not in STATES:
        sys.exit(f"error: the state must be one of {', '.join(STATES)}")
    known = {e.get("id") for e in read_log(folder) if e.get("action") in ("comment", "note", "decide")}
    unknown = [i for i in ids if i not in known]
    if unknown:
        sys.exit(f"error: no comment or message with id {', '.join(unknown)}. Run --pending to see the ids.")
    with (folder / "answers.jsonl").open("a", encoding="utf-8") as f:
        for i in ids:
            # The user accepting in words is recorded as their accept, the same as the page's Accept button.
            event = {"action": "accept", "to": i, "by": "agent, from the user's words"} if state == "accepted" else \
                    {"action": "status", "to": i, "status": state}
            f.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S"), **event}) + "\n")
    print(f"Marked {state}: {', '.join(ids)}")


def pending(folder: Path) -> None:
    """Print each comment and message that is neither done nor accepted, in its latest form, including those the
    user reopened, so work can resume after an interruption."""
    items, order, state, reasons = {}, [], {}, {}
    for e in read_log(folder):
        a, i = e.get("action"), e.get("id")
        if a in ("comment", "note", "decide") and i and not e.get("to"):  # an answer belongs to the item it answers
            if i not in items:
                order.append(i)
            items[i] = e
        elif a == "delete" and i in items:
            items[i] = None
        elif a == "status":
            state[e.get("to")] = e.get("status")
        elif a in ("accept", "reopen"):
            state[e.get("to")] = "accepted" if a == "accept" else "reopened"
            if a == "reopen":
                reasons[e.get("to")] = e.get("reason")
    # Done waits for the user; accepted is finished; reopened is work again.
    open_items = [items[i] for i in order if items.get(i) and state.get(i) not in ("done", "accepted")]
    for e in open_items:
        extra = {"reopened_because": reasons[e["id"]]} if state.get(e["id"]) == "reopened" and reasons.get(e["id"]) else {}
        print(json.dumps({**e, "status": state.get(e["id"], "new"), **extra}, ensure_ascii=False))
    print(f"{len(open_items)} not done.")


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
    parser.add_argument("--status", nargs="+", metavar=("DIR STATE", "ID"),
                        help="DIR STATE ID...: mark comments or messages as seen, asked (waiting for the user), working or done; accepted only when the user accepted it in words")
    parser.add_argument("--pending", metavar="DIR", help="list the comments and messages not marked done")
    args = parser.parse_args()

    if args.wait:
        sys.exit(wait(Path(args.wait).expanduser().resolve(), args.timeout))
    if args.status:
        if len(args.status) < 3:
            parser.error("--status needs DIR, a STATE and at least one ID")
        return set_status(Path(args.status[0]).expanduser().resolve(), args.status[1], args.status[2:])
    if args.pending:
        return pending(Path(args.pending).expanduser().resolve())
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
