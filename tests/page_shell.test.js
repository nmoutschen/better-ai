// The shared capabilities of src/better_ai/page/page.js: the page config, the decision-question renderer, the approve
// panel, requirement confirmations and the log a page draws. Run with `node --test tests/*.test.js`. The DOM is a
// minimal stand-in: just what these functions touch.
const test = require('node:test');
const assert = require('node:assert/strict');
const { read, loadPage } = require('./harness');
const { panelOn } = require('./dom');

const source = read('page', 'page.js');

class Node {
  constructor(tag) { this.tag = tag; this.className = ''; this.dataset = {}; this.children = []; this.listeners = {}; this.attrs = {}; this.hidden = false; this.textContent = ''; this._html = ''; }
  get classList() { const n = this; return { add(c) { n.className += ' ' + c; } }; }
  set innerHTML(v) { this._html = v; }
  get innerHTML() { return this._html; }
  append(...kids) { this.children.push(...kids); }
  insertAdjacentHTML(_where, html) { this._html += html; }
  addEventListener(type, fn) { this.listeners[type] = fn; }
  setAttribute(k, v) { this.attrs[k] = v; }
  click() { this.listeners.click(); }
  focus() { Node.focused = this; }
  querySelector(sel) { return this.found && this.found[sel] || null; }
}

function load(config) {
  const document = {
    createElement: tag => new Node(tag),
    getElementById: id => id === 'page-config' && config ? { textContent: JSON.stringify(config) } : null,
    get activeElement() { return Node.focused; },
    body: { tag: 'body' },
    contains: () => true,
    querySelectorAll: sel => (load.thread && load.thread[sel]) || [],
  };
  return loadPage({ document, Date, JSON, Object, Math, String, Array, isNaN });
}
const copy = list => Array.from(list);

test('the page reads its role and capabilities from the config the server wrote', () => {
  const page = load({ agent: 'architect', capabilities: ['pins', 'approve'] });
  assert.equal(page.pageRole(), 'architect');
  assert.equal(page.pageCan('approve'), true);
  assert.equal(page.pageCan('confirm'), false);
  const bare = load(null);
  assert.equal(bare.pageRole(), 'agent');
  assert.equal(bare.pageCan('approve'), false);
});

test('approve sends nothing, and builds nothing, on a page that does not declare it', () => {
  const page = load({ agent: 'x', capabilities: ['pins'] });
  assert.equal(page.pageApprove({ button: new Node('button'), panel: new Node('div'), params: () => ({}) }), null);
});

test('the approve panel opens and closes, and sends approve with the page\'s own fields once saved', () => {
  const page = load({ agent: 'x', capabilities: ['approve'] });
  const button = new Node('button'), panel = new Node('div'); panel.hidden = true;
  const approve = page.pageApprove({ button, panel, label: 'Review request', params: () => ({ again: false, text: 'Approved' }) });
  button.click();
  assert.equal(panel.hidden, false);
  assert.equal(button.attrs['aria-expanded'], 'true');
  const sent = [];
  const conversation = { send(method, params, what, done) { sent.push({ method, params, what }); done(); } };
  let finished = false;
  approve.send(conversation, () => { finished = true; });
  assert.equal(sent.length, 1);
  assert.equal(sent[0].method, 'approve');
  assert.equal(sent[0].params.text, 'Approved');
  assert.match(sent[0].params.id, /^approval-/);
  assert.equal(sent[0].what, 'Review request');
  assert.equal(panel.hidden, true);  // closed once saved
  assert.equal(finished, true);
});

test('a refusal leaves the approve panel open', () => {
  const page = load({ agent: 'x', capabilities: ['approve'] });
  const button = new Node('button'), panel = new Node('div');
  const approve = page.pageApprove({ button, panel, params: () => ({}) });
  approve.toggle(true);
  approve.send({ send(m, p, w, done, fail) { fail(); } }, null, () => {});
  assert.equal(panel.hidden, false);
});

test('a confirmation is sent only where the page declares confirm', () => {
  const sent = [];
  const conversation = { send(...args) { sent.push(args); } };
  assert.equal(load({ capabilities: [] }).pageConfirm(conversation, 'R1', 'the wording', 'ok'), false);
  assert.equal(sent.length, 0);
  assert.equal(load({ capabilities: ['confirm'] }).pageConfirm(conversation, 'R1', 'the wording', 'ok'), true);
  assert.equal(sent[0][0], 'confirm');
  assert.equal(sent[0][1].requirement, 'R1');
  assert.equal(sent[0][1].wording, 'the wording');
});

test('decisions enter the log among the events, nothing before what it answers', () => {
  const page = load({});
  const decisions = [{ id: 'D1', at: '2026-11-22T10:00:00Z' }];
  const events = [
    { type: 'answer', id: 'a1', decision: 'D1', at: '2026-11-22T09:00:00Z' },  // a clock that disagrees
    { type: 'note', id: 'm1', at: '2026-11-22T09:30:00Z' },
  ];
  const log = copy(page.pageDecisionEvents(decisions, events));
  assert.deepEqual(log.map(e => e.id), ['m1', 'D1', 'a1']);
});

// ---- the decision question, the same on every page that shows decisions

// The entry the panel gives a decision's renderer: the decision's thread from the one state machine (pageThreads), after
// the conversation LOG.
function entryOf(page, x, log = []) {
  const t = Array.from(page.pageThreads(page.pageDecisionEvents([x], log), ['comment', 'note', 'answer'])).find(t => t.id === x.id);
  return { kind: 'decision', e: t.root, replies: t.messages.slice(1), thread: t };
}
function decision(page, overrides, options) {
  const sent = [], boxes = [];
  const conversation = {
    send(method, params, what, done, fail) { sent.push({ method, params, what }); if (done) done(); },
    box(li, id, label, from, onSend) { boxes.push({ id, label, onSend }); },
  };
  const d = page.pageDecision(Object.assign({
    conversation, now: () => Date.parse('2026-11-22T10:00:00Z') / 1000, md: t => '<p>' + t + '</p>', esc: t => String(t), id: p => p + '-1',
  }, options));
  const x = Object.assign({ id: 'D1', at: '2026-11-22T09:00:00Z', asked: 'Which size?', status: 'waiting', default: 'Take the small one', deadline: '2026-11-22T10:10:00Z' }, overrides);
  const entry = entryOf(page, x);
  return { d, x, entry, sent, boxes, render: (log, actions) => d.item(log ? entryOf(page, x, log) : entry, {}, actions !== false) };
}
const ANSWER = { type: 'answer', id: 'a1', decision: 'D1', text: 'x', default: false, by: 'user', at: '2026-11-22T09:30:00Z' };
const statusOf = (s, read = 1) => ({ type: 'status', to: 'a1', status: s, by: 'coordinator', read, at: '2026-11-22T09:31:00Z' });
const buttons = foot => foot.children.filter(n => n.tag === 'button');

