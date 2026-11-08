#!/usr/bin/env python3
"""Show a lesson as a local page, and write the learner's answers back for the agent.

Usage:
  python3 lesson.py check LESSON             validate lesson.json and print every text, value and label the page shows
  python3 lesson.py serve LESSON [--port N]  serve the page; the learner's answers are written to LESSON/answers/;
                                             exits by itself once lesson.json has "status": "ended"
  python3 lesson.py wait LESSON [--timeout S]
                                             block until an answer without feedback exists, print it, exit 0;
                                             exit 2 on timeout

LESSON is a lesson directory described in templates/lesson.md. The agent writes lesson.json and feedback/;
the page writes answers/. Every diagram is laid out here, so the agent never draws one by hand.
"""

import argparse
import hashlib
import http.server
import json
import re
import sys
import time
import webbrowser
from pathlib import Path

ID = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
LINK = re.compile(r"\]\(#([A-Za-z0-9_-]+)/(\d+)\)")
CARD_KINDS = ("terms", "text", "example", "practice")
BLOCK_TYPES = ("p", "list", "table", "steps", "timeline", "code")
MARKS = ("allow", "reject", "neutral")
VERDICTS = ("right", "partly", "wrong", "hint")
MAX_BODY = 40_000


# ---------- reading ----------

def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def attempts(lesson: Path) -> list[dict]:
    """Every answer the learner submitted, with the agent's feedback when it exists."""
    out = []
    for path in sorted((lesson / "answers").glob("*.json")) if (lesson / "answers").is_dir() else []:
        answer = read_json(path)
        if not isinstance(answer, dict):
            continue
        answer["file"] = path.name
        answer["feedback"] = read_json(lesson / "feedback" / path.name)
        out.append(answer)
    out.sort(key=lambda a: (a.get("id", ""), a.get("attempt", 0)))
    return out


def load(lesson: Path) -> dict:
    return {"lesson": read_json(lesson / "lesson.json", {}), "attempts": attempts(lesson), "now": time.time(), "version": VERSION}


DEFAULT_FIELDS = [{"id": "answer", "type": "text", "label": "Your answer, and how you got it"}]


def answerable(spec: dict) -> dict:
    """Map each practice card id to (whether it is a quiz question, its answer fields)."""
    ids = {}
    for chunk in spec.get("chunks", []) if isinstance(spec, dict) else []:
        for card in chunk.get("cards", []):
            if card.get("kind") == "practice" and isinstance(card.get("id"), str):
                ids[card["id"]] = (bool(chunk.get("quiz")), card.get("fields") or DEFAULT_FIELDS)
    return ids


# ---------- check ----------

def check(spec) -> tuple[list[str], list[str], list[str]]:
    errors, warnings, digest = [], [], []
    if not isinstance(spec, dict):
        return ["lesson.json is missing or is not a JSON object"], [], []
    for key in ("title", "goal"):
        if not isinstance(spec.get(key), str) or not spec[key].strip():
            errors.append(f"top level: '{key}' must be a non-empty string")
    if spec.get("status", "active") not in ("active", "ended"):
        errors.append("top level: 'status' must be 'active' or 'ended'")
    digest += [f"TITLE  {spec.get('title', '')}", f"GOAL   {spec.get('goal', '')}"]
    chunks = spec.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        errors.append("top level: 'chunks' must be a non-empty list")
        return errors, warnings, digest
    seen_chunks, seen_cards, current = set(), set(), 0
    for i, chunk in enumerate(chunks, 1):
        where = f"chunk {i}"
        if not isinstance(chunk, dict):
            errors.append(f"{where}: must be an object")
            continue
        cid = chunk.get("id")
        if not isinstance(cid, str) or not ID.match(cid) or cid in seen_chunks:
            errors.append(f"{where}: 'id' must be unique, letters, digits, - or _")
        seen_chunks.add(cid)
        status = chunk.get("status", "planned")
        if status not in ("planned", "current", "done", "skipped"):
            errors.append(f"{where}: 'status' must be planned, current, done or skipped")
        current += status == "current"
        if not isinstance(chunk.get("title"), str) or not chunk["title"].strip():
            errors.append(f"{where}: 'title' is required")
        digest.append(f"\nCHUNK {cid} [{status}{', quiz' if chunk.get('quiz') else ''}]  {chunk.get('title', '')}")
        cards = chunk.get("cards", [])
        if not isinstance(cards, list):
            errors.append(f"{where}: 'cards' must be a list")
            continue
        if status in ("current", "done") and not cards:
            errors.append(f"{where}: a {status} chunk needs cards")
        if chunk.get("quiz") and any(c.get("kind") != "practice" for c in cards if isinstance(c, dict)):
            errors.append(f"{where}: a quiz chunk holds only practice cards, so nothing on it shows the answer")
        for j, card in enumerate(cards, 1):
            check_card(card, f"{where} card {j}", errors, warnings, digest, seen_cards)
    if current > 1:
        errors.append("top level: at most one chunk can be 'current'")
    check_links(spec, "lesson.json", errors)
    return errors, warnings, digest


def check_links(spec, where, errors):
    """Every [text](#chunk-id/n) link must point at a card that exists."""
    sizes = {c.get("id"): len(c.get("cards", [])) for c in spec.get("chunks", []) if isinstance(c, dict)}
    for cid, n in LINK.findall(json.dumps(spec, ensure_ascii=False)):
        if cid not in sizes or not 1 <= int(n) <= sizes[cid]:
            errors.append(f"{where}: link #{cid}/{n} points at no card")


