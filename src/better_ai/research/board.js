// A page written by `render` carries its data in #page-data and has no server; a served page reads /data.
// What the board shows of an invalid record, said under the errors band.
const ERRORS_NOTE = "Questions and the brief are shown marked not valid, claims and sources under the question they name, and messages without the parts that failed; other records are only listed here.";
// The page's data, read before anything depends on it: the page is a read-only copy when it has any.
const snapshotText = document.getElementById("page-data") && document.getElementById("page-data").textContent;
const SNAPSHOT = typeof snapshotText === "string" && snapshotText ? JSON.parse(snapshotText) : null;
const $ = id => document.getElementById(id);
const esc = pageEscape;
const has = v => v && v !== "none";
const plural = (n, w) => `${n} ${w}${n === 1 ? "" : "s"}`;
const mins = s => s < 90 ? "under 2 min" : `${Math.round(s / 60)} min`;
// A question's status is one of the schema's words; one this table lacks still counts as to do.
const STATE = { "answered": ["answered", "ok"], "in progress": ["working", "working"], "open": ["to do", "plain"], "proposed": ["proposed", "plain"],
  "contested": ["contested", "error"], "not found": ["not found", "error"], "unclear": ["unclear", "error"] };
const FILL = { ok: "#6B7F5E", working: "#E8725C", plain: "#C4B69C", error: "#9A3B2A" };
const SIZE = { high: 10, medium: 7, low: 4.5 };  // dot radius by priority; a question without one is drawn as medium
const CLOSED = new Set(["answered", "contested", "not found"]);
let D = null, LAYOUT = "", OPEN = null, REPLIES = -1, SCROLLED = false, CLOSED_PAGE = false;  // OPEN: what the open pop-up shows, as {kind, id}

