// The shared capabilities of src/better_ai/page/page.js: the page config, the decision-question renderer, the approve
// panel, requirement confirmations and the log a page draws. Run with `node --test tests/*.test.js`. The DOM is a
// minimal stand-in: just what these functions touch.
const test = require('node:test');
const assert = require('node:assert/strict');
const { read, loadPage } = require('./harness');

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

function decision(page, overrides, options) {
  const sent = [], boxes = [];
  const conversation = {
    send(method, params, what, done, fail) { sent.push({ method, params, what }); if (done) done(); },
    box(li, id, label, from, onSend) { boxes.push({ id, label, onSend }); },
    progress(st) { const n = new Node('span'); n.textContent = st; return n; },
  };
  const d = page.pageDecision(Object.assign({
    conversation, now: () => Date.parse('2026-11-22T10:00:00Z') / 1000, md: t => '<p>' + t + '</p>', esc: t => String(t), id: p => p + '-1',
  }, options));
  const x = Object.assign({ id: 'D1', at: '2026-11-22T09:00:00Z', asked: 'Which size?', status: 'waiting', default: 'Take the small one', deadline: '2026-11-22T10:10:00Z' }, overrides);
  const entry = { e: { x }, replies: [] };
  return { d, x, entry, sent, boxes, render: (state, actions) => d.item(entry, state || {}, actions !== false) };
}
const buttons = foot => foot.children.filter(n => n.tag === 'button');

test('a waiting decision shows its question, the default and the deadline, with Use the default and Answer', () => {
  const page = load({ agent: 'coordinator', capabilities: ['decisions'] });
  const t = decision(page);
  const [li, foot] = t.render();
  assert.match(li.innerHTML, /Which size\?/);
  assert.match(li.innerHTML, /If you don&#39;t answer|If you don't answer: Take the small one/);
  assert.match(li.innerHTML, /default in 10 min/);
  assert.match(li.className, /open-q/);
  assert.equal(li.dataset.state, 'asked');
  assert.match(foot.innerHTML, /Waiting for you/);
  assert.deepEqual(buttons(foot).map(b => b.textContent), ['✓', 'Answer']);
  assert.equal(t.d.waiting(t.entry, {}), true);
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

test('the user\'s answer moves the question on: answered, waiting for the agent, then applied', () => {
  const page = load({ agent: 'coordinator', capabilities: ['decisions'] });
  const t = decision(page);
  t.entry.replies = [{ type: 'answer', id: 'a1', decision: 'D1', text: 'x', default: false }];
  let [li, foot] = t.render({ a1: undefined });
  assert.match(foot.innerHTML, /You answered/);
  assert.match(li.innerHTML, /answered, waiting for the coordinator/);
  assert.equal(t.d.waiting(t.entry, {}), false);
  assert.equal(t.d.waiting(t.entry, { a1: 'asked' }), true);  // the agent asked back: the user is up again
  [li, foot] = t.render({ a1: 'done' });
  assert.match(foot.innerHTML, /Applied/);
  const applied = decision(page, { status: 'answered', answer: { type: 'page', event: 'a1' } });
  applied.entry.replies = [{ type: 'answer', id: 'a1', decision: 'D1', text: 'x', default: false }];
  assert.deepEqual(buttons(applied.render()[1]).map(b => b.textContent), ['Reply']);
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
  assert.deepEqual(buttons(t.render({}, false)[1]), []);
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
  t.entry.replies = [{ type: 'answer', id: 'a1', decision: 'D1', text: 'x', default: false }];
  const [li, foot] = t.render({ a1: 'done' });
  assert.match(foot.innerHTML, /Applied/);
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

test('the question footer is a filled check and a quiet Answer on one row, and each control names the question', () => {
  const t = decision(load({ capabilities: ['decisions'] }));
  const [, foot] = t.render();
  const [use, answer] = buttons(foot);
  assert.match(use.className, /btn--sm/);
  assert.doesNotMatch(use.className, /btn--quiet/);
  assert.match(answer.className, /btn--quiet/);
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
  assert.deepEqual(buttons(foot).map(b => b.textContent), ['✓', 'Answer']);
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
  const [, foot] = items[0].t.d.item(items[1].t.entry, {}, true);  // one pageDecision draws every question of a page  // the thread redraws the question
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
  const conversation = { box() {}, progress: () => new Node('span'),
    send(m, p, w, done) { load.thread['li.open-q'] = [rows[0].n, rows[2].n]; done(); } };
  const d = page.pageDecision({ conversation, now: () => 0, md: t => t, esc: String, id: p => p + '-1' });
  rows = ['D1', 'D2', 'D3'].map(id => {
    const [n, foot] = d.item({ e: { x: { id, at: '2026-11-22T09:00:00Z', asked: 'Q ' + id, status: 'waiting', default: 'x' } }, replies: [] }, {}, true);
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
  const conversation = { box() {}, progress: () => new Node('span'), send(m, p, w, done) { finish.push(done); } };
  const d = page.pageDecision(Object.assign({ conversation, now: () => 0, md: t => t, esc: String, id: p => p + '-1' }, options));
  const draw = id => {
    const [n, foot] = d.item({ e: { x: { id, at: '2026-11-22T09:00:00Z', asked: 'Q ' + id, status: 'waiting', default: 'x' } }, replies: [] }, {}, true);
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
