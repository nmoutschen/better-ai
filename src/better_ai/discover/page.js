'use strict';
// The discovery page. Everything above "Start" is plain functions of the page's data (what /data serves) and of the
// conversation: they build HTML strings, every record field through pageEscape (page.js), and touch no element. What
// follows draws them and sends the user's events. The shell, the tabs, the table, the chips, the agents at work and the
// decision question are the shared page's (page.js, page.css); this file adds only what is the discovery's.

const esc = pageEscape;
const s = value => typeof value === 'string' ? value : '';  // a record may lack a field or hold another type
const cap = text => text.charAt(0).toUpperCase() + text.slice(1);
const plural = (n, one, many) => n + ' ' + (n === 1 ? one : many);

// ---------- Words ----------
const TABS = [['moves', 'Moves'], ['problems', 'Problems'], ['opportunities', 'Opportunities'], ['behaviours', 'Behaviours'],
  ['evidence', 'Evidence'], ['options', 'Options'], ['tests', 'Tests'], ['brief', 'Brief']];
const KIND_TAB = { problem: 'problems', opportunity: 'opportunities', behaviour: 'behaviours' };
const KIND_ORDER = ['problem', 'opportunity', 'behaviour'];
const KIND_NOUN = { problem: 'problems', opportunity: 'opportunities', behaviour: 'behaviours' };
const MOVES = ['test first', 'expand', 'shrink', 'switch', 'adopt', 'pause', 'stop'];
const CONFIRMED = ['expand', 'adopt', 'stop'];  // the moves that are costly or hard to undo: a second click
const WRITES_BRIEF = ['expand', 'shrink', 'adopt', 'stop'];
const STEP_NAMES = { 1: 'your idea and appetite', 2: 'the draft', 3: 'the reality check', 4: 'evidence about your users', 5: 'your calls',
  6: 'plan the test', 7: 'run the test', 8: 'write the brief', 9: 'design and build', 10: 'learn from real use' };
const KINDS = { say: 'Something said', did: 'Something done', commit: 'Something committed to', data: 'Numbers', desk: 'Something read' };
const WORDS = { 'your users': 'Your users', elsewhere: 'Elsewhere' };

// A chip is a state word, coloured by what it means (page.css): done is moss, being worked terracotta, waiting for you
// umber, and only Contradicted is red.
const STATE_CHIPS = {
  supported: ['ok', 'Supported'], contradicted: ['error', 'Contradicted'], checking: ['working', 'Checking'],
  'waiting for you': ['wait', 'Waiting for you'], proposed: ['wait', 'Proposed'], 'being written': ['working', 'being written'],
  'needs a test': ['', 'Needs a test'], unverified: ['', 'Unverified'], 'risk accepted': ['', 'Risk accepted'],
  chosen: ['', 'Chosen'], alternative: ['', 'Alternative idea'],
};
const chip = (word, kind) => '<span class="chip' + (kind ? ' ' + kind : '') + '">' + esc(word) + '</span>';
function stateChip(state, o) {
  o = o || {};
  const known = STATE_CHIPS[state];
  if (!known) return chip(s(state) || 'Unknown', '');
  let word = known[1];
  if (state === 'checking' && o.minutes != null) word += ', ' + o.minutes + ' min';
  if (state === 'being written' && o.version) word = o.version + ' ' + word;
  return chip(word, known[0]);
}

// The whole minutes from AT to NOW (seconds); null when AT is not a time.
function ageMin(at, now) {
  const t = Date.parse(at);
  return isFinite(t) ? Math.max(0, Math.floor((now - t / 1000) / 60)) : null;
}

// ---------- Links ----------
// A source address is a link only when it is http or https; anything else is shown as text.
function safeLink(url, label) {
  if (typeof url === 'string' && /^https?:\/\/\S+$/i.test(url)) {
    return '<a href="' + esc(url) + '" rel="noopener noreferrer" target="_blank">' + esc(label) + '</a>';
  }
  return esc(label);
}
// Every ID shown outside its own row is a link to that row.
function idLink(id, known) {
  return known.has(id) ? '<a href="#row-' + esc(id) + '" data-goto="' + esc(id) + '">' + esc(id) + '</a>' : esc(id);
}
function knownIds(data) {
  const ids = new Set();
  [data.items, data.evidence, data.tests, data.options, data.decisions, data.moves, data.briefs].forEach(list => (list || []).forEach(r => { if (r && s(r.id)) ids.add(r.id); }));
  return ids;
}
function tabOf(id, data) {
  const item = (data.items || []).find(i => i.id === id);
  if (item) return KIND_TAB[item.kind] || 'moves';
  if (/^E-/.test(id)) return 'evidence';
  if (/^X\d/.test(id)) return 'tests';
  if (/^K\d/.test(id)) return 'options';
  if (/^v\d/.test(id)) return 'brief';
  return 'moves';
}

// The first sentence of a text, and whether there is more: nothing is cut without a More that holds it all.
function firstSentence(text) {
  const t = s(text).trim();
  const m = /^[^]*?[.!?](?=\s|$)/.exec(t);
  let first = m ? m[0] : t.split('\n')[0];
  let more = first.length < t.length;
  if (first.length > 220) { first = first.slice(0, 220).replace(/\s+\S*$/, '') + '…'; more = true; }
  return { first, more };
}
function fold(text) {
  const { first, more } = firstSentence(text);
  return '<span class="first">' + esc(first) + '</span>' + (more ? '<details class="more"><summary>More</summary><p>' + esc(s(text)) + '</p></details>' : '');
}

// ---------- Open questions: one function for the header, the badges, the Moves tab and the conversation (S80) ----------
// A decision is open while it waits and the user has not answered it on the page, by the shared rule. A due move is a
// waiting decision about the discovery, so it counts with the others.
function openQuestions(decisions, log) {
  const open = new Set(pageOpenDecisions(decisions, log, [], null).map(c => c.e.id));
  return (decisions || []).filter(x => open.has(x.id));
}
function aboutTab(decision, items) {
  const about = decision.about || {};
  if (about.type === 'item' || about.type === 'risk') {
    const item = (items || []).find(i => i.id === about.item);
    return item ? KIND_TAB[item.kind] || 'moves' : 'moves';
  }
  return about.type === 'option' ? 'options' : about.type === 'evidence' ? 'evidence' : 'moves';
}
// The badge of each tab: Moves counts every open question; each other tab those about what it shows.
function badges(open, items) {
  const counts = { moves: open.length };
  open.forEach(d => { const tab = aboutTab(d, items); if (tab !== 'moves') counts[tab] = (counts[tab] || 0) + 1; });
  return counts;
}
const tabLabel = (label, n) => n ? label + ', ' + plural(n, 'open question', 'open questions') : label;
// Where the focus goes after the check on question ID: the next open question after it, wrapping, on its check or, with no
// default, its Answer; null when no other question is open (then the move, if one is due).
function nextAfter(open, id) {
  const i = open.findIndex(d => d.id === id);
  for (let k = 1; k < open.length; k++) {
    const d = open[(i + k) % open.length];
    if (d.id !== id) return { id: d.id, use: !!s(d.default) };
  }
  return null;
}
const dueMove = open => open.find(d => (d.about || {}).type === 'discovery') || null;
const hasQuestion = (open, id) => open.some(d => (d.about || {}).item === id);