def check_fields(fields, where, errors, digest):
    if not isinstance(fields, list) or not fields:
        errors.append(f"{where}: 'fields' must be a non-empty list")
        return
    seen = set()
    for f in fields:
        if not isinstance(f, dict) or not isinstance(f.get("id"), str) or not ID.match(f["id"]) or f["id"] in seen:
            errors.append(f"{where}: each field needs a unique 'id' (letters, digits, - or _)")
            continue
        seen.add(f["id"])
        if not isinstance(f.get("label"), str) or not f["label"].strip():
            errors.append(f"{where}: field {f['id']} needs a 'label'")
        if f.get("type", "text") != "text":
            errors.append(f"{where}: field {f['id']} 'type' must be text")
        digest.append(f"    field {f['id']} {f.get('label', '')}" + (f" (prefill: {f['prefill']!r})" if f.get("prefill") else ""))


def check_card(card, where, errors, warnings, digest, seen_cards):
    if not isinstance(card, dict):
        errors.append(f"{where}: must be an object")
        return
    kind = card.get("kind")
    if kind not in CARD_KINDS:
        errors.append(f"{where}: 'kind' must be one of {', '.join(CARD_KINDS)}")
        return
    if not isinstance(card.get("title"), str) or not card["title"].strip():
        errors.append(f"{where}: 'title' is required")
    digest.append(f"  [{kind}] {card.get('title', '')}")
    if kind == "terms":
        terms = card.get("terms")
        if not isinstance(terms, list) or not terms:
            errors.append(f"{where}: 'terms' must be a non-empty list of {{term, means}}")
        else:
            for t in terms:
                if not isinstance(t, dict) or not t.get("term") or not t.get("means"):
                    errors.append(f"{where}: each term needs 'term' and 'means'")
                else:
                    digest.append(f"    {t['term']}: {t['means']}")
            if len(terms) > 7:
                warnings.append(f"{where}: {len(terms)} terms on one card; split them so each is used soon after it is named")
    if kind == "practice":
        pid = card.get("id")
        if not isinstance(pid, str) or not ID.match(pid) or pid in seen_cards:
            errors.append(f"{where}: a practice card needs a unique 'id' (letters, digits, - or _)")
        seen_cards.add(pid)
        digest[-1] += f"  (id {pid})"
        if "fields" in card:
            check_fields(card["fields"], where, errors, digest)
    blocks = card.get("blocks", [])
    if kind != "terms" and (not isinstance(blocks, list) or not blocks):
        errors.append(f"{where}: 'blocks' must be a non-empty list")
        return
    for k, block in enumerate(blocks if isinstance(blocks, list) else [], 1):
        check_block(block, f"{where} block {k}", errors, warnings, digest)


def check_block(b, where, errors, warnings, digest):
    if not isinstance(b, dict) or b.get("type") not in BLOCK_TYPES:
        errors.append(f"{where}: 'type' must be one of {', '.join(BLOCK_TYPES)}")
        return
    t = b["type"]
    if t == "p":
        if not isinstance(b.get("text"), str) or not b["text"].strip():
            errors.append(f"{where}: 'text' is required")
        else:
            digest.append(f"    {b['text']}")
            if len(b["text"]) > 600:
                warnings.append(f"{where}: paragraph over 600 characters; split it or move part to the next card")
    elif t == "list":
        items = b.get("items")
        if not isinstance(items, list) or not items or not all(isinstance(i, str) for i in items):
            errors.append(f"{where}: 'items' must be a non-empty list of strings")
        else:
            digest += [f"    {f'{n}.' if b.get('numbered') else '-'} {i}" for n, i in enumerate(items, 1)]
    elif t == "code":
        if not isinstance(b.get("text"), str):
            errors.append(f"{where}: 'text' is required")
        else:
            digest += ["    | " + line for line in b["text"].splitlines()]
    elif t == "table":
        cols, rows = b.get("columns"), b.get("rows")
        if not isinstance(cols, list) or not cols or not isinstance(rows, list) or not rows:
            errors.append(f"{where}: 'columns' and 'rows' must be non-empty lists")
            return
        for r in rows:
            if not isinstance(r, list) or len(r) != len(cols):
                errors.append(f"{where}: every row needs {len(cols)} cells")
                return
        if len(rows) > 15:
            warnings.append(f"{where}: {len(rows)} rows; a table this long is hard to follow on one card")
        digest.append("    " + " | ".join(map(str, cols)))
        hl = set(b.get("highlight", []))
        digest += ["    " + " | ".join(map(str, r)) + ("   <- highlighted" if i in hl else "") for i, r in enumerate(rows)]
    elif t == "steps":
        items = b.get("items")
        if not isinstance(items, list) or not items:
            errors.append(f"{where}: 'items' must be a non-empty list of {{label, note}}")
            return
        if len(items) > 7:
            warnings.append(f"{where}: {len(items)} steps; split the process")
        for n, s in enumerate(items, 1):
            if not isinstance(s, dict) or not s.get("label"):
                errors.append(f"{where}: each step needs a 'label'")
            else:
                digest.append(f"    {n}. {s['label']}" + (f" — {s['note']}" if s.get("note") else ""))
    elif t == "timeline":
        check_timeline(b, where, errors, warnings, digest)
    if b.get("caption"):
        digest.append(f"    caption: {b['caption']}")


