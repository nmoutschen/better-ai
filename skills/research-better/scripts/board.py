#!/usr/bin/env python3
"""Show a research board as a live page: what agents are working on now, and the question tree.

Usage:
  python3 board.py watch BOARD [--port N]      serve a page that updates as agents write;
                                               exits by itself when the board's status is stopped
  python3 board.py snapshot BOARD --out FILE   write a static HTML page

BOARD is the board directory described in templates/board.md.
"""

import argparse
import http.server
import json
import os
import sys
import time
import webbrowser
from pathlib import Path

KINDS = ("questions", "claims", "sources")
FIRST_SEEN: dict = {}  # (agent, line number, text) -> time the viewer first read that log line


def born(path: Path) -> float:
    """Creation time where the filesystem records it, else last modification."""
    stat = path.stat()
    return getattr(stat, "st_birthtime", stat.st_mtime)


def read_entry(path: Path) -> dict:
    entry = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() and " " not in key.strip():
            entry[key.strip()] = value.strip()
    entry.setdefault("id", path.stem)
    entry["_born"] = born(path)
    entry["_changed"] = path.stat().st_mtime
    return entry


def load(board: Path) -> dict:
    data = {"brief": {}, "logs": {}, "now": time.time()}
    if (board / "brief.md").exists():
        data["brief"] = read_entry(board / "brief.md")
    for kind in KINDS:
        folder = board / kind
        files = sorted(folder.glob("*.md")) if folder.is_dir() else []
        data[kind] = [read_entry(path) for path in files]
    if (board / "logs").is_dir():
        for path in sorted((board / "logs").glob("*.md")):
            lines = [line for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
            stamped = []
            for i, line in enumerate(lines):
                key = (path.stem, i, line)
                stamped.append([FIRST_SEEN.get(key), line])
            data["logs"][path.stem] = {"last": lines[-1] if lines else "", "lines": stamped[-60:], "count": len(lines),
                                       "_born": born(path), "_changed": path.stat().st_mtime}
    return data


PAGE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Research board</title>
<link href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Space+Grotesk:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root { --cream:#FFFCF7; --linen:#F2EDE5; --sand:#C4B69C; --terracotta:#E8725C; --moss:#6B7F5E; --umber:#5C4033;
  --ink:#33302B; --heading:#1C1A17; --muted:#78736B; --line:#DDD6CA;
  --serif:'Libre Baskerville', Georgia, serif; --sans:'Space Grotesk', -apple-system, sans-serif;
  --saya:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='130' height='75' viewBox='0 0 10 10' preserveAspectRatio='none'%3E%3Cpath fill='%23FFFCF7' fill-opacity='0.22' d='m0-1 4 4 1-1-1-1 1-1 1 1 1-1 1 1-7 7-1-1 1-1-1-1 1-1 1 1 1-1-4-4m0 8 3 3h-3m11 0-4-4-1 1 1 1-1 1-1-1-1 1-1-1 7-7 1 1-1 1 1 1-1 1-1-1-1 1 4 4m0-8-3-3h3'/%3E%3C/svg%3E");
  /* One colour per status; every status also has its own glyph and label. */
  --st-open:var(--muted); --st-partial:var(--sand); --st-progress:var(--umber); --st-answered:var(--moss);
  --st-contested:var(--terracotta); --st-notfound:var(--sand); --st-unclear:var(--terracotta); --st-scope:var(--line); }
* { box-sizing:border-box; }
html, body { height:100%; margin:0; }
body { background:var(--cream); color:var(--ink); font:400 15px/1.55 var(--sans); -webkit-font-smoothing:antialiased;
  display:flex; flex-direction:column; }
.band { height:10px; flex:none; background:var(--umber) var(--saya); background-size:13px 7.5px; }
.band--thin { height:6px; }
body { --pad:max(40px, (100% - 100rem) / 2); }
header { flex:none; padding:20px var(--pad) 12px; }
h1 { font:700 26px/1.2 var(--serif); color:var(--heading); margin:0 0 6px; }
.status { color:var(--muted); margin:0; } .status b { color:var(--heading); }
.conn { color:var(--heading); margin:4px 0 0; } .conn b { color:var(--umber); }
.card .q, .answer .q, .answer .sum, dialog h3, dialog li { overflow-wrap:anywhere; }
.meter { height:4px; background:var(--linen); display:flex; gap:2px; margin-top:10px; }
.meter i { display:block; height:100%; }
main { flex:1; min-height:0; display:grid; grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);
  grid-template-rows:auto minmax(0,1fr); gap:20px 48px; padding:8px var(--pad) 16px; }