// ---------- What the records say ----------
const lastOf = list => list[list.length - 1];
const writesBrief = (move, data) => {
  const option = (data.options || []).find(o => o.id === move.option);
  return !!option && WRITES_BRIEF.includes(option.move);
};
const optionOf = (data, id) => (data.options || []).find(o => o.id === id);
const moveName = (data, move) => { const o = optionOf(data, move.option); return o ? cap(s(o.move)) : s(move.option); };
const briefNumber = id => { const m = /^v(\d+)$/.exec(s(id)); return m ? Number(m[1]) : 0; };
// The brief's version as the header and the log say it: final, being written after a move, or a draft.
function briefLabel(data) {
  const briefs = data.briefs || [], last = lastOf(data.moves || []), latest = lastOf(briefs);
  const next = 'v' + (Math.max(0, ...briefs.map(b => briefNumber(b.id))) + 1);
  if (last && writesBrief(last, data) && !briefs.some(b => b.move === last.id)) return next + ', being written';
  if (!latest) return 'no brief yet';
  return latest.id + ', ' + (latest.status === 'final' ? 'final' : last && latest.move === last.id && writesBrief(last, data) ? 'being written' : 'draft');
}
function briefFor(data, move) {
  const found = (data.briefs || []).find(b => b.move === move.id);
  if (found) return found.id + ', ' + (found.status === 'final' ? 'final' : 'being written');
  return writesBrief(move, data) ? 'being written' : 'none for this move';
}
const step = head => STEP_NAMES[head.step] ? 'Step ' + head.step + ': ' + STEP_NAMES[head.step] : 'Step ' + s(head.step);

// What an item is and what bears on it, read from the records.
const countsFor = (data, id, about, direction) => (data.evidence || []).filter(e => e.status === 'counts' && e.about === about &&
  (e.bears_on || []).some(b => b.item === id && b.direction === direction)).length;
const checkingOn = (data, id) => (data.evidence || []).filter(e => e.status === 'checking' && (e.bears_on || []).some(b => b.item === id)).length;
const lastChange = (data, id, field) => { let found = null; (data.changes || []).forEach(c => { if (c.field === field && (c.about || {}).item === id) found = c; }); return found; };

// The agent's latest record, as the page's Python serves it from summary's rule: one rule, not a copy here (L4).
function lastWord(data, name) {
  const t = Date.parse((data.last_word || {})[name]);
  return isFinite(t) ? t : null;
}
// The at-work list: each item and test with a checker, each piece of evidence with a verifier, aged from `since`.
function agentRows(data, now) {
  const row = (who, what, since, goto, o) => {
    const heard = lastWord(data, who), started = Date.parse(since);
    return Object.assign({ who, what, since, last: Math.max(isFinite(started) ? started : 0, heard || 0) || null, data: { goto } }, o);
  };
  const rows = [];
  (data.items || []).forEach(i => { if (s(i.checker)) rows.push(row(i.checker, i.id + ': ' + firstSentence(i.text).first, i.since, i.id, { state: 'Checking', second: (i.tries || []).length > 1 })); });
  (data.tests || []).forEach(t => { if (s(t.checker) && t.status !== 'removed') rows.push(row(t.checker, t.id + ': ' + firstSentence(t.what).first, t.since, t.id, { state: 'Running', second: false })); });
  (data.evidence || []).forEach(e => { if (e.status === 'checking' && s(e.verifier)) rows.push(row(e.verifier, 'Checking quote ' + e.id, e.since, e.id, { state: 'Checking', kind: 'verifier', second: (e.tries || []).length > 1 })); });
  return rows;
}
const atWork = (data, now) => pageAgents(agentRows(data, now), { now, quietAfter: data.quiet_after, empty: 'No agent is working right now.' });

// ---------- The user's events ----------
const uid = prefix => prefix + '-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 5);
// The choose event: the option, the revision of it as the page showed it, and whether the second click was made.
function chooseParams(option, revision, confirmed) {
  return { id: uid('c'), option: option.id, revision: s(revision), confirmed: !!confirmed };
}
// Remove… on evidence from the user, or in an internal discovery, asks for the words to be redacted everywhere; any other
// removal is a plain remove with its reason.
function removeFor(record, head, reason) {
  const origin = (record.origin || {}).type;
  if (/^E-/.test(s(record.id)) && (origin === 'you' || (head || {}).setting === 'internal')) return { method: 'redact', params: { evidence: record.id } };
  return { method: 'remove', params: { record: record.id, reason } };
}
// The choose event the agent has not dealt with: not done, and no move records it. Choose waits for it (S105); once the
// event is done with no move, the user may choose again (S57).
function pendingChoose(log, states, moves) {
  const recorded = new Set((moves || []).map(m => (m.answer || {}).event).filter(Boolean));
  let found = null;
  (log || []).forEach(e => {
    if (e.type === 'choose' && e.by === 'user' && e.id && !recorded.has(e.id) && states[e.id] !== 'done' && states[e.id] !== 'accepted') found = e;
  });
  return found;
}

// ---------- The header ----------
// The header holds figures only (DESIGN.md, stats header): the step of ten, the brief version, the open questions.
// The step's name, the last move and the brief's state live on their tabs.
function headerHTML(data, open) {
  const head = data.head || {}, briefs = data.briefs || [];
  const stat = (big, label) => '<span class="stat"><b>' + big + '</b>' + esc(label) + '</span>';
  const version = briefs.length ? 'v' + Math.max(...briefs.map(b => briefNumber(b.id))) : '–';
  return stat(esc(s(head.step) || '–') + '<span class="of"> / 10</span>', 'step') + stat(esc(version), 'brief') +
    (open.length ? '<button type="button" class="stat" id="questions"><b>' + open.length + '</b>' + (open.length === 1 ? 'open question' : 'open questions') + '</button>'
      : '<span class="stat"><b>0</b>open questions</span>');
}

// ---------- Tables ----------
const table = (heads, rows, cls) => '<div class="tablewrap"><table class="tbl' + (cls ? ' ' + cls : '') + '"><thead><tr>' + heads.map(h => '<th scope="col">' + esc(h) + '</th>').join('') +
  '</tr></thead><tbody>' + rows.join('') + '</tbody></table></div>';
const intro = text => '<p class="intro">' + esc(text) + '</p>';
const link = (data, ids, known) => ids.length ? ids.map(i => idLink(i, known)).join(', ') : '<span class="muted">None</span>';
const button = (label, attrs, cls) => '<button type="button" class="btn btn--sm ' + (cls || 'btn--quiet') + '" ' + attrs + '>' + esc(label) + '</button>';
const invalidNote = r => r && r._errors && r._errors.length ? '<p class="invalid">Not valid: ' + esc(r._errors[0]) + '</p>' : '';
const chatMark = '<span class="muted chat">recorded from the chat</span>';

