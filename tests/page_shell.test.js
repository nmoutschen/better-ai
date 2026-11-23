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
}

function load(config) {
  const document = {
    createElement: tag => new Node(tag),
    getElementById: id => id === 'page-config' && config ? { textContent: JSON.stringify(config) } : null,
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

function decision(page, overrides) {
  const sent = [], boxes = [];
  const conversation = {
    send(method, params, what, done, fail) { sent.push({ method, params, what }); if (done) done(); },
    box(li, id, label, from, onSend) { boxes.push({ id, label, onSend }); },
    progress(st) { const n = new Node('span'); n.textContent = st; return n; },
  };
  const d = page.pageDecision({
    conversation, now: () => Date.parse('2026-11-22T10:00:00Z') / 1000, md: t => '<p>' + t + '</p>', esc: t => String(t), id: p => p + '-1',
  });
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
  assert.deepEqual(buttons(foot).map(b => b.textContent), ['Use the default', 'Answer']);
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

// ---- the page token

const fragment = (hash, stored) => {
  const kept = { ...(stored ? { pageToken: stored } : {}) }, replaced = [];
  return { kept, replaced, globals: {
    location: { hash, pathname: '/', search: '' },
    history: { replaceState: (...args) => replaced.push(args[2]) },
    sessionStorage: { getItem: k => kept[k] ?? null, setItem: (k, v) => { kept[k] = v; } },
  } };
};
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
    if (url === '/rpc') return Promise.resolve({ status: 200, ok: true, json: () => Promise.resolve({ error: { code: -32001, message: 'page out of date: reload' } }) });
    return url.startsWith('/events') ? new Promise(() => {}) : answer(200);
  }, {}, where.globals);
  page.conversation.send('note', { id: 'm1', text: 'my long answer', to: null }, 'Reply', () => { finished = true; }, () => { failed = true; });
  await page.flush();
  assert.equal(sent.find(r => r.url === '/rpc').init.headers['X-Page-Token'], 'tok');
  assert.equal(finished, false);  // done is what clears the typed text: it is not called
  assert.equal(failed, true);
  assert.equal(page.els['.toast'].textContent, 'Not sent: reply. page out of date: reload');
  assert.equal(page.els['.notes .status'].textContent, 'Not sent: page out of date: reload');
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
  assert.equal(page.els['.offline'].textContent, 'page out of date: reload');
});