section { min-height:0; overflow-y:auto; overflow-x:hidden; container-type:inline-size; }
.workers { grid-column:1 / -1; }
/* A stopped board with no worker drops the Workers row so the findings get the room. */
main:has(> .workers[hidden]) { grid-template-rows:minmax(0,1fr); }
h2 { font:700 12px var(--sans); letter-spacing:.1em; text-transform:uppercase; color:var(--muted);
  border-top:2px solid var(--line); padding-top:10px; margin:0 0 12px; display:flex; justify-content:space-between; }
h2 span { font-weight:400; letter-spacing:0; text-transform:none; }
.empty { color:var(--muted); font-style:italic; margin:0; grid-column:1 / -1; }
#work { display:grid; grid-template-columns:repeat(var(--n, 1), minmax(0, 1fr)); grid-auto-rows:10rem; gap:12px; max-height:42vh; overflow-y:auto; }
/* Compact rows share the list's columns (subgrid), so names, questions, meta and last actions line up down the list. */
#work.compact { grid-template-columns:fit-content(8em) minmax(0,1.6fr) auto minmax(0,1fr); grid-auto-rows:auto; gap:4px 14px; }
#work.compact .card { display:grid; grid-column:1 / -1; grid-template-columns:subgrid; align-items:baseline; padding:6px 14px 6px 22px; }
#work.compact .card::before { width:6px; }
#work.compact .agent { white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
#work.compact .q { -webkit-line-clamp:1; margin:0; font-size:14px; }
#work.compact .last { margin:0; -webkit-line-clamp:1; }
/* Narrower: the question gets its own line; what the worker is doing goes underneath. */
@container (max-width:56rem) {
  #work.compact { grid-template-columns:fit-content(7em) auto minmax(0,1fr); }
  #work.compact .card { row-gap:1px; }
  #work.compact .q { grid-column:2 / -1; }
  #work.compact .meta { grid-column:2; }
}
@container (max-width:34rem) {
  #work.compact { grid-template-columns:minmax(0,1fr); }
  #work.compact .card { padding:8px 12px 8px 22px; }
  #work.compact .card > span { grid-column:1 / -1; }
  #work.compact .q { -webkit-line-clamp:2; }
}
#work:has(.empty) { grid-auto-rows:auto; }
.card { position:relative; background:var(--linen); padding:10px 14px 10px 24px; cursor:pointer; overflow:hidden;
  display:flex; flex-direction:column; text-align:left; border:0; font:inherit; color:inherit; }