// An item's row: what it is, how important, its state, what bears on it, what settled that state and what it rests on.
function itemRow(item, data, ctx, known) {
  const view = item.state;
  const more = [];
  if (firstSentence(item.text).more) more.push('<p>' + esc(s(item.text)) + '</p>');
  if (item.testable && s(item.testable.text)) more.push('<p><b>Testable form (' + esc(s(item.testable.form)) + '):</b> ' + esc(item.testable.text) + '</p>');
  if (s(item.ambiguity)) more.push('<p><b>Unclear:</b> ' + esc(item.ambiguity) + '</p>');
  const accepted = item.accepted_risks || [];
  if ((item.risks || []).length) {
    more.push('<p><b>Risks</b></p><ul>' + item.risks.map(r => '<li>' + esc(s(r.id)) + ', ' + esc(s(r.kind)) + ': ' + esc(s(r.text)) + (accepted.includes(r.id) ? ' (accepted)' : '') + '</li>').join('') + '</ul>');
  }
  const change = lastChange(data, item.id, 'state'), cause = change && change.cause || {};
  const settled = [].concat((cause.evidence || []).map(e => idLink(e, known)), cause.test ? [idLink(cause.test, known)] : [],
    cause.answer && cause.answer.type === 'decision' ? [idLink(cause.answer.id, known)] : cause.answer ? ['you, ' + (cause.answer.type === 'chat' ? 'in the chat' : 'on the page')] : [],
    cause.reasoning ? ['reasoning'] : []);
  const tests = (data.tests || []).filter(t => t.status !== 'removed' && (t.settles || []).includes(item.id)).map(t => idLink(t.id, known));
  const mine = (about, direction) => countsFor(data, item.id, about, direction);
  const evidence = ['your users', 'elsewhere'].map(about => WORDS[about] + ': ' + mine(about, 'for') + ' for, ' + mine(about, 'against') + ' against').join('<br>') +
    (checkingOn(data, item.id) ? '<br><span class="muted">' + checkingOn(data, item.id) + ' checking</span>' : '');
  const minutes = item.checker ? ageMin(item.since, ctx.now) : null;
  const importance = item.importance ? cap(item.importance) : '<span class="muted">Not set</span>';
  return '<tr id="row-' + esc(item.id) + '"><td><strong>' + esc(item.id) + '</strong></td>' +
    '<td><span class="first">' + esc(firstSentence(item.text).first) + '</span>' + (item.alternative ? ' ' + chip('Alternative idea') : '') +
    (more.length ? '<details class="more"><summary>More</summary>' + more.join('') + '</details>' : '') + invalidNote(item) + '</td>' +
    '<td>' + importance + '</td>' +
    '<td>' + stateChip(view, { minutes }) + (hasQuestion(ctx.open, item.id) ? ' ' + chip('Question open', 'wait') : '') + '</td>' +
    '<td>' + evidence + '</td>' +
    '<td>' + (settled.length ? settled.join(', ') : '<span class="muted">Nothing yet</span>') + (tests.length ? '<br><span class="muted">Tests: ' + tests.join(', ') + '</span>' : '') + '</td>' +
    '<td>' + link(data, item.rests_on || [], known) + '</td>' +
    '<td><div class="row-actions">' + button('Change', 'data-open-form="change" data-record="' + esc(item.id) + '"') + '</div></td></tr>';
}
function itemsTable(kind, data, ctx) {
  const known = knownIds(data), items = (data.items || []).filter(i => i.kind === kind);
  const label = cap(KIND_NOUN[kind]), what = { problem: 'A problem is something that goes wrong for people. Example: "People lose track of what they checked."',
    opportunity: 'An opportunity is something that could go right. Example: "A weekly digest of what changed."',
    behaviour: 'A behaviour is something the idea does, in a form you can test. Example: "When an item changes, the page shows its new state."' }[kind];
  return '<h2>' + esc(label) + '</h2>' + intro(what) + (items.length ? table(['ID', 'Item', 'Importance', 'State', 'Evidence', 'Settled by', 'Rests on', 'Actions'], items.map(i => itemRow(i, data, ctx, known)), 'items') :
    '<p class="muted">' + (kind === 'opportunity' ? 'No opportunities yet. The draft may not need one.' : 'No ' + KIND_NOUN[kind] + ' yet.') + '</p>');
}

// ---------- Evidence ----------
function evidenceStatus(e, ctx) {
  if (e.status === 'counts') return chip('Counts', 'ok');
  if (e.status === 'checking') {
    if ((ctx.open || []).some(d => (d.about || {}).type === 'evidence' && d.about.evidence === e.id)) return chip('Waiting for your confirmation', 'wait') + '<p class="muted">It does not count until you confirm it.</p>';
    if (!s(e.verifier)) { const m = ageMin(e.at, ctx.now); return chip('Waiting for a verifier' + (m != null ? ', ' + m + ' min' : '')) + '<p class="muted">It does not count until the check passes.</p>'; }
    const m = ageMin(e.since, ctx.now);
    return chip('Checking quote' + (m != null ? ', ' + m + ' min' : ''), 'working') + '<p class="muted">It does not count until the check passes.</p>';
  }
  if (e.status === 'not reachable') return chip('Source not reachable') + '<p class="muted">' + esc(s(e.reason)) + ' It does not count.</p>';
  if (e.status === 'unverified') return chip('Not checked') + '<p class="muted">' + esc(s(e.reason)) + ' It does not count.</p>';
  return chip(s(e.status) || 'Unknown');
}
function evidenceSource(e) {
  const o = e.origin || {};
  if (o.type === 'web') return safeLink(o.url, s(e.source_title) || s(o.url));
  if (o.type === 'file') return 'File ' + esc(s(o.path));
  if (o.type === 'tool') return 'Tool ' + esc(s(o.tool)) + ' ' + esc(s(o.ref));
  if (o.type === 'you') return 'You, ' + (((o.given || {}).type === 'chat') ? 'in the chat' : 'on this page') + (s(e.said_by_role) ? ', ' + esc(e.said_by_role) : '');
  return esc(s(e.source_title) || s(e.source));
}
function evidenceRow(e, data, ctx, known) {
  const chat = (e.origin || {}).type === 'you' && ((e.origin.given || {}).type === 'chat');
  const bears = (e.bears_on || []).map(b => idLink(b.item, known) + ' ' + esc(s(b.direction))).join(', ');
  return '<tr id="row-' + esc(e.id) + '"><td><strong>' + esc(e.id) + '</strong></td>' +
    '<td>' + fold(e.text) + '<br><span class="muted">' + evidenceSource(e) + '</span>' + (chat ? '<br>' + chatMark : '') + invalidNote(e) + '</td>' +
    '<td>' + esc(KINDS[e.kind] || s(e.kind)) + '</td><td>' + evidenceStatus(e, ctx) + ((e.tries || []).length > 1 ? ' <em class="second">second try</em>' : '') + '</td>' +
    '<td>' + (bears || '<span class="muted">Nothing</span>') + '</td>' +
    '<td><div class="row-actions">' + button('Remove…', 'data-open-form="remove" data-record="' + esc(e.id) + '"') + '</div></td></tr>';
}
function evidencePanel(data, ctx) {
  const known = knownIds(data), live = (data.evidence || []).filter(e => e.status !== 'removed');
  const mine = live.filter(e => e.about === 'your users'), other = live.filter(e => e.about !== 'your users');
  const heads = ['ID', 'What you saw or were told', 'Kind', 'State', 'Bears on', 'Actions'];
  const unknown = (data.items || []).filter(i => live.some(e => e.about !== 'your users' && (e.bears_on || []).some(b => b.item === i.id)) &&
    !live.some(e => e.about === 'your users' && (e.bears_on || []).some(b => b.item === i.id)));
  return '<h2>Evidence</h2>' + intro('Evidence is what you saw or were told, and what research found. Example: "Three of five owners re-ran the report by hand."') +
    '<p>' + button('Add evidence…', 'data-open-form="add-evidence"', '') + '</p><div id="slot-add-evidence"></div>' +
    (live.length ? '<h3>About your users</h3>' + (mine.length ? table(heads, mine.map(e => evidenceRow(e, data, ctx, known))) : '<p class="muted">None yet.</p>') +
      '<h3>Not yet known for your users</h3>' + (unknown.length ? '<ul class="plain">' + unknown.map(i => '<li>' + idLink(i.id, known) + ' ' + esc(firstSentence(i.text).first) + '</li>').join('') + '</ul>' : '<p class="muted">Nothing: every item with evidence has some from your users.</p>') +
      '<h3>From elsewhere</h3>' + (other.length ? table(heads, other.map(e => evidenceRow(e, data, ctx, known))) : '<p class="muted">None yet.</p>')
      : '<p class="muted">No evidence yet.</p>');
}