def check_timeline(b, where, errors, warnings, digest):
    start, end = b.get("start"), b.get("end")
    if not all(isinstance(v, (int, float)) for v in (start, end)) or end <= start:
        errors.append(f"{where}: 'start' and 'end' must be numbers with end > start")
        return
    unit = b.get("unit", "")
    for band in b.get("bands", []):
        if not isinstance(band, dict) or not all(isinstance(band.get(k), (int, float)) for k in ("from", "to")):
            errors.append(f"{where}: each band needs numeric 'from' and 'to'")
            continue
        if band["from"] < start or band["to"] > end or band["to"] <= band["from"]:
            errors.append(f"{where}: band {band.get('label', '')} lies outside {start}–{end} or is empty")
        digest.append(f"    band {band['from']}–{band['to']}{unit}: {band.get('label', '')}")
    events = b.get("events", [])
    if not isinstance(events, list) or not events:
        errors.append(f"{where}: 'events' must be a non-empty list of {{at, mark, label}}")
        return
    for e in events:
        if not isinstance(e, dict) or not isinstance(e.get("at"), (int, float)):
            errors.append(f"{where}: each event needs a numeric 'at'")
            continue
        if not start <= e["at"] <= end:
            errors.append(f"{where}: event at {e['at']} lies outside {start}–{end}")
        if e.get("mark", "neutral") not in MARKS:
            errors.append(f"{where}: event 'mark' must be one of {', '.join(MARKS)}")
        digest.append(f"    event {e['at']}{unit} [{e.get('mark', 'neutral')}] {e.get('label', '')}")
    if len(events) > 40:
        warnings.append(f"{where}: {len(events)} events; the markers will crowd")
    if b.get("legend") and not isinstance(b["legend"], dict):
        errors.append(f"{where}: 'legend' must map marks to words, such as {{\"allow\": \"allowed\"}}")


# ---------- page ----------