test('a waiting decision shows its question, the default and the deadline, with Use the default and Answer', () => {
  const page = load({ agent: 'coordinator', capabilities: ['decisions'] });
  const t = decision(page);
  const [li, foot] = t.render();
  assert.match(li.innerHTML, /Which size\?/);
  assert.match(li.innerHTML, /If you don&#39;t answer|If you don't answer: Take the small one/);
  assert.match(li.innerHTML, /default in 10 min/);
  assert.match(li.className, /open-q/);
  assert.equal(t.entry.thread.state, 'you');
  assert.doesNotMatch(foot.innerHTML, /progress/);  // the row says the state once; the foot holds the buttons
  assert.deepEqual(buttons(foot).map(b => b.textContent), ['Use the default', 'Answer']);  // D11: the check only closes
});

test('Use the default answers with the default text, marked as the default', () => {
  const t = decision(load({ capabilities: ['decisions'] }));
  const [, foot] = t.render();
  buttons(foot)[0].click();
  assert.equal(t.sent.length, 1);
  assert.equal(t.sent[0].method, 'answer');
  assert.deepEqual(Object.assign({}, t.sent[0].params), { id: 'a-1', decision: 'D1', text: 'Take the small one', default: true });
});

test('Answer opens the reply box and sends the user\'s own words as a non-default answer', () => {
  const t = decision(load({ capabilities: ['decisions'] }));
  const [, foot] = t.render();
  buttons(foot)[1].click();
  assert.equal(t.boxes[0].label, 'Your answer');
  let done = false;
  t.boxes[0].onSend('The large one', () => { done = true; });
  assert.deepEqual(Object.assign({}, t.sent[0].params), { id: 'a-1', decision: 'D1', text: 'The large one', default: false });
  assert.equal(done, true);
});

test('a decision that waits for the work has no default button and no deadline', () => {
  const t = decision(load({ capabilities: ['decisions'] }), { default: null, deadline: null });
  const [li, foot] = t.render();
  assert.deepEqual(buttons(foot).map(b => b.textContent), ['Answer']);
  assert.doesNotMatch(li.innerHTML, /default in|If you don't answer/);
});

test('a deadline that has passed says the default is due', () => {
  const t = decision(load({ capabilities: ['decisions'] }), { deadline: '2026-11-22T09:59:00Z' });
  assert.match(t.render()[0].innerHTML, /default due now/);
});

test('the user\'s answer moves the question on, by its thread: answered, waiting for the agent, then applied', () => {
  const page = load({ agent: 'coordinator', capabilities: ['decisions'] });
  const t = decision(page);
  let [li, foot] = t.render([ANSWER]);
  assert.match(li.innerHTML, /answered, waiting for the coordinator/);
  assert.deepEqual(buttons(foot).map(b => b.textContent), ['Reply']);
  [li, foot] = t.render([ANSWER, statusOf('asked')]);  // the agent asked back: the user's turn again
  assert.match(li.className, /open-q/);
  assert.deepEqual(buttons(foot).map(b => b.textContent), ['Use the default', 'Answer']);  // D11: the check only closes
  const before = { type: 'note', id: 'm0', to: null, text: 'hi', by: 'user', at: '2026-11-22T09:10:00Z' };
  [li] = t.render([before, ANSWER, statusOf('asked', 0)]);  // decided before reading the answer, line 1: changes nothing
  assert.match(li.innerHTML, /answered, waiting for the coordinator/);
  [li] = t.render([ANSWER, statusOf('done')]);
  assert.match(li.innerHTML, /answered by you/);
  const applied = decision(page, { status: 'answered', answer: { type: 'page', event: 'a1' } });
  assert.deepEqual(buttons(applied.render([ANSWER])[1]).map(b => b.textContent), ['Reply']);
});

test('a decision the agent took, or that fell to its default, can be replied to', () => {
  const page = load({ capabilities: ['decisions'] });
  const decided = decision(page, { status: 'decided', decision: 'Use the small one', default: undefined, deadline: undefined });
  const [li, foot] = decided.render();
  assert.match(li.innerHTML, /Decided:/);
  assert.match(li.innerHTML, /Use the small one/);
  assert.deepEqual(buttons(foot).map(b => b.textContent), ['Reply']);
  const defaulted = decision(page, { status: 'defaulted' });
  assert.match(defaulted.render()[0].innerHTML, /decided by the default/);
  assert.match(defaulted.render()[0].innerHTML, /Default applied: Take the small one/);
});

test('a page without actions shows the decision without buttons', () => {
  const t = decision(load({ capabilities: ['decisions'] }));
  assert.deepEqual(buttons(t.render(null, false)[1]), []);
});

// ---- the strips, on every served page

function stripsOn(extra, fetchAnswer, ids = {}, more = {}) {
  const el = (more) => Object.assign({
    value: '', textContent: '', className: '', hidden: false, dataset: {}, style: {},
    classList: { toggle() {}, add() {}, remove() {} }, addEventListener() {}, querySelector() { return el(); },
    querySelectorAll() { return []; }, replaceChildren() {}, append() {}, appendChild() {}, focus() {}, setAttribute() {},
  }, more);
  const els = { '.offline': el({ hidden: true }), '.unwatched': el({ hidden: true }), '#note': el(), '.thread': el(), '.notes .empty': el(),
    '.toast': el({ hidden: true }), '.notes .status': el() };
  const timers = [];
  const globals = {
    document: { querySelector: s => els[s] || el(), querySelectorAll: () => [], getElementById: id => ids[id] || null, contains: () => true },
    Date, JSON, Object, Math, String, Array, isNaN, fetch: (url, init) => fetchAnswer(url, init),
    setTimeout: f => timers.push(f), clearTimeout() {}, requestAnimationFrame: f => f(), ...more,
  };
  const context = loadPage(globals);
  const conversation = context.pageConversation(Object.assign({ served: true, thread: els['.thread'] }, extra));
  conversation.start();
  const flush = () => new Promise(resolve => setImmediate(resolve));
  const round = async () => { await flush(); await flush(); const due = timers.splice(0); due.forEach(f => f()); await flush(); await flush(); };
  return { els, round, conversation, context, flush: async () => { await flush(); await flush(); await flush(); } };
}

test('a page that does not stream shows the not-watching strip when /listening says false', async () => {
  const page = stripsOn({ stream: false }, url => url === '/listening' ? Promise.resolve({ json: () => Promise.resolve(false) }) : Promise.reject(new Error('unexpected ' + url)));
  await page.round();
  assert.equal(page.els['.unwatched'].hidden, false);
  assert.equal(page.els['.offline'].hidden, true);
});

test('a page that does not stream shows the closed strip after two failed fetches, not one', async () => {
  const page = stripsOn({ stream: false }, () => Promise.reject(new Error('down')));
  await page.flush();
  assert.equal(page.els['.offline'].hidden, true);  // once is a blip
  await page.round();
  assert.equal(page.els['.offline'].hidden, false);
});

test('a page that does not stream hides the closed strip again once the server answers', async () => {
  let up = false;
  const page = stripsOn({ stream: false }, () => up ? Promise.resolve({ json: () => Promise.resolve(true) }) : Promise.reject(new Error('down')));
  await page.round(); await page.round();
  assert.equal(page.els['.offline'].hidden, false);
  up = true;
  await page.round();
  assert.equal(page.els['.offline'].hidden, true);
  assert.equal(page.els['.unwatched'].hidden, true);
});

test('an answered decision the agent applied says answered by you and hides the default line', () => {
  const t = decision(load({ agent: 'coordinator', capabilities: ['decisions'] }));
  const [li] = t.render([ANSWER, statusOf('done')]);
  assert.match(li.innerHTML, /answered by you/);
  assert.doesNotMatch(li.innerHTML, /decided/);
  assert.doesNotMatch(li.innerHTML, /If you don't answer/);
});

test('the shared count says how many records are in the format before this change, and hides when there are none', async () => {
  const note = { hidden: true, textContent: '' };
  let count = 3;
  const page = stripsOn({}, url => url === '/old' ? Promise.resolve({ json: () => Promise.resolve(count) })
    : url.startsWith('/events') ? new Promise(() => {}) : Promise.resolve({ json: () => Promise.resolve(null), text: () => Promise.resolve('0') }), { oldnote: note });
  await page.flush();
  assert.equal(note.hidden, false);
  assert.equal(note.textContent, '3 records in the format before this change: kept as is, not converted.');
  count = 1;
  await page.round();
  assert.equal(note.textContent, '1 record in the format before this change: kept as is, not converted.');
  count = 0;
  await page.round();
  assert.equal(note.hidden, true);
  assert.equal(note.textContent, '');
});

test('the research board and the code-better dashboard draw a decision question with the shared renderer, and neither has its own', () => {
  for (const rel of ['research/board.js', 'code/dashboard.js']) {
    const text = read(...rel.split('/'));
    assert.match(text, /pageDecision\(\{/, rel + ' does not call pageDecision');
    assert.doesNotMatch(text, /['"`]Use the default['"`]/, rel + ' words the default button itself');
  }
  assert.match(source, /Use the default/);
});

// ---- the question footer, the accessible names and the focus (every page), and the suggested default (a page's option)

test('the question footer is an outlined check and a filled Answer on one row, and each control names the question', () => {
  // The user's rule c13 (.design/conversation-panel/brief.md): Answer is the one filled button, the check is outlined.
  const t = decision(load({ capabilities: ['decisions'] }));
  const [, foot] = t.render();
  const [use, answer] = buttons(foot);
  assert.match(use.className, /btn--sm/);
  assert.match(use.className, /btn--quiet/);
  assert.doesNotMatch(answer.className, /btn--quiet/);
  assert.match(foot.className, /\bquestion\b/);  // page.css keeps this footer on one row
  assert.equal(use.attrs['aria-label'], 'Use the default for: Which size?');
  assert.equal(answer.attrs['aria-label'], 'Answer: Which size?');
  const applied = decision(load({ capabilities: ['decisions'] }), { status: 'decided', decision: 'Small' });
  assert.equal(buttons(applied.render()[1])[0].attrs['aria-label'], 'Reply to: Which size?');
});

test('a page that sets suggested shows Suggested default and never a deadline or "If you don\'t answer"', () => {
  const page = load({ capabilities: ['decisions'] });
  const t = decision(page, { deadline: '2026-11-22T10:10:00Z' }, { suggested: true });
  const [li, foot] = t.render();
  assert.match(li.innerHTML, /Suggested default: Take the small one/);
  assert.doesNotMatch(li.innerHTML, /default in|default due|If you don&#39;t answer|If you don't answer/);
  assert.deepEqual(buttons(foot).map(b => b.textContent), ['Use the default', 'Answer']);  // D11: the check only closes
  const late = decision(page, { deadline: '2026-11-22T09:00:00Z' }, { suggested: true });
  assert.doesNotMatch(late.render()[0].innerHTML, /due now/);
});

function questions(page, ids) {
  // Rendered questions in a thread: the stand-in document lists them, as page.js finds them in the page.
  const items = ids.map(id => {
    const t = decision(page, { id });
    const [li, foot] = t.render();
    li.dataset.d = id;
    li.found = { '.use': buttons(foot)[0], '.answer': buttons(foot)[1] };
    return { t, li, use: buttons(foot)[0], foot };
  });
  load.thread = { 'li.open-q': items.map(i => i.li), 'li[data-state="asked"]': items.map(i => i.li) };
  return items;
}

test('after the check, the focus moves to the next open question, then to the next thing that waits', async () => {
  const page = load({ capabilities: ['decisions'] });
  const items = questions(page, ['D1', 'D2']);
  Node.focused = null;
  items[0].use.click();
  assert.equal(Node.focused, items[1].use);
  load.thread['li.open-q'] = [items[1].li];
  load.thread['li[data-state="asked"]'] = [items[1].li];
  items[1].use.click();  // the last question: nothing else waits, the focus stays where it is
  assert.equal(Node.focused, items[1].use);
  const note = new Node('li'); note.dataset.state = 'asked'; note.dataset.id = 'M1';
  load.thread['li[data-state="asked"]'] = [items[1].li, note];
  items[1].use.click();
  assert.equal(Node.focused, note);
  const move = new Node('button');
  const withMove = decision(page, { id: 'D9' }, { next: () => move });
  const [, f9] = withMove.render();
  load.thread = {};
  Node.focused = buttons(f9)[0];
  buttons(f9)[0].click();
  assert.equal(Node.focused, move);  // the page's own next thing, such as a move that is due
  load.thread = null;
});

test('when the redraw replaces the next question after the check, its new check takes the focus', async () => {
  const page = load({ capabilities: ['decisions'] });
  const items = questions(page, ['D1', 'D2']);
  Node.focused = items[0].use;
  items[0].use.click();
  const [, foot] = items[0].t.d.item(items[1].t.entry, {}, true);  // one pageDecision draws every question of a page: the thread redraws the question
  Node.focused = null;
  await Promise.resolve(); await Promise.resolve();
  assert.equal(Node.focused, buttons(foot)[0]);
  load.thread = null;
});

// The decision records the code-better dashboard and the research board draw, as their schemas have them. A page that
// does not set `suggested` draws them as it always did: the deadline, "If you don't answer" and the default.
test('code-better and research-better decisions render as before, with the deadline and "If you don\'t answer"', () => {
  const page = load({ agent: 'coordinator', capabilities: ['decisions'] });
  const fixtures = [
    { id: 'D1', at: '2026-11-22T09:00:00Z', asked: 'Keep the old endpoint?', status: 'waiting', default: 'Keep it', deadline: '2026-11-22T10:20:00Z' },
    { id: 'Q-3', at: '2026-11-22T09:00:00Z', asked: 'Which source first?', status: 'waiting', default: 'The survey', deadline: '2026-11-22T10:01:00Z' },
    { id: 'D2', at: '2026-11-22T09:00:00Z', asked: 'Wait for the audit?', status: 'waiting', default: 'No', deadline: '2026-11-22T09:30:00Z' },
  ];
  const seen = fixtures.map(x => decision(page, x, {}).render()[0].innerHTML);
  assert.match(seen[0], /default in 20 min/);
  assert.match(seen[1], /default in under 2 min/);
  assert.match(seen[2], /default due now/);
  seen.forEach(html => { assert.match(html, /If you don(&#39;|')t answer: /); assert.doesNotMatch(html, /Suggested default/); });
});

// The thread can be redrawn before `done` runs (a page that is not served redraws in send; a served one by its poll): the
// answered question is then gone, and the target must come from what the click saw.
test('after the check on the middle of three questions, the focus goes to the third, though the thread redrew first', () => {
  const page = load({ capabilities: ['decisions'] });
  let rows = [];
  const conversation = { box() {},
    send(m, p, w, done) { load.thread['li.open-q'] = [rows[0].n, rows[2].n]; done(); } };
  const d = page.pageDecision({ conversation, now: () => 0, md: t => t, esc: String, id: p => p + '-1' });
  rows = ['D1', 'D2', 'D3'].map(id => {
    const [n, foot] = d.item(entryOf(page, { id, at: '2026-11-22T09:00:00Z', asked: 'Q ' + id, status: 'waiting', default: 'x' }), {}, true);
    n.dataset.d = id; n.found = { '.use': buttons(foot)[0], '.answer': buttons(foot)[1] };
    return { n, use: buttons(foot)[0] };
  });
  load.thread = { 'li.open-q': rows.map(r => r.n) };
  Node.focused = null;
  rows[1].use.click();
  assert.equal(Node.focused, rows[2].use);
  load.thread = null;
});

test('a later redraw does not take the focus from where the user went', async () => {
  const page = load({ capabilities: ['decisions'] });
  const items = questions(page, ['D1', 'D2']);
  items[0].use.click();
  const composer = new Node('textarea');
  Node.focused = composer;
  const [, foot] = items[0].t.d.item(items[1].t.entry, {}, true);
  await Promise.resolve(); await Promise.resolve();
  assert.equal(Node.focused, composer);
  load.thread = null;
});

// ---- the page token

const fragment = (hash, stored) => {
  const kept = { ...(stored ? { pageToken: stored } : {}) }, replaced = [];
  return { kept, replaced, globals: {
    location: { hash, pathname: '/', search: '' },
    history: { replaceState: (...args) => replaced.push(args[2]) },
    sessionStorage: { getItem: k => kept[k] ?? null, setItem: (k, v) => { kept[k] = v; }, removeItem: k => { delete kept[k]; } },
  } };
};
const answerWith = value => Promise.resolve({ status: 200, ok: true, json: () => Promise.resolve(value) });
const answer = status => Promise.resolve({ status, ok: status < 400, json: () => Promise.resolve({ total: 0, events: [] }), text: () => Promise.resolve('0') });

test('every request to the server carries the token the opened address gave in its fragment, and the fragment goes', async () => {
  const seen = [], where = fragment('#t=abc_DEF-123');
  const page = stripsOn({}, (url, init) => { seen.push({ url, init }); return url.startsWith('/events') ? new Promise(() => {}) : answer(200); }, {}, where.globals);
  await page.flush();
  const asked = seen.filter(r => r.url === '/data' || r.url.startsWith('/events'));
  assert.ok(asked.length > 0);
  for (const r of asked) assert.equal(r.init.headers['X-Page-Token'], 'abc_DEF-123', r.url);
  assert.deepEqual(where.replaced, ['/']);  // the token is not left in the address bar
  assert.equal(where.kept.pageToken, 'abc_DEF-123');  // a reload of the page keeps it
  await page.context.pageFetch('/data');
  assert.equal(seen.at(-1).init.headers['X-Page-Token'], 'abc_DEF-123');
});

test('a reloaded page, with no fragment left, sends the token it kept', async () => {
  const seen = [], where = fragment('', 'kept-token');
  const page = stripsOn({}, (url, init) => { seen.push(init); return url.startsWith('/events') ? new Promise(() => {}) : answer(200); }, {}, where.globals);
  await page.context.pageFetch('/data');
  assert.equal(seen.at(-1).headers['X-Page-Token'], 'kept-token');
  assert.deepEqual(where.replaced, []);
});

test('a message the page sends goes with the token, and a refusal as out of date is shown and keeps the typed text', async () => {
  const sent = [], where = fragment('#t=tok');
  let finished = false, failed = false;
  const page = stripsOn({}, (url, init) => {
    sent.push({ url, init });
    if (url === '/rpc') return Promise.resolve({ status: 200, ok: true, json: () => Promise.resolve({ error: { code: -32001, message: 'page out of date: open the address the agent gave' } }) });
    return url.startsWith('/events') ? new Promise(() => {}) : answer(200);
  }, {}, where.globals);
  page.conversation.send('note', { id: 'm1', text: 'my long answer', to: null }, 'Reply', () => { finished = true; }, () => { failed = true; });
  await page.flush();
  assert.equal(sent.find(r => r.url === '/rpc').init.headers['X-Page-Token'], 'tok');
  assert.equal(finished, false);  // done is what clears the typed text: it is not called
  assert.equal(failed, true);
  assert.equal(page.els['.toast'].textContent, 'Not sent: reply. page out of date: open the address the agent gave');
  assert.equal(page.els['.notes .status'].textContent, 'Not sent: page out of date: open the address the agent gave');
  assert.equal(page.els['.offline'].textContent, 'page out of date: open the address the agent gave');
  assert.equal(page.els['.offline'].hidden, false);
  assert.equal(where.kept.pageToken, undefined);  // the saved token is dropped: a reload never fixes it
});

test('a read the server answers as out of date shows that on the page, and the stream does not retry', async () => {
  let events = 0;
  const where = fragment('#t=old');
  const page = stripsOn({}, url => {
    if (url.startsWith('/events')) { events++; return events > 20 ? new Promise(() => {}) : answer(401); }
    return answer(200);
  }, {}, where.globals);
  await page.round(); await page.round();
  assert.equal(events, 1);
  assert.equal(page.els['.offline'].hidden, false);
  assert.equal(page.els['.offline'].textContent, 'page out of date: open the address the agent gave');
  assert.equal(where.kept.pageToken, undefined);  // the token it saved is dropped
});

test('a stale page stops all polling and cannot reload for an in-flight server revision', async () => {
  const where = fragment('#t=old'), sent = [];
  let reloads = 0, revisions = 0, nextRevision;
  where.globals.location.reload = () => { reloads++; };
  const page = stripsOn({}, url => {
    sent.push(url);
    if (url === '/data') return answer(401);
    if (url.startsWith('/events')) return new Promise(() => {});
    if (url === '/rev' && ++revisions === 2) return new Promise(resolve => { nextRevision = resolve; });
    return answer(200);
  }, {}, where.globals);
  await page.round();
  assert.equal(revisions, 2);
  await assert.rejects(page.context.pageFetch('/data'), { stale: true });
  const atRefusal = sent.slice();
  nextRevision({ status: 200, text: () => Promise.resolve('new revision') });
  await page.round();
  await page.round();
  assert.deepEqual(sent, atRefusal);
  assert.equal(reloads, 0);
});

test('the design canvas shows only the out of date message when its data is refused for the token', async () => {
  const where = fragment('#t=old'), problem = { textContent: '', hidden: true };
  const strip = { textContent: '', hidden: true };
  const document = { querySelector: s => s === '.offline' ? strip : null, getElementById: id => id === 'canvas-problem' ? problem : null };
  const context = loadPage({ document, Date, JSON, Object, Math, String, Array, isNaN, fetch: () => answer(401), ...where.globals });
  const vm = require('node:vm');
  vm.runInNewContext(read('design', 'canvas.js'), Object.assign(context, { document }));
  await new Promise(resolve => setImmediate(resolve)); await new Promise(resolve => setImmediate(resolve));
  assert.equal(strip.textContent, 'page out of date: open the address the agent gave');
  assert.equal(problem.hidden, true);  // not also "could not load its versions"
  assert.equal(problem.textContent, '');
});

function unreadableCanvas(revision) {
  const where = fragment('#t=old'), elements = { 'canvas-problem': { hidden: true }, status: {}, title: {} };
  const strip = { hidden: true }, sent = [], timers = [];
  let loads = 0, reloads = 0;
  where.globals.location.reload = () => { reloads++; };
  const document = { querySelector: s => s === '.offline' ? strip : null, getElementById: id => elements[id] || null };
  const context = loadPage({ document, setTimeout: run => timers.push(run), fetch: url => {
    sent.push(url);
    return url === '/data' ? ++loads === 1 ? answerWith({ error: 'A version cannot be read' }) : answer(401) : revision();
  }, ...where.globals });
  require('node:vm').runInNewContext(read('design', 'canvas.js'), context);
  const flush = () => new Promise(resolve => setImmediate(resolve));
  return { context, sent, flush, strip, problem: elements['canvas-problem'], reloads: () => reloads,
    round: async () => { timers.splice(0).forEach(run => run()); await flush(); } };
}

test('an unreadable design canvas reloads when the agent fixes a version', async () => {
  let revision = 'unreadable';
  const canvas = unreadableCanvas(() => Promise.resolve({ status: 200, text: () => Promise.resolve(revision) }));
  await canvas.flush();
  assert.equal(canvas.problem.textContent, 'A version cannot be read');
  await canvas.round();
  assert.equal(canvas.reloads(), 0);
  revision = 'fixed';
  await canvas.round();
  assert.equal(canvas.reloads(), 1);
});

test('an unreadable design canvas stops recovery polling and ignores pending revisions after token refusal', async () => {
  let revisions = 0, nextRevision;
  const canvas = unreadableCanvas(() => ++revisions === 1 ? answer(200) : new Promise(resolve => { nextRevision = resolve; }));
  await canvas.flush();
  await canvas.round();
  assert.equal(revisions, 2);
  await assert.rejects(canvas.context.pageFetch('/data'), { stale: true });
  const atRefusal = canvas.sent.slice();
  nextRevision({ status: 200, text: () => Promise.resolve('agent fixed it') });
  await canvas.flush();
  await canvas.round();
  assert.deepEqual(canvas.sent, atRefusal);
  assert.equal(canvas.reloads(), 0);
  assert.equal(canvas.strip.hidden, false);
});

test('a page that does not stream stays out of date once any request was refused, whatever /listening says later', async () => {
  const where = fragment('#t=old');
  const page = stripsOn({ stream: false }, url => url === '/listening' ? answerWith(true) : answer(401), {}, where.globals);
  await page.context.pageFetch('/data').catch(() => {});
  await page.round(); await page.round();
  assert.equal(page.els['.offline'].hidden, false);
  assert.equal(page.els['.offline'].textContent, 'page out of date: open the address the agent gave');
});

test('a page out of date shows only the out of date strip: /listening goes through pageFetch, and the not-watching note stays hidden', async () => {
  const where = fragment('#t=old'), sent = [];
  const page = stripsOn({ stream: false }, (url, init) => { sent.push([url, ((init || {}).headers || {})['X-Page-Token']]);
    return url === '/listening' ? answerWith(false) : answer(401); }, {}, where.globals);
  await page.round();
  assert.deepEqual(sent.find(x => x[0] === '/listening'), ['/listening', 'old']);  // with the token, as every request of the page
  await page.context.pageFetch('/data').catch(() => {});
  await page.round(); await page.round();
  assert.equal(page.els['.unwatched'].hidden, true);
  assert.equal(page.els['.offline'].hidden, false);
  assert.equal(page.els['.offline'].textContent, 'page out of date: open the address the agent gave');
});

// ---- the focus after the check, when the send takes time

// A conversation whose send does not finish until the test says so.
function slowRows(page, ids, options) {
  const finish = [];
  const conversation = { box() {}, send(m, p, w, done) { finish.push(done); } };
  const d = page.pageDecision(Object.assign({ conversation, now: () => 0, md: t => t, esc: String, id: p => p + '-1' }, options));
  const draw = id => {
    const [n, foot] = d.item(entryOf(page, { id, at: '2026-11-22T09:00:00Z', asked: 'Q ' + id, status: 'waiting', default: 'x' }), {}, true);
    n.dataset.d = id; n.found = { '.use': buttons(foot)[0], '.answer': buttons(foot)[1] };
    return { n, use: buttons(foot)[0] };
  };
  return { finish, draw };
}

test('the check does not take the focus when the user moved it during the send', () => {
  const page = load({ capabilities: ['decisions'] });
  const { finish, draw } = slowRows(page);
  const rows = ['D1', 'D2'].map(draw);
  load.thread = { 'li.open-q': rows.map(r => r.n) };
  Node.focused = rows[0].use;
  rows[0].use.click();
  const composer = new Node('textarea');
  Node.focused = composer;  // the user went to the message box while the answer was on its way
  finish[0]();
  assert.equal(Node.focused, composer);
  load.thread = null;
});

test('the check moves the focus on when it is still on the clicked button, or nowhere', () => {
  const page = load({ capabilities: ['decisions'] });
  const { finish, draw } = slowRows(page);
  const rows = ['D1', 'D2'].map(draw);
  load.thread = { 'li.open-q': rows.map(r => r.n) };
  Node.focused = rows[0].use;
  rows[0].use.click();
  finish[0]();
  assert.equal(Node.focused, rows[1].use);
  Node.focused = null;
  rows[0].use.click();
  finish[1]();
  assert.equal(Node.focused, rows[1].use);
  load.thread = null;
});

test('what the page says waits next is asked at focus time, not held from before a redraw', () => {
  const page = load({ capabilities: ['decisions'] });
  const before = new Node('button'), after = new Node('button');
  let current = before;
  const { finish, draw } = slowRows(page, [], { next: () => current });
  const row = draw('D1');
  load.thread = { 'li.open-q': [row.n] };
  Node.focused = row.use;
  row.use.click();
  current = after;  // the redraw replaced the element
  finish[0]();
  assert.equal(Node.focused, after);
  load.thread = null;
});

test('another item the agent asked about is found again by its id after a redraw', () => {
  const page = load({ capabilities: ['decisions'] });
  const { finish, draw } = slowRows(page);
  const row = draw('D1');
  const old = new Node('li'); old.dataset.id = 'M7'; old.dataset.state = 'asked';
  load.thread = { 'li.open-q': [row.n], 'li[data-state="asked"]': [old] };
  Node.focused = row.use;
  row.use.click();
  const redrawn = new Node('li'); redrawn.dataset.id = 'M7'; redrawn.dataset.state = 'asked';
  load.thread = { 'li.open-q': [], 'li[data-state="asked"]': [redrawn] };
  finish[0]();
  assert.equal(Node.focused, redrawn);
  load.thread = null;
});

test('the accessible names of a question carry its words without Markdown marks', () => {
  const t = decision(load({ capabilities: ['decisions'] }), { asked: 'Which **size** of `box`, see [the guide](http://x)?' });
  const [use, answer] = buttons(t.render()[1]);
  assert.equal(use.attrs['aria-label'], 'Use the default for: Which size of box, see the guide?');
  assert.equal(answer.attrs['aria-label'], 'Answer: Which size of box, see the guide?');
});

// ---- the Conversation panel: one row per thread (.design/conversation-panel/design.md, S11-S23)
// pageConversation runs on a small stand-in DOM: elements keep their children, attributes, listeners and focus, and
// answer the simple selectors page.js uses (tag, .class, #id, [attr], [attr="v"], and one space between parts).

const HOUR = 3600 * 1000;
const at = hoursAgo => new Date(Date.now() - hoursAgo * HOUR).toISOString().slice(0, 19) + 'Z';
// A panel on the stand-in shell, not served: what it sends goes to its own log, as on a page opened from a file.
const panel = (log, extra, options) => panelOn(log, extra, options);
const userNote = (id, text, h, more = {}) => Object.assign({ type: 'note', id, text, to: null, by: 'user', at: at(h) }, more);
const agentReply = (id, to, text, h) => ({ type: 'reply', id, to, text, by: 'coordinator', at: at(h) });
const status = (to, s, h, read) => Object.assign({ type: 'status', to, status: s, by: 'coordinator', at: at(h) }, read == null ? {} : { read });
// One thread in each state: your turn, the agent's turn not seen, seen and working, done by the agent, closed by you.
const EVERY_STATE = [
  userNote('m1', 'Can we merge this into the board start? It would save a step.', 10),
  agentReply('r1', 'm1', 'Yes. Shall I?', 9.5), status('m1', 'asked', 9.5),
  userNote('m2', 'How about AG-UI?', 8),
  userNote('m3', 'Q3 exactly once delivery semantics are hard to achieve.', 7), status('m3', 'seen', 6),
  userNote('m4', 'Check the schema.', 5), status('m4', 'working', 4),
  userNote('m5', "What's next?", 3), agentReply('r5', 'm5', 'Step 4.', 2), status('m5', 'done', 2),
  userNote('m6', 'Old question.', 30), status('m6', 'done', 29), { type: 'accept', to: 'm6', by: 'user', at: at(28) },
];
const text = n => n.textContent.replace(/\s+/g, ' ').trim();
const actions = li => li.querySelectorAll('.tacts button');

test('S11 each thread is one row: its state, who started it and its first sentence, the triangle, the count and its buttons', () => {
  const p = panel(EVERY_STATE);
  p.filter('all');
  const you = p.rowOf('m1'), seen = p.rowOf('m3'), working = p.rowOf('m4'), done = p.rowOf('m5'), fresh = p.rowOf('m2');
  assert.equal(text(you.querySelector('.chip')), 'Your turn');
  assert.match(text(you.querySelector('.tage')), /^Waiting, 10 h$/);
  assert.equal(you.querySelector('.progress'), null);
  assert.equal(text(you.querySelector('.tgist')), 'You: Can we merge this into the board start?');
  assert.equal(text(fresh.querySelector('.chip')), 'Agent’s turn');
  assert.equal(text(fresh.querySelector('.progress')), 'Not seen, 8 h');
  assert.equal(fresh.querySelectorAll('.progress .bars i.on').length, 0);
  assert.equal(text(seen.querySelector('.progress')), 'Seen, 6 h');
  assert.equal(seen.querySelectorAll('.progress .bars i.on').length, 1);
  assert.equal(text(working.querySelector('.progress')), 'Working, 4 h');
  assert.equal(working.querySelectorAll('.progress .bars i.on').length, 2);
  assert.equal(done.querySelector('.chip'), null);  // a done row has no step and no turn: its bars say it
  assert.equal(text(done.querySelector('.progress')), 'Done, 2 h');
  assert.equal(done.querySelectorAll('.progress.done .bars i.on').length, 3);
  assert.equal(done.querySelectorAll('.progress .bars i').length, 3);
  // The triangle is drawn: points down while folded.
  assert.match(you.querySelector('.tfold').innerHTML, /<polygon points="0,0 16,0 8,13.86"/);
  assert.match(text(done.querySelector('.tmeta')), /^2 messages, last \d+ \w{3}, \d\d:\d\d$/);
  assert.match(text(fresh.querySelector('.tmeta')), /^1 message, last /);
  const words = li => actions(li).map(b => b.textContent);
  assert.deepEqual(words(you), ['✓', 'Answer']);
  assert.deepEqual(words(fresh), ['✓', 'Reply']);
  assert.deepEqual(words(working), ['✓', 'Reply']);
  assert.deepEqual(words(done), ['✓', 'Reopen']);
  assert.deepEqual(words(p.rowOf('m6')), ['Reopen']);
  // The edge colour follows the state.
  assert.deepEqual(['m1', 'm2', 'm3', 'm4', 'm5', 'm6'].map(id => p.rowOf(id).dataset.state), ['asked', 'seen', 'seen', 'working', 'done', 'done']);
});

test('S11 a thread the agent started says Agent: (its name) and a deleted comment shows no row', () => {
  const p = panel([
    { type: 'reply', id: 'r9', to: null, text: 'Spec check 1 found 16 gaps. Details below.', by: 'coordinator', at: at(1) },
    { type: 'comment', id: 'c1', n: 1, text: 'gone', on: {}, by: 'user', at: at(1) }, { type: 'delete', to: 'c1', by: 'user', at: at(1) },
  ], { crumb: () => null, commentBody: () => null });
  assert.deepEqual(p.rows().map(li => li.dataset.id), ['r9']);
  assert.equal(text(p.rowOf('r9').querySelector('.tgist')), 'Coordinator: Spec check 1 found 16 gaps.');
});

test('S12 the head is one native button that opens and folds the thread, and keeps the focus', () => {
  const p = panel(EVERY_STATE);
  const head = p.rowOf('m5').querySelector('.thead');
  assert.equal(head.tagName, 'BUTTON');
  assert.equal(head.type, 'button');  // Enter and Space press a native button
  assert.equal(head.getAttribute('aria-expanded'), 'false');
  head.focus();
  head.click();
  const opened = p.rowOf('m5').querySelector('.thead');
  assert.equal(opened.getAttribute('aria-expanded'), 'true');
  assert.equal(p.document.activeElement, opened);
  assert.match(opened.querySelector('.tfold').innerHTML, /<polygon points="0,13.86 8,0 16,13.86"/);
  assert.ok(p.rowOf('m5').querySelector('.tbody'));
  opened.click();
  const folded = p.rowOf('m5').querySelector('.thead');
  assert.equal(folded.getAttribute('aria-expanded'), 'false');
  assert.equal(p.rowOf('m5').querySelector('.tbody'), null);
  assert.equal(p.document.activeElement, folded);
});

test('S13 an open thread shows its messages flat across the row: yours on white, the agent\'s on linen, no box inside', () => {
  const p = panel(EVERY_STATE);
  p.rowOf('m5').querySelector('.thead').click();
  const body = p.rowOf('m5').querySelector('.tbody');
  assert.deepEqual(body.children.map(m => m.className), ['tmsg mine', 'tmsg agent']);
  assert.equal(body.querySelectorAll('li').length, 0);
  assert.equal(text(body.children[0].querySelector('.who')), 'You');
  assert.equal(text(body.children[1].querySelector('.who')), 'Coordinator');
  assert.match(text(body.children[1]), /Step 4\./);
  assert.equal(p.rowOf('m5').querySelector('.tgist'), null);  // open, the first message shows in full below
});

test('S14 Open lists done, then the agent\'s turn, then your turn last; All lists every thread in time order; both count', () => {
  const p = panel(EVERY_STATE);
  assert.deepEqual(p.rows().map(li => li.dataset.id), ['m5', 'm2', 'm3', 'm4', 'm1']);
  assert.equal(p.$('[data-filter="open"]').textContent, 'Open (5)');
  assert.equal(p.$('[data-filter="all"]').textContent, 'All (6)');
  p.filter('all');
  assert.deepEqual(p.rows().map(li => li.dataset.id), ['m1', 'm2', 'm3', 'm4', 'm5', 'm6']);
  assert.equal(p.$('[data-filter="all"]').getAttribute('aria-pressed'), 'true');
});

test('S14 with every thread closed, Open says nothing is open', () => {
  const p = panel([userNote('m1', 'x', 2), { type: 'accept', to: 'm1', by: 'user', at: at(1) }]);
  assert.equal(p.rows().length, 0);
  assert.equal(text(p.$('.thread li.sys')), 'Nothing open: every thread is done and closed.');
  assert.equal(p.$('.notes .empty').hidden, true);
  assert.equal(panel([]).$('.notes .empty').hidden, false);
});

test('S15 the list opens on its end, and a button says how many rows are above the view and goes to them', () => {
  const p = panel(null);
  const list = p.$('.thread');
  list.scrollHeight = 900; list.clientHeight = 300;
  p.conv.setLog(EVERY_STATE);
  assert.equal(list.scrollTop, 900);
  list.rect = { top: 100 };
  p.rows().forEach((li, k) => { li.rect = { top: 100 + k * 150 - 600 }; });
  list.dispatch('scroll');
  const cue = p.$('.tabove');
  assert.equal(cue.hidden, false);
  assert.equal(cue.textContent, '▲ 4 more threads above');
  cue.click();
  assert.equal(list.scrolledTo.top, 0);
  p.rows().forEach(li => { li.rect = { top: 200 }; });
  list.dispatch('scroll');
  assert.equal(cue.hidden, true);
});

test('S16 the top bar says how many threads are your turn, and takes you to the first one\'s Answer', () => {
  const log = EVERY_STATE.concat([agentReply('r2', 'm2', 'Which part?', 1), status('m2', 'asked', 1)]);
  const p = panel(log);
  const fig = p.$('#status button.stat');
  assert.ok(fig);
  assert.equal(text(fig), '2 your turn');
  assert.equal(text(fig.querySelector('b')), '2');
  assert.doesNotMatch(text(p.$('#status')), /Loading/);
  p.filter('all');
  fig.click();
  assert.equal(p.$('[data-filter="open"]').getAttribute('aria-pressed'), 'true');
  const focused = p.document.activeElement;
  assert.equal(focused.textContent, 'Answer');
  assert.equal(focused.closest('li.trow').dataset.id, 'm1');
  const none = panel([userNote('m1', 'x', 1)]);
  assert.equal(none.$('#status button.stat'), null);
  assert.equal(text(none.$('#status .stat')), '0 your turn');
});

test('S17 Answer opens the thread with a labelled box under its last message; Ctrl+Enter sends a note to the thread', () => {
  const p = panel(EVERY_STATE);
  const answer = actions(p.rowOf('m1')).find(b => b.textContent === 'Answer');
  answer.click();
  const li = p.rowOf('m1'), box = li.querySelector('.why');
  assert.ok(li.querySelector('.tbody'));
  const order = li.children.map(c => c.className.split(' ')[0]);
  assert.ok(order.indexOf('tbody') < order.indexOf('why'), order.join());
  const ta = box.querySelector('textarea'), lab = box.querySelector('label');
  assert.equal(lab.textContent, 'Your answer');
  assert.equal(lab.htmlFor, ta.id);
  assert.equal(p.document.activeElement, ta);
  assert.equal(actions(li).length, 0);  // the buttons wait while the box is open
  ta.input('Yes, merge it.');
  ta.key('Enter', { ctrlKey: true });
  assert.deepEqual(p.sent().map(e => [e.type, e.to, e.text]), [['note', 'm1', 'Yes, merge it.']]);
  const after = p.rowOf('m1');
  assert.equal(after.querySelector('.why'), null);
  assert.equal(text(after.querySelector('.chip')), 'Agent’s turn');
  assert.equal(text(after.querySelector('.progress')), 'Not seen, just now');
  assert.equal(p.document.activeElement, after.querySelector('.thead'));
});

test('S17 Escape cancels the box and gives the focus back to the button that opened it; Cmd+Enter sends a reply', () => {
  const p = panel(EVERY_STATE);
  actions(p.rowOf('m2')).find(b => b.textContent === 'Reply').click();
  const ta = p.rowOf('m2').querySelector('.why textarea');
  assert.equal(p.rowOf('m2').querySelector('.why label').textContent, 'Your reply');
  ta.key('Escape');
  assert.equal(p.rowOf('m2').querySelector('.why'), null);
  assert.equal(p.document.activeElement.textContent, 'Reply');
  assert.equal(p.document.activeElement.closest('li.trow').dataset.id, 'm2');
  p.document.activeElement.click();
  const again = p.rowOf('m2').querySelector('.why textarea');
  again.input('the HTTP part');
  again.key('Enter', { metaKey: true });
  assert.deepEqual(p.sent().map(e => [e.type, e.to, e.text]), [['note', 'm2', 'the HTTP part']]);
  assert.match(p.sent()[0].id, /^m-/);
});

test('S18 an empty answer, reopen reason or message shows an error next to its field and records nothing', () => {
  const p = panel(EVERY_STATE);
  actions(p.rowOf('m1')).find(b => b.textContent === 'Answer').click();
  p.rowOf('m1').querySelector('.why .btn').click();
  let box = p.rowOf('m1').querySelector('.why');
  assert.equal(text(box.querySelector('.err')), 'Write your answer first.');
  assert.equal(box.querySelector('.err').hidden, false);
  assert.equal(box.querySelector('textarea').getAttribute('aria-invalid'), 'true');
  assert.equal(box.querySelector('textarea').getAttribute('aria-describedby'), box.querySelector('.err').id);
  assert.equal(p.document.activeElement, box.querySelector('textarea'));
  p.filter('all');
  actions(p.rowOf('m6')).find(b => b.textContent === 'Reopen').click();
  box = p.rowOf('m6').querySelector('.why');
  assert.equal(box.querySelector('label').textContent, 'Why reopen it?');
  box.querySelector('textarea').input('   ');
  box.querySelector('.btn').click();
  assert.equal(text(p.rowOf('m6').querySelector('.why .err')), 'Say why you reopen it.');
  p.$('.notes .send .btn').dispatch('click');
  assert.equal(text(p.$('.notes .send .status')), 'Write your message first.');
  assert.match(p.$('.notes .send .status').className, /error/);
  assert.equal(p.document.activeElement, p.$('#note'));
  assert.deepEqual(p.sent(), []);
});

test('S19 the check closes after a 6-second window with its own Undo, and two closes keep two Undos', () => {
  const p = panel(EVERY_STATE);
  const close = id => actions(p.rowOf(id)).find(b => b.textContent === '✓').click();
  close('m2');
  let row = p.rowOf('m2');
  assert.match(row.className, /closing/);
  assert.equal(text(row.querySelector('.chip')), 'Closed');
  assert.equal(p.document.activeElement, row.querySelector('button'));
  assert.equal(p.document.activeElement.textContent, 'Undo');
  assert.deepEqual(p.sent(), []);
  p.tick(3000);
  close('m1');  // the second close keeps its own Undo, and the first one's window runs on
  assert.equal(p.$$('li.trow.closing').length, 2);
  assert.equal(p.$('[data-filter="open"]').textContent, 'Open (5)');  // still in place while it can be undone
  assert.equal(text(p.$('#status .stat')), '0 your turn');
  p.tick(3000);
  assert.deepEqual(p.sent().map(e => [e.type, e.to]), [['accept', 'm2']]);
  assert.equal(p.rowOf('m2'), undefined);
  p.rowOf('m1').querySelector('button').click();  // Undo
  p.tick(6000);
  assert.deepEqual(p.sent().map(e => [e.type, e.to]), [['accept', 'm2']]);
  row = p.rowOf('m1');
  assert.equal(text(row.querySelector('.chip')), 'Your turn');
  assert.equal(p.document.activeElement, row.querySelector('.thead'));
  p.filter('all');
  assert.equal(text(p.rowOf('m2').querySelector('.progress')), 'Done, just now');
  assert.deepEqual(actions(p.rowOf('m2')).map(b => b.textContent), ['Reopen']);
});

test('S19 a close in its undo window keeps the page busy, so a new render does not reload it away', () => {
  const p = panel(EVERY_STATE);
  assert.equal(p.conv.busy(), false);
  actions(p.rowOf('m2')).find(b => b.textContent === '✓').click();
  assert.equal(p.conv.busy(), true);
  p.tick(6000);
  assert.deepEqual(p.sent().map(e => [e.type, e.to]), [['accept', 'm2']]);
  assert.equal(p.conv.busy(), false);
});

test('S19 after the window the focus goes to the head of the row now in its place', () => {
  const p = panel(EVERY_STATE);
  actions(p.rowOf('m2')).find(b => b.textContent === '✓').click();
  p.tick(6000);
  assert.equal(p.document.activeElement, p.rowOf('m3').querySelector('.thead'));
});

test('S20 a done thread offers Reopen, which asks why and records reopen; one the agent finished also has Confirm done', () => {
  const p = panel(EVERY_STATE);
  const [ok, reopen] = actions(p.rowOf('m5'));
  assert.equal(p.label(ok), "Confirm done: What's next?");
  assert.equal(reopen.textContent, 'Reopen');
  reopen.click();
  const ta = p.rowOf('m5').querySelector('.why textarea');
  ta.input('step 4 is not done');
  p.rowOf('m5').querySelector('.why .btn').click();
  assert.deepEqual(p.sent().map(e => [e.type, e.to, e.text]), [['reopen', 'm5', 'step 4 is not done']]);
  const row = p.rowOf('m5');
  assert.equal(text(row.querySelector('.chip')), 'Agent’s turn');
  assert.match(text(row.querySelector('.progress')), /^Not seen/);
  assert.equal(text(row.querySelectorAll('.tbody .tmsg').pop().querySelector('.tag')), 'Reopened');
});

test('S21 Answer is the one filled button on a row; the check, Reply and Reopen are outlined', () => {
  const p = panel(EVERY_STATE);
  p.filter('all');
  for (const li of p.rows()) {
    for (const b of actions(li)) {
      assert.match(b.className, /\bbtn\b/);
      if (b.textContent === 'Answer') assert.doesNotMatch(b.className, /btn--quiet/);
      else assert.match(b.className, /btn--quiet/, b.textContent);
    }
  }
  assert.equal(p.$$('.tacts button').filter(b => !b.classList.contains('btn--quiet')).length, 1);
});

test('S22 the head names the state, who started the thread, its first sentence and Open or Fold; each action names the sentence', () => {
  const p = panel(EVERY_STATE);
  p.filter('all');
  assert.equal(p.label(p.rowOf('m1').querySelector('.thead')), 'Your turn. You: Can we merge this into the board start. Open the thread');
  assert.equal(p.label(p.rowOf('m3').querySelector('.thead')), 'Agent’s turn, seen. You: Q3 exactly once delivery semantics are hard to achieve. Open the thread');
  assert.equal(p.label(p.rowOf('m2').querySelector('.thead')), 'Agent’s turn, not seen. You: How about AG-UI. Open the thread');
  assert.equal(p.label(p.rowOf('m5').querySelector('.thead')), "Done. You: What's next. Open the thread");
  p.rowOf('m5').querySelector('.thead').click();
  assert.match(p.label(p.rowOf('m5').querySelector('.thead')), /Fold the thread$/);
  const names = li => actions(li).map(p.label);
  assert.deepEqual(names(p.rowOf('m1')), ['Close: Can we merge this into the board start?', 'Answer: Can we merge this into the board start?']);
  assert.deepEqual(names(p.rowOf('m2')), ['Close: How about AG-UI?', 'Reply: How about AG-UI?']);
  assert.deepEqual(names(p.rowOf('m6')), ['Reopen: Old question.']);
  actions(p.rowOf('m2'))[0].click();
  assert.equal(p.label(p.rowOf('m2').querySelector('button')), 'Undo closing: How about AG-UI?');
});

test('S23 a redraw keeps the focused control, and a draft with its caret', () => {
  const p = panel(EVERY_STATE);
  actions(p.rowOf('m2'))[1].focus();
  p.conv.setLog(EVERY_STATE.concat([status('m3', 'working', 0.5)]));
  assert.equal(p.document.activeElement.textContent, 'Reply');
  assert.equal(p.document.activeElement.closest('li.trow').dataset.id, 'm2');
  assert.ok(p.document.contains(p.document.activeElement));
  actions(p.rowOf('m1'))[1].click();
  const ta = p.rowOf('m1').querySelector('.why textarea');
  ta.input('half an answ');
  ta.setSelectionRange(4, 6);
  p.conv.setLog(EVERY_STATE.concat([status('m3', 'working', 0.5), status('m4', 'seen', 0.2)]));
  const again = p.rowOf('m1').querySelector('.why textarea');
  assert.notEqual(again, ta);
  assert.equal(again.value, 'half an answ');
  assert.equal(p.document.activeElement, again);
  assert.deepEqual([again.selectionStart, again.selectionEnd], [4, 6]);
  assert.equal(p.conv.busy(), true);  // a reload would lose it: the page waits
});

test('S23 when the focused control goes, the focus moves to the head of the row now at its place', () => {
  const p = panel(EVERY_STATE);
  p.rowOf('m2').querySelector('.thead').focus();
  p.conv.setLog(EVERY_STATE.concat([{ type: 'accept', to: 'm2', by: 'user', at: at(0.1) }]));
  assert.equal(p.document.activeElement, p.rowOf('m3').querySelector('.thead'));
});

test('a comment keeps its crumb, and Show, Edit and Delete, in its row', () => {
  const calls = [];
  const comment = { type: 'comment', id: 'c1', n: 1, text: 'Too wide. Make it narrower.', on: { key: 'box' }, by: 'user', at: at(2) };
  const p = panel([comment], doc => ({
    byId: id => (id === 'c1' ? { id: 'c1', n: 1 } : null), showLabel: n => 'Show comment ' + n,
    crumb: e => { const x = doc.createElement('p'); x.className = 'crumb'; x.textContent = 'on ' + e.on.key; return x; },
    commentBody: e => { const x = doc.createElement('p'); x.className = 'body'; x.textContent = e.text; return x; },
    reveal: e => calls.push(['reveal', e.id]), edit: it => calls.push(['edit', it.id]), remove: it => calls.push(['remove', it.id]),
  }));
  const row = p.rowOf('c1');
  assert.equal(text(row.querySelector('.tgist')), 'You: Too wide.');
  const links = row.querySelectorAll('.tleft .link');
  assert.deepEqual(links.map(b => b.textContent), ['Show', 'Edit', 'Delete']);
  assert.deepEqual(links.map(p.label), ['Show comment 1', 'Edit comment 1', 'Delete comment 1']);
  links.forEach(b => b.click());
  assert.deepEqual(calls, [['reveal', 'c1'], ['reveal', 'c1'], ['edit', 'c1'], ['remove', 'c1']]);
  p.rowOf('c1').querySelector('.thead').click();
  const first = p.rowOf('c1').querySelector('.tbody .tmsg');
  assert.equal(text(first.querySelector('.crumb')), 'on box');
  assert.equal(text(first.querySelector('.body')), 'Too wide. Make it narrower.');
  assert.equal(text(first.querySelector('.n')), '1');
});

// A decision drawn by the shared renderer, in the panel's own context, as the dashboard and the board do.
function decisionPanel(x, conversation = []) {
  const kinds = {};
  let ctx = null;
  const p = panel(null, { kinds }, { setup: (context, conv) => {
    ctx = context;
    kinds.decision = context.pageDecision({ conversation: conv, now: () => Date.now() / 1000, md: t => context.pageEscape(t), esc: context.pageEscape, id: k => k + '-1' }).item;
  } });
  p.conv.setLog(ctx.pageDecisionEvents([Object.assign({ id: 'D1', at: at(2), asked: 'Which size? Pick one.', status: 'waiting' }, x)], conversation));
  return p;
}

test('a waiting decision keeps its default, deadline, use-the-default check and Answer in its row, as your turn', () => {
  const p = decisionPanel({ default: 'Small', deadline: new Date(Date.now() + 30 * 60000).toISOString() });
  const row = p.rowOf('D1');
  assert.equal(text(row.querySelector('.chip')), 'Your turn');
  assert.equal(text(row.querySelector('.tgist')), 'Coordinator: Which size?');
  assert.ok(row.classList.contains('open-q'));  // pageDecision finds the next open question by it
  assert.equal(row.dataset.d, 'D1');
  const [close, use, answer] = actions(row);
  assert.deepEqual([close.textContent, p.label(close)], ['✓', 'Close: Which size?']);  // any thread can be closed
  assert.equal(use.textContent, 'Use the default');  // D11: the default says its words
  assert.equal(p.label(use), 'Use the default for: Which size? Pick one.');
  assert.match(use.className, /btn--quiet/);
  assert.equal(answer.textContent, 'Answer');
  assert.doesNotMatch(answer.className, /btn--quiet/);
  assert.equal(row.querySelectorAll('.tacts .progress').length, 0);  // the row's state says it once
  assert.equal(text(p.$('#status .stat')), '1 your turn');
  row.querySelector('.thead').click();
  const body = text(p.rowOf('D1').querySelector('.tbody'));
  assert.match(body, /If you don't answer: Small/);
  assert.match(body, /default in 30 min/);
  actions(p.rowOf('D1'))[2].click();
  const ta = p.rowOf('D1').querySelector('.why textarea');
  assert.equal(p.rowOf('D1').querySelector('.why label').textContent, 'Your answer');
  ta.input('Large');
  ta.key('Enter', { ctrlKey: true });
  assert.deepEqual(p.sent().filter(e => e.type !== 'decision').map(e => [e.type, e.decision, e.text, e.default]), [['answer', 'D1', 'Large', false]]);
  assert.equal(text(p.rowOf('D1').querySelector('.chip')), 'Agent’s turn');
});

test('use the default answers with the default from the row', () => {
  const p = decisionPanel({ default: 'Small' });
  actions(p.rowOf('D1'))[1].click();
  assert.deepEqual(p.sent().filter(e => e.type !== 'decision').map(e => [e.type, e.decision, e.text, e.default]), [['answer', 'D1', 'Small', true]]);
});

test('page kinds without controls of their own, such as an approval, keep their text and get the row\'s buttons', () => {
  const p = panel([{ type: 'approve', id: 'ap1', option: 'After', label: 'Ship After', text: 'Looks right.', by: 'user', at: at(1) }],
    doc => ({ itemKinds: ['comment', 'note', 'approve'], kinds: { approve: c => { const li = doc.createElement('li'); li.className = 'msg me decision'; li.textContent = 'You approved ' + c.e.label; return li; } } }));
  const row = p.rowOf('ap1');
  assert.equal(text(row.querySelector('.tgist')), 'You: Looks right.');
  assert.deepEqual(actions(row).map(b => b.textContent), ['✓', 'Reply']);
  row.querySelector('.thead').click();
  assert.equal(text(p.rowOf('ap1').querySelector('.tbody .tmsg')), 'You approved Ship After');
});

test('a read-only copy draws the rows with no actions, and the head still opens them', () => {
  const p = panel(EVERY_STATE, { readOnly: true });
  assert.equal(p.$$('.tacts button').length, 0);
  p.rowOf('m5').querySelector('.thead').click();
  assert.ok(p.rowOf('m5').querySelector('.tbody'));
});

test('the pins get each user item\'s state from its thread', () => {
  let seen = null;
  const p = panel(EVERY_STATE, { rendered: s => { seen = s; } });
  assert.deepEqual(JSON.parse(JSON.stringify(seen)), { m1: 'asked', m2: 'new', m3: 'seen', m4: 'working', m5: 'done', m6: 'accepted' });
  assert.equal(p.conv.state().m6, 'accepted');
});

test('reopen from a pin opens the thread with the reopen box, from All when it was closed', () => {
  const p = panel(EVERY_STATE);
  p.conv.reopen('m6');
  assert.equal(p.$('[data-filter="all"]').getAttribute('aria-pressed'), 'true');
  assert.equal(p.rowOf('m6').querySelector('.why label').textContent, 'Why reopen it?');
});

// ---- Page kinds in the rows, from the verifier's walk of the pages
test('a done thread of a kind with its own buttons can still be confirmed and reopened: a decided decision keeps Reply between ✓ and Reopen', () => {
  const p = decisionPanel({ status: 'decided', decision: 'Small' });
  const row = p.rowOf('D1');
  assert.equal(row.dataset.state, 'done');
  assert.deepEqual(actions(row).map(b => b.textContent), ['✓', 'Reply', 'Reopen']);
  assert.deepEqual(actions(row).map(p.label), ['Confirm done: Which size?', 'Reply to: Which size? Pick one.', 'Reopen: Which size?']);
  actions(row)[0].click();
  p.tick(6000);
  assert.deepEqual(p.sent().filter(e => e.type === 'accept').map(e => e.to), ['D1']);
  assert.equal(p.rowOf('D1'), undefined);  // closed: it left Open
});

test('the first sentence of a page kind without text is its words without its head, each block ended by a stop', () => {
  const p = panel([{ type: 'closed', id: 'x1', by: 'worker-2', question: 'Q-4', status: 'answered', at: at(1) }], doc => ({
    kinds: { closed: () => {
      const li = doc.createElement('li');
      li.innerHTML = '<div class="head"><span class="who">worker-2</span><span class="when">19:54</span></div><p class="what">Answered: Who supports ACP</p><div class="body md"><p>Zed does.</p></div>';
      return li;
    } } }));
  assert.equal(text(p.rowOf('x1').querySelector('.tgist')), 'Coordinator: Answered: Who supports ACP.');  // a stop ends each block
});

test('rows shown elsewhere (nodes) are open, without actions, and their head is plain: nothing to fold', () => {
  const p = panel(EVERY_STATE);
  const [row] = Array.from(p.conv.nodes(e => e.id === 'm3'));
  const head = row.querySelector('.thead');
  assert.equal(head.tagName, 'DIV');
  assert.equal(head.getAttribute('aria-expanded'), null);
  assert.equal(row.querySelector('.tfold'), null);
  assert.equal(row.querySelectorAll('.tacts button').length, 0);
  assert.ok(row.querySelector('.tbody'));
});

test('a row keeps its buttons on one line: the left part wraps, the buttons do not', () => {
  const css = read('page', 'page.css');
  assert.match(css, /\.tfoot \{[^}]*flex-wrap:nowrap/);
  assert.match(css, /\.tacts \{[^}]*flex:none/);
  assert.match(css, /\.tleft \{[^}]*min-width:0[^}]*flex-wrap:wrap/);
});

test('a page places the figure in its own slot with stats, and puts it back after rewriting its header with figure()', () => {
  const p = panel(EVERY_STATE, doc => {
    const slot = doc.createElement('span'); slot.id = 'yourturn';
    doc.querySelector('#status').append(slot);
    return { stats: () => doc.getElementById('yourturn') };
  });
  assert.equal(text(p.$('#yourturn')), '1 your turn');
  const status = p.$('#status');
  status.innerHTML = '<span class="stat"><b>3</b>steps</span><span class="yourturn" id="yourturn"></span>';
  assert.equal(p.$('#yourturn .stat'), null);
  p.conv.figure();
  assert.equal(text(p.$('#yourturn')), '1 your turn');
  assert.equal(p.$$('#status .stat').length, 2);  // one figure of the page's, and the one figure for your turn
});