// ---------- Options and the picker ----------
const optionsInOrder = data => (data.options || []).slice().sort((a, z) => MOVES.indexOf(a.move) - MOVES.indexOf(z.move));
function optionNote(o, data, ctx) {
  return (o.note === 'proposed' ? chip('Proposed', 'wait') : o.note ? '<span class="muted">' + esc(cap(s(o.note))) + '</span>' : '') +
    (data.chosen === o.id ? ' ' + chip('Chosen') : '') + (ctx.pending && ctx.pending.option === o.id ? ' ' + chip('Waiting for the agent', 'working') : '');
}
function optionsPanel(data, ctx) {
  const options = optionsInOrder(data);
  return '<h2>Options</h2>' + intro('Your options, by move. Each is one concrete way to go on. Example: "Shrink: owners only."') +
    (options.length ? table(['Move', 'Option', 'Cost', 'Speed', 'Upkeep', 'How hard to undo'], options.map(o => '<tr id="row-' + esc(o.id) + '"><td>' + esc(cap(s(o.move))) + '</td>' +
      '<td><strong>' + esc(s(o.id)) + '</strong> ' + esc(s(o.text)) + '<br>' + optionNote(o, data, ctx) + invalidNote(o) + '</td><td>' + esc(s(o.cost)) + '</td><td>' + esc(s(o.speed)) + '</td><td>' + esc(s(o.upkeep)) + '</td><td>' + esc(s(o.undo)) + '</td></tr>'))
      : '<p class="muted">Options appear once the evidence is in.</p>');
}
function choosePanel(data, ctx) {
  const options = optionsInOrder(data), n = ctx.open.length, pending = ctx.pending;
  const selected = ctx.selected && options.some(o => o.id === ctx.selected) ? ctx.selected : (options.find(o => o.note === 'proposed') || options.find(o => o.note !== 'ruled out by your appetite') || options[0] || {}).id;
  const groups = MOVES.filter(m => options.some(o => o.move === m)).map(m => '<fieldset><legend>' + esc(cap(m)) + '</legend>' + options.filter(o => o.move === m).map(o =>
    '<label class="opt"><input type="radio" name="option" value="' + esc(o.id) + '" data-revision="' + esc(s((data.revisions || {})[o.id])) + '"' + (o.id === selected ? ' checked' : '') + '> <span><b>' + esc(s(o.text)) + '</b> ' + optionNote(o, data, { pending: null }) +
    '<br><span class="muted">Cost ' + esc(s(o.cost)) + ' · speed ' + esc(s(o.speed)) + ' · upkeep ' + esc(s(o.upkeep)) + ' · undo ' + esc(s(o.undo)) + '</span></span></label>').join('') + '</fieldset>').join('');
  const confirms = options.filter(o => CONFIRMED.includes(o.move)).map(o => '<div class="confirm" data-confirm-for="' + esc(o.id) + '" hidden><p><b>' + esc(cap(o.move)) + ' is costly or hard to undo.</b></p>' +
    '<p>Cost: ' + esc(s(o.cost)) + '. How hard to undo: ' + esc(s(o.undo)) + '.</p><div class="row-actions"><button type="button" class="btn btn--sm" data-confirm-choose="' + esc(o.id) + '" data-revision="' + esc(s((data.revisions || {})[o.id])) + '"' + (pending ? ' disabled' : '') + '>Choose ' + esc(cap(o.move)) + '</button>' +
    '<button type="button" class="btn btn--quiet btn--sm" data-cancel-confirm>Cancel</button></div></div>').join('');
  return '<p class="menu-h">Choose a move</p>' +
    '<p class="muted" id="open-line"' + (n ? '' : ' hidden') + '>' + (n === 1 ? '1 question is still open: answer it first, or take its default' : n + ' questions are still open: answer them first, or take their defaults') + '</p>' +
    '<p id="pending-line"' + (pending ? '' : ' hidden') + '>' + chip('Waiting for the agent', 'working') + ' Your choice was sent: the agent writes it down before you can choose again.</p>' +
    (options.length ? '<div class="options">' + groups + '</div>' + confirms +
      '<div class="row-actions pickfoot"><button type="button" class="btn" data-choose' + (pending ? ' disabled' : '') + '>Choose this move</button><button type="button" class="btn btn--quiet" data-cancel-picker>Cancel</button></div>'
      : '<p class="muted">Options appear once the evidence is in.</p>');
}

// ---------- Tests ----------
const RUNNERS = { you: 'you', analyst: 'an analyst', 'code-better': '/code-better' };
function testRow(t, data, ctx, known, when) {
  const running = t.status === 'running' ? chip('Running', 'working') + ' <span class="muted">by ' + esc(RUNNERS[t.runner] || s(t.runner)) + (t.checker ? ', ' + esc(t.checker) : '') + '</span>' : t.status === 'done' ? chip('Done', 'ok') : chip('Planned');
  const result = t.result ? '<p>' + esc(s(t.result.text)) + ' ' + (t.result.outcome === 'changes' ? chip('changes the decision', 'wait') : chip('holds', 'ok')) + '</p>' : '';
  const actions = t.status === 'removed' ? '' : '<div class="row-actions">' + (!t.result ? button('Add result…', 'data-open-form="result" data-record="' + esc(t.id) + '"') : '') +
    button('Remove…', 'data-open-form="remove" data-record="' + esc(t.id) + '"') + (t.status === 'planned' ? button('Change', 'data-open-form="change" data-record="' + esc(t.id) + '"') : '') + '</div>';
  return '<tr id="row-' + esc(t.id) + '"><td>' + esc(when) + '<br>' + running + '</td><td><strong>' + esc(t.id) + '</strong></td><td>' + esc(s(t.what)) + result + invalidNote(t) + '</td><td>' + esc(s(t.rule)) + '</td>' +
    '<td>' + esc(s(t.cost)) + '</td><td>' + link(data, t.settles || [], known) + '</td><td>' + actions + '</td></tr>';
}
function testsPanel(data, ctx) {
  const known = knownIds(data), tests = (data.tests || []).filter(t => t.status !== 'removed'), removed = (data.tests || []).filter(t => t.status === 'removed');
  let first = true;
  const when = t => t.status === 'running' ? 'Now' : t.status === 'done' ? 'Done' : first ? (first = false, 'Next') : 'Later';
  return '<h2>Tests</h2>' + intro('A test is the cheapest way to settle what you do not know yet, run in this order. Example: "Ask five people to find a past check."') +
    (tests.length ? table(['When', 'ID', 'What', 'Stop or change rule', 'Cost', 'Settles', 'Actions'], tests.map(t => testRow(t, data, ctx, known, when(t)))) : '<p class="muted">No tests planned.</p>') +
    (removed.length ? '<h3>Removed tests</h3>' + table(['ID', 'What', 'Why removed'], removed.map(t => '<tr id="row-' + esc(t.id) + '"><td><strong>' + esc(t.id) + '</strong></td><td>' + esc(s(t.what)) + '</td><td>' + esc(s(t.reason)) + '</td></tr>')) : '');
}

// ---------- Brief ----------
const briefBody = b => b.text != null ? '<div class="brief">' + b.text + '</div>' :
  '<p>' + esc(s(b.decision)) + '</p>' + (s(b.why) ? '<p><b>Why:</b> ' + esc(b.why) + '</p>' : '') + ((b.questions || []).length ? '<p><b>Open questions for design</b></p><ul>' + b.questions.map(q => '<li>' + esc(q) + '</li>').join('') + '</ul>' : '');
