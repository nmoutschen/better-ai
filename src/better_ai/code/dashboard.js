const $ = id => document.getElementById(id);
const esc = pageEscape;
const has = v => v && v !== "none";
const STATIC = !!document.getElementById("page-data");  // a page written by `render`: its data is in it, and nothing is served
let D = null, REPLIES = -1, RANGE = "2h";

// status:begin
// A task's mode as a tag, one colour per mode.
const MODES = {feature: "feature", "bug fix": "bugfix", bugfix: "bugfix", refactor: "refactor", tests: "tests"};
const modeTag = m => typeof m === "string" && m.trim() && m.trim() !== "none" ? `<span class="mode m-${MODES[m.trim().toLowerCase()] || "other"}">${esc(m)}</span>` : "";
// A task's status as tasks.jsonl writes it (modes/coordinate.md), as an icon key and a word. A blocked task says what it
// waits on from its reason and waits_on: a task of the list, the user, or the repair limit; anything else shows as written.
// An unknown status is an error the coordinator made: it shows in red as written, never as another stage.
const TASK_STATUS = {todo: ["todo", "to do"], building: ["building", "building"], built: ["built", "built"],
  verifying: ["verifying", "verifying"], "changes needed": ["changes", "changes needed"], verified: ["verified", "verified"],
  merged: ["merged", "merged"], done: ["done", "done"]};
const DONE = new Set(["done", "merged"]);
const isDone = t => !(t._errors && t._errors.length) && DONE.has(String(t.status || "").trim().toLowerCase());
function taskStatus(t, tasks) {
  const raw = String(t.status || "").trim(), s = raw.toLowerCase();
  // A record that did not validate says so, in the error style, with its first message; an unknown status still shows as written.
  if (t._errors && t._errors.length && (TASK_STATUS[s] || s === "blocked")) return {key: "other", word: `not valid: ${t._errors[0]}`};
  if (s === "blocked") {
    const reason = String(t.reason || "").trim(), r = reason.toLowerCase(), on = String(t.waits_on || "").trim();
    const word = !r ? "blocked" : r === "user" ? "waiting on you" : r === "repair limit" ? "repair limit"
      : r === "task" ? (tasks.some(x => x.id === on) ? `waiting on ${on}` : `blocked: ${on}`) : `blocked: ${reason}`;
    return {key: "blocked", word};
  }
  const [key, word] = TASK_STATUS[s] || ["other", raw ? `not a status: ${raw}` : "no status"];
  return {key, word};
}
// status:end