// ---------- Shape the board ----------
function prepare(d) {
  // A valid merged question is shown by the one it was merged into; a valid withdrawn claim and a valid question out
  // of scope are not shown. An invalid one is shown, marked, so that nothing a broken file names vanishes.
  const all = new Set(d.questions.map(q => q.id));
  const merged = Object.fromEntries(d.questions.filter(q => q.status === "merged" && !q._errors && all.has(q.merged_into)).map(q => [q.id, q.merged_into]));
  // A merge counts only when following it ends on a question that is not merged: questions merged into themselves or
  // into each other stay on the board, with their claims.
  const steps = Object.keys(merged).length;
  Object.keys(merged).filter(id => { let at = merged[id]; for (let i = 0; i < steps && at !== id && at in merged; i++) at = merged[at]; return at === id; })
    .forEach(id => delete merged[id]);
  const into = id => { for (let i = 0; merged[id] && i <= steps; i++) id = merged[id]; return id; };
  const qs = d.questions.filter(q => (q.status !== "out of scope" || q._errors) && !merged[q.id]);
  const ids = new Set(qs.map(q => q.id)), qOfSource = {};
  d.claims = d.claims.filter(c => c.status !== "withdrawn" || c._errors);
  d.claims.forEach(c => { if (!qOfSource[c.source]) qOfSource[c.source] = c.question; });
  const searches = {};
  Object.values(d.logs || {}).forEach(l => (l.searches || []).forEach(r => { const id = into(r.question); searches[id] = (searches[id] || 0) + 1; }));
  qs.forEach(q => {
    q.view = STATE[q.status] ? q.status : "open";
    q.label = has(q.title) ? q.title : shorten(q.question || q.id);
    q.claimsList = d.claims.filter(c => into(c.question) === q.id);
    q.searches = searches[q.id] || 0;
    q.prio = ["high", "medium", "low"].includes(q.priority) ? q.priority : "";
    // Where it was raised: the question it came after, else the question its origin is or the source's claim belongs to.
    const origin = q.origin || {};  // an invalid record may lack it
    const o = into(q.raised_in || (origin.type === "question" ? origin.question : origin.type === "source" ? qOfSource[origin.source] : null));
    q.parent = ids.has(o) && o !== q.id ? o : null;
  });
  // A loop in the origins would hang the layout: cut it at the question that closes it.
  qs.forEach(q => { const seen = new Set([q.id]); let p = q.parent;
    while (p) { if (seen.has(p)) { q.parent = null; break; } seen.add(p); p = (qs.find(x => x.id === p) || {}).parent; } });
  d.qs = qs; d.byId = Object.fromEntries(qs.map(q => [q.id, q]));
  return d;
}
function shorten(t) { const s = String(t).split(/ \(|, |: |; | — /)[0]; return s.length <= 60 ? s : s.slice(0, 59).replace(/\s+\S*$/, "") + "…"; }
const stateOf = q => STATE[q.view] || STATE.open;

// ---------- Slices ----------
const CX = 470, CY = 300, R1 = 100, RMAX = 215;
function layout(d) {
  const seeds = d.qs.filter(q => !q.parent).sort((a, z) => a._born - z._born || a.id.localeCompare(z.id));
  const kids = {}; d.qs.forEach(q => { if (q.parent) (kids[q.parent] ||= []).push(q); });
  Object.values(kids).forEach(l => l.sort((a, z) => a._born - z._born || a.id.localeCompare(z.id)));
  const place = {}, w = 2 * Math.PI / Math.max(1, seeds.length);
  let maxd = 1;
  seeds.forEach((s, i) => {
    const start = -Math.PI / 2 + i * w; place[s.id] = [1, start + w / 2];
    let level = [s], depth = 1;
    for (;;) {
      const next = level.flatMap(p => kids[p.id] || []); if (!next.length) break;
      depth++; maxd = Math.max(maxd, depth);
      // More than five in one slice and ring: alternate two radii so the dots do not touch.
      next.forEach((c, j) => { place[c.id] = [depth + (next.length > 5 && j % 2 ? 0.45 : 0), start + w * (0.12 + 0.76 * (j + 0.5) / next.length)]; });
      level = next;
    }
  });
  const rad = depth => maxd === 1 ? R1 : R1 + (depth - 1) * (RMAX - R1) / (maxd - 1 + 0.45);
  const pos = {}; Object.entries(place).forEach(([id, [dp, a]]) => { pos[id] = [CX + rad(dp) * Math.cos(a), CY + rad(dp) * Math.sin(a), a, dp]; });
  return {seeds, pos, maxd, rad, w};
}
function drawMap(d) {
  if (!d.qs.length) { $("content").innerHTML = ""; return showEmpty(true); }
  showEmpty(false);
  const {seeds, pos, maxd, rad, w} = layout(d), out = [];
  for (let k = 1; k <= maxd; k++) out.push(`<circle cx="${CX}" cy="${CY}" r="${rad(k).toFixed(0)}" fill="none" stroke="#F2EDE5" stroke-width="1.5"/>`);
  if (seeds.length > 1) seeds.forEach((s, i) => { const a = -Math.PI / 2 + i * w;
    out.push(`<line x1="${(CX + 55 * Math.cos(a)).toFixed(0)}" y1="${(CY + 55 * Math.sin(a)).toFixed(0)}" x2="${(CX + (RMAX + 14) * Math.cos(a)).toFixed(0)}" y2="${(CY + (RMAX + 14) * Math.sin(a)).toFixed(0)}" stroke="#F2EDE5" stroke-width="1.5"/>`); });
  d.qs.forEach(q => { const [x1, y1, a] = pos[q.id], p = q.parent && pos[q.parent];
    const [x0, y0] = p ? p : [CX + 46 * Math.cos(a), CY + 46 * Math.sin(a)];
    out.push(`<line x1="${x0.toFixed(0)}" y1="${y0.toFixed(0)}" x2="${x1.toFixed(0)}" y2="${y1.toFixed(0)}" stroke="#DDD6CA" stroke-width="1.5"/>`); });
  const center = has(d.brief.short) ? d.brief.short : "";
  out.push(`<circle cx="${CX}" cy="${CY}" r="44" fill="#5C4033"/>` + (center ? wrap(center, 14, 2).map((t, i, l) =>
    `<text x="${CX}" y="${CY + 5 + (i - (l.length - 1) / 2) * 15}" text-anchor="middle" style="fill:#FFFCF7;font-weight:700;font-size:13px">${esc(t)}</text>`).join("") : ""));
  d.qs.forEach(q => {
    const [x, y, a, dp] = pos[q.id], [word, cls] = stateOf(q), r = SIZE[q.prio] || SIZE.medium;  // size is priority; the pop-up and tooltip name it
    // Hollow marks: proposed (sand), not found (terracotta), unclear (terracotta, dashed). Filled: the rest, by colour.
    const hollow = (stroke, dash) => `<circle class="dot" cx="${x.toFixed(0)}" cy="${y.toFixed(0)}" r="${r - 1}" fill="#FFFCF7" stroke="${stroke}" stroke-width="2.5"${dash ? ' stroke-dasharray="3 2"' : ""}/>`;
    const dot = q.view === "proposed" ? hollow("#78736B") : q.view === "not found" ? hollow("#9A3B2A") : q.view === "unclear" ? hollow("#9A3B2A", true)
      : `<circle class="dot filled" cx="${x.toFixed(0)}" cy="${y.toFixed(0)}" r="${r}" fill="${FILL[cls]}"/>`;
    const ring = q.view === "in progress" ? `<circle cx="${x.toFixed(0)}" cy="${y.toFixed(0)}" r="${r + 4}" fill="none" stroke="#E8725C" stroke-dasharray="3 2"/>` : "";
    const mark = q._errors ? `<text class="bang" x="${(x + r + 3).toFixed(0)}" y="${(y - r).toFixed(0)}">!</text>` : "";
    const right = x >= CX, far = dp > 1 ? `<text class="far" x="${(x + (r + 4) * (right ? 1 : -1)).toFixed(0)}" y="${(y + 4).toFixed(0)}" text-anchor="${right ? "start" : "end"}">${esc(q.label)}</text>` : "";
    const who = q.view === "in progress" && has(q.owner) ? `, ${q.owner} on it` : "";
    out.push(`<g class="q${OPEN && OPEN.id === q.id ? " sel" : ""}" data-q="${esc(q.id)}" tabindex="0" role="button" aria-label="${esc(q.label)}: ${word}${q.prio ? ", " + q.prio + " priority" : ""}${esc(who)}${q._errors ? ", " + esc(notValid(q)) : ""}"><title>${esc(q.label)}${q.prio ? ` (${q.prio} priority)` : ""}${q._errors ? ` - ${esc(notValid(q))}` : ""}</title>${ring}${dot}${mark}${far}</g>`);
  });
  seeds.forEach(s => {  // each slice's name, at the edge, outside every dot
    const a = pos[s.id][2], lx = CX + (RMAX + 26) * Math.cos(a), ly = CY + (RMAX + 26) * Math.sin(a);
    const anchor = Math.abs(Math.cos(a)) < 0.06 ? "middle" : Math.cos(a) > 0 ? "start" : "end";
    const lines = wrap(s.label, 22, 2), y0 = ly + 4 - (lines.length - 1) * 7 + (Math.sin(a) > 0.9 ? 8 : Math.sin(a) < -0.9 ? -6 : 0);
    out.push(`<g class="q" data-q="${esc(s.id)}" aria-hidden="true"><text class="rim" text-anchor="${anchor}">${lines.map((t, i) =>
      `<tspan x="${lx.toFixed(0)}" ${i ? 'dy="1.15em"' : `y="${y0.toFixed(0)}"`}>${esc(t)}</tspan>`).join("")}</text></g>`);
  });
  $("content").innerHTML = out.join("");
}
function wrap(text, width, max) {
  const lines = [""];
  for (const word of String(text).split(/\s+/)) {
    if (lines[lines.length - 1] && (lines[lines.length - 1] + " " + word).length > width) {
      if (lines.length === max) { lines[lines.length - 1] += "…"; return lines; }
      lines.push("");
    }
    lines[lines.length - 1] = (lines[lines.length - 1] + " " + word).trim();
  }
  return lines;
}
function showEmpty(on) {
  let e = document.querySelector(".zoomwrap .empty");
  if (on && !e) { e = document.createElement("p"); e.className = "empty"; e.textContent = "No questions on the board yet."; document.querySelector(".zoomwrap").append(e); }
  if (!on && e) e.remove();
}

// ---------- Zoom and pan: the map's viewBox changes, names keep their size on screen ----------
const svg = $("map"); let HOME = [70, 25, 800, 560], vb = HOME.slice();
function setView() {
  // Panning keeps the middle of the view over the questions' dots, so the map cannot be lost off screen.
  const dots = [...document.querySelectorAll("#content circle.dot")].map(c => [+c.getAttribute("cx"), +c.getAttribute("cy")]);
  if (dots.length) {
    const xs = dots.map(d => d[0]), ys = dots.map(d => d[1]);
    const cx = Math.min(Math.max(...xs), Math.max(Math.min(...xs), vb[0] + vb[2] / 2));
    const cy = Math.min(Math.max(...ys), Math.max(Math.min(...ys), vb[1] + vb[3] / 2));
    vb[0] = cx - vb[2] / 2; vb[1] = cy - vb[3] / 2;
  }
  svg.setAttribute("viewBox", vb.join(" ")); svg.classList.toggle("close", HOME[2] / vb[2] > 1.6);
  // Names keep the same size on screen at any zoom and window size: --z is map units per screen pixel.
  const ctm = svg.getScreenCTM(); svg.style.setProperty("--z", ctm && ctm.a ? 1 / ctm.a : vb[2] / HOME[2]);
}
// Fit: the whole map, names included. Names keep their size on screen, so in a small window they take more map units;
// fitting twice settles the view on the drawing as it measures at that size.
let FITTED = true;
function fit() {
  for (let i = 0; i < 2; i++) {
    let b; try { b = $("content").getBBox(); } catch (e) { return; }
    if (!b.width) return;
    const pad = 16, r = svg.getBoundingClientRect(), aspect = r.width / Math.max(1, r.height);
    let w = b.width + 2 * pad, h = b.height + 2 * pad;
    if (w / h < aspect) w = h * aspect; else h = w / aspect;
    HOME = [b.x + b.width / 2 - w / 2, b.y + b.height / 2 - h / 2, w, h]; vb = HOME.slice(); setView();
  }
  FITTED = true;
}
addEventListener("resize", () => { if (FITTED) fit(); else setView(); });
function userMoved() { FITTED = false; if (OPEN && OPEN.kind === "question") closePop(); }
function zoom(f, cx, cy) {
  const nw = Math.min(HOME[2] * 1.5, Math.max(HOME[2] / 6, vb[2] * f)), k = nw / vb[2];
  if (cx == null) { cx = vb[0] + vb[2] / 2; cy = vb[1] + vb[3] / 2; }
  vb = [cx - (cx - vb[0]) * k, cy - (cy - vb[1]) * k, vb[2] * k, vb[3] * k]; setView();
}
function toMap(ev) { const r = svg.getBoundingClientRect(), s = Math.max(vb[2] / r.width, vb[3] / r.height);
  return [vb[0] + (ev.clientX - r.left - (r.width - vb[2] / s) / 2) * s, vb[1] + (ev.clientY - r.top - (r.height - vb[3] / s) / 2) * s]; }
const wrapEl = document.querySelector(".zoomwrap");
wrapEl.addEventListener("wheel", ev => { ev.preventDefault(); userMoved(); const [x, y] = toMap(ev); zoom(ev.deltaY > 0 ? 1.15 : 1 / 1.15, x, y); }, {passive: false});
document.querySelectorAll("[data-z]").forEach(b => b.addEventListener("click", () => {
  userMoved(); if (b.dataset.z === "fit") fit();
  if (b.dataset.z !== "fit") zoom(b.dataset.z === "in" ? 1 / 1.4 : 1.4); }));
// Double-click zooms in on that point; with Shift, out.
wrapEl.addEventListener("dblclick", ev => { if (ev.target.closest(".q")) return; ev.preventDefault(); userMoved(); const [x, y] = toMap(ev); zoom(ev.shiftKey ? 1.6 : 1 / 1.6, x, y); });
let drag = null;
wrapEl.addEventListener("pointerdown", ev => { if (ev.target.closest(".q")) return; userMoved(); drag = [ev.clientX, ev.clientY, vb[0], vb[1]]; wrapEl.classList.add("drag"); });
addEventListener("pointermove", ev => { if (!drag) return; const r = svg.getBoundingClientRect(), s = Math.max(vb[2] / r.width, vb[3] / r.height);
  vb[0] = drag[2] - (ev.clientX - drag[0]) * s; vb[1] = drag[3] - (ev.clientY - drag[1]) * s; setView(); });
addEventListener("pointerup", () => { drag = null; wrapEl.classList.remove("drag"); });

// ---------- The conversation: page.js, shared with the other pages; the board adds the worker's closing messages ----------
// A decision is one of the coordinator's messages, placed where it happened (pageDecisionEvents). One written before this
// change has the old words; it is read as the new ones, and the page counts it.
const OLD_STATUS = {pending: "waiting", default: "defaulted", changed: "answered"};
const decisions = d => (d.decisions || []).map(x => x._old && OLD_STATUS[x.status] ? {...x, status: OLD_STATUS[x.status]} : x);
const clock = at => pageTime(at);
const headHTML = (who, at, extra) => `<div class="head"><span class="who">${who}</span><span class="when">${esc(extra || clock(at))}</span></div>`;
function li(cls, html) { const x = document.createElement("li"); x.className = cls; x.innerHTML = html; return x; }
// A worker's message when it closes a question. The title and the count of new questions are read from the board now,
// so a later rewrite or a question added after the close shows; the answer is the question's gist as the worker wrote it.
const CLOSEWORD = {answered: "Answered", contested: "Contested", "not found": "Not found", unclear: "Unclear"};
function closedItem(c) {
  const e = c.e, q = D.byId[e.question], n = D.qs.filter(x => x.parent === e.question).length;
  const title = q ? `<button type="button" class="qlink" data-open="question:${esc(e.question)}">${esc(q.label)}</button>` : esc(e.question);
  const more = n ? `<p class="added">Raised ${plural(n, "new question")}.</p>` : "";
  return li("msg worker", `${headHTML(esc(e.by || "A worker"), e.at)}
    <p class="what">${esc(CLOSEWORD[e.status] || e.status)}: ${title}</p>${q && has(q.gist) ? md(q.gist) : ""}${more}`);
}
function crumb(e) {
  const x = document.createElement("span");
  if (e.on) { x.className = "crumb"; x.innerHTML = `<span class="path">on</span><span class="el"><button type="button" data-open="${esc(e.on.kind)}:${esc(e.on.id)}">${esc(e.on.title || e.on.id)}</button></span>`; }
  return x;
}
const md = text => pageMarkdown(text).outerHTML;  // Markdown, built as elements: safe to place as HTML
function commentBody(e) { return pageMarkdown(e.text); }
const kinds = {closed: closedItem};
const conv = pageConversation({
  served: !SNAPSHOT, readOnly: !!SNAPSHOT, stream: false, name: "board", agent: "Coordinator", thread: $("thread"),
  agentKinds: ["reply", "closed"], kinds, crumb, commentBody,
  // No working or accept step on the board: the coordinator answers most messages from the board at once, and an
  // answered item is finished.
  steps: ["seen", "done"], labels: {done: "Answered"}, shown: st => st === "working" ? "seen" : st === "accepted" ? "done" : st,
  accept: false, filter: false,
  // A decision waiting for the user comes last, next to the message box, until they answer it; so does a message of
  // theirs that the coordinator asked about.
  waiting: (c, state) => c.kind === "decision" ? decision.waiting(c, state) : ["comment", "note"].includes(c.kind) && state[c.e.id] === "asked",
  afterSend: () => tick(),
});
const uid = p => p + "-" + Date.now().toString(36) + Math.random().toString(36).slice(2, 5);
// The decision question is the shared one: default, deadline, Use the default, Answer.
const decision = pageDecision({conversation: conv, now: () => D.now, md, esc, id: uid});
kinds.decision = decision.item;
// The decisions waiting for the user, by the rule every page shares: asked and not yet answered on the page, or asked
// back about the answer.
const waitingCount = d => pageOpenDecisions(decisions(d), d.conversation).length;

// ---------- The right column ----------
function drawAgents(d) {
  const working = d.qs.filter(q => q.view === "in progress");
  const checkers = {}; d.claims.forEach(c => { if (c.status === "checking") checkers[c.checker] = c; });
  const dry = name => { const l = ((d.logs || {})[name] || {}).searches || []; let n = 0;  // searches in a row that found no new term
    for (let i = l.length - 1; i >= 0 && !(l[i].new_terms || []).length; i--) n++; return n; };
  const heard = who => (d.last_word || {})[who] || null;  // the agent's last word, which the board's server reads
  const rows = working.map(q => { const who = has(q.owner) ? q.owner : "unassigned", n = dry(who);
    return {who, what: q.label, last: heard(who), data: {a: who, for: q.id}, note: n >= 5 ? `${n} searches with nothing new` : ""}; })
    .concat(Object.keys(checkers).sort().map(v => ({who: v, what: "Checking claims", last: heard(v), kind: "verifier", data: {a: v}})));
  setHTML($("agents"), pageAgents(rows, {now: d.now, quietAfter: d.quiet_after, empty: d.brief.status === "stopped" ? "The run has stopped." : "No agent is working right now."}));
}

function setHTML(el, html) { if (el._html !== html) el.innerHTML = el._html = html; }

// ---------- Pop-ups ----------
// pagePopup holds the pop-up's element, focus, Tab and Escape; the board says what it shows and where it goes.
let PENDING = null;  // what openPop asks for, taken by fill once the pop-up is open
const pop = pagePopup({
  fill: () => { if (PENDING) { OPEN = PENDING; PENDING = null; } fillPop(); },
  place: anchor => placePop(anchor),
  opened: el => {
    document.querySelectorAll(".map .q").forEach(g => g.classList.toggle("sel", OPEN.kind === "question" && g.dataset.q === OPEN.id));
    el.addEventListener("toggle", () => placePop(OPEN && OPEN.anchor), true);
  },
  closed: () => { OPEN = null; document.querySelectorAll(".map .sel").forEach(g => g.classList.remove("sel")); },
});
const openPop = (kind, id, anchor) => { PENDING = {kind, id, anchor}; pop.open(anchor); };
const closePop = () => pop.close();
function placePop(anchor) {
  const el = $("pop"); if (!el || !anchor) return;
  const r = anchor.getBoundingClientRect(), w = el.offsetWidth, h = el.offsetHeight;
  let left = anchor.closest("aside") ? r.left - w - 12 : r.left + r.width / 2 - w / 2, top = anchor.closest("aside") ? r.top : r.bottom + 8;
  el.style.maxHeight = (innerHeight - 20) + "px";
  left = Math.max(10, Math.min(left, innerWidth - w - 10)); if (top + h > innerHeight - 10) top = Math.max(10, (anchor.closest("aside") ? innerHeight : r.top - 8) - h - (anchor.closest("aside") ? 10 : 0));
  el.style.left = left + "px"; el.style.top = top + "px";
}
function fillPop() {
  const el = $("pop"); if (!el || !D) return;
  const ta = el.querySelector("textarea"), typed = ta ? ta.value : "", focused = ta && document.activeElement === ta;
  const {kind, id} = OPEN;
  let html, match;
  if (kind === "question") {
    const q = D.byId[id]; if (!q) return closePop();
    const [word, cls] = stateOf(q), n = q.claimsList.length, ver = q.claimsList.filter(c => c.status === "verified").length;
    const failed = q.claimsList.filter(c => c.status === "unverified").length;
    const parent = q.parent ? D.byId[q.parent] : null, srcs = new Set(q.claimsList.map(c => c.source)).size;
    const gist = has(q.gist) ? q.gist : has(q.summary) ? q.summary : "";
    const checked = !n ? "" : ver === n ? ", all verified" : ver || failed ? `, ${ver} verified${failed ? `, ${failed} failed` : ""}` : ", none checked yet";
    // The header says what it is, its title and the full question; the answer, the claims and the conversation follow.
    html = `<div class="hd"><p class="kind">Question, <span class="chip ${cls}">${word}</span>${q.view === "in progress" && has(q.owner) ? " by " + esc(q.owner) : ""}${q.prio ? `, ${q.prio} priority` : ""}</p>
      <h3 dir="auto">${esc(q.label)}</h3>${has(q.question) ? `<p class="full" dir="auto">${esc(q.question)}</p>` : ""}${q._errors ? `<p>${invalidHTML(q)}</p>` : ""}</div>
      <div class="bd">${has(q.summary) ? `<p dir="auto">${esc(q.summary)}</p>` : gist ? `<p dir="auto">${esc(gist)}</p>` : ""}
      ${parent ? `<p class="muted" dir="auto">Raised by: ${esc(parent.label)}</p>` : ""}
      <div class="sec"><h4 class="section-h">${n ? `${plural(n, "claim")} from ${plural(srcs, "source")}${checked}` : "No claims yet"}</h4>
      ${n ? `<ul class="claims">${q.claimsList.map(c => { const s = (D.sources.find(x => x.id === c.source) || {});
        const v = c.status, mark = v === "verified" ? "✓" : v === "unverified" ? "✗" : "○";
        const cited = has(s.date) || s.category ? ` (${[s.date, s.category].filter(has).map(esc).join(", ")})` : "";
        return `<li dir="auto"><span aria-label="${v === "verified" ? "verified" : v === "unverified" ? "failed" : "not checked yet"}">${mark}</span> ${esc(c.claim)} <span class="muted">${esc(s.author || s.publisher || c.source)}${cited}</span> ${invalidHTML(c)}${s._errors ? " " + invalidHTML({_errors: ["source " + s.id + ": " + s._errors[0]]}) : ""}</li>`; }).join("")}</ul>` : ""}</div>
      <div class="sec"><h4 class="section-h">Conversation</h4><ul class="thread"></ul>`;
    match = e => e.on && e.on.kind === "question" && e.on.id === id;
  } else if (D.claims.some(c => c.checker === id)) {
    const mine = D.claims.filter(c => c.checker === id), v = x => x.status;
    const holding = mine.filter(c => v(c) === "checking"), failed = mine.filter(c => v(c) === "unverified");
    html = `<div class="hd"><p class="kind">Verifier, <span class="chip working">checking</span></p><h3>${esc(id)}</h3></div>
      <div class="bd"><p>Checked ${plural(mine.length - holding.length, "claim")}: ${mine.filter(c => v(c) === "verified").length} verified, ${failed.length} failed.</p>
      ${holding.length ? `<div class="sec"><h4 class="section-h">Checking now</h4><ul>${holding.map(c => `<li dir="auto">${esc(c.claim)}</li>`).join("")}</ul></div>` : ""}
      ${failed.length ? `<div class="sec"><h4 class="section-h">Failed</h4><ul>${failed.map(c => `<li dir="auto">${esc(c.claim)} <span class="muted">${esc(c.reason)}</span></li>`).join("")}</ul></div>` : ""}
      <div class="sec"><h4 class="section-h">Conversation</h4><ul class="thread"></ul>`;
    match = e => e.on && e.on.kind === "agent" && e.on.id === id;
  } else {
    const log = (D.logs || {})[id] || {}, q = D.byId[(D.qs.find(x => x.view === "in progress" && x.owner === id) || {}).id];
    // Repeated searches collapse into one line with a count, so an agent going in circles shows at a glance.
    const counts = new Map();
    (log.searches || []).slice().reverse().forEach(r => counts.set(r.query, (counts.get(r.query) || 0) + 1));
    const s = [...counts].slice(0, 5).map(([q, n]) => n > 1 ? `${q} (${n} times)` : q);
    html = `<div class="hd"><p class="kind">Agent, <span class="chip working">working</span></p><h3>${esc(id)}${q ? " on " + esc(q.label) : ""}</h3></div>
      <div class="bd"><div class="sec"><h4 class="section-h">Latest searches</h4>
      <ul>${s.map(x => `<li dir="auto">${esc(x)}</li>`).join("") || "<li>None logged yet.</li>"}</ul></div>
      <div class="sec"><h4 class="section-h">Conversation</h4><ul class="thread"></ul>`;
    match = e => e.on && e.on.kind === "agent" && e.on.id === id;
  }
  const label = kind === "question" ? "Ask or comment on this question" : `Message about ${id}'s work`;
  html = `<button type="button" class="x" aria-label="Close">×</button>` + html + (SNAPSHOT ? "" :
    `<form class="ask popask"><textarea aria-label="${esc(label)}" placeholder="${esc(label)}"></textarea><button type="submit" class="btn">Send</button></form>`) + "</div></div>";
  const mine = conv.nodes(match), key = html + mine.map(n => n.outerHTML).join("");
  if (el._html === key) return;
  el.innerHTML = html; el._html = key;
  el.querySelector("ul.thread").append(...mine);
  const h3 = el.querySelector("h3"); if (h3) { h3.id = "pop-title"; h3.setAttribute("tabindex", "-1"); }
  const t = el.querySelector("textarea"); if (t) { t.value = typed; if (focused) t.focus({preventScroll: true}); }
  placePop(OPEN && OPEN.anchor);
}

// ---------- Sending to the coordinator: the message box and replies are page.js's; the pop-ups and decisions are the board's ----------
document.addEventListener("submit", ev => {
  ev.preventDefault();
  const f = ev.target; if (!f.classList.contains("popask")) return;
  const ta = f.querySelector("textarea"), text = ta.value.trim(); if (!text) return ta.focus();
  const q = OPEN.kind === "question" ? D.byId[OPEN.id] : null;  // a failed send keeps the box and its text
  conv.send("comment", {id: uid("c"), on: {kind: OPEN.kind, id: OPEN.id, title: q ? q.label : OPEN.id}, text}, "Comment", () => { ta.value = ""; fillPop(); });
});
document.addEventListener("click", ev => {
  const t = ev.target;
  if (t.closest("#goal")) { $("goal").classList.toggle("open"); return; }
  if (t.closest("#to-waiting")) { const q = document.querySelector("#thread .open-q"); if (!q) return;
    q.scrollIntoView({block: "start"}); const b = q.querySelector(".change"); if (b) b.focus({preventScroll: true}); return; }
  if (pop.click(t)) return;
  const g = t.closest(".map .q"); if (g) return openPop("question", g.dataset.q, g);
  const a = t.closest("[data-a]"); if (a) return openPop("agent", a.dataset.a, a);
  const o = t.closest("[data-open]"); if (o) { const [kind, id] = o.dataset.open.split(/:(.*)/s); return openPop(kind, id, o); }
  if ($("pop") && !t.closest("form, .why")) closePop();
});
document.addEventListener("keydown", ev => {
  if (pop.key(ev)) return;
  if ((ev.key === "Enter" || ev.key === " ") && ev.target.matches && ev.target.matches(".map .q")) { ev.preventDefault(); openPop("question", ev.target.dataset.q, ev.target); }
  if (ev.key === "Enter" && !ev.shiftKey && ev.target.matches && ev.target.matches("form.popask textarea")) { ev.preventDefault(); ev.target.form.requestSubmit(); }
});

// ---------- Render ----------
function render(d) {
  D = prepare(d);
  const b = d.brief || {}, qs = D.qs, now = d.now;
  $("title").textContent = has(b.title) ? b.title : b.topic || "Research board";
  $("title").title = b.topic || ""; document.title = `${$("title").textContent} · Research board`;
  $("briefbad").textContent = notValid(b); $("briefbad").hidden = !notValid(b);
  $("goal").textContent = has(b.goal) ? b.goal : ""; $("goal").title = b.goal || ""; $("goal").hidden = !has(b.goal);
  const start = Math.min(now, ...[...d.questions, ...d.claims, ...d.sources].map(e => e._born));
  const answered = qs.filter(q => CLOSED.has(q.view)).length, workers = qs.filter(q => q.view === "in progress").length;
  const left = qs.filter(q => ["open", "in progress", "proposed"].includes(q.view)).length;
  const rate = answered / Math.max(1, now - start), eta = answered >= 3 && left ? ` ${left / rate < 90 ? "Under 2 min" : "About " + Math.round(left / rate / 60) + " min"} left at this pace.` : "";
  const stat = (n, label, cls) => `<span class="stat${cls ? " " + cls : ""}"><b>${n}</b>${label}</span>`;
  const leftText = left / rate < 90 ? "<2 min" : `~${Math.round(left / rate / 60)} min`;
  const waitingN = waitingCount(d);
  const phase = CLOSED_PAGE ? stat("Closed", `since ${new Date(now * 1000).toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"})}`)
    : b.status === "stopped" ? stat("Stopped", `after ${mins(now - start)}`, "done")
    : b.status === "checking" ? stat("Checking", "last claims") : stat(mins(now - start).replace(" min", "m").replace("under 2m", "<2m"), "running");
  const live = !CLOSED_PAGE && (b.status === "running" || !b.status);
  setHTML($("status"), `<span class="stat"><b>${answered}<span class="of"> / ${qs.length}</span></b>questions closed
      <span class="meter" aria-hidden="true"><i style="width:${qs.length ? (100 * answered / qs.length).toFixed(0) : 0}%"></i></span></span>`
    + (live ? stat(workers, workers === 1 ? "worker on questions" : "workers on questions") + (answered >= 3 && left ? stat(leftText, "left at this pace") : "") : "")
    + (waitingN && !CLOSED_PAGE ? `<button type="button" class="stat" id="to-waiting"><b>${waitingN}</b>${waitingN === 1 ? "decision waiting for you" : "decisions waiting for you"}</button>` : "") + phase);
  const key = JSON.stringify(qs.map(q => [q.id, q.parent, q.view, q.label, q.searches, q.owner, q._errors && q._errors[0], OPEN && OPEN.id === q.id]).concat([b.short]));
  if (key !== LAYOUT) { LAYOUT = key; drawMap(D); if (FITTED) fit(); }
  const replies = (d.conversation || []).filter(e => e.type === "reply");
  if (REPLIES >= 0 && replies.length > REPLIES) conv.flash("Coordinator: " + pageMarkdownText(replies[replies.length - 1].text).slice(0, 120), "ok");
  REPLIES = replies.length;
  drawAgents(D);
  // Redraw when the log changes, when a question a worker's message names changes, and every half minute while a
  // decision counts down to its default.
  conv.setLog(pageDecisionEvents(decisions(D), D.conversation), [waitingN ? Math.round(now / 30) : 0, D.qs.map(q => [q.id, q.label, q.parent])]);
  if (OPEN) fillPop();
}

// The records the board could not show are listed by page.js's band; the rest of the board is drawn anyway, and the page
// is reachable, so this band and the closed notice never go together.
// invalid:begin
// A record the board still shows although it broke the schema says so, in the error colour, with its first message.
const notValid = r => r && r._errors && r._errors.length ? `not valid: ${r._errors[0]}` : "";
const invalidHTML = r => notValid(r) ? `<span class="invalid">${esc(notValid(r))}</span>` : "";
// invalid:end
// ---------- Polling ----------
let fails = 0;
function tick() {
  return pageFetch("/data", {cache: "no-store"}).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(d => { fails = 0; CLOSED_PAGE = false; pageShowErrors($("errors"), d.errors, ERRORS_NOTE); render(d); },
      e => { if (e && e.stale) return; if (++fails >= 2 && !CLOSED_PAGE) { CLOSED_PAGE = true; $("errors").hidden = true; if (D) render(D); } });
}
if (SNAPSHOT) { pageShowErrors($("errors"), SNAPSHOT.errors, ERRORS_NOTE); render(SNAPSHOT); document.querySelectorAll("#noteform").forEach(f => f.remove()); }
else { conv.start(); tick(); setInterval(tick, 2000); }
setView();