function briefPanel(data, ctx) {
  const briefs = (data.briefs || []).slice().reverse(), current = briefs[0], earlier = briefs.slice(1);
  const render = b => '<h3 id="row-' + esc(b.id) + '">' + esc(b.id) + ' ' + (b.status === 'final' ? chip('Final', 'ok') : chip('Draft')) + ' <span class="muted">for ' + esc(s(b.move)) + '</span></h3>' + briefBody({ ...b, text: b.text != null ? (ctx.markdown || esc)(b.text) : null });
  const last = lastOf(data.moves || []), writing = last && writesBrief(last, data) && !(data.briefs || []).some(b => b.move === last.id);
  return '<h2>Brief</h2>' + (writing ? '<p>' + chip('being written', 'working') + ' ' + esc(briefLabel(data).split(',')[0]) + ' is being written for ' + idLink(last.id, knownIds(data)) + ' (' + esc(moveName(data, last)) + ').</p>' : '') + intro('The brief is what the discovery hands on to design: the decision, why, and what is still open. Example: "Shrink: owners only, because three of five asked for it."') +
    (current ? render(current) + (earlier.length ? '<details class="more"><summary>Earlier versions (' + earlier.length + ')</summary>' + earlier.map(render).join('') + '</details>' : '')
      : '<p class="muted">No brief yet. A move that writes one adds it here.</p>');
}

// ---------- Moves ----------
function aboutHTML(d, data, known) {
  const about = d.about || {}, item = (data.items || []).find(i => i.id === about.item);
  if (about.type === 'item') return 'About ' + idLink(s(about.item), known) + (item ? ' ' + esc(firstSentence(item.text).first) : '');
  if (about.type === 'risk') { const r = item && (item.risks || []).find(x => x.id === about.risk); return 'About ' + esc(s(about.risk)) + ' of ' + idLink(s(about.item), known) + (r ? ': ' + esc(s(r.text)) : ''); }
  if (about.type === 'option') return 'About ' + idLink(s(about.option), known);
  if (about.type === 'evidence') return 'About ' + idLink(s(about.evidence), known);
  return 'About the whole idea';
}
// The user's answer to a decision: the page's answer event, or the words the coordinator copied from the chat.
function answerOf(d, data) {
  const answer = d.answer || {};
  const event = (data.conversation || []).filter(e => e.type === 'answer' && e.decision === d.id).pop();
  if (answer.type === 'chat') return { text: s(answer.text), chat: true, byDefault: false };
  const e = answer.type === 'page' ? (data.conversation || []).find(x => x.id === (answer.event)) || event : event;
  return e ? { text: s(e.text), chat: false, byDefault: e.default === true } : null;
}
// The evidence a decision is about, so a question such as "Is the result right?" shows what it asks about: its words
// (a command or query and its result) and where they come from.
function evidenceBlock(d, data) {
  const about = d.about || {};
  const e = about.type === 'evidence' ? (data.evidence || []).find(x => x.id === about.evidence) : null;
  return e ? '<blockquote class="evq">' + esc(s(e.text)) + '<br><span class="muted">' + evidenceSource(e) + '</span></blockquote>' : '';
}
function questionRow(d, data, ctx, known) {
  const due = (d.about || {}).type === 'discovery';
  return '<li class="q" id="row-' + esc(d.id) + '" data-d="' + esc(d.id) + '"><div><strong>' + esc(d.id) + '</strong> <span class="muted">' + aboutHTML(d, data, known) + '</span></div>' +
    '<div class="ask">' + fold(d.asked) + '</div>' + evidenceBlock(d, data) + (s(d.default) ? '<p class="muted">Suggested default: ' + esc(d.default) + '</p>' : '') +
    '<div class="row-actions">' + (s(d.default) ? '<button type="button" class="btn btn--sm answer" data-use="' + esc(d.id) + '" aria-label="Use the default for ' + esc(d.id) + '">✓</button>' : '') +
    '<button type="button" class="btn btn--sm btn--quiet" data-answer="' + esc(d.id) + '" aria-label="Answer ' + esc(d.id) + '">Answer</button>' +
    (due ? '<button type="button" class="btn btn--sm" data-open-picker' + (ctx.pending ? ' disabled' : '') + '>Choose a move…</button>' : '') + '</div></li>';
}
function answeredRow(d, data, known) {
  const a = answerOf(d, data);
  return '<li class="q" id="row-' + esc(d.id) + '"><div><strong>' + esc(d.id) + '</strong> <span class="muted">' + aboutHTML(d, data, known) + '</span></div>' +
    '<div class="ask">' + fold(d.asked) + '</div>' + evidenceBlock(d, data) + (a ? '<p>' + (a.byDefault ? 'Default taken: ' : 'Your answer: ') + esc(a.text) + (a.chat ? ' ' + chatMark : '') + (d.status !== 'answered' ? ' <span class="muted">(waiting for the coordinator)</span>' : '') + '</p>' : '') + '</li>';
}
function moveRow(m, data) {
  const o = optionOf(data, m.option), chat = (m.answer || {}).type === 'chat';
  return '<li id="row-' + esc(m.id) + '"><p><strong>Decision at step ' + esc(s(m.step)) + ': ' + esc(moveName(data, m)) + '</strong>' + (o ? ', ' + esc(s(o.text)) : '') + '</p>' +
    '<p>' + esc(s(m.why)) + '</p><p class="muted">Brief: ' + esc(briefFor(data, m)) + (chat ? ' · ' : '') + (chat ? chatMark : '') + '</p></li>';
}
const SETTING_ROWS = [['appetite', 'Appetite', 'Options checks again which moves your appetite rules out.'],
  ['setting', 'Setting', 'Internal or external changes how the page and the brief treat people’s words: Remove… on evidence redacts it in an internal discovery.'],
  ['brought', 'Brought', 'Analysts read only the sources you name here.']];
function movesPanel(data, ctx) {
  const known = knownIds(data), head = data.head || {}, open = ctx.open, openIds = new Set(open.map(d => d.id));
  const answered = (data.decisions || []).filter(d => !openIds.has(d.id));
  const moves = (data.moves || []).slice().reverse(), shown = moves.slice(0, 10), older = moves.slice(10);
  return '<h2>Moves</h2>' + intro('Where the idea stands, what waits for you, and the moves you have made. Example: "Shrink: owners only, because three of five asked for it."') +
    '<h3>The idea</h3><p>' + esc(s(head.idea)) + '</p>' +
    '<h3>Waiting for you</h3>' + (open.length ? '<ul class="qs">' + open.map(d => questionRow(d, data, ctx, known)).join('') + '</ul>' : '<p class="muted">Nothing waits for you.</p>') +
    (ctx.pending ? '<p>' + chip('Waiting for the agent', 'working') + ' You chose ' + idLink(s(ctx.pending.option), known) + '.</p>' : '') +
    (answered.length ? '<h3>Answered</h3><ul class="qs">' + answered.map(d => answeredRow(d, data, known)).join('') + '</ul>' : '') +
    '<h3>Decision log</h3>' + (moves.length ? '<ul class="log">' + shown.map(m => moveRow(m, data)).join('') + '</ul>' +
      (older.length ? '<details class="more"><summary>Earlier moves (' + older.length + ')</summary><ul class="log">' + older.map(m => moveRow(m, data)).join('') + '</ul></details>' : '') : '<p class="muted">No move yet.</p>') +
    '<h3>Setting</h3><table class="tbl settings"><tbody>' + SETTING_ROWS.map(([field, label, note]) => '<tr><th scope="row">' + esc(label) + '</th><td>' + (esc(s(head[field])) || '<span class="muted">Not set</span>') +
      '<p class="muted">' + esc(note) + '</p></td><td><div class="row-actions">' + button('Change', 'data-open-form="change" data-record="discovery" data-field="' + field + '"') + '</div></td></tr>').join('') + '</tbody></table>';
}

