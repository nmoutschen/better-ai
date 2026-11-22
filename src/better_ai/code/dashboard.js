const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const has = v => v && v !== "none";
const plural = (n, w) => `${n} ${w}${n === 1 ? "" : "s"}`;
const ago = s => s < 60 ? "just now" : s < 5400 ? `${Math.round(s / 60)} min ago` : `${Math.round(s / 3600)} h ago`;
const STATEWORD = {working: "working", waiting: "waiting", blocked: "blocked", finished: "handed back"};
// An agent at work that has not written to its log for this long is shown as quiet, with the stuck ones. Builders log
// after each step, so a long silence usually means a stuck command or a lost agent.
const QUIET = 15 * 60;
const ORDER = {blocked: 0, quiet: 1, waiting: 2, working: 3};
const stateOf = (a, now) => a.state === "working" && now - a._changed > QUIET ? "quiet" : a.state;
const word = (a, now) => stateOf(a, now) === "quiet" ? `quiet ${Math.round((now - a._changed) / 60)} min` : STATEWORD[a.state];
const STATIC = !!document.getElementById("page-data");  // a page written by `render`: its data is in it, and nothing is served
let D = null, OPEN = null, REPLIES = -1;  // OPEN: the agent the pop-up shows, as {id, anchor}

// An agent's log line as a person reads it: a step shows its text, any other line says what kind it is first.
const LABEL = {start: "Start", asked: "Asked", blocked: "Blocked", handed_back: "Handed back"};
const words = l => l.type === "step" ? l.text : l.type === "handed_back" ? `${LABEL.handed_back}: ${[l.result, l.text].filter(Boolean).join(", ")}`
  : `${LABEL[l.type] || l.type}: ${l.text}`;
// status:begin
// What an agent does: the card's edge is the mode of its task, one colour per mode. A builder's tag is that mode; a
// verifier's tag says "verifier", so it never reads as a builder at work on the task again. No role counts as a builder.
const MODES = {feature: "feature", "bug fix": "bugfix", bugfix: "bugfix", refactor: "refactor", tests: "tests"};
const modeOf = a => String(a.mode || "").trim().toLowerCase();
const isVerifier = a => String(a.role || "").trim().toLowerCase() === "verifier";
const modeClass = a => { const m = modeOf(a); return m && m !== "none" ? "m-" + (MODES[m] || "other") : "m-other"; };
const agentClass = modeClass;
const agentTag = a => { const m = modeOf(a);
  return isVerifier(a) ? `<span class="mode r-verifier">verifier</span>` : m && m !== "none" ? `<span class="mode ${modeClass(a)}">${esc(m)}</span>` : ""; };
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
// The status word as HTML: it may carry a field of tasks.jsonl as written, so it is escaped; a long one is cut, in full on hover.
const statusLabel = (t, tasks, icons) => { const {key, word} = taskStatus(t, tasks);
  return `<span class="tstat ${key}" title="${esc(word)}">${(icons || {})[key] || ""}<span class="w">${esc(word)}</span></span>`; };
// status:end
// One icon per state, drawn in currentColor so blocked and quiet take the red of their text.
const ICON = {
  working: '<svg viewBox="0 0 14 14" aria-hidden="true"><path d="M3 2l9 5-9 5z" fill="currentColor"/></svg>',
  waiting: '<svg viewBox="0 0 14 14" aria-hidden="true"><rect x="3" y="2" width="3" height="10" fill="currentColor"/><rect x="8" y="2" width="3" height="10" fill="currentColor"/></svg>',
  blocked: '<svg viewBox="0 0 14 14" aria-hidden="true"><circle cx="7" cy="7" r="5.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M3 11L11 3" stroke="currentColor" stroke-width="2"/></svg>',
  quiet: '<svg viewBox="0 0 14 14" aria-hidden="true"><circle cx="7" cy="7" r="5.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M7 4v3.5l2.5 1.5" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>',
  finished: '<svg viewBox="0 0 14 14" aria-hidden="true"><path d="M2.5 7.5l3 3 6-7" fill="none" stroke="currentColor" stroke-width="2"/></svg>',
};
// The state icon; a quiet agent also shows how long it has been quiet, the one figure the icon cannot carry.
const stateIcon = (a, now) => { const s = stateOf(a, now), w = word(a, now);
  return `<span class="state ${s}" role="img" aria-label="${esc(w)}" title="${esc(w)}">${ICON[s]}${s === "quiet" ? esc(w.replace(/^quiet /, "")) : ""}</span>`; };