.card::before { content:""; position:absolute; left:0; top:0; bottom:0; width:10px; background:var(--terracotta) var(--saya); background-size:13px 7.5px; }
.card:focus-visible .q { color:var(--terracotta); }
.card > span { display:block; }
.card .agent { font:700 12px var(--sans); letter-spacing:.08em; text-transform:uppercase; color:var(--terracotta); }
.card .q { font:500 15px/1.4 var(--sans); color:var(--heading); margin:2px 0 4px; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
.card .meta { font-size:13px; color:var(--muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.card .last { font-size:12.5px; color:var(--ink); margin-top:auto; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; overflow-wrap:anywhere; }
.g { display:inline-block; width:1.25em; font-weight:700; flex:none; }
.legend { font-size:12px; color:var(--muted); display:flex; gap:14px; flex-wrap:wrap; margin:-4px 0 10px; }
ul.tree, ul.tree ul { list-style:none; margin:0; padding:0; }
ul.tree ul { margin-left:9px; padding-left:16px; border-left:1px solid var(--line); }
.row { display:flex; gap:6px; align-items:baseline; width:100%; padding:5px 0 5px 8px; border:0; border-left:3px solid var(--st);
  border-bottom:1px solid var(--linen); background:none; font:inherit; color:inherit; text-align:left; cursor:pointer; }
.row:focus-visible .text { color:var(--terracotta); }
.row .text { flex:1; min-width:0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font-size:14px; }
.row.active .text { color:var(--heading); font-weight:600; }
.row.closed .text { color:var(--muted); }
.row .tag { font:700 11px var(--sans); letter-spacing:.06em; text-transform:uppercase; color:var(--cream); background:var(--umber); padding:1px 6px; }
.row .pri { font:700 11px var(--sans); letter-spacing:.06em; color:var(--muted); width:4.5em; text-align:right; flex:none; }
.row .pri-high { color:var(--heading); }
.row .pri-low { font-weight:500; }
.row .prog { font-size:12px; color:var(--muted); white-space:nowrap; }
.answer { display:block; width:100%; text-align:left; background:none; border:0; border-bottom:1px solid var(--linen);
  padding:0 0 14px; margin:0 0 14px; font:inherit; color:inherit; cursor:pointer; }
.answer .q { font:500 14px/1.4 var(--sans); color:var(--heading); display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
.answer:focus-visible .q { color:var(--terracotta); }
.answer .sum { font:400 14px/1.65 var(--serif); margin:4px 0 0; display:-webkit-box; -webkit-line-clamp:4; -webkit-box-orient:vertical; overflow:hidden; }
dialog { max-width:44rem; width:calc(100% - 3rem); max-height:85vh; max-height:85dvh; border:0; padding:0; background:var(--cream); color:var(--ink); }
dialog:focus { outline:none; }
:focus-visible { outline:2px solid var(--terracotta); outline-offset:2px; }
dialog::backdrop { background:rgba(51,48,43,.45); }
dialog .band { height:6px; }
dialog .inner { padding:20px 28px 24px; overflow:auto; max-height:calc(85vh - 6px); max-height:calc(85dvh - 6px); }
dialog .close { float:right; border:0; background:none; font:700 12px var(--sans); letter-spacing:.08em; color:var(--muted); cursor:pointer; text-transform:uppercase; }
dialog h3 { font:700 20px/1.35 var(--serif); color:var(--heading); margin:6px 0 10px; }
dialog .kicker { font:700 12px var(--sans); letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }
dialog .sum { font:400 15px/1.7 var(--serif); margin:0 0 12px; }
dialog .note { font-size:13px; color:var(--muted); margin:0 0 16px; }
dialog h4 { font:700 12px var(--sans); letter-spacing:.1em; text-transform:uppercase; color:var(--muted); border-top:2px solid var(--line); padding-top:8px; margin:18px 0 6px; }
dialog ul { margin:0; padding:0; list-style:none; }
dialog li { font-size:13.5px; padding:6px 0; border-bottom:1px solid var(--linen); }
dialog li .by { display:block; font-size:12px; color:var(--muted); }
dialog li a { color:var(--terracotta); text-underline-offset:2px; }
dialog .log li { font-size:12.5px; overflow-wrap:anywhere; }
.foot { flex:none; display:flex; flex-wrap:wrap; gap:0 16px; justify-content:space-between; padding:4px var(--pad); font-size:12px; color:var(--muted); }
.foot a { color:var(--muted); }
.status, .card .meta, .row .prog, h2 span, .legend, .foot { font-variant-numeric:tabular-nums; }
@media (hover:hover) {
  .card:hover .q, .row:hover .text, .answer:hover .q, .foot a:hover { color:var(--terracotta); }
}
/* Narrow questions column: let a question use two lines instead of a handful of characters. */
@container (max-width:30rem) {
  .row .text { white-space:normal; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; }
  .row .prog { display:none; }
}
@media (pointer:coarse) { dialog .close { padding:12px 14px; margin:-12px -14px 0 0; } }
/* One column: the page scrolls as a whole, so nothing scrolls inside it. */
@media (max-width:900px) { main { grid-template-columns:1fr; } body { height:auto; } #work { max-height:none; } }
@media (max-width:600px) {
  body { --pad:20px; }
  dialog { width:calc(100% - 1rem); max-height:92dvh; }
  dialog .inner { padding:16px 18px 20px; max-height:calc(92dvh - 6px); }
}
</style></head><body>
<div class="band"></div>
<header><h1 id="topic" dir="auto">Research board</h1><p class="status" id="status">Loading the board…</p>
<p class="conn" id="conn" role="status" hidden></p><div class="meter" id="meter" aria-hidden="true"></div></header>
<main>
  <section class="workers" id="workers"><h2>Workers <span id="wcount"></span></h2><div id="work"></div></section>
  <section><h2>Questions <span id="qcount"></span></h2><div class="legend" id="legend"></div><ul class="tree" id="tree"></ul></section>
  <section><h2>Answers <span id="acount"></span></h2><div id="answers"></div></section>
</main>
<div class="band band--thin"></div>
<footer class="foot"><span id="hidden"></span><span>research-better by <a href="https://n14n.dev/" target="_blank" rel="noopener">n14n.dev</a> · <span id="updated"></span></span></footer>
<dialog id="modal" aria-labelledby="mtitle"><div class="band"></div><div class="inner"><button class="close" id="close">Close</button><div id="mbody"></div></div></dialog>
<script>
const SNAPSHOT = __SNAPSHOT__;
const STATUS = {  // glyph, label, colour variable
  "in progress": ["◐", "in progress", "--st-progress"], "partial": ["◔", "open, has evidence", "--st-partial"],
  "open": ["○", "open", "--st-open"], "answered": ["●", "answered", "--st-answered"], "contested": ["◆", "contested", "--st-contested"],
  "not found": ["✕", "not found", "--st-notfound"], "unclear": ["?", "unclear", "--st-unclear"], "out of scope": ["–", "out of scope", "--st-scope"] };
const CLOSED = new Set(["answered", "contested", "not found", "out of scope"]);
const RANK = {high:0, medium:1, low:2};
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const mins = secs => secs < 90 ? "under 2 min" : `${Math.round(secs / 60)} min`;
const plural = (n, w) => `${n} ${w}${n === 1 ? "" : "s"}`;
const $ = id => document.getElementById(id);
const has = v => v && v !== "none";
let D = null, CURRENT = null;

function prepare(d) {
  const byQ = {}; d.claims.forEach(c => (byQ[c.question] ||= []).push(c));
  const src = Object.fromEntries(d.sources.map(s => [s.id, s]));
  d.questions.forEach(q => {
    q.claimsList = byQ[q.id] || [];
    q.srcCount = new Set(q.claimsList.map(c => c.source)).size;
    q.view = String(q.status || "open").trim().toLowerCase();
    if (!STATUS[q.view] || q.view === "partial") q.view = "open";  // agents write statuses by hand; never let a typo break the page
    if (q.view === "open" && q.claimsList.length) q.view = "partial";  // reopened, or started and released
  });
  d.src = src; return d;
}
const glyph = v => { const [g, l, c] = STATUS[v] || STATUS.open; return `<span class="g" style="color:var(${c})" role="img" aria-label="${l}">${g}</span>`; };
const originOf = q => (q.origin || "").split(/[ ,;(]/)[0];
const safeUrl = u => /^https?:\/\//i.test(String(u || "").trim()) ? String(u).trim() : "";  // source URLs come from web pages
const progress = q => `${plural(q.claimsList.length, "claim")} from ${plural(q.srcCount, "source")}`;

function render(d) {
  D = prepare(d);
  const now = d.now, b = d.brief || {}, qs = d.questions;
  const stopAt = (b["stop-at"] || "medium").toLowerCase(), stopped = b.status === "stopped";
  const start = Math.min(now, ...[...qs, ...d.claims, ...d.sources].map(e => e._born));
  const scope = qs.filter(q => (RANK[q.priority] ?? 1) <= (RANK[stopAt] ?? 1) && q.view !== "out of scope");
  const done = scope.filter(q => CLOSED.has(q.view)).length, working = qs.filter(q => q.view === "in progress");
  $("topic").textContent = b.topic || "Research board";
  document.title = b.topic ? `${b.topic} · Research board` : "Research board";
  $("status").innerHTML = stopped
    ? `Stopped after ${mins(now - start)}. <b>${done} of ${scope.length}</b> questions at ${esc(stopAt)} priority or above are closed.`
    : `<b>${done} of ${scope.length}</b> questions closed at ${esc(stopAt)} priority or above · <b>${working.length}</b> in progress · ${mins(now - start)} in`;
  const m = $("meter"); m.innerHTML = "";
  ["answered", "contested", "not found", "in progress", "partial"].forEach(v => {
    const n = scope.filter(q => q.view === v).length;
    if (n) { const i = document.createElement("i"); i.style.flex = n; i.style.background = `var(${STATUS[v][2]})`; i.title = `${n} ${STATUS[v][1]}`; m.append(i); } });
  const rest = scope.filter(q => q.view === "open" || q.view === "unclear").length;
  if (rest) { const i = document.createElement("i"); i.style.flex = rest; m.append(i); }

  // Workers: one card per question in progress, all the same height.
  $("wcount").textContent = working.length ? plural(working.length, "question") + " in progress" : "";
  setHTML($("work"), working.sort((a, z) => a._changed - z._changed).map(q => {
    const owner = has(q.owner) ? q.owner : "", log = (d.logs || {})[owner] || {};
    return `<button class="card" data-worker="${esc(owner)}" data-q="${esc(q.id)}"><span class="agent">${esc(owner || "unassigned")}</span>
      <span class="q" dir="auto">${esc(q.question)}</span><span class="meta">${mins(now - q._changed)} · ${plural(q.claimsList.length, "claim")} · ${plural(q.srcCount, "source")}</span>
      <span class="last" dir="auto">${log.last ? "Last: " + esc(log.last) : "No search logged yet."}</span></button>`;
  }).join("") || '<p class="empty">No question is in progress right now.</p>');
  $("workers").hidden = stopped && !working.length;  // the status line already says it stopped
  fitWork();

  // Questions: the tree of what raised what.
  const qOfS = {}; d.claims.forEach(c => { if (c.source && !qOfS[c.source]) qOfS[c.source] = c.question; });
  const ids = new Set(qs.map(q => q.id)), shown = qs.filter(q => q.view !== "out of scope");
  const parent = q => { const o = originOf(q);
    if (ids.has(o) && o !== q.id) return o;
    if (o.startsWith("S-") && ids.has(qOfS[o]) && qOfS[o] !== q.id) return qOfS[o]; return null; };
  const kids = {}, roots = [];
  shown.forEach(q => { const p = parent(q); p && shown.some(x => x.id === p) ? (kids[p] ||= []).push(q) : roots.push(q); });
  const weight = q => q.view === "in progress" ? 0 : CLOSED.has(q.view) ? 2 : 1;
  const order = l => l.sort((a, z) => weight(a) - weight(z) || (RANK[a.priority] ?? 3) - (RANK[z.priority] ?? 3) || a._born - z._born);
  const node = q => {
    const v = q.view, sub = order(kids[q.id] || []).map(node).join("");
    const right = v === "in progress" ? `<span class="prog">${plural(q.claimsList.length, "claim")}</span><span class="tag">${esc(has(q.owner) ? q.owner : "unassigned")}</span>`
      : v === "partial" ? `<span class="prog">${plural(q.claimsList.length, "claim")}</span>` : "";
    return `<li><button class="row ${v === "in progress" ? "active" : ""} ${CLOSED.has(v) ? "closed" : ""}" style="--st:var(${STATUS[v][2]})" data-q="${esc(q.id)}">
      ${glyph(v)}<span class="text" dir="auto">${esc(q.question)}</span>${right}${has(q.priority) ? `<span class="pri pri-${esc(q.priority)}">${esc(q.priority.toUpperCase())}</span>` : ""}</button>${sub ? `<ul>${sub}</ul>` : ""}</li>`; };
  setHTML($("tree"), order(roots).map(node).join("") || '<li class="empty">No questions yet.</li>');
  const counts = {}; shown.forEach(q => counts[q.view] = (counts[q.view] || 0) + 1);
  setHTML($("legend"), Object.keys(STATUS).filter(v => counts[v]).map(v => `<span>${glyph(v)}${counts[v]} ${STATUS[v][1]}</span>`).join(""));
  $("qcount").textContent = plural(shown.length, "question");

  // Answers: every closed question with a summary, newest first.
  const answers = qs.filter(q => CLOSED.has(q.view) && q.view !== "out of scope").sort((a, z) => z._changed - a._changed);
  $("acount").textContent = answers.length ? `${answers.length}, newest first` : "";
  setHTML($("answers"), answers.map(q => `<button class="answer" data-q="${esc(q.id)}"><span class="q" dir="auto">${glyph(q.view)}${esc(q.question)}</span>
    ${has(q.summary) ? `<span class="sum" dir="auto">${esc(q.summary)}</span>` : ""}</button>`).join("") || '<p class="empty">No answers yet.</p>');

  const hidden = qs.length - shown.length;
  $("hidden").textContent = hidden ? `${plural(hidden, "out-of-scope question")} hidden` : "";
  $("updated").textContent = SNAPSHOT ? "snapshot" : `updated ${new Date(now * 1000).toLocaleTimeString()}`;
  if ($("modal").open && CURRENT) CURRENT();  // keep an open panel current
}

// Detail panels.
function showQuestion(id) {
  const q = D.questions.find(x => x.id === id); if (!q) return;
  const v = q.view, now = D.now;
  const state = v === "in progress" ? `${esc(has(q.owner) ? q.owner : "unassigned")} has worked on it for ${mins(now - q._changed)} · ${progress(q)} so far`
    : `${STATUS[v][1]} · ${progress(q)}`;
  const link = s => { const u = safeUrl(s.url);
    return u ? ` · <a href="${esc(u)}" target="_blank" rel="noopener noreferrer">source</a>` : has(s.url) ? ` · ${esc(s.url)}` : ""; };
  const claims = q.claimsList.map(c => { const s = D.src[c.source] || {};
    return `<li dir="auto">${esc(c.claim)}<span class="by">${esc(s.author || s.publisher || c.source)}${has(s.date) ? ` (${esc(s.date)})` : ""}${link(s)} · ${esc(s.trust || "?")} trust · ${esc(c.verified || "unchecked")}</span></li>`; }).join("");
  const children = D.questions.filter(x => originOf(x) === q.id && x.id !== q.id).map(x => `<li dir="auto">${glyph(x.view)}${esc(x.question)}</li>`).join("");
  setPanel(`<div class="kicker">${glyph(v)}${esc(q.priority || "")} priority · ${esc(q.id)}</div><h3 id="mtitle" dir="auto">${esc(q.question)}</h3>
    <p class="note">${state}</p>${has(q.summary) ? `<p class="sum" dir="auto">${esc(q.summary)}</p>` : ""}${has(q.note) ? `<p class="note" dir="auto">Note: ${esc(q.note)}</p>` : ""}
    ${claims ? `<h4>Claims</h4><ul>${claims}</ul>` : ""}${children ? `<h4>Questions it raised</h4><ul>${children}</ul>` : ""}`);
  CURRENT = () => showQuestion(id); openModal();
}
function showWorker(name, qid) {
  if (!name) return showQuestion(qid);
  const prefix = `-${name}-`, mine = k => D[k].filter(e => e.id.includes(prefix));
  const log = (D.logs || {})[name] || {}, lines = (log.lines || []).slice().reverse();
  const clock = t => t ? new Date(t * 1000).toLocaleTimeString([], {hour: "2-digit", minute: "2-digit", second: "2-digit"}) : "time not recorded";
  const current = D.questions.find(q => q.id === qid);
  setPanel(`<div class="kicker">Worker</div><h3 id="mtitle">${esc(name)}</h3>
    <p class="note" dir="auto">${current ? `Working on: ${esc(current.question)}` : ""}</p>
    <p class="note">Created ${plural(mine("claims").length, "claim")}, ${plural(mine("sources").length, "source")}, and ${plural(mine("questions").length, "question")}.</p>
    <h4>Activity</h4><ul class="log">${lines.map(([t, l]) => `<li dir="auto"><span class="by">${clock(t)}</span>${esc(l)}</li>`).join("") || "<li>No activity logged.</li>"}</ul>`);
  CURRENT = () => showWorker(name, qid); openModal();
}

// Workers show as cards while each card gets at least 200px, and as a compact list otherwise
// (more than five workers, or a narrow window). Re-checked whenever the window changes size.
function fitWork() {
  const w = $("work"), n = w.querySelectorAll(".card").length, cols = Math.max(1, Math.min(n, 5));
  w.style.setProperty("--n", cols);
  w.classList.toggle("compact", n > 5 || (n > 0 && (w.clientWidth - 12 * (cols - 1)) / cols < 200));
}
new ResizeObserver(fitWork).observe($("work"));

// Live updates must not take away what the reader is doing: replace a region only when its
// content changed, and put focus back on the same item when it was inside the replaced region.
const keyOf = el => { const t = el && el.closest && el.closest("[data-q]"); return t ? {cls: t.classList[0], q: t.dataset.q} : null; };
const find = (root, k) => k && root.querySelector(`.${k.cls}[data-q="${CSS.escape(k.q)}"]`);
function setHTML(el, html) {
  if (el._html === html) return;
  const a = document.activeElement, k = el.contains(a) ? keyOf(a) : null;
  el.innerHTML = el._html = html;
  const back = find(el, k); if (back) back.focus({preventScroll: true});
}
function setPanel(html) {
  const m = $("mbody"), sel = getSelection();
  const busy = !sel.isCollapsed && m.contains(sel.anchorNode) || m.contains(document.activeElement);
  if ($("modal").open && m._html !== html && busy) return;  // the reader is selecting or on a link: update on a later tick
  setHTML(m, html);
}
let OPENER = null;
function openModal() { if (!$("modal").open) { OPENER = keyOf(document.activeElement); $("modal").showModal(); } }
$("modal").addEventListener("close", () => {  // also fires on Escape
  CURRENT = null; $("mbody")._html = null;
  const back = find(document.querySelector("main"), OPENER); if (back && document.activeElement !== back) back.focus({preventScroll: true});
});
$("close").onclick = () => $("modal").close();
$("modal").addEventListener("click", e => { if (e.target === $("modal")) $("modal").close(); });
document.addEventListener("click", e => {
  const card = e.target.closest(".card"); if (card) return showWorker(card.dataset.worker, card.dataset.q);
  const q = e.target.closest("[data-q]"); if (q && !e.target.closest("dialog")) showQuestion(q.dataset.q);
});

if (SNAPSHOT) render(SNAPSHOT);
else {
  // After three failed polls in a row, say so; a quiet page that stopped updating looks like a quiet research.
  let fails = 0;
  const lost = on => {
    const c = $("conn"); c.hidden = !on; if (!on) return;
    c.innerHTML = D ? `<b>Connection lost.</b> The board viewer stopped answering after ${new Date(D.now * 1000).toLocaleTimeString()}; this is the last state it sent.`
      : `<b>Can't reach the board viewer.</b> Check that board.py watch is still running.`;
  };
  const tick = () => fetch("board.json", {cache: "no-store"})
    .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
    .then(d => { fails = 0; lost(false); try { render(d); } catch (err) { console.error("board render failed", err); } },
          () => { if (++fails === 3 && D?.brief?.status !== "stopped") lost(true); });
  tick(); setInterval(tick, 2000);
}
</script></body></html>
"""


def page(snapshot: dict | None) -> str:
    embedded = "null" if snapshot is None else json.dumps(snapshot).replace("</", "<\\/")
    return PAGE.replace("__SNAPSHOT__", embedded)


def stamp_logs(board: Path, initial: bool) -> None:
    """Record when each log line first appears. Lines present before the viewer started get no time."""
    now = time.time()
    for path in sorted((board / "logs").glob("*.md")) if (board / "logs").is_dir() else []:
        lines = [line for line in path.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]
        for i, line in enumerate(lines):
            FIRST_SEEN.setdefault((path.stem, i, line), None if initial else now)


def board_stopped(board: Path) -> bool:
    brief = board / "brief.md"
    return brief.exists() and read_entry(brief).get("status") == "stopped"


def watch(board: Path, port: int, open_browser: bool, linger: float) -> None:
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            # Only answer requests addressed to this machine, so a web page cannot read the board via DNS rebinding.
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
            if host not in ("127.0.0.1", "localhost"):
                self.send_error(403)
                return
            if self.path.startswith("/board.json"):
                stamp_logs(board, initial=False)
                body, kind = json.dumps(load(board)).encode(), "application/json"
            elif self.path in ("/", "/index.html"):
                body, kind = page(None).encode(), "text/html; charset=utf-8"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    stamp_logs(board, initial=True)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.timeout = 1
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"Watching {board} at {url}", flush=True)
    print("Stops by itself once the board's status is stopped (or press Ctrl+C).", flush=True)
    if open_browser:
        webbrowser.open(url)
    stopped_at = None
    try:
        while True:
            server.handle_request()
            stamp_logs(board, initial=False)
            if stopped_at is None and board_stopped(board):
                stopped_at = time.time()
            if stopped_at is not None and time.time() - stopped_at > linger:
                print("Board stopped; viewer exiting. The open page keeps the last state.", flush=True)
                break
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Show a research board as a web page.")
    sub = parser.add_subparsers(dest="command", required=True)
    w = sub.add_parser("watch", help="serve a live page")
    w.add_argument("board")
    w.add_argument("--port", type=int, default=0, help="port to serve on (default: any free port)")
    w.add_argument("--linger", type=float, default=10, help="seconds to keep serving after the board stops")
    w.add_argument("--no-browser", action="store_true", help="do not open a browser")
    s = sub.add_parser("snapshot", help="write a static page")
    s.add_argument("board")
    s.add_argument("--out", required=True)
    args = parser.parse_args()
    board = Path(args.board).expanduser().resolve()
    if not board.is_dir():
        sys.exit(f"error: {board} is not a directory")
    if args.command == "watch":
        watch(board, args.port, not args.no_browser, args.linger)
    else:
        Path(args.out).write_text(page(load(board)), encoding="utf-8")
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