PAGE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lesson</title>
<link href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Space+Grotesk:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root { --cream:#FFFCF7; --linen:#F2EDE5; --sand:#C4B69C; --terracotta:#E8725C; --moss:#6B7F5E; --umber:#5C4033;
  --ink:#33302B; --heading:#1C1A17; --muted:#78736B; --line:#DDD6CA;
  --serif:'Libre Baskerville', Georgia, serif; --sans:'Space Grotesk', -apple-system, sans-serif;
  --mono:ui-monospace, 'SF Mono', Menlo, Consolas, monospace;
  --saya:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='130' height='75' viewBox='0 0 10 10' preserveAspectRatio='none'%3E%3Cpath fill='%23FFFCF7' fill-opacity='0.22' d='m0-1 4 4 1-1-1-1 1-1 1 1 1-1 1 1-7 7-1-1 1-1-1-1 1-1 1 1 1-1-4-4m0 8 3 3h-3m11 0-4-4-1 1 1 1-1 1-1-1-1 1-1-1 7-7 1 1-1 1 1 1-1 1-1-1-1 1 4 4m0-8-3-3h3'/%3E%3C/svg%3E"); }
* { box-sizing:border-box; }
html, body { margin:0; }
body { background:var(--cream); color:var(--ink); font:400 15px/1.6 var(--sans); -webkit-font-smoothing:antialiased;
  min-height:100vh; display:flex; flex-direction:column; --pad:max(32px, (100% - 72rem) / 2); }
.band { height:10px; background:var(--umber) var(--saya); background-size:13px 7.5px; }
.band--thin { height:6px; }
header { padding:20px var(--pad) 10px; }
h1 { font:700 26px/1.2 var(--serif); color:var(--heading); margin:0 0 4px; }
.goal { margin:0; color:var(--ink); max-width:60rem; } .goal b { color:var(--heading); }
.rule { margin:4px 0 0; font-size:13px; color:var(--muted); }
.conn { color:var(--heading); margin:6px 0 0; } .conn b { color:var(--terracotta); }
main { flex:1; display:grid; grid-template-columns:minmax(12rem, 17rem) minmax(0, 1fr); gap:24px 48px; padding:12px var(--pad) 24px; }
h2.label { font:700 12px var(--sans); letter-spacing:.1em; text-transform:uppercase; color:var(--muted);
  border-top:2px solid var(--line); padding-top:10px; margin:0 0 10px; }
nav ol { list-style:none; margin:0; padding:0; counter-reset:c; }
nav li button { display:flex; gap:8px; align-items:baseline; width:100%; text-align:left; border:0; background:none; font:inherit; color:inherit;
  padding:6px 0 6px 8px; border-left:3px solid var(--line); border-bottom:1px solid var(--linen); cursor:pointer; }
nav li button:disabled { cursor:not-allowed; color:var(--muted); }
nav li .n { font:700 12px var(--sans); color:var(--muted); width:1.6em; flex:none; font-variant-numeric:tabular-nums; }
nav li .st { margin-left:auto; font-size:12px; color:var(--muted); white-space:nowrap; padding-right:4px; }
nav li.done button { border-left-color:var(--moss); }
nav li.current button { border-left-color:var(--terracotta); color:var(--heading); font-weight:600; }
nav li.open button { background:var(--linen); }
nav li.quiz .st { color:var(--terracotta); font-weight:700; }
nav ol.cards { margin:4px 0 8px 22px; }
nav ol.cards button { display:block; border:0; background:none; border-left:2px solid var(--linen); padding:4px 0 4px 10px; font-size:13.5px; line-height:1.35; color:var(--ink); font-weight:400; }
nav ol.cards button.here { border-left-color:var(--terracotta); color:var(--heading); font-weight:600; }
nav ol.cards .ck { display:block; font:700 10.5px var(--sans); letter-spacing:.08em; text-transform:uppercase; color:var(--muted); }
a.goto { color:var(--terracotta); text-underline-offset:2px; }
article { min-width:0; max-width:46rem; }
.kicker { font:700 12px var(--sans); letter-spacing:.08em; text-transform:uppercase; color:var(--muted); margin:0 0 4px; }
.kicker .kind { color:var(--terracotta); }
article h2.title { font:700 22px/1.3 var(--serif); color:var(--heading); margin:0 0 14px; }
.blocks > :not(:first-child) { margin-top:16px; }
.blocks p { font:400 16px/1.75 var(--serif); margin:0; }
.blocks ul, .blocks ol:not(.steps) { margin:0; padding-left:1.4em; font:400 16px/1.7 var(--serif); }
code { font:13.5px var(--mono); background:var(--linen); padding:1px 4px; }
pre { font:13.5px/1.55 var(--mono); background:var(--linen); padding:12px 14px; margin:0; overflow-x:auto; border-left:3px solid var(--sand); }
pre code { background:none; padding:0; }
figure { margin:0; }
figcaption { font-size:13px; color:var(--muted); margin-top:6px; }
table { border-collapse:collapse; width:100%; font-size:14px; font-variant-numeric:tabular-nums; }
th { font:700 13px var(--sans); color:var(--muted); text-align:left; border-bottom:2px solid var(--line); padding:6px 10px; }
td { padding:6px 10px; border-bottom:1px solid var(--linen); vertical-align:top; }
td.num, th.num { text-align:right; }
tr.hl td { background:var(--linen); color:var(--heading); font-weight:600; }
tr.hl td:first-child { box-shadow:inset 3px 0 0 var(--terracotta); }
.terms { display:grid; grid-template-columns:fit-content(14em) 1fr; gap:0 20px; margin:0; }
.terms dt { font-weight:700; color:var(--heading); padding:8px 0; border-bottom:1px solid var(--linen); }
.terms dd { margin:0; padding:8px 0; border-bottom:1px solid var(--linen); font-family:var(--serif); }
ol.steps { list-style:none; margin:0; padding:0; display:flex; flex-wrap:wrap; gap:10px 0; align-items:stretch; counter-reset:s; }
ol.steps li { display:flex; align-items:stretch; counter-increment:s; }
ol.steps li .box { background:var(--linen); padding:8px 12px 8px 14px; border-left:3px solid var(--umber); max-width:14rem; }
ol.steps li .box::before { content:counter(s); display:block; font:700 11px var(--sans); color:var(--muted); }
ol.steps li .box b { display:block; color:var(--heading); font-weight:600; }
ol.steps li .box span { display:block; font-size:13px; color:var(--muted); }
ol.steps li + li::before { content:"→"; align-self:center; padding:0 8px; color:var(--umber); font-weight:700; }
svg text { font-family:var(--sans); }
.legend { display:flex; flex-wrap:wrap; gap:4px 16px; font-size:13px; color:var(--muted); margin-top:4px; }
.sr { position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; }
form { margin-top:22px; border-top:2px solid var(--line); padding-top:14px; display:grid; gap:12px; }
label { display:grid; gap:4px; font:700 12px var(--sans); letter-spacing:.06em; text-transform:uppercase; color:var(--muted); }
label small { font-weight:400; letter-spacing:0; text-transform:none; }
textarea { font:400 15px/1.5 var(--sans); color:var(--ink); background:#fff; border:1px solid var(--line); padding:8px 10px; resize:vertical; min-height:4.5em; }
textarea:focus { outline:2px solid var(--terracotta); outline-offset:0; border-color:transparent; }
fieldset { border:0; padding:0; margin:0; display:flex; flex-wrap:wrap; gap:6px 16px; align-items:center; }
fieldset legend { font:700 12px var(--sans); letter-spacing:.06em; text-transform:uppercase; color:var(--muted); padding:0; margin-bottom:4px; width:100%; }
fieldset label { display:flex; gap:6px; align-items:center; font:400 14px var(--sans); letter-spacing:0; text-transform:none; color:var(--ink); }
.btn { font:700 13px var(--sans); letter-spacing:.06em; text-transform:uppercase; border:0; padding:9px 16px; cursor:pointer; background:var(--umber); color:var(--cream); }
.btn:disabled { opacity:.5; cursor:default; }
.btn--plain { background:none; color:var(--heading); border:1px solid var(--line); }
.sent { font-size:13px; color:var(--muted); margin:0; }
.attempt { margin-top:18px; border-left:3px solid var(--line); padding:4px 0 4px 14px; }
.attempt .who { font:700 12px var(--sans); letter-spacing:.06em; text-transform:uppercase; color:var(--muted); }
.attempt .ans { white-space:pre-wrap; margin:2px 0 6px; overflow-wrap:anywhere; }
.attempt .why { white-space:pre-wrap; margin:0 0 6px; color:var(--muted); font-size:14px; overflow-wrap:anywhere; }
.fb { background:var(--linen); padding:8px 12px; margin-top:6px; }
.fb .v { font:700 12px var(--sans); letter-spacing:.08em; text-transform:uppercase; }
.fb.right .v { color:var(--moss); } .fb.wrong .v, .fb.hint .v { color:var(--terracotta); } .fb.partly .v { color:var(--umber); }
.fb .blocks p { font-size:15px; }
.waiting { font-size:13px; color:var(--muted); font-style:italic; margin:4px 0 0; }
.pager { display:flex; gap:10px; align-items:center; margin-top:28px; border-top:1px solid var(--linen); padding-top:14px; }
.pager .pos { color:var(--muted); font-size:13px; font-variant-numeric:tabular-nums; margin-right:auto; }
.banner { background:var(--linen); border-left:3px solid var(--terracotta); padding:8px 12px; margin:0 0 16px; font-size:14px; }
.empty { color:var(--muted); font-style:italic; }
:focus-visible { outline:2px solid var(--terracotta); outline-offset:2px; }
.foot { display:flex; justify-content:space-between; padding:4px var(--pad); font-size:12px; color:var(--muted); }
.foot a { color:var(--muted); }
@media (hover:hover) { nav li button:not(:disabled):hover { color:var(--terracotta); } .btn--plain:hover { border-color:var(--terracotta); } }
@media (max-width:800px) { main { grid-template-columns:1fr; } body { --pad:20px; } }
</style></head><body>
<div class="band"></div>
<header><h1 id="title">Lesson</h1><p class="goal" id="goal"></p>
<p class="rule">Quizzes are closed-book: answer from memory, without looking back or asking for help.</p>
<p class="conn" id="conn" role="status" hidden></p></header>
<main>
  <nav aria-label="Chunks"><h2 class="label">Chunks</h2><ol id="chunks"></ol></nav>
  <article id="card" aria-live="polite"><p class="empty">Loading the lesson…</p></article>
</main>
<div class="band band--thin"></div>
<footer class="foot"><span id="updated"></span><span>teach-better by <a href="https://n14n.dev/" target="_blank" rel="noopener">n14n.dev</a></span></footer>
<script>
const VERSION = "__VERSION__";  // the server's page version; an open tab compares it to spot an updated page
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const inline = s => esc(s).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
  .replace(/\[([^\]]+)\]\(#([A-Za-z0-9_-]+)\/(\d+)\)/g, '<a class="goto" href="#$2/$3">$1</a>')  // a link to a card
  .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)"<>]+)\)/g, '<a class="goto" href="$2" target="_blank" rel="noopener">$1</a>');  // a link to a source
const $ = id => document.getElementById(id);
const KIND = {terms:"Key terms", text:"Explanation", example:"Worked example", practice:"Practice"};
const MARK = {allow:["●", "var(--moss)"], reject:["✕", "var(--terracotta)"], neutral:["○", "var(--umber)"]};
const VERDICT = {right:"Right", partly:"Partly right", wrong:"Not yet", hint:"Hint"};
let L = null, A = [], pos = null, drafts = {}, sending = false;

function chunks() { return (L && L.chunks) || []; }
function quizOn() { return chunks().find(c => c.status === "current" && c.quiz); }
function locked(c) { const q = quizOn(); return q && c !== q; }
function flat() { const out = []; chunks().forEach((c, ci) => (c.cards || []).forEach((card, k) => out.push({ci, k}))); return out; }

function blocks(list) { return `<div class="blocks">${(list || []).map(block).join("")}</div>`; }
function block(b) {
  const cap = b.caption ? `<figcaption>${inline(b.caption)}</figcaption>` : "";
  if (b.type === "p") return `<p>${inline(b.text)}</p>`;
  if (b.type === "list") { const tag = b.numbered ? "ol" : "ul"; return `<${tag}>${b.items.map(i => `<li>${inline(i)}</li>`).join("")}</${tag}>`; }
  if (b.type === "code") return `<figure><pre><code>${esc(b.text)}</code></pre>${cap}</figure>`;
  if (b.type === "table") {
    const isNum = k => b.rows.every(r => typeof r[k] === "number" || /^-?[\d.,]+%?$/.test(String(r[k]).trim()));
    const nums = b.columns.map((_, k) => isNum(k)), hl = new Set(b.highlight || []);
    return `<figure><table><thead><tr>${b.columns.map((c, k) => `<th class="${nums[k] ? "num" : ""}">${inline(c)}</th>`).join("")}</tr></thead><tbody>` +
      b.rows.map((r, i) => `<tr class="${hl.has(i) ? "hl" : ""}">${r.map((v, k) => `<td class="${nums[k] ? "num" : ""}">${inline(v)}</td>`).join("")}</tr>`).join("") +
      `</tbody></table>${cap}</figure>`;
  }
  if (b.type === "steps") return `<figure><ol class="steps">${b.items.map(s => `<li><div class="box"><b>${inline(s.label)}</b>${s.note ? `<span>${inline(s.note)}</span>` : ""}</div></li>`).join("")}</ol>${cap}</figure>`;
  if (b.type === "timeline") return timeline(b, cap);
  return "";
}

function timeline(b, cap) {
  const W = 720, left = 24, right = 24, span = b.end - b.start, unit = b.unit || "";
  const x = v => left + (v - b.start) / span * (W - left - right);
  const rows = [];  // stack markers that would overlap
  const evs = [...b.events].sort((p, q) => p.at - q.at).map(e => {
    let r = 0; while (rows[r] !== undefined && x(e.at) - rows[r] < 15) r++;
    rows[r] = x(e.at); return {...e, r};
  });
  const levels = Math.max(1, rows.length), bandTop = 22, axisY = bandTop + 18 + levels * 16, H = axisY + 34;
  let s = `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="${esc(b.caption || "Timeline")}">`;
  (b.bands || []).forEach((bd, i) => {
    const x1 = x(bd.from), x2 = x(bd.to);
    s += `<rect x="${x1}" y="${bandTop}" width="${x2 - x1}" height="${axisY - bandTop}" fill="${bd.highlight ? "var(--sand)" : i % 2 ? "var(--cream)" : "var(--linen)"}" opacity="${bd.highlight ? .45 : 1}"/>`;
    s += `<line x1="${x1}" x2="${x1}" y1="${bandTop - 4}" y2="${axisY}" stroke="var(--sand)" stroke-dasharray="3 3"/>`;
    if (bd.label) s += `<text x="${(x1 + x2) / 2}" y="${bandTop - 8}" text-anchor="middle" font-size="12" fill="var(--muted)">${esc(bd.label)}</text>`;
  });
  s += `<line x1="${left}" x2="${W - right}" y1="${axisY}" y2="${axisY}" stroke="var(--ink)"/>`;
  const ticks = b.ticks || (() => { const n = 8, raw = span / n, p = Math.pow(10, Math.floor(Math.log10(raw))), st = [1, 2, 5, 10].map(m => m * p).find(m => m >= raw);
    const t = []; for (let v = Math.ceil(b.start / st) * st; v <= b.end + 1e-9; v += st) t.push(+v.toFixed(6)); return t; })();
  ticks.forEach(t => { s += `<line x1="${x(t)}" x2="${x(t)}" y1="${axisY}" y2="${axisY + 5}" stroke="var(--ink)"/><text x="${x(t)}" y="${axisY + 19}" text-anchor="middle" font-size="12" fill="var(--ink)">${esc(t)}${esc(unit)}</text>`; });
  evs.forEach(e => {
    const [g, col] = MARK[e.mark || "neutral"], cx = x(e.at), cy = axisY - 12 - e.r * 16;
    s += `<line x1="${cx}" x2="${cx}" y1="${cy + 6}" y2="${axisY}" stroke="${col}" stroke-width="1" opacity=".5"/>`;  // a stem pins a stacked marker to its exact time
    s += `<text x="${cx}" y="${cy + 5}" text-anchor="middle" font-size="15" font-weight="700" fill="${col}"><title>${esc(e.at)}${esc(unit)} ${esc(e.label || "")}</title>${g}</text>`;
  });
  s += `</svg>`;
  const used = [...new Set(b.events.map(e => e.mark || "neutral"))], words = b.legend || {};
  const legend = used.length > 1 || words[used[0]] ? `<div class="legend">${used.map(m => `<span><b style="color:${MARK[m][1]}">${MARK[m][0]}</b> ${esc(words[m] || m)}</span>`).join("")}</div>` : "";
  const text = `<ul class="sr">${(b.bands || []).map(bd => `<li>${esc(bd.label || "")} from ${esc(bd.from)} to ${esc(bd.to)}${esc(unit)}</li>`).join("")}${b.events.map(e => `<li>${esc(e.at)}${esc(unit)}: ${esc(words[e.mark || "neutral"] || e.mark || "")} ${esc(e.label || "")}</li>`).join("")}</ul>`;
  return `<figure>${s}${legend}${cap}${text}</figure>`;
}

function attemptsFor(id) { return A.filter(a => a.id === id); }
function attemptHtml(a) {
  const f = a.feedback, conf = a.confidence ? ` · confidence ${esc(a.confidence)}` : "";
  return `<div class="attempt"><div class="who">Attempt ${esc(a.attempt)}${conf}</div><p class="ans">${esc(a.answer)}</p>` +
    (a.explanation ? `<p class="why">${esc(a.explanation)}</p>` : "") +
    (f ? `<div class="fb ${esc(f.verdict)}"><div class="v">${esc(VERDICT[f.verdict] || f.verdict)}</div>${f.text ? blocks([{type:"p", text:f.text}]) : ""}${f.blocks ? blocks(f.blocks) : ""}</div>`
       : `<p class="waiting">${a.quiz ? "Saved. You get feedback once you have answered every question in the quiz." : "Sent. Waiting for feedback…"}</p>`) + `</div>`;
}

function form(card, quiz) {
  const tries = attemptsFor(card.id), last = tries[tries.length - 1];
  const done = last && last.feedback && last.feedback.verdict === "right";
  const pending = last && !last.feedback;
  if (quiz && last) return tries.map(attemptHtml).join("");  // a quiz question takes one answer
  const d = drafts[card.id] || {};
  const prior = tries.map(attemptHtml).join("");
  if (done || pending) return prior;
  const lastValue = id => last ? ((last.fields || []).find(x => x.id === id) || {}).value ?? (id === "answer" ? last.answer : undefined) : undefined;  // a retry starts from the previous answer
  const fields = card.fields || [{id:"answer", type:"text", label:"Your answer, and how you got it", hint:"in your own words"}];
  const field = f => `<label>${inline(f.label)}${f.hint ? ` <small>(${esc(f.hint)})</small>` : ""}<textarea name="f:${esc(f.id)}" required rows="${fields.length > 1 ? 3 : 5}">${esc(d[`f:${f.id}`] ?? lastValue(f.id) ?? f.prefill ?? "")}</textarea></label>`;
  return prior + `<form id="answer" data-id="${esc(card.id)}">
    ${fields.map(field).join("")}
    <fieldset><legend>How confident are you? <small>(optional)</small></legend>
      ${["low", "medium", "high"].map(c => `<label><input type="radio" name="confidence" value="${c}" ${d.confidence === c ? "checked" : ""}> ${c}</label>`).join("")}</fieldset>
    <div><button class="btn" type="submit">${quiz ? "Submit" : "Send answer"}</button></div>
  </form>`;
}

function show() {
  if (!L) return;
  const all = flat();
  if (!all.length) { $("card").innerHTML = `<p class="empty">No cards yet.</p>`; return; }
  const q = quizOn();
  if (!pos && location.hash) {
    const [id, k] = decodeURIComponent(location.hash.slice(1)).split("/"), ci = chunks().findIndex(c => c.id === id);
    if (ci >= 0) pos = {ci, k: Math.max(0, (+k || 1) - 1)};
  }
  if (!pos || !chunks()[pos.ci] || !(chunks()[pos.ci].cards || [])[pos.k] || locked(chunks()[pos.ci])) {
    const cur = q || chunks().find(c => c.status === "current") || chunks()[0];
    pos = {ci: chunks().indexOf(cur), k: 0};
  }
  const c = chunks()[pos.ci], card = c.cards[pos.k], i = all.findIndex(p => p.ci === pos.ci && p.k === pos.k);
  history.replaceState(null, "", `#${encodeURIComponent(c.id)}/${pos.k + 1}`);  // a reload keeps the learner's place
  const kind = c.quiz ? "Quiz" : KIND[card.kind];
  let h = q ? `<p class="banner"><b>Closed-book quiz.</b> The other chunks are hidden until you finish it.</p>` : "";
  h += `<p class="kicker"><span class="kind">${esc(kind)}</span> · ${esc(c.title)} · card ${pos.k + 1} of ${c.cards.length}</p><h2 class="title">${inline(card.title)}</h2>`;
  if (card.kind === "terms") h += `<dl class="terms">${card.terms.map(t => `<dt>${inline(t.term)}</dt><dd>${inline(t.means)}</dd>`).join("")}</dl>`;
  if (card.blocks) h += blocks(card.blocks);
  if (card.kind === "practice") h += form(card, c.quiz);
  const prev = all[i - 1], next = all[i + 1];
  h += `<div class="pager"><span class="pos">${i + 1} / ${all.length}</span>
    <button class="btn btn--plain" id="prev" ${ok(prev) ? "" : "disabled"}>← Back</button>
    <button class="btn btn--plain" id="next" ${ok(next) ? "" : "disabled"}>Next →</button></div>`;
  const active = document.activeElement, keep = active && active.name && active.form ? active.name : null;
  $("card").innerHTML = h;
  if (keep && $("answer")) { const el = $("answer").elements[keep]; if (el && el.focus) el.focus(); }
  $("prev").onclick = () => go(prev);
  $("next").onclick = () => go(next);
  const f = $("answer");
  if (f) {
    f.oninput = () => { const fd = new FormData(f); drafts[f.dataset.id] = Object.fromEntries(fd); };
    f.onsubmit = async ev => {
      ev.preventDefault(); if (sending) return; sending = true;
      const fd = Object.fromEntries(new FormData(f)), card = cardAt(pos), out = {};
      (card.fields || [{id:"answer", type:"text"}]).forEach(fl => {
        out[fl.id] = fd[`f:${fl.id}`];
      });
      f.querySelector("button").disabled = true;
      try {
        const r = await fetch("/answer", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({id:f.dataset.id, confidence:fd.confidence, fields:out})});
        if (!r.ok) throw new Error(await r.text());
        delete drafts[f.dataset.id]; await poll();
      } catch (e) { alert("Could not send the answer: " + e.message); f.querySelector("button").disabled = false; }
      sending = false;
    };
  }
  renderNav();
}

function cardAt(p) { const c = chunks()[p.ci]; return c && (c.cards || [])[p.k]; }
function ok(p) { return p && cardAt(p) && !locked(chunks()[p.ci]); }
function go(p) {
  if (!ok(p)) return;
  pos = {ci:p.ci, k:p.k}; show(); window.scrollTo(0, 0);
}
document.addEventListener("click", e => {
  const a = e.target.closest("a.goto"); if (!a || !a.getAttribute("href").startsWith("#")) return;
  e.preventDefault();
  const [id, k] = decodeURIComponent(a.getAttribute("href").slice(1)).split("/"), ci = chunks().findIndex(c => c.id === id);
  if (ci >= 0) go({ci, k:(+k || 1) - 1});
});

function renderNav() {
  $("chunks").innerHTML = chunks().map((c, ci) => {
    const lk = locked(c), st = c.status === "done" ? "done" : c.status === "skipped" ? "skipped" : c.quiz ? "quiz" : c.status === "current" ? "now" : "";
    const cls = [c.status, c.quiz && c.status !== "done" ? "quiz" : "", pos && pos.ci === ci ? "open" : ""].join(" ");
    const usable = (c.cards || []).length && !lk;
    return `<li class="${cls}"><button data-ci="${ci}" ${usable ? "" : "disabled"} ${pos && pos.ci === ci ? 'aria-current="true"' : ""}>
      <span class="n">${ci + 1}</span><span>${esc(lk ? "Hidden during the quiz" : c.title)}</span><span class="st">${esc(st)}</span></button>${
      pos && pos.ci === ci ? `<ol class="cards">${c.cards.map((card, k) => `<li><button data-ci="${ci}" data-k="${k}" ${k === pos.k ? 'aria-current="true" class="here"' : ""}>
        <span class="ck">${esc(c.quiz ? "Quiz" : KIND[card.kind])}</span>${inline(card.title)}</button></li>`).join("")}</ol>` : ""}</li>`;
  }).join("");
  document.querySelectorAll("nav button[data-ci]").forEach(btn => btn.onclick = () => go({ci:+btn.dataset.ci, k:+(btn.dataset.k || 0)}));
}

document.addEventListener("keydown", e => {
  if (["TEXTAREA", "INPUT", "SELECT"].includes(document.activeElement.tagName)) return;
  if (e.key === "ArrowRight" && $("next")) $("next").click();
  if (e.key === "ArrowLeft" && $("prev")) $("prev").click();
});

let lastSig = "";
async function poll() {
  try {
    const r = await fetch("/lesson.json", {cache:"no-store"}); const d = await r.json();
    $("conn").hidden = true;
    if (d.version && d.version !== VERSION) {
      $("conn").innerHTML = `<b>This page was updated.</b> <a href="${esc(location.hash)}" onclick="location.reload();return false">Reload</a> to see the new version. Copy any answer you are typing first.`;
      $("conn").hidden = false;
    }
    const sig = JSON.stringify([d.lesson, d.attempts]);
    if (sig === lastSig) return; lastSig = sig;
    L = d.lesson || {}; A = d.attempts || [];
    $("title").textContent = L.title || "Lesson"; document.title = (L.title || "Lesson") + " · Lesson";
    $("goal").innerHTML = L.goal ? `<b>Goal:</b> ${inline(L.goal)}` : "";
    $("updated").textContent = "Updated " + new Date().toLocaleTimeString();
    if (L.status === "ended") $("conn").innerHTML = "<b>Lesson ended.</b> This page keeps the last state.", $("conn").hidden = false;
    show();
  } catch (e) { $("conn").innerHTML = "<b>Not connected.</b> The lesson server has stopped; the page shows the last state."; $("conn").hidden = false; }
}
poll(); setInterval(poll, 2000);
</script></body></html>
"""


VERSION = hashlib.sha1(PAGE.encode()).hexdigest()[:12]
PAGE = PAGE.replace("__VERSION__", VERSION)


# ---------- server ----------

def save_answer(lesson: Path, payload: dict) -> tuple[int, str]:
    spec = read_json(lesson / "lesson.json", {})
    ids = answerable(spec)
    pid = payload.get("id")
    if not isinstance(pid, str) or pid not in ids:
        return 400, "unknown practice card"
    quiz, fields = ids[pid]
    sent = payload.get("fields") if isinstance(payload.get("fields"), dict) else {}
    confidence = payload.get("confidence") if payload.get("confidence") in ("low", "medium", "high") else None
    answers, lines = [], []
    for f in fields:
        value = str(sent.get(f["id"]) or "").strip()[:5000]
        if not value or value == str(f.get("prefill", "")).strip():
            return 400, f"fill in: {f['label']}"
        answers.append({"id": f["id"], "label": f["label"], "value": value})
        lines.append(value if len(fields) == 1 else f"{f['label']}: {value}")
    answer = "\n".join(lines)
    folder = lesson / "answers"
    folder.mkdir(exist_ok=True)
    (lesson / "feedback").mkdir(exist_ok=True)
    n = 1 + sum(1 for _ in folder.glob(f"{pid}.*.json"))
    record = {"id": pid, "attempt": n, "quiz": quiz, "answer": answer[:20000], "fields": answers,
              "confidence": confidence, "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    (folder / f"{pid}.{n}.json").write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return 200, "saved"


def serve(lesson: Path, port: int, open_browser: bool, linger: float) -> None:
    class Handler(http.server.BaseHTTPRequestHandler):
        def local(self) -> bool:
            # Only answer requests addressed to this machine, so a web page cannot reach the lesson via DNS rebinding.
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
            return host in ("127.0.0.1", "localhost")

        def reply(self, code: int, body: bytes, kind: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if not self.local():
                return self.send_error(403)
            if self.path.startswith("/lesson.json"):
                return self.reply(200, json.dumps(load(lesson)).encode(), "application/json")
            if self.path in ("/", "/index.html"):
                return self.reply(200, PAGE.encode(), "text/html; charset=utf-8")
            self.send_error(404)

        def do_POST(self):
            # Only this page may write answers: same host, and a JSON body that a cross-site form cannot send.
            origin = self.headers.get("Origin", "")
            if not self.local() or self.path != "/answer" or not re.match(r"^http://(127\.0\.0\.1|localhost):\d+$", origin):
                return self.send_error(403)
            if not (self.headers.get("Content-Type") or "").startswith("application/json"):
                return self.send_error(415)
            size = int(self.headers.get("Content-Length") or 0)
            if size <= 0 or size > MAX_BODY:
                return self.send_error(413)
            try:
                payload = json.loads(self.rfile.read(size))
            except ValueError:
                return self.reply(400, b"invalid JSON", "text/plain")
            code, msg = save_answer(lesson, payload if isinstance(payload, dict) else {})
            self.reply(code, msg.encode(), "text/plain; charset=utf-8")

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.timeout = 1
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"Serving {lesson} at {url}", flush=True)
    print('Stops by itself once lesson.json has "status": "ended" (or press Ctrl+C).', flush=True)
    if open_browser:
        webbrowser.open(url)
    ended_at = None
    try:
        while True:
            server.handle_request()
            if ended_at is None and read_json(lesson / "lesson.json", {}).get("status") == "ended":
                ended_at = time.time()
            if ended_at is not None and time.time() - ended_at > linger:
                print("Lesson ended; server exiting. The open page keeps the last state.", flush=True)
                break
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def ready(lesson: Path) -> list[dict]:
    """Answers that need feedback now. A quiz answer waits until every question in its quiz has an answer."""
    spec, tried = read_json(lesson / "lesson.json", {}), attempts(lesson)
    answered = {a["id"] for a in tried}
    quiz_of = {}
    for chunk in spec.get("chunks", []):
        if chunk.get("quiz"):
            ids = [c.get("id") for c in chunk.get("cards", []) if c.get("kind") == "practice"]
            for i in ids:
                quiz_of[i] = ids
    return [a for a in tried if a["feedback"] is None and all(i in answered for i in quiz_of.get(a["id"], []))]


def wait(lesson: Path, timeout: float) -> int:
    deadline = time.time() + timeout
    while time.time() < deadline:
        pending = ready(lesson)
        if pending:
            for a in pending:
                a.pop("feedback", None)
                print(json.dumps(a, ensure_ascii=False))
            print(f"Write feedback to {lesson / 'feedback'}/<file> with the same file name.", flush=True)
            return 0
        time.sleep(1)
    print("No new answer before the timeout.", flush=True)
    return 2


def main() -> None:
    parser = argparse.ArgumentParser(description="Show a lesson as a page and collect the learner's answers.")
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("check", help="validate lesson.json and print what the page shows")
    c.add_argument("lesson")
    s = sub.add_parser("serve", help="serve the lesson page")
    s.add_argument("lesson")
    s.add_argument("--port", type=int, default=0, help="port to serve on (default: any free port)")
    s.add_argument("--linger", type=float, default=10, help="seconds to keep serving after the lesson ends")
    s.add_argument("--no-browser", action="store_true", help="do not open a browser")
    w = sub.add_parser("wait", help="block until the learner sends an answer")
    w.add_argument("lesson")
    w.add_argument("--timeout", type=float, default=3600, help="seconds to wait (default: 3600)")
    args = parser.parse_args()
    lesson = Path(args.lesson).expanduser().resolve()
    if not lesson.is_dir():
        sys.exit(f"error: {lesson} is not a directory")
    if args.command == "check":
        errors, warnings, digest = check(read_json(lesson / "lesson.json"))
        print("\n".join(digest))
        for w_ in warnings:
            print(f"warning: {w_}")
        for e in errors:
            print(f"error: {e}")
        if errors:
            sys.exit(1)
        print("\nok" if not warnings else "\nok, with warnings")
    elif args.command == "serve":
        errors, _, _ = check(read_json(lesson / "lesson.json"))
        if errors:
            sys.exit("error: lesson.json does not pass check; run: python3 lesson.py check " + str(lesson))
        serve(lesson, args.port, not args.no_browser, args.linger)
    else:
        sys.exit(wait(lesson, args.timeout))


if __name__ == "__main__":
    main()