const who = a => esc(a.name);
const taskOf = a => a.task ? (D.tasks || []).find(t => t.id === a.task) : undefined;
// A task's requirements with their text from the spec; an ID the spec does not hold shows as missing, not hidden.
const reqsOf = t => { const r = (t || {}).requirements; return (Array.isArray(r) ? r : []).map(id => [String(id), (D.requirements || {})[id]]); };
const reqItems = t => reqsOf(t).map(([id, text]) => `<li dir="auto"><b>${esc(id)}</b>${text ? esc(text) : '<span class="missing">not in the spec</span>'}</li>`).join("");
const taskLabel = a => { const t = taskOf(a); return t ? `${t.id}: ${t.task ?? ""}` : a.task ? `Task ${a.task}` : "No task named"; };

// errors:begin
// The records that did not validate, as a band above the work: where each is, its field, why, and who wrote it. A file
// can hold anything, so every part is text. The valid records are on the page as usual; this band never replaces them.
const errorsHTML = errors => !errors || !errors.length ? "" :
  `<h2 id="errors-h">${errors.length} ${errors.length === 1 ? "record is" : "records are"} not valid</h2><ul>${errors.map(e =>
    `<li><code>${esc(e.file)}:${esc(e.line)}</code> <b>${esc(e.field)}</b>: ${esc(e.message)}${e.by ? ` <span class="by">written by ${esc(e.by)}</span>` : ""}</li>`).join("")}</ul>`;
// errors:end

// ---------- The agents ----------
function drawAgents(d) {
  setHTML($("key"), ["working", "waiting", "blocked", "quiet"].map(s => `<li><span class="state ${s}">${ICON[s]}</span>${s === "waiting" ? "waiting on coordinator" : s}</li>`).join(""));
  // The stuck agents first, then by task number, so the user finds both a problem and a given task without reading every card.
  // The tasks keep tasks.jsonl's order, so the agents follow it too.
  const num = a => { const i = (d.tasks || []).findIndex(t => t.id === a.task); return i < 0 ? Infinity : i; }, now = d.now;
  const live = d.agents.filter(a => a.state !== "finished")
    .sort((a, z) => ORDER[stateOf(a, now)] - ORDER[stateOf(z, now)] || num(a) - num(z) || a.name.localeCompare(z.name));
  setHTML($("cards"), live.map(a => `<li><button type="button" class="card ${stateOf(a, now)} ${agentClass(a)}" data-a="${esc(a.name)}">
      <p class="meta">${agentTag(a)} ${stateIcon(a, now)} ${who(a)}</p>
      <h3 dir="auto">${esc(taskLabel(a))}</h3>
      ${reqsOf(taskOf(a)).length ? `<ul class="reqs">${reqItems(taskOf(a))}</ul>` : ""}
      <ol>${a.lines.filter(l => l.type !== "start").slice(-3).map(l => `<li dir="auto">${esc(words(l))}</li>`).join("")}</ol>
      <p class="ago">Updated ${ago(d.now - a._changed)}</p></button></li>`).join("")
    || `<li class="empty">No agent is working right now.</li>`);
}
// ---------- The tasks ----------
const svg = body => `<svg viewBox="0 0 14 14" aria-hidden="true">${body}</svg>`;
const TICON = {todo: svg('<circle cx="7" cy="7" r="5" fill="none" stroke="currentColor" stroke-width="1.6"/>'),
  building: ICON.working,
  built: svg('<circle cx="7" cy="7" r="5.5" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M4.5 7.2l1.8 1.8 3.3-3.8" fill="none" stroke="currentColor" stroke-width="1.6"/>'),
  verifying: svg('<circle cx="6" cy="6" r="3.6" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M8.7 8.7L12.5 12.5" stroke="currentColor" stroke-width="2"/>'),
  changes: svg('<path d="M11.5 3v4.5H3.5" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M6.5 4.3L3.2 7.5l3.3 3.2" fill="none" stroke="currentColor" stroke-width="1.8"/>'),
  verified: ICON.finished,
  // merged: two branches joined
  merged: svg('<circle cx="4" cy="2.8" r="1.7" fill="currentColor"/><circle cx="4" cy="11.2" r="1.7" fill="currentColor"/><circle cx="10.5" cy="7" r="1.7" fill="currentColor"/><path d="M4 4.5V9.5M4 4.5C4 7 6.5 7 8.8 7" fill="none" stroke="currentColor" stroke-width="1.6"/>'),
  // done, in a single-agent list: finished, a filled tick
  done: svg('<circle cx="7" cy="7" r="6" fill="currentColor"/><path d="M4.3 7.2l1.9 1.9 3.6-4" fill="none" style="stroke:var(--cream)" stroke-width="1.8"/>'),
  blocked: ICON.blocked,
  other: svg('<circle cx="7" cy="7" r="5.5" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M5.3 5.6a1.8 1.8 0 1 1 2.5 1.6c-.5.3-.8.6-.8 1.2v.5" fill="none" stroke="currentColor" stroke-width="1.4"/><circle cx="7" cy="10.4" r=".85" fill="currentColor"/>')};