// timeline:begin
// The task timeline (design: .design/code-better-board/design.md). Every value comes from the records the server sends:
// tasks, agents (card and log, each line with its `at`), rounds and fixes (rounds.jsonl), and each branch's git activity.
// A record can hold anything, so every reader checks its type and every text is escaped. Times are epoch seconds.
const BUCKET = 300;
const list = v => Array.isArray(v) ? v : [];
const str = v => typeof v === "string" ? v : "";
const sec = at => { const n = typeof at === "string" ? Date.parse(at) : NaN; return Number.isFinite(n) ? n / 1000 : null; };
const hm = s => { const d = new Date(s * 1000); return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`; };
const mins = s => Math.max(0, Math.floor(s / 60));
const ICONS = {
  todo: '<svg viewBox="0 0 14 14" aria-hidden="true"><circle cx="7" cy="7" r="5" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>',
  building: '<svg viewBox="0 0 14 14" aria-hidden="true"><path d="M3 2l9 5-9 5z" fill="currentColor"/></svg>',
  built: '<svg viewBox="0 0 14 14" aria-hidden="true"><circle cx="7" cy="7" r="5.5" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M4.5 7.2l1.8 1.8 3.3-3.8" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>',
  verifying: '<svg viewBox="0 0 14 14" aria-hidden="true"><circle cx="6" cy="6" r="3.6" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M8.7 8.7L12.5 12.5" stroke="currentColor" stroke-width="2"/></svg>',
  changes: '<svg viewBox="0 0 14 14" aria-hidden="true"><path d="M11.5 3v4.5H3.5" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M6.5 4.3L3.2 7.5l3.3 3.2" fill="none" stroke="currentColor" stroke-width="1.8"/></svg>',
  verified: '<svg viewBox="0 0 14 14" aria-hidden="true"><path d="M2.5 7.5l3 3 6-7" fill="none" stroke="currentColor" stroke-width="2"/></svg>',
  merged: '<svg viewBox="0 0 14 14" aria-hidden="true"><circle cx="4" cy="2.8" r="1.7" fill="currentColor"/><circle cx="4" cy="11.2" r="1.7" fill="currentColor"/><circle cx="10.5" cy="7" r="1.7" fill="currentColor"/><path d="M4 4.5V9.5M4 4.5C4 7 6.5 7 8.8 7" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>',
  blocked: '<svg viewBox="0 0 14 14" aria-hidden="true"><circle cx="7" cy="7" r="5.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M3 11L11 3" stroke="currentColor" stroke-width="2"/></svg>',
  quiet: '<svg viewBox="0 0 14 14" aria-hidden="true"><circle cx="7" cy="7" r="5.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M7 4v3.5l2.5 1.5" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>',
  other: '<svg viewBox="0 0 14 14" aria-hidden="true"><circle cx="7" cy="7" r="5.5" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M5.3 5.6a1.8 1.8 0 1 1 2.5 1.6c-.5.3-.8.6-.8 1.2v.5" fill="none" stroke="currentColor" stroke-width="1.4"/><circle cx="7" cy="10.4" r=".85" fill="currentColor"/></svg>',
};
ICONS.done = ICONS.merged;
const tasksOf = d => list(d && d.tasks).filter(t => t && typeof t === "object");
const agentsOf = (t, d) => list(d && d.agents).filter(a => a && typeof a === "object" && a.task === t.id && ["builder", "verifier"].includes(a.role));
const mergedAt = t => isDone(t) ? sec(t.status_at) : null;
const gitOf = (branch, d) => { const g = d && d.git && typeof d.git === "object" ? d.git[branch] : null; return g && typeof g === "object" ? g : null; };

// An agent's log cut into its rounds: a round ends at a hand-back, and any line after one starts the next round, as
// when the coordinator resumed the same agent instead of starting a new one.
function roundsOfAgent(a) {
  const out = [];
  let cur = [];
  for (const l of list(a.lines).filter(l => l && typeof l === "object")) {
    cur.push(l);
    if (l.type === "handed_back") { out.push(cur); cur = []; }
  }
  if (cur.length || !out.length) out.push(cur);
  return out;
}
// The task's phases in time order: a build or verify per round of each agent card, from the `at` of its first and
// hand-back log lines, and a coordinator fix per fix record, which lasts until the next phase starts, the merge, or now.
function phasesOf(t, d) {
  const now = d.now, out = [];
  for (const a of agentsOf(t, d)) roundsOfAgent(a).forEach((lines, i) => {
    // The first round starts when the agent started, which the lines the page holds may no longer show.
    const start = i === 0 ? sec(a.started) ?? sec((lines[0] || {}).at) ?? sec(a.at) : lines.map(l => sec(l.at)).find(x => x !== null) ?? null;
    if (start === null) return;
    const back = lines.find(l => l.type === "handed_back");
    out.push({kind: a.role === "verifier" ? "v" : "b", agent: str(a.name), branch: str(a.branch), start,
      end: back ? sec(back.at) : null, result: back ? str(back.result) : "", lines});
  });
  for (const f of list(d.fixes)) {
    if (!f || f.task !== t.id || sec(f.at) === null) continue;
    out.push({kind: "f", start: sec(f.at), end: null, text: str(f.text), lines: []});
  }
  out.sort((x, y) => x.start - y.start);
  // A verify's round is the one its round record names, if the coordinator added one for its verifier; otherwise the
  // count of verifies so far. A build's round follows the last verify before it.
  let round = 0;
  out.forEach((p, i) => {
    const next = i + 1 < out.length ? out[i + 1].start : null;
    if (p.kind === "v") { const r = roundRecord(t, p, d, false); round = r && Number.isInteger(r.round) ? r.round : round + 1; p.round = round; }
    else p.round = round + 1;
    // An agent that never handed back, as one stopped or lost, ends where the next phase starts.
    if (p.end === null && p.kind !== "f" && next !== null) p.end = next;
    // A fix lasts until the next phase or the merge, at least one bucket when it comes after both, as a fix after the merge does.
    if (p.kind === "f") { const stop = next ?? mergedAt(t); p.end = stop !== null && stop > p.start ? stop : Math.min(now, p.start + BUCKET); }
  });
  return out;
}
// The lines changed on the phase's branch in each 5 minutes of the phase, cut at its start and end: [from, to, lines].
function bucketsOf(p, d) {
  const g = gitOf(p.branch, d);
  if (!g) return [];
  const counts = new Map(list(g.buckets).filter(b => Array.isArray(b)).map(b => [Number(b[0]), Number(b[1]) || 0]));
  const end = p.end ?? d.now, out = [];
  for (let b = Math.floor(p.start / BUCKET) * BUCKET; b < end; b += BUCKET)
    out.push([Math.max(b, p.start), Math.min(b + BUCKET, end), counts.get(b) || 0]);
  return out;
}
const openBuild = (t, d) => { const p = phasesOf(t, d).at(-1); return p && p.kind === "b" && p.end === null ? p : null; };
// When an open build was last heard from: its start, its agent's last word (the server's, by the rule every page shares)
// or its branch's last file change, whichever is latest. Null when no build is open.
function heardOf(t, d) {
  const p = openBuild(t, d);
  if (!p || isDone(t)) return null;
  const a = agentsOf(t, d).find(x => x.name === p.agent), g = gitOf(p.branch, d);
  return Math.max(p.start, (a && sec(a.last_word)) ?? p.start, g && Number(g.last) > p.start ? Number(g.last) : p.start);
}
// What a task row says of its state: a class for its colour, an icon and a word.
function statusOf(t, d) {
  const {key, word} = taskStatus(t, tasksOf(d));
  if (key === "other") return {cls: "warn", icon: ICONS.other, word};
  if (isDone(t)) { const at = mergedAt(t); return {cls: "merged", icon: ICONS.merged, word: at ? `${word} ${hm(at)}` : word}; }
  if (key === "blocked") {
    const r = String(t.reason || "").trim().toLowerCase();
    if (r === "user") return {cls: "you", icon: '<span class="q" aria-hidden="true">?</span>', word};
    return {cls: r === "repair limit" ? "warn" : "", icon: ICONS.blocked, word};
  }
  const heard = heardOf(t, d);
  // Quiet from the page's threshold on: `quiet_after`, the server's, the same for every page.
  if (heard !== null && d.quiet_after > 0 && d.now - heard >= d.quiet_after)
    return {cls: "warn", icon: ICONS.quiet, word: `${word}, quiet ${mins(d.now - heard)} min`};
  return {cls: "", icon: ICONS[key] || ICONS.other, word};
}
const groupOf = (t, d) => isDone(t) ? "merged" : agentsOf(t, d).length ? "working" : "pending";
const roundOf = (t, d) => { const p = phasesOf(t, d).at(-1); return p ? p.round : 1; };
const failures = (t, d) => phasesOf(t, d).filter(p => p.kind === "v" && p.result === "fails" && p.end !== null);
// The round record of a verify: the first naming its verifier that was added after the verify started, so a resumed
// verifier's later round never takes its earlier round's record; for a failed verify with none, the one of its round
// number that names no verifier of this task, so a verify never shows another verifier's findings.
function roundRecord(t, p, d, byNumber = true) {
  const mine = list(d.rounds).filter(x => x && typeof x === "object" && x.task === t.id);
  const own = mine.find(x => p.agent && x.verifier === p.agent && (sec(x.at) ?? Infinity) >= p.start);
  if (own || !byNumber || p.result !== "fails") return own;
  const named = new Set(agentsOf(t, d).filter(a => a.role === "verifier").map(a => a.name));
  return mine.find(x => x.round === p.round && !named.has(x.verifier));
}
const findingsOf = (t, p, d) => { const r = roundRecord(t, p, d);
  return list(r && r.findings).filter(f => f && typeof f.text === "string"); };
function lastChange(t, d) {
  const branches = new Set(agentsOf(t, d).map(a => str(a.branch)));
  const times = [...branches].map(b => gitOf(b, d)).filter(Boolean).map(g => Number(g.last)).filter(Number.isFinite);
  return times.length ? Math.max(...times) : null;
}

// The range of the axis: it ends now and spans exactly the chosen hours, blank before the run's start when the run is
// shorter; All spans the whole run, at least ten minutes.
const HOURS = {"1h": 1, "2h": 2, "6h": 6};
function rangeOf(d, range) {
  const now = d.now;
  if (range in HOURS) return [now - HOURS[range] * 3600, now];
  let t0 = sec(d.start) ?? now;
  if (now - t0 < 600) t0 = now - 600;
  return [t0, now];
}
const runningWord = d => { const s = d.now - (sec(d.start) ?? d.now);
  return s < 120 ? "<2m" : s < 3600 ? `${mins(s)}m` : `${Math.floor(s / 3600)}h${String(mins(s % 3600)).padStart(2, "0")}m`; };
function peakOf(d, t0, t1) {
  let peak = 1;
  for (const t of tasksOf(d)) for (const p of phasesOf(t, d)) if (p.kind === "b")
    for (const [a, b, n] of bucketsOf(p, d)) if (b > t0 && a < t1) peak = Math.max(peak, n);
  return peak;
}

// The lane as one SVG in minutes from t0, so neighbouring pieces share exact edges. A build is one stepped shape whose
// height follows the lines changed (4 px for any change, up to 16 px at the peak); a stretch with no change is one
// dotted line; a verify is a terracotta-dark bar, a fix an umber bar.
const BASE = 24;
function laneSVG(t, d, t0, t1, peak) {
  peak = peak || peakOf(d, t0, t1);
  const x = s => ((Math.min(Math.max(s, t0), t1) - t0) / 60).toFixed(3), out = [];
  const bar = (a, b, fill, h) => b > t0 && a < t1 ? out.push(`<rect x="${x(a)}" y="${BASE - h}" width="${Math.max(0, x(b) - x(a)).toFixed(3)}" height="${h}" fill="${fill}"/>`) : 0;
  const dots = (a, b) => b > t0 && a < t1 ? out.push(`<line x1="${x(a)}" x2="${x(b)}" y1="${BASE - 1.5}" y2="${BASE - 1.5}" stroke="var(--umber)" stroke-width="3" stroke-dasharray="3 3" vector-effect="non-scaling-stroke"/>`) : 0;
  for (const p of phasesOf(t, d)) {
    const end = p.end ?? d.now;
    if (p.kind === "v") { bar(p.start, end, "var(--terracotta-dark)", 6); continue; }
    if (p.kind === "f") { bar(p.start, end, "var(--umber)", 6); continue; }
    const buckets = bucketsOf(p, d);
    if (!buckets.length) { bar(p.start, end, "var(--sand)", 4); continue; }
    let run = [], quiet = null;
    const flush = () => {
      if (!run.length) return;
      let path = `M${x(run[0][0])},${BASE}`;
      for (const [a, b, n] of run) { const h = (4 + 12 * Math.min(n, peak) / peak).toFixed(2); path += ` L${x(a)},${BASE - h} L${x(b)},${BASE - h}`; }
      out.push(`<path d="${path} L${x(run.at(-1)[1])},${BASE} Z" fill="var(--sand)"/>`); run = [];
    };
    for (const bk of buckets) {
      if (bk[2] > 0) { if (quiet) { dots(...quiet); quiet = null; } run.push(bk); continue; }
      flush(); quiet = quiet ? [quiet[0], bk[1]] : [bk[0], bk[1]];
    }
    flush(); if (quiet) dots(...quiet);
  }
  return `<svg class="bars" viewBox="0 0 ${((t1 - t0) / 60).toFixed(3)} 28" preserveAspectRatio="none" aria-hidden="true">${out.join("")}</svg>`;
}
// The events of a lane: a failed verify as a red rule with "✕ R<n>", whose blocking findings show on hover and focus;
// a merge as a moss rule. Near the end of the axis the word goes left of its rule.
function marksHTML(t, d, t0, t1) {
  const pct = s => (100 * (s - t0) / (t1 - t0)), out = [];
  const side = s => pct(s) > 93 ? " flip" : "";
  for (const p of failures(t, d)) {
    if (p.end < t0 || p.end > t1) continue;
    const blocking = findingsOf(t, p, d).filter(f => f.blocking === true).map(f => f.text);
    const label = `Round ${p.round} verify failed at ${hm(p.end)}${blocking.length ? ": " + blocking.join("; ") : ""}`;
    // The findings open toward the middle of the lane, so they stay inside the view.
    out.push(`<button type="button" class="ev fail${side(p.end)}${pct(p.end) > 50 ? " tipleft" : ""}" style="left:${pct(p.end).toFixed(2)}%" aria-label="${esc(label)}">`
      + `<b aria-hidden="true">✕ R${p.round}</b>${blocking.length ? `<span class="tip" role="tooltip">${blocking.map(esc).join("<br>")}</span>` : ""}</button>`);
  }
  const m = mergedAt(t);
  if (m !== null && m >= t0 && m <= t1) out.push(`<span class="ev done${side(m)}" style="left:${pct(m).toFixed(2)}%"><b>MERGED</b></span>`);
  return out.join("");
}
// The row's name for assistive technology, from the same records as the lane.
function rowName(t, d) {
  const s = statusOf(t, d), round = roundOf(t, d), last = lastChange(t, d);
  return [`${str(t.id)} ${str(t.task)}`, str(t.mode), s.word, round > 1 && !isDone(t) ? `round ${round}` : "",
    ...failures(t, d).map(p => `round ${p.round} verify failed at ${hm(p.end)}`),
    last !== null && !isDone(t) ? `last file change ${mins(d.now - last)} min ago` : ""].filter(Boolean).join(", ");
}
const stepWords = l => l.type === "step" ? str(l.text) : l.type === "handed_back" ? `handed back: ${[l.result, l.text].map(str).filter(Boolean).join(", ")}`
  : l.type === "start" ? str(l.text) || "start" : `${l.type}: ${str(l.text)}`;
const reqsOf = (t, d) => list(t.requirements).map(id => [String(id), (d.requirements || {})[id]]);
// The task's detail, inside the shared pop-up: what it must make true, its branch, each phase newest first, and the
// conversation about it.
function popupHTML(t, d) {
  const s = statusOf(t, d), round = roundOf(t, d), last = lastChange(t, d);
  const reqs = reqsOf(t, d).map(([id, text]) => `<li dir="auto"><b>${esc(id)}</b><span>${typeof text === "string" ? esc(text) : '<span class="missing">not in the spec</span>'}</span></li>`).join("");
  const branch = [...new Set(agentsOf(t, d).map(a => str(a.branch)).filter(Boolean))].map(b => {
    const g = gitOf(b, d);
    return g ? `<p class="muted">Branch <code>${esc(b)}</code>: +${Number(g.added) || 0} −${Number(g.removed) || 0} in ${Number(g.files) || 0} files, ${Number(g.commits) || 0} commits${last !== null ? `, last file change ${mins(d.now - last)} min ago` : ""}.</p>` : `<p class="muted">No git data for <code>${esc(b)}</code>.</p>`;
  }).join("");
  const phases = phasesOf(t, d).reverse().map(p => {
    const to = p.end === null ? "now" : hm(p.end);
    if (p.kind === "f") return `<div class="sec rnd f"><h4 class="section-h">Fix</h4><p dir="auto">Coordinator, ${hm(p.start)} to ${to}: ${esc(p.text)}</p></div>`;
    const head = p.kind === "b" ? `Build, round ${p.round}` : `Verify, round ${p.round}${p.result === "fails" ? ": failed" : p.result === "passes" ? ": passed" : ""}`;
    const lines = bucketsOf(p, d).reduce((n, b) => n + b[2], 0);
    const steps = p.lines.filter(l => sec(l.at) !== null).map(l => `<li dir="auto"><time>${hm(sec(l.at))}</time>${esc(stepWords(l))}</li>`).join("");
    const found = p.kind === "v" ? findingsOf(t, p, d) : [];
    const blocking = found.filter(f => f.blocking === true), other = found.filter(f => f.blocking !== true);
    return `<div class="sec rnd ${p.kind}${p.result === "fails" ? " fail" : ""}"><h4 class="section-h">${head}</h4>`
      + `<p dir="auto">${esc(p.agent)}${p.branch ? ` on <code>${esc(p.branch)}</code>` : ""}, ${hm(p.start)} to ${to}.</p>`
      + (p.kind === "b" && gitOf(p.branch, d) ? `<p class="muted">${lines} lines changed.</p>` : "")
      + (steps ? `<ol class="tsteps">${steps}</ol>` : "")
      + (blocking.length ? `<p>Blocking:</p><ul>${blocking.map(f => `<li dir="auto">${esc(f.text)}</li>`).join("")}</ul>` : "")
      + (other.length ? `<p class="muted">Not blocking: ${other.map(f => esc(f.text)).join("; ")}</p>` : "") + "</div>";
  }).join("");
  return `<div class="hd"><p class="kind">${modeTag(t.mode)} ${esc(t.id)}, ${esc(s.word)}${round > 1 && !isDone(t) ? `, round ${round}` : ""}</p>`
    + `<h3 dir="auto">${esc(t.task)}</h3></div><div class="bd">`
    + `<div class="sec"><h4 class="section-h">Must make true</h4>${reqs ? `<ul class="req-list">${reqs}</ul>` : '<p class="muted">No requirement named.</p>'}`
    + `${typeof t.check === "string" && t.check.trim() && t.check.trim() !== "none" ? `<p class="check">Check: <code>${esc(t.check)}</code></p>` : ""}${branch}</div>`
    + phases + `<div class="sec"><h4 class="section-h">Conversation</h4><ul class="thread"></ul>`
    + `<form class="ask popask"><textarea aria-label="Message about ${esc(t.id)}" placeholder="Message about ${esc(t.id)}"></textarea><button type="submit" class="btn">Send</button></form></div></div>`;
}
// The axis of a table: a label and a thin line at each step of the range, and the now line.
function axisHTML(t0, t1) {
  const span = t1 - t0, step = span <= 3600 ? 900 : span <= 7200 ? 1800 : span <= 6 * 3600 ? 3600 : span <= 12 * 3600 ? 7200 : 4 * 3600;
  const ticks = [];
  for (let s = Math.ceil(t0 / step) * step; s <= t1; s += step) ticks.push(s);
  const pct = s => (100 * (s - t0) / span).toFixed(2);
  return {labels: ticks.map(s => `<span style="left:${pct(s)}%">${hm(s)}</span>`).join(""),
    lines: ticks.map(s => `<i class="grid" style="left:${pct(s)}%"></i>`).join("") + '<i class="now"></i>'};
}
// The three tables, Working, Pending and Merged, each with its own axis on the same range; tasks keep tasks.jsonl order.
function tablesHTML(d, range) {
  const tasks = tasksOf(d);
  if (!tasks.length) return '<p class="empty">The coordinator has not split the change into tasks yet.</p>';
  const [t0, t1] = rangeOf(d, range), peak = peakOf(d, t0, t1), axis = axisHTML(t0, t1);
  const row = t => { const s = statusOf(t, d);
    return `<li class="row"><button type="button" class="lab" data-t="${esc(t.id)}" aria-haspopup="dialog" aria-label="${esc(rowName(t, d))}">`
      + `<span class="first"><span class="id">${esc(t.id)}</span>${modeTag(t.mode)}<span class="t" title="${esc(t.task)}">${esc(t.task)}</span></span>`
      + `<span class="ts ${s.cls}">${s.icon}<span class="w">${esc(s.word)}</span></span></button>`
      + `<div class="lane" data-t="${esc(t.id)}">${axis.lines}${laneSVG(t, d, t0, t1, peak)}${marksHTML(t, d, t0, t1)}</div></li>`; };
  const before = range === "all" ? [] : tasks.filter(t => groupOf(t, d) === "merged" && (mergedAt(t) ?? t1) < t0);
  return [["working", "Working"], ["pending", "Pending"], ["merged", "Merged"]].map(([key, name]) => {
    const rows = tasks.filter(t => groupOf(t, d) === key);
    if (!rows.length) return "";
    const more = key === "merged" && before.length ? `<p class="before">${before.length} ${before.length === 1 ? "task" : "tasks"} merged before ${hm(t0)}. <button type="button" class="link" data-range="all">Show all</button></p>` : "";
    return `<section class="tbl" aria-labelledby="h-${key}"><h2 class="section-h" id="h-${key}">${name} (${rows.length})</h2>${more}`
      + `<div class="axisrow" aria-hidden="true"><span></span><div class="axis">${axis.labels}</div></div><ul class="rows">${rows.map(row).join("")}</ul></section>`;
  }).join("");
}
// timeline:end

function setHTML(el, html) { if (el._html !== html) el.innerHTML = el._html = html; }

// ---------- The conversation: page.js; the decision question is the shared one ----------
const md = text => pageMarkdown(text).outerHTML;  // Markdown, built as elements: safe to place as HTML
const uid = p => p + "-" + Date.now().toString(36) + Math.random().toString(36).slice(2, 5);
// The shared decision item, with what only this page shows: where the question is from, and that a record is not valid.
function decisionItem(c, state, actions) {
  const [item, foot] = dec.item(c, state, actions), x = c.e.x;
  const from = [has(x.raised_by) ? x.raised_by : "", has(x.task) ? "task " + x.task : ""].filter(Boolean).join(", ");
  const extra = (from ? `<p class="what">From ${esc(from)}</p>` : "") + (x._errors && x._errors.length ? `<p class="what invalid">not valid: ${esc(x._errors[0])}</p>` : "");
  if (extra) item.querySelector(".head").insertAdjacentHTML("afterend", extra);
  return [item, foot];
}
function crumb(e) {
  const x = document.createElement("span");
  if (e.on) { x.className = "crumb"; x.innerHTML = `<span class="path">on</span><span class="el"><button type="button" data-t="${esc(e.on.id)}">${esc(e.on.title || e.on.id)}</button></span>`; }
  return x;
}
function commentBody(e) { return pageMarkdown(e.text); }
const conv = pageConversation({
  served: !STATIC, stream: false, thread: $("thread"),
  kinds: {decision: decisionItem}, crumb, commentBody, stats: () => $("yourturn"),
  afterSend: () => tick(),
});
const dec = pageDecision({conversation: conv, now: () => D.now, md, esc, id: uid});

// ---------- The pop-up for a task: its detail and a box to ask about it ----------
// The pop-up itself is page.js's (pagePopup); the task it shows is OPENID, and `$("pop")` says whether it is open.
const popup = pagePopup({modal: true, fill: () => fillPop(), place: anchor => placePop(anchor)});
let OPENID = null;
function openPop(id, anchor) { OPENID = id; popup.open(anchor); }
// The pop-up stays inside the view column, under its row if it fits, never over the conversation; its body scrolls.
function placePop(anchor) {
  const el = $("pop"), main = document.querySelector("main.view"); if (!el || !anchor || !main) return;
  const m = main.getBoundingClientRect(), r = anchor.getBoundingClientRect(), w = Math.min(el.offsetWidth, m.width - 20);
  el.style.width = w + "px";
  const left = Math.max(m.left + 10, Math.min(r.left + 40, m.right - w - 10));
  let top = r.bottom + 6;
  if (top + 240 > innerHeight) top = Math.max(m.top + 10, innerHeight - Math.min(el.scrollHeight, innerHeight - m.top - 20) - 10);
  el.style.left = left + "px"; el.style.top = top + "px"; el.style.maxHeight = (innerHeight - top - 10) + "px";
}
function fillPop() {
  const el = $("pop"); if (!el || !D) return;
  const t = tasksOf(D).find(x => x.id === OPENID); if (!t) return popup.close();
  const ta = el.querySelector("textarea"), typed = ta ? ta.value : "", focused = ta && document.activeElement === ta;
  const html = `<button type="button" class="x" aria-label="Close">×</button>` + popupHTML(t, D);
  const mine = conv.nodes(e => e.on && e.on.kind === "task" && e.on.id === t.id), key = html + mine.map(n => n.outerHTML).join("");
  if (el._html === key) return;
  const scroll = el.scrollTop;
  el.innerHTML = html; el._html = key;
  el.querySelector("ul.thread").append(...mine);
  const box = el.querySelector("textarea"); box.value = typed; if (focused) box.focus({preventScroll: true});
  el.scrollTop = scroll;
}

// ---------- Sending: the message box and replies are page.js's; the pop-up and the answers are the dashboard's ----------
document.addEventListener("submit", ev => {
  ev.preventDefault();
  const f = ev.target; if (!f.classList.contains("popask")) return;
  const ta = f.querySelector("textarea"), text = ta.value.trim(); if (!text) return ta.focus();
  const t = tasksOf(D).find(x => x.id === OPENID) || {};
  conv.send("comment", {id: uid("c"), on: {kind: "task", id: OPENID, title: `${OPENID} ${str(t.task)}`.trim()}, text}, "Comment", () => { ta.value = ""; fillPop(); });
});
document.addEventListener("click", ev => {
  const t = ev.target;
  const r = t.closest("[data-range]");
  if (r) { RANGE = r.dataset.range; drawRange(); if (D) drawTables(D); return; }
  if (popup.click(t)) return;
  if (t.closest(".ev")) return;
  // A row's label or its lane opens the task; focus comes back to the label, the row's keyboard target.
  const row = t.closest("[data-t]"); if (row) return openPop(row.dataset.t, (row.closest(".row") || row).querySelector(".lab") || row);
  if ($("pop") && !t.closest("form, .why")) popup.close();
});
document.addEventListener("keydown", ev => {
  if (popup.key(ev)) return;
  if (ev.key === "Enter" && !ev.shiftKey && ev.target.matches && ev.target.matches("form.popask textarea")) { ev.preventDefault(); ev.target.form.requestSubmit(); }
});

// ---------- Render ----------
function drawRange() {
  document.querySelectorAll("#range [data-range]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.range === RANGE)));
}
function drawTables(d) {
  const focused = document.activeElement && document.activeElement.closest && document.activeElement.closest("[data-t]");
  setHTML($("tables"), tablesHTML(d, RANGE));
  // A refresh every two seconds redraws the rows: focus stays on the row it was on.
  if (focused && !document.contains(focused)) { const again = $("tables").querySelector(`[data-t="${CSS.escape(focused.dataset.t)}"]`); if (again) again.focus({preventScroll: true}); }
  if ($("pop")) { const again = $("tables").querySelector(`[data-t="${CSS.escape(OPENID)}"]`); if (again) popup.anchor = again; }
}
function render(d) {
  D = d;
  $("title").textContent = d.name || "Change dashboard"; document.title = `${$("title").textContent} · Change dashboard`;
  const tasks = tasksOf(d), done = tasks.filter(isDone).length;
  // A question the user answered in the page no longer waits for them, even before the coordinator applies the answer.
  // It waits again when the coordinator asked back about the answer.
  conv.setLog(pageDecisionEvents(d.decisions, d.conversation), (d.decisions || []).map(x => [x.id, x.status, x.answer, x.decision, x._changed]));
  const stat = (n, label, cls) => `<span class="stat${cls ? " " + cls : ""}"><b>${n}</b>${label}</span>`;
  setHTML($("status"), (tasks.length ? `<span class="stat"><b>${done}<span class="of"> / ${tasks.length}</span></b>tasks done
      <span class="meter" aria-hidden="true"><i style="width:${(100 * done / tasks.length).toFixed(0)}%"></i></span></span>` : "")
    + `<span class="yourturn" id="yourturn"></span>`  // page.js's "N your turn" figure
    + (d.start ? stat(esc(runningWord(d)), "running") : ""));
  conv.figure();
  pageShowErrors($("errors"), d.errors);
  drawRange();
  drawTables(d);
  const replies = (d.conversation || []).filter(e => e.type === "reply");
  if (REPLIES >= 0 && replies.length > REPLIES) conv.flash("Coordinator: " + pageMarkdownText(replies[replies.length - 1].text).slice(0, 120), "ok");
  REPLIES = replies.length;
  if ($("pop")) { fillPop(); placePop(popup.anchor); }
}

// load:begin
function tick() {
  if (STATIC) return Promise.resolve();
  return pageFetch("/data", {cache: "no-store"}).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }).then(render, () => {});
}
// load:end
if (STATIC) render(JSON.parse($("page-data").textContent));
else { tick(); setInterval(tick, 2000); }
conv.start();