// ---------- Forms: one inline form for each act, with labelled fields (the shared .rec) ----------
const field = (id, label, control) => '<label for="' + id + '">' + esc(label) + '</label>' + control;
const form = (kind, record, inner, submit) => '<form class="rec" data-form="' + kind + '" data-record="' + esc(record) + '">' + inner +
  '<div class="row-actions"><button type="submit" class="btn btn--sm">' + esc(submit) + '</button><button type="button" class="btn btn--quiet btn--sm" data-cancel-form>Cancel</button></div></form>';
function addEvidenceForm(data) {
  const items = (data.items || []).map(i => field('bears-' + esc(i.id), i.id + ': ' + firstSentence(i.text).first, '<select id="bears-' + esc(i.id) + '" data-bears="' + esc(i.id) + '"><option value="">Does not bear on it</option>' +
    '<option value="for">Supports it</option><option value="against">Goes against it</option></select>')).join('');
  return form('add-evidence', '', field('ev-text', 'What you saw or were told', '<textarea id="ev-text" required></textarea>') + field('ev-source', 'Where it comes from', '<input id="ev-source" required>') +
    field('ev-kind', 'Kind', '<select id="ev-kind">' + Object.keys(KINDS).map(k => '<option value="' + k + '">' + esc(KINDS[k]) + '</option>').join('') + '</select>') +
    field('ev-about', 'About', '<select id="ev-about"><option value="your users">Your users</option><option value="elsewhere">Elsewhere</option></select>') +
    '<fieldset><legend>What it bears on</legend>' + (items || '<p class="muted">No items yet.</p>') + '</fieldset>', 'Add evidence');
}
function resultForm(test) {
  return form('result', test.id, field('rs-text', 'What the test showed', '<textarea id="rs-text" required></textarea>') +
    '<fieldset><legend>What it means for the decision</legend><label><input type="radio" name="outcome" value="holds" checked> It holds: the decision stands</label>' +
    '<label><input type="radio" name="outcome" value="changes"> It changes the decision</label></fieldset>', 'Add result');
}
function removeForm(record, head) {
  const redact = removeFor(record, head, '').method === 'redact';
  return form('remove', record.id, redact ? '<p>This removes the words from the page and from the briefs. The coordinator closes the page to do it.</p>' :
    field('rm-reason', 'Why remove ' + record.id + '?', '<textarea id="rm-reason" required></textarea>'), 'Remove');
}
const CHANGE_FIELDS = { item: [['text', 'Text'], ['importance', 'Importance (high or lower)']], test: [['what', 'What'], ['rule', 'Stop or change rule'], ['cost', 'Cost']] };
function changeForm(kind, record, fieldName) {
  const label = { appetite: 'Appetite', setting: 'Setting', brought: 'Brought' }[fieldName];
  const choose = fieldName ? '<input type="hidden" id="ch-field" value="' + esc(fieldName) + '">' : field('ch-field', 'What to change', '<select id="ch-field">' + (CHANGE_FIELDS[kind] || []).map(([k, l]) => '<option value="' + k + '">' + esc(l) + '</option>').join('') + '</select>');
  const value = fieldName === 'setting' ? field('ch-value', 'New setting', '<select id="ch-value"><option value="external">External</option><option value="internal">Internal</option></select>') :
    field('ch-value', label ? 'New ' + label.toLowerCase() : 'New value', '<textarea id="ch-value" required></textarea>');
  return form('change', record, choose + value, 'Change');
}

// ---------- Start ----------
const $ = (selector, root) => (root || document).querySelector(selector);
const $$ = (selector, root) => Array.prototype.slice.call((root || document).querySelectorAll(selector));
const byId = id => document.getElementById(id);
const setHTML = (el, html) => { if (el && el._html !== html) { el.innerHTML = html; el._html = html; } };

let DATA = null, TAB = 'moves', DIRTY = false, SENT = null, SELECTED = null, FOCUS_AFTER = null, OFFSET = 0, FAILS = 0;
const nowSec = () => Date.now() / 1000 + OFFSET;
const view = $('.view');
const tabs = $$('.tabs [role="tab"]');
const panel = key => byId('panel-' + key);
const md = text => pageMarkdown(text).outerHTML;

// The text of a brief, without the markers that tie each block of evidence to its id.
const markdown = text => md(s(text).replace(/<!--[^]*?-->\n?/g, ''));

let conv = null, decision = null;
const waitingOf = (c, state) => c.kind === 'decision' ? decision.waiting(c, state) : c.kind === 'note' && state[c.e.id] === 'asked';
const currentOpen = () => openQuestions(DATA.decisions, DATA.conversation);
const ITEM_KINDS = ['note', 'choose', 'add_evidence', 'add_result', 'remove', 'edit', 'redact'];
const threadState = () => pageThread(pageDecisionEvents(DATA.decisions, DATA.conversation), ITEM_KINDS, null).state;
const currentPending = () => {
  const found = pendingChoose(DATA.conversation, threadState(), DATA.moves);
  return found || (SENT && !DATA.moves.some(m => (m.answer || {}).event === SENT.id) && !(DATA.conversation || []).some(e => e.id === SENT.id) ? SENT : null);
};
const formOpen = () => !!($('.rec', view) || $('.why', view) || $('.why', byId('thread')));

// What each of the user's events says in the thread.
function eventText(e) {
  const o = DATA ? optionOf(DATA, e.option) : null;
  switch (e.type) {
    case 'choose': return 'Chose ' + (o ? cap(s(o.move)) + ': ' + s(o.text) : s(e.option)) + (e.confirmed ? ' (confirmed)' : '') + '.';
    case 'add_evidence': return 'Added evidence: ' + s(e.text) + ' (' + s(e.source) + ')';
    case 'add_result': return 'Added a result for ' + s(e.test) + ': ' + s(e.text) + ' (' + (e.outcome === 'changes' ? 'changes the decision' : 'holds') + ')';
    case 'remove': return 'Removed ' + s(e.record) + ': ' + s(e.reason);
    case 'edit': return 'Changed ' + s(e.record) + ', ' + s(e.field) + ': ' + s(e.value);
    case 'redact': return 'Asked to remove the words of ' + s(e.evidence) + '.';
    default: return '';
  }
}
function eventItem(c) {
  const li = document.createElement('li'), head = document.createElement('div'), p = document.createElement('p');
  li.className = 'msg me';
  head.className = 'head';
  head.innerHTML = '<span class="who">You</span><span class="when">' + esc(pageTime(c.e.at)) + '</span>';
  p.textContent = eventText(c.e);
  li.append(head, p);
  return li;
}
const eventKinds = {};
['choose', 'add_evidence', 'add_result', 'remove', 'edit', 'redact'].forEach(name => { eventKinds[name] = eventItem; });

function context() {
  const open = currentOpen();
  return { open, now: nowSec(), pending: currentPending(), selected: SELECTED, markdown, badges: badges(open, DATA.items) };
}