function drawTasks(d) {
  const tasks = d.tasks || [];
  $("tasks-sec").hidden = !tasks.length;
  // The heading says how many tasks are done of how many, since past five rows the list scrolls and the rest are out of sight.
  $("tasks-h").textContent = `Tasks: ${tasks.filter(isDone).length} of ${tasks.length} done`;
  // The tasks keep their own order, the one tasks.jsonl gives, each with the status tasks.jsonl gives it.
  setHTML($("tasks"), tasks.map(t => {
    const live = d.agents.filter(a => a.task && a.task === t.id && a.state !== "finished");
    const tag = typeof t.mode === "string" && has(t.mode) ? `<span class="mode m-${MODES[t.mode.trim().toLowerCase()] || "other"}">${esc(t.mode)}</span>` : "";
    const open = OPENTASKS.has(t.id) ? " open" : "";
    return `<li><details data-t="${esc(t.id)}"${open}><summary><span class="n">${esc(t.id)}</span>
      ${statusLabel(t, tasks, TICON)}${tag}<span class="t" dir="auto">${esc(t.task)}</span>
      ${live.length ? `<span class="on">${esc(live.map(a => a.name).join(", "))}</span>` : ""}</summary>
      <div class="body">${reqsOf(t).length ? `<ul class="req-list">${reqItems(t)}</ul>` : '<p class="empty">No requirement named.</p>'}
      ${has(t.check) ? `<p class="check">Check: <code>${esc(t.check)}</code></p>` : ""}
      ${live.length ? `<p class="agents">${live.map(a => `<button type="button" data-a="${esc(a.name)}">${esc(a.name)}</button>`).join("")}</p>` : ""}</div></details></li>`;
  }).join(""));
}
// The task list's own scroll bar: shown only when the list holds more than it shows, its thumb sized and placed from
// the list's scroll. Dragging the thumb scrolls the list; a click on the track moves it by one view. The wheel and
// the keyboard scroll the list itself, as usual.
function syncBar() {
  const ul = $("tasks"), bar = $("sbar"), th = $("sthumb"), h = ul.clientHeight, full = ul.scrollHeight;
  bar.hidden = full <= h + 1; if (bar.hidden) return;
  const size = Math.max(24, h * h / full);
  th.style.height = size + "px"; th.style.top = (ul.scrollTop / (full - h)) * (h - size) + "px";
}
$("tasks").addEventListener("scroll", syncBar, {passive: true});
addEventListener("resize", syncBar);
$("sbar").addEventListener("pointerdown", ev => {
  const ul = $("tasks"), th = $("sthumb");
  if (ev.target !== th) { ul.scrollTop += (ev.offsetY < th.offsetTop ? -1 : 1) * ul.clientHeight; return; }
  ev.preventDefault(); th.setPointerCapture(ev.pointerId);
  const y0 = ev.clientY, top0 = ul.scrollTop, rate = (ul.scrollHeight - ul.clientHeight) / (ul.clientHeight - th.offsetHeight);
  const move = e => { ul.scrollTop = top0 + (e.clientY - y0) * rate; };
  th.addEventListener("pointermove", move);
  th.addEventListener("pointerup", () => th.removeEventListener("pointermove", move), {once: true});
});
// Which task rows the user opened, so a refresh every two seconds does not fold them again.
const OPENTASKS = new Set();
document.addEventListener("toggle", ev => { const t = ev.target.dataset && ev.target.dataset.t;
  if (t !== undefined) { ev.target.open ? OPENTASKS.add(t) : OPENTASKS.delete(t); syncBar(); } }, true);
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
  if (e.on) { x.className = "crumb"; x.innerHTML = `<span class="path">on</span><span class="el"><button type="button" data-a="${esc(e.on.id)}">${esc(e.on.title || e.on.id)}</button></span>`; }
  return x;
}
function commentBody(e) { return pageMarkdown(e.text); }
const conv = pageConversation({
  served: !STATIC, stream: false, thread: $("thread"),
  kinds: {decision: decisionItem}, crumb, commentBody,
  // No accept step: the coordinator answers or acts, and an answered item is finished.
  steps: ["seen", "working", "done"], labels: {done: "Answered"}, shown: st => st === "accepted" ? "done" : st,
  accept: false, filter: false, latestLast: true,
  // A question waiting for the user, or a message of theirs the coordinator asked about, counts as open; it keeps its
  // place in time, so the newest message is always last.
  waiting: (c, state) => c.kind === "decision" ? dec.waiting(c, state) : ["comment", "note"].includes(c.kind) && state[c.e.id] === "asked",
  afterSend: () => tick(),
});
const dec = pageDecision({conversation: conv, now: () => D.now, md, esc, id: uid});

