#!/usr/bin/env python3
"""Show a lesson as a local page, and write the learner's answers back for the agent.

Usage:
  python3 lesson.py check LESSON             validate lesson.json and print every text, value and label the page shows
  python3 lesson.py serve LESSON [--port N]  serve the page; the learner's answers are written to LESSON/answers/;
                                             exits by itself once lesson.json has "status": "ended"
  python3 lesson.py wait LESSON [--timeout S]
                                             block until an answer without feedback exists, print it, exit 0;
                                             exit 2 on timeout
  python3 lesson.py build LESSON [--out DIR] write a static page that needs no server: answers stay in the
                                             reader's browser, and hints and solutions open on a click

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

HERE = Path(__file__).resolve().parent  # lesson.html, the page template, sits next to this script
ID = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
LINK = re.compile(r"\]\(#([A-Za-z0-9_-]+)/(\d+)\)")
CARD_KINDS = ("terms", "text", "example", "practice")
BLOCK_TYPES = ("p", "list", "table", "steps", "timeline", "code")
MARKS = ("allow", "reject", "neutral")
VERDICTS = ("right", "partly", "wrong", "hint", "noted")
FIELD_TYPES = ("text", "short", "choice", "rank")
MAX_BODY = 40_000


# ---------- reading ----------

def filled(value) -> bool:
    """A string with something other than whitespace in it."""
    return isinstance(value, str) and bool(value.strip())


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
        if not filled(spec.get(key)):
            errors.append(f"top level: '{key}' must be a non-empty string")
    if spec.get("status", "active") not in ("active", "ended"):
        errors.append("top level: 'status' must be 'active' or 'ended'")
    if "audience" in spec and not filled(spec["audience"]):
        errors.append("top level: 'audience' must be a non-empty string")
    digest += [f"TITLE  {spec.get('title', '')}", f"GOAL   {spec.get('goal', '')}"]
    if spec.get("audience"):
        digest.append(f"FOR    {spec['audience']}")
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
        if not filled(chunk.get("title")):
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


def check_fields(fields, where, errors, warnings, digest):
    if not isinstance(fields, list) or not fields:
        errors.append(f"{where}: 'fields' must be a non-empty list")
        return
    seen = set()
    for f in fields:
        if not isinstance(f, dict) or not isinstance(f.get("id"), str) or not ID.match(f["id"]) or f["id"] in seen:
            errors.append(f"{where}: each field needs a unique 'id' (letters, digits, - or _)")
            continue
        seen.add(f["id"])
        if not filled(f.get("label")):
            errors.append(f"{where}: field {f['id']} needs a 'label'")
        kind = f.get("type", "text")
        if kind not in FIELD_TYPES:
            errors.append(f"{where}: field {f['id']} 'type' must be one of {', '.join(FIELD_TYPES)}")
            continue
        line = f"    field {f['id']} [{kind}] {f.get('label', '')}"
        if kind in ("text", "short"):
            if f.get("prefill"):
                line += f" (prefill: {f['prefill']!r})"
            if "options" in f:
                errors.append(f"{where}: field {f['id']} 'options' works only on choice and rank fields")
            if "multiple" in f:
                errors.append(f"{where}: field {f['id']} 'multiple' works only on choice fields")
        else:
            opts = f.get("options")
            least = 3 if kind == "rank" else 2
            if not isinstance(opts, list) or len(opts) < least or not all(isinstance(o, str) and o.strip() for o in opts):
                errors.append(f"{where}: field {f['id']} needs 'options': a list of at least {least} non-empty strings")
            elif len(set(opts)) != len(opts):
                errors.append(f"{where}: field {f['id']} has duplicate options")
            elif len(opts) > 8:
                warnings.append(f"{where}: field {f['id']} has {len(opts)} options; more than 8 is hard to compare")
            if "prefill" in f:
                errors.append(f"{where}: field {f['id']} 'prefill' works only on text and short fields")
            if "multiple" in f and (kind != "choice" or not isinstance(f["multiple"], bool)):
                errors.append(f"{where}: field {f['id']} 'multiple' must be true or false, on a choice field")
            if isinstance(opts, list):
                line += (" (pick several)" if f.get("multiple") else "") + "".join(f"\n      - {o}" for o in opts)
        digest.append(line)


def check_card(card, where, errors, warnings, digest, seen_cards):
    if not isinstance(card, dict):
        errors.append(f"{where}: must be an object")
        return
    kind = card.get("kind")
    if kind not in CARD_KINDS:
        errors.append(f"{where}: 'kind' must be one of {', '.join(CARD_KINDS)}")
        return
    if not filled(card.get("title")):
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
            check_fields(card["fields"], where, errors, warnings, digest)
    blocks = card.get("blocks", [])
    if kind != "terms" and (not isinstance(blocks, list) or not blocks):
        errors.append(f"{where}: 'blocks' must be a non-empty list")
        return
    for k, block in enumerate(blocks if isinstance(blocks, list) else [], 1):
        check_block(block, f"{where} block {k}", errors, warnings, digest)
    if kind == "practice":
        check_static(card, where, errors, warnings, digest)


def check_static(card, where, errors, warnings, digest):
    """The fields a static page shows behind a click: hints, a worked solution, and common wrong answers."""
    hints = card.get("hints", [])
    if not isinstance(hints, list) or not all(filled(h) for h in hints):
        errors.append(f"{where}: 'hints' must be a list of non-empty strings")
    else:
        if len(hints) > 3:
            warnings.append(f"{where}: {len(hints)} hints; more than 3 gives the answer away step by step")
        digest += [f"    hint {n}: {h}" for n, h in enumerate(hints, 1)]
    if "solution" in card:
        if not isinstance(card["solution"], list) or not card["solution"]:
            errors.append(f"{where}: 'solution' must be a non-empty list of blocks")
        else:
            digest.append("    solution:")
            for k, block in enumerate(card["solution"], 1):
                check_block(block, f"{where} solution block {k}", errors, warnings, digest)
    wrong = card.get("wrong", [])
    if not isinstance(wrong, list) or not all(isinstance(w, dict) and filled(w.get("answer")) and filled(w.get("why")) for w in wrong):
        errors.append(f"{where}: 'wrong' must be a list of {{answer, why}}")
    else:
        digest += [f"    wrong: {w['answer']} -> {w['why']}" for w in wrong]


def check_block(b, where, errors, warnings, digest):
    if not isinstance(b, dict) or b.get("type") not in BLOCK_TYPES:
        errors.append(f"{where}: 'type' must be one of {', '.join(BLOCK_TYPES)}")
        return
    t = b["type"]
    if t == "p":
        if not filled(b.get("text")):
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

PAGE = (HERE / "lesson.html").read_text(encoding="utf-8")


VERSION = hashlib.sha1(PAGE.encode()).hexdigest()[:12]
PAGE = PAGE.replace("__VERSION__", VERSION)


def static_errors(spec: dict) -> list[str]:
    """What a static page needs beyond check: a solution on every practice card, since no one answers the reader."""
    return [f"practice card {card.get('id')}: a static page needs a 'solution'"
            for chunk in spec.get("chunks", []) for card in chunk.get("cards", [])
            if card.get("kind") == "practice" and "solution" not in card]


def build(lesson: Path, out: Path) -> None:
    """Write out/index.html: the lesson page with lesson.json inside it, for any static host."""
    spec = read_json(lesson / "lesson.json")
    data = json.dumps({"lesson": spec}, ensure_ascii=False).replace("</", "<\\/")  # keep the JSON inside its <script>
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(PAGE.replace("const STATIC = null;", f"const STATIC = {data};"), encoding="utf-8")


# ---------- server ----------

def read_field(f: dict, raw) -> tuple[dict, str]:
    """Turn one submitted field into the record written to answers/, or return why it is refused.
    Choice and rank fields arrive as option indexes and are stored as the option texts."""
    kind, label = f.get("type", "text"), f["label"]
    record = {"id": f["id"], "label": label, "type": kind}
    if kind in ("text", "short"):
        value = str(raw or "").strip()[:5000]
        if not value or value == str(f.get("prefill", "")).strip():
            return {}, f"fill in: {label}"
        record["value"] = value
        return record, ""
    opts = f.get("options") or []
    picks = raw if isinstance(raw, list) else ([] if raw in (None, "") else [raw])
    try:
        picks = [int(i) for i in picks]
    except (TypeError, ValueError):
        return {}, f"not a valid answer: {label}"
    if any(not 0 <= i < len(opts) for i in picks) or len(set(picks)) != len(picks):
        return {}, f"not a valid answer: {label}"
    chosen = [opts[i] for i in picks]
    if kind == "rank":
        if len(picks) != len(opts):
            return {}, f"rank every option: {label}"
        record["order"] = chosen
        record["value"] = "; ".join(f"{n}. {o}" for n, o in enumerate(chosen, 1))
    else:
        if not picks or (len(picks) > 1 and not f.get("multiple")):
            return {}, f"choose {'at least one option' if f.get('multiple') else 'one option'}: {label}"
        record["selected"] = chosen
        record["value"] = "; ".join(chosen)
    return record, ""


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
        record, error = read_field(f, sent.get(f["id"]))
        if error:
            return 400, error
        answers.append(record)
        lines.append(record["value"] if len(fields) == 1 else f"{f['label']}: {record['value']}")
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
    if open_browser and not webbrowser.open(url):
        print("Could not open a browser on this machine. If the user's browser runs on another machine, this address does not reach it.", flush=True)
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
    b = sub.add_parser("build", help="write a static page that needs no server")
    b.add_argument("lesson")
    b.add_argument("--out", help="output directory (default: LESSON/site)")
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
    elif args.command == "build":
        spec = read_json(lesson / "lesson.json")
        errors, _, _ = check(spec)
        errors += static_errors(spec) if not errors else []
        if errors:
            sys.exit("\n".join(f"error: {e}" for e in errors))
        out = Path(args.out).expanduser().resolve() if args.out else lesson / "site"
        build(lesson, out)
        print(f"Wrote {out / 'index.html'}")
    elif args.command == "serve":
        errors, _, _ = check(read_json(lesson / "lesson.json"))
        if errors:
            sys.exit("error: lesson.json does not pass check; run: python3 lesson.py check " + str(lesson))
        serve(lesson, args.port, not args.no_browser, args.linger)
    else:
        sys.exit(wait(lesson, args.timeout))


if __name__ == "__main__":
    main()