function paint() {
  if (!DATA) return;
  if (formOpen()) { DIRTY = true; return; }
  DIRTY = false;
  const c = context(), data = DATA, kept = focusKey(document.activeElement);
  const head = data.head || {};
  pageShowErrors(byId('errors'), data.errors);
  document.title = 'Discovery: ' + firstSentence(head.idea).first;
  byId('title').textContent = 'Discovery';
  const goal = byId('goal');
  goal.textContent = s(head.idea); goal.hidden = !s(head.idea);
  setHTML(byId('status'), headerHTML(data, c.open));
  setHTML(panel('moves'), movesPanel(data, c));
  KIND_ORDER.forEach(kind => setHTML(panel(KIND_TAB[kind]), itemsTable(kind, data, c)));
  setHTML(panel('evidence'), evidencePanel(data, c));
  setHTML(panel('options'), optionsPanel(data, c));
  setHTML(panel('tests'), testsPanel(data, c));
  setHTML(panel('brief'), briefPanel(data, c));
  setHTML(byId('agents'), atWork(data, c.now));
  if (picker.hidden) setHTML(picker, choosePanel(data, c)); else { syncPicker(c); fitPicker(); }
  tabs.forEach(button => {
    const key = button.id.slice(4), n = c.badges[key] || 0, label = TABS.find(t => t[0] === key)[1];
    button.setAttribute('aria-label', tabLabel(label, n));
    const badge = $('.count', button);
    if (n) { if (badge) badge.textContent = n; else button.insertAdjacentHTML('beforeend', '<span class="count" aria-hidden="true">' + n + '</span>'); } else if (badge) badge.remove();
  });
  pickerButton.disabled = !!c.pending;
  conv.setLog(pageDecisionEvents(data.decisions, data.conversation), [c.open.map(d => d.id), data.revisions]);
  if (FOCUS_AFTER) { const target = $(FOCUS_AFTER); FOCUS_AFTER = null; if (target) target.focus({ preventScroll: true }); }
  else if (kept && (!document.activeElement || document.activeElement === document.body)) { const back = $(kept); if (back) back.focus({ preventScroll: true }); }
}

// Where the focus is, as a selector that finds its copy after a redraw; null when it is not in the board.
const quoted = text => String(text).split('\\').join('\\\\').split('"').join('\\"');
function focusKey(el) {
  if (!el || el === document.body || !view.contains(el)) return null;
  const panelEl = el.closest('[role="tabpanel"]'), scope = panelEl ? '#' + panelEl.id + ' ' : '';
  if (el.id) return '#' + el.id;
  for (const name of ['data-use', 'data-answer', 'data-goto', 'data-open-picker', 'data-open-form']) {
    if (el.hasAttribute(name)) {
      let sel = '[' + name + '="' + quoted(el.getAttribute(name)) + '"]';
      if (name === 'data-open-form') sel += '[data-record="' + quoted(s(el.dataset.record)) + '"]';
      return scope + sel;
    }
  }
  return null;
}
// An open picker is not rebuilt while the user works in it: only what changes live (the open-question line, the wait for
// the agent) is updated in place.
function syncPicker(c) {
  const n = c.open.length, line = $('#open-line', picker), wait = $('#pending-line', picker);
  if (line) { line.hidden = !n; line.textContent = n === 1 ? '1 question is still open: answer it first, or take its default' : n + ' questions are still open: answer them first, or take their defaults'; }
  if (wait) wait.hidden = !c.pending;
  $$('[data-choose], [data-confirm-choose]', picker).forEach(b => { b.disabled = !!c.pending; });
}

function showTab(key) {
  if (!panel(key)) key = 'moves';
  if (key !== TAB) view.scrollTop = 0;
  TAB = key;
  tabs.forEach(button => {
    const on = button.id === 'tab-' + key;
    button.setAttribute('aria-selected', String(on));
    button.tabIndex = on ? 0 : -1;
    panel(button.id.slice(4)).hidden = !on;
  });
}
// Goes to the row an ID names, opens its tab and marks it.
function goto(id) {
  showTab(tabOf(id, DATA));
  $$('.highlighted', view).forEach(r => r.classList.remove('highlighted'));
  const row = byId('row-' + id);
  if (!row) return;
  row.classList.add('highlighted');
  row.tabIndex = -1;
  row.focus({ preventScroll: true });
  row.scrollIntoView({ block: 'center' });
}

// ---------- The picker: Choose a move… ----------
const picker = document.createElement('div'), pickerButton = document.createElement('button');
picker.className = 'decide picker';
picker.id = 'picker';
picker.hidden = true;
pickerButton.type = 'button';
pickerButton.className = 'btn btn--quiet';
pickerButton.id = 'open-picker';
pickerButton.textContent = 'Choose a move…';
pickerButton.setAttribute('aria-controls', 'picker');
pickerButton.setAttribute('aria-expanded', 'false');
function fitPicker() {
  const top = (document.querySelector('header') || { getBoundingClientRect: () => ({ bottom: 0 }) }).getBoundingClientRect().bottom;
  const bottom = byId('noteform').getBoundingClientRect().top;
  picker.style.maxHeight = Math.max(0, bottom - top - 8) + 'px';
}
addEventListener('resize', () => { if (!picker.hidden) fitPicker(); });
function togglePicker(on) {
  picker.hidden = !on;
  if (on) fitPicker();
  pickerButton.setAttribute('aria-expanded', String(on));
  if (on) { const first = $('input[name="option"]:checked', picker) || $('input[name="option"]', picker); if (first) first.focus(); } else pickerButton.focus();
}
function chosenOption() {
  const input = $('input[name="option"]:checked', picker);
  return input ? optionOf(DATA, input.value) : null;
}
function sendChoose(option, revision, confirmed, buttons) {
  const params = chooseParams(option, revision, confirmed);
  buttons.forEach(b => { b.disabled = true; });
  conv.send('choose', params, 'Choice', () => { SENT = Object.assign({ type: 'choose', by: 'user', at: new Date().toISOString().slice(0, 19) + 'Z' }, params); togglePicker(false); paint(); },
    () => buttons.forEach(b => { b.disabled = false; }));
}
picker.addEventListener('change', event => { if (event.target.name === 'option') SELECTED = event.target.value; });
picker.addEventListener('click', event => {
  const target = event.target.closest('button');
  if (!target) return;
  if (target.matches('[data-cancel-picker]')) return togglePicker(false);
  if (target.matches('[data-cancel-confirm]')) { $$('.confirm', picker).forEach(x => { x.hidden = true; }); $('[data-choose]', picker).hidden = false; return; }
  if (target.matches('[data-choose]')) {
    const option = chosenOption();
    if (!option) return;
    if (CONFIRMED.includes(option.move)) {
      const step = $('[data-confirm-for="' + option.id + '"]', picker);
      step.hidden = false; target.hidden = true;
      return $('[data-confirm-choose]', step).focus();
    }
    return sendChoose(option, $('input[name="option"]:checked', picker).dataset.revision, false, [target]);
  }
  if (target.matches('[data-confirm-choose]')) sendChoose(optionOf(DATA, target.dataset.confirmChoose), target.dataset.revision, true, [target]);
});
picker.addEventListener('keydown', event => { if (event.key === 'Escape') { event.preventDefault(); togglePicker(false); } });
pickerButton.addEventListener('click', () => togglePicker(picker.hidden));