// ---------- The pop-up for an agent: its whole recent log, and a box to ask about its work ----------
function openPop(id, anchor) {
  closePop(); OPEN = {id, anchor};
  const el = document.createElement("div"); el.className = "qpop"; el.setAttribute("role", "dialog"); el.id = "pop";
  document.body.append(el); fillPop(); placePop(anchor);
  const h3 = el.querySelector("h3"); if (h3) { h3.id = "pop-title"; el.setAttribute("aria-labelledby", "pop-title"); h3.setAttribute("tabindex", "-1"); h3.focus({preventScroll: true}); }
}
function closePop() { const p = $("pop"); if (p) p.remove(); const back = OPEN && OPEN.anchor; OPEN = null; if (back && document.contains(back)) back.focus({preventScroll: true}); }
function placePop(anchor) {
  const el = $("pop"); if (!el || !anchor) return;
  const r = anchor.getBoundingClientRect(), w = el.offsetWidth, h = el.offsetHeight, side = !!anchor.closest("aside");
  let left = side ? r.left - w - 12 : r.left, top = side ? r.top : r.bottom + 8;
  left = Math.max(10, Math.min(left, innerWidth - w - 10)); if (top + h > innerHeight - 10) top = Math.max(10, innerHeight - h - 10);
  el.style.left = left + "px"; el.style.top = top + "px";
}
function fillPop() {
  const el = $("pop"); if (!el || !D) return;
  const ta = el.querySelector("textarea"), typed = ta ? ta.value : "", focused = ta && document.activeElement === ta;
  // An agent that handed back leaves the page, its pop-up too.
  const a = D.agents.find(x => x.name === OPEN.id && x.state !== "finished"); if (!a) return closePop();
  const label = `Message about ${a.name}'s work`;
  const task = taskOf(a), reqs = reqsOf(task).length, check = task && has(task.check);
  // The header says who and what; then what the agent must make true, its steps, and the conversation about its work.
  const html = `<button type="button" class="x" aria-label="Close">×</button>
    <div class="hd"><p class="kind">${agentTag(a)} ${stateIcon(a, D.now)} ${who(a)}${has(a.branch) ? " on " + esc(a.branch) : ""}</p>
    <h3 dir="auto">${esc(taskLabel(a))}</h3></div>
    <div class="bd">${reqs || check ? `<div class="sec"><h4 class="section-h">${isVerifier(a) ? "Checks the work against" : "Must make true"}</h4>${reqs ? `<ul class="req-list">${reqItems(task)}</ul>` : ""}
    ${check ? `<p class="check">Check: <code>${esc(task.check)}</code></p>` : ""}</div>` : ""}
    <div class="sec"><h4 class="section-h">Steps so far</h4><ol class="steps">${a.lines.map(l => `<li dir="auto">${esc(words(l))}</li>`).join("") || "<li>None logged yet.</li>"}</ol></div>
    <div class="sec"><h4 class="section-h">Conversation</h4><ul class="thread"></ul>
    <form class="ask popask"><textarea aria-label="${esc(label)}" placeholder="${esc(label)}"></textarea><button type="submit" class="btn">Send</button></form></div></div>`;
  const mine = conv.nodes(e => e.on && e.on.kind === "agent" && e.on.id === a.name), key = html + mine.map(n => n.outerHTML).join("");
  if (el._html === key) return;
  el.innerHTML = html; el._html = key;
  el.querySelector("ul.thread").append(...mine);
  const t = el.querySelector("textarea"); t.value = typed; if (focused) t.focus({preventScroll: true});
  placePop(OPEN.anchor);
}

// ---------- Sending: the message box and replies are page.js's; the pop-up and the answers are the dashboard's ----------
document.addEventListener("submit", ev => {
  ev.preventDefault();
  const f = ev.target; if (!f.classList.contains("popask")) return;
  const ta = f.querySelector("textarea"), text = ta.value.trim(); if (!text) return ta.focus();
  conv.send("comment", {id: uid("c"), on: {kind: "agent", id: OPEN.id, title: OPEN.id}, text}, "Comment", () => { ta.value = ""; fillPop(); });
});
document.addEventListener("click", ev => {
  const t = ev.target;
  if (t.closest("#to-waiting")) { const q = document.querySelector("#thread .open-q"); if (!q) return;
    q.scrollIntoView({block: "start"}); const b = q.querySelector(".change"); if (b) b.focus({preventScroll: true}); return; }
  if (t.closest(".qpop .x")) return closePop();
  if (t.closest(".qpop")) return;
  const a = t.closest("[data-a]"); if (a) return openPop(a.dataset.a, a);
  if ($("pop") && !t.closest("form, .why")) closePop();
});
document.addEventListener("keydown", ev => {
  // Tab stays inside the open pop-up, so focus never goes to the cards hidden under it.
  if (ev.key === "Tab" && $("pop") && $("pop").contains(ev.target)) {
    const f = [...$("pop").querySelectorAll("button, textarea, [tabindex]")], i = f.indexOf(ev.target);
    if (ev.shiftKey && i <= 0) { ev.preventDefault(); f[f.length - 1].focus(); }
    else if (!ev.shiftKey && i === f.length - 1) { ev.preventDefault(); f[0].focus(); }
  }
  if (ev.key === "Escape" && $("pop") && !(ev.target.closest && ev.target.closest(".why"))) { ev.preventDefault(); closePop(); }
  if (ev.key === "Enter" && !ev.shiftKey && ev.target.matches && ev.target.matches("form.popask textarea")) { ev.preventDefault(); ev.target.form.requestSubmit(); }
});

// ---------- Render ----------
function render(d) {
  D = d;
  $("title").textContent = d.name || "Change dashboard"; document.title = `${$("title").textContent} · Change dashboard`;
  const tasks = d.tasks || [], done = tasks.filter(isDone).length;
  const working = d.agents.filter(a => a.state !== "finished").length;
  // A question the user answered in the page no longer waits for them, even before the coordinator applies the answer.
  // It waits again when the coordinator asked back about the answer.
  conv.setLog(pageDecisionEvents(d.decisions, d.conversation), (d.decisions || []).map(x => [x.id, x.status, x.answer, x.decision, x._changed]));
  const st = conv.state(), last = {};
  (d.conversation || []).filter(e => e.type === "answer").forEach(e => { last[e.decision] = e; });
  const waitingN = (d.decisions || []).filter(x => dec.step(dec.status(x), last[x.id], st) === 0).length;
  const stat = (n, label, cls) => `<span class="stat${cls ? " " + cls : ""}"><b>${n}</b>${label}</span>`;
  setHTML($("status"), (tasks.length ? `<span class="stat"><b>${done}<span class="of"> / ${tasks.length}</span></b>tasks done
      <span class="meter" aria-hidden="true"><i style="width:${(100 * done / tasks.length).toFixed(0)}%"></i></span></span>` : "")
    + stat(working, working === 1 ? "agent at work" : "agents at work")
    + (waitingN ? `<button type="button" class="stat" id="to-waiting"><b>${waitingN}</b>${waitingN === 1 ? "open question" : "open questions"}</button>`
      : stat(0, "open questions")));
  const band = errorsHTML(d.errors);
  $("errors").hidden = !band; setHTML($("errors"), band);
  $("notice").hidden = !d.old; $("notice").textContent = plural(d.old || 0, "record") + " written in the format before this change: kept as is, not converted.";
  drawAgents(d);
  drawTasks(d);
  syncBar();
  const replies = (d.conversation || []).filter(e => e.type === "reply");
  if (REPLIES >= 0 && replies.length > REPLIES) conv.flash("Coordinator: " + pageMarkdownText(replies[replies.length - 1].text).slice(0, 120), "ok");
  REPLIES = replies.length;
  if (OPEN) fillPop();
}

// load:begin
function tick() {
  if (STATIC) return Promise.resolve();
  return fetch("/data", {cache: "no-store"}).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }).then(render, () => {});
}
// load:end
if (STATIC) render(JSON.parse($("page-data").textContent));
else { tick(); setInterval(tick, 2000); }
conv.start();