// ---------- Forms ----------
function formFor(kind, id, fieldName) {
  const data = DATA;
  if (kind === 'add-evidence') return addEvidenceForm(data);
  if (kind === 'result') return resultForm((data.tests || []).find(t => t.id === id));
  if (kind === 'remove') return removeForm((data.evidence || []).concat(data.tests || []).find(r => r.id === id) || { id }, data.head);
  if (kind === 'change') return changeForm(id === 'discovery' ? '' : /^X/.test(id) ? 'test' : 'item', id, fieldName);
  return '';
}
function closeForm(box, keepFocus) {
  const opener = box._opener;
  (box.closest('tr') && box.closest('tr').classList.contains('formrow') ? box.closest('tr') : box).remove();
  if (opener && !keepFocus && document.contains(opener)) opener.focus();
  if (DIRTY) paint();
}
function openForm(button) {
  const kind = button.dataset.openForm, row = button.closest('tr');
  const open = row && row.nextElementSibling && row.nextElementSibling.classList.contains('formrow') ? row.nextElementSibling : null;
  if (open) return closeForm(open.querySelector('.rec'));
  // One form at a time (no duplicate ids). Remove the others without a repaint, which would detach this row; a pending
  // repaint runs when this form closes.
  $$('.rec', view).forEach(other => { const tr = other.closest('tr.formrow'); (tr || other).remove(); });
  const html = formFor(kind, button.dataset.record, button.dataset.field);
  let box;
  if (kind === 'add-evidence') {
    const slot = byId('slot-add-evidence');
    if (slot.firstChild) return closeForm(slot.firstChild);
    slot.innerHTML = html; box = slot.firstChild;
  } else {
    row.insertAdjacentHTML('afterend', '<tr class="formrow"><td colspan="9">' + html + '</td></tr>');
    box = row.nextElementSibling.querySelector('.rec');
  }
  box._opener = button;
  const first = $('textarea, input:not([type=hidden]), select', box);
  if (first) first.focus();
}
// The event a submitted form sends.
function formEvent(box) {
  const kind = box.dataset.form, record = box.dataset.record, value = id => { const el = $('#' + id, box); return el ? el.value.trim() : ''; };
  if (kind === 'add-evidence') {
    const bears = $$('[data-bears]', box).filter(x => x.value).map(x => ({ item: x.dataset.bears, direction: x.value }));
    return ['add_evidence', { id: uid('a'), text: value('ev-text'), source: value('ev-source'), kind: value('ev-kind'), about: value('ev-about'), bears_on: bears }, 'Evidence'];
  }
  if (kind === 'result') return ['add_result', { id: uid('r'), test: record, text: value('rs-text'), outcome: $('input[name="outcome"]:checked', box).value }, 'Result'];
  if (kind === 'change') return ['edit', { id: uid('h'), record, field: value('ch-field'), value: value('ch-value') }, 'Change'];
  const target = (DATA.evidence || []).concat(DATA.tests || []).find(r => r.id === record) || { id: record };
  const made = removeFor(target, DATA.head, value('rm-reason'));
  return [made.method, Object.assign({ id: uid('m') }, made.params), 'Removal'];
}
view.addEventListener('submit', event => {
  if (!event.target.matches('.rec')) return;
  event.preventDefault();
  const box = event.target, submit = $('[type=submit]', box), [method, params, what] = formEvent(box);
  submit.disabled = true;
  conv.send(method, params, what, () => closeForm(box), () => { submit.disabled = false; });
});
view.addEventListener('keydown', event => {
  const box = event.target.closest && event.target.closest('.rec');
  if (box && event.key === 'Escape') { event.preventDefault(); closeForm(box); return; }
  if (event.target.matches('[role="tab"]')) {
    const i = tabs.indexOf(event.target);
    const next = { ArrowLeft: (i + tabs.length - 1) % tabs.length, ArrowRight: (i + 1) % tabs.length, Home: 0, End: tabs.length - 1 }[event.key];
    if (next !== undefined) { event.preventDefault(); tabs[next].click(); tabs[next].focus(); }
  }
});

// ✓ and Answer act on the same question as in the conversation: the same answer events.
function answerHere(row, id, text, byDefault, done, fail) {
  conv.send('answer', { id: uid('a'), decision: id, text, default: byDefault }, 'Answer', done, fail);
}
view.addEventListener('click', event => {
  const target = event.target.closest('button, a');
  if (!target) return;
  if (target.matches('[role="tab"]')) return showTab(target.id.slice(4));
  if (target.matches('[data-goto]')) { event.preventDefault(); return goto(target.dataset.goto); }
  if (target.matches('[data-open-form]')) return openForm(target);
  if (target.matches('[data-cancel-form]')) return closeForm(target.closest('.rec'));
  if (target.matches('[data-open-picker]')) return togglePicker(true);
  const row = target.closest('li.q');
  if (target.matches('[data-use]') && row) {
    const id = target.dataset.use, next = nextAfter(currentOpen(), id);
    FOCUS_AFTER = next ? 'li.q[data-d="' + next.id + '"] [' + (next.use ? 'data-use' : 'data-answer') + ']' : '#open-picker';
    const d = DATA.decisions.find(x => x.id === id);
    target.disabled = true;
    return answerHere(row, id, s(d && d.default), true, () => tick(), () => { target.disabled = false; FOCUS_AFTER = null; });
  }
  if (target.matches('[data-answer]') && row) {
    return conv.box(row, target.dataset.answer, 'Your answer', target, (text, done) => answerHere(row, target.dataset.answer, text, false, () => { done(); tick(); }));
  }
});
document.addEventListener('keydown', event => { if (event.key === 'Escape' && !picker.hidden && picker.contains(event.target)) togglePicker(false); });

// ---------- Poll ----------
let LAST = '';
function tick() {
  return pageFetch('/data', { cache: 'no-store' }).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }).then(d => {
    FAILS = 0;
    OFFSET = (d.now || Date.now() / 1000) - Date.now() / 1000;
    const key = JSON.stringify(d);
    if (key === LAST && !DIRTY) return;
    LAST = key; DATA = d;
    if (SENT && (d.conversation || []).some(e => e.id === SENT.id)) SENT = null;
    paint();
  }, e => { if (e && e.stale) return; FAILS++; });
}
const waiting = (c, state) => waitingOf(c, state);
conv = pageConversation({
  served: true, stream: false, agent: 'Coordinator', thread: byId('thread'), itemKinds: ITEM_KINDS,
  kinds: eventKinds, steps: ['seen', 'done'], labels: { done: 'Done' }, shown: st => st === 'working' ? 'seen' : st === 'accepted' ? 'done' : st, accept: false,
  waiting, afterSend: () => tick(), busy: formOpen,
});
decision = pageDecision({ conversation: conv, now: nowSec, md, esc, id: uid, suggested: true, next: () => { const open = DATA && currentOpen(); return open && dueMove(open) ? pickerButton : null; } });
eventKinds.decision = (c, state, actions) => {
  const made = decision.item(c, state, actions), block = evidenceBlock(c.e.x, DATA);
  if (block) made[0].querySelector('.head').insertAdjacentHTML('afterend', block);
  return made;
};
(function mount() {
  const noteForm = byId('noteform');
  if (!noteForm) return;
  noteForm.prepend(picker);
  const send = $('.notes .send .btn');
  if (send) send.after(pickerButton);
})();
// A row of the at-work list opens its record's tab and marks its row (A3): the list sits outside the view.
byId('agents').addEventListener('click', event => {
  const button = event.target.closest('[data-goto]');
  if (button) goto(button.dataset.goto);
});
byId('status').addEventListener('click', event => {
  if (!event.target.closest('#questions')) return;
  const first = $('li.open-q', byId('thread'));
  const target = first && ($('.use', first) || $('.answer', first));
  if (target) { first.scrollIntoView({ block: 'nearest' }); target.focus(); }
});
showTab('moves');
conv.start();
tick();
setInterval(() => { if (DATA) paint(); }, 30000);
setInterval(tick, 2000);
