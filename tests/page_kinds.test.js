// Every live page's kinds of thread, in every state of the one state machine, on the page's own script with the shared
// panel (tests/pages-live.js): each row offers the shared controls of its state, whatever its kind, and every event a
// row sends carries what the page's schemas require, as the message box's do (lesson L3). Run with
// `node --test tests/*.test.js`.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { livePage, at, LIVE_DATA } = require('./pages-live');
const { text, actions } = require('./dom');

const SCHEMAS = path.join(__dirname, '..', 'src', 'better_ai');
const schema = rel => JSON.parse(fs.readFileSync(path.join(SCHEMAS, rel), 'utf8'));
const COMMON = schema('schemas/conversation.schema.json');
const EVENTS = { canvas: 'design/schemas/canvas-events.schema.json', show: 'show/schemas/show-events.schema.json',
  architect: 'architect/schemas/architect-events.schema.json', dashboard: 'code/schemas/dashboard-events.schema.json',
  board: 'research/schemas/board-events.schema.json', discover: 'discover/schemas/discover-events.schema.json' };
// The fields an event of TYPE must have on PAGE: the shared schema's and the page's own, besides what the server sets.
function required(page, type) {
  const own = schema(EVENTS[page]), fields = new Set();
  (COMMON.$defs[type] && COMMON.$defs[type].required || []).forEach(f => fields.add(f));
  (own.allOf || []).forEach(rule => {
    if (rule.if && rule.if.properties && rule.if.properties.type && rule.if.properties.type.const === type) {
      (rule.then.required || []).forEach(f => fields.add(f));
      const ref = rule.then.$ref && own.$defs[rule.then.$ref.split('/').pop()];
      ((ref && ref.required) || []).forEach(f => fields.add(f));
    }
  });
  ['at', 'by'].forEach(f => fields.delete(f));
  return [...fields];
}

const AGENT = 'coordinator';
const user = (type, id, more = {}) => Object.assign({ type, id, by: 'user', at: at(5) }, more);
const status = (to, s, read) => ({ type: 'status', to, status: s, by: AGENT, read, at: at(4) });
// A root event in each state: the agent's turn (not seen, working), your turn, done by the agent, closed by you.
function userStates(root) {
  const id = root.id;
  return {
    agent: [root],
    working: [root, status(id, 'working', 0)],
    you: [root, { type: 'reply', id: 'r-' + id, to: id, text: 'Which one?', by: AGENT, at: at(4) }, status(id, 'asked', 0)],
    done: [root, status(id, 'done', 0)],
    closed: [root, { type: 'accept', to: id, by: 'user', at: at(4) }],
  };
}
const decision = (id, more) => Object.assign({ id, at: at(6), asked: 'Which size? Pick one.', status: 'waiting', default: 'Small',
  deadline: new Date(Date.now() + 3600e3).toISOString() }, more);
function decisionStates(id) {
  return {
    you: { decisions: [decision(id)], log: [] },
    agent: { decisions: [decision(id)], log: [user('answer', 'a-' + id, { decision: id, text: 'Large', default: false })] },
    done: { decisions: [decision(id, { status: 'decided', decision: 'Small', default: undefined, deadline: undefined })], log: [] },
    closed: { decisions: [decision(id, { status: 'decided', decision: 'Small', default: undefined, deadline: undefined })],
      log: [{ type: 'accept', to: id, by: 'user', at: at(4) }] },
  };
}

// Each page's kinds: plain messages of the user's, its own kinds, and the decisions of the pages that have them.
const NOTE = id => user('note', id, { to: null, text: 'Can it be narrower?' });
const KINDS = {
  canvas: {
    note: NOTE('m1'),
    comment: user('comment', 'c1', { n: 1, text: 'Too wide.', on: { version: 'A', screen: '1440x900', target: {}, spot: { fx: 0.5, fy: 0.5 } } }),
    approve: user('approve', 'ap1', { option: 'A', label: 'Build A', carries: [], text: 'Go.' }),
  },
  show: {
    note: Object.assign(NOTE('m1'), { on: { slide: 1, part: null } }),
    comment: user('comment', 'c1', { n: 1, text: 'Unclear.', on: { slide: 1, part: '', headline: 'H', target: {}, spot: { fx: 0.5, fy: 0.5 } } }),
  },
  architect: {
    note: NOTE('m1'),
    comment: user('comment', 'c1', { n: 1, text: 'Why here?', on: { id: 'box-x', selector: '#box-x' } }),
    approve: user('approve', 'ap1', { option: 'after', label: 'Ship After', carries: [], text: null, again: false, perspectives: [], changes: [] }),
  },
  dashboard: { note: NOTE('m1'), comment: user('comment', 'c1', { text: 'Why?', on: { kind: 'task', id: 'T1', title: 'T1' } }) },
  board: { note: NOTE('m1'), comment: user('comment', 'c1', { text: 'Why?', on: { kind: 'question', id: 'Q-1', title: 'Page speed' } }) },
  discover: { note: NOTE('m1'), choose: user('choose', 'ch1', { option: 'K2', revision: 'r2' }) },
};
// Kinds that need no reply start closed by the user (D8, D10): only Reopen.
const CLOSED_KINDS = {
  canvas: user('verdict', 'v1', { version: 'A', verdict: 'up' }),
  architect: user('confirm', 'k1', { requirement: 'R1', wording: 'w', text: 'Confirmed requirement R1.' }),
  board: { type: 'closed', id: 'x1', by: 'worker-2', question: 'Q-1', status: 'answered', at: at(5) },
};
const DECISION_PAGES = ['dashboard', 'board', 'discover'];

// The page, once what it loads has arrived (the deck reads /data before it starts its conversation).
async function open(name) {
  const p = livePage(name, LIVE_DATA[name] || {});
  for (let i = 0; i < 5; i++) await new Promise(resolve => setImmediate(resolve));
  return p;
}
function feedState(p, name, log, decisions) {
  if (name === 'dashboard' || name === 'board' || name === 'discover') p.feed(log, { decisions: decisions || [] });
  else p.feed(log);
}

// The controls a row of STATE must offer, by the states.md table, whatever the kind.
function assertControls(row, state, where) {
  const words = actions(row).map(b => b.textContent), labels = actions(row).map(b => b.getAttribute('aria-label') || '');
  if (state === 'closed') return assert.deepEqual(words, ['Reopen'], where);
  assert.equal(words[0], '✓', where + ': the check comes first');
  assert.match(labels[0], state === 'done' ? /^Confirm done: / : /^Close: /, where);
  if (state === 'you') assert.ok(words.includes('Answer'), where + ': Answer');
  if (state === 'agent' || state === 'working') assert.ok(words.includes('Reply'), where + ': Reply');
  if (state === 'done') assert.equal(words[words.length - 1], 'Reopen', where + ': Reopen last');
  assert.ok(!words.slice(1).includes('✓'), where + ': one check only');
}

// Every event a row sends: Answer or Reply with the box, Reopen with a reason, the check after its undo window.
function assertSends(p, name, row, state, where) {
  const before = p.conv.log().length, id = row.dataset.id;
  const sent = () => p.conv.log().slice(before);
  const button = words => actions(p.rowOf(id)).find(b => b.textContent === words);
  const viaBox = words => {
    button(words).click();
    const box = p.rowOf(id).querySelector('.why textarea');
    box.input('Walk words.');
    box.key('Enter', { ctrlKey: true });
  };
  if (state === 'you' || state === 'agent' || state === 'working') viaBox(state === 'you' ? 'Answer' : 'Reply');
  else viaBox('Reopen');
  for (const e of sent()) {
    for (const field of required(name, e.type)) assert.ok(field in e && e[field] !== undefined, `${where}: ${e.type} lacks ${field}`);
  }
  assert.equal(sent().length, 1, where);
}

for (const name of Object.keys(KINDS)) {
  test(`${name}: every kind of row offers the shared controls of its state, and what it sends meets the page's schemas`, async () => {
    const cases = [];
    for (const [kind, root] of Object.entries(KINDS[name])) {
      for (const [state, log] of Object.entries(userStates(root))) cases.push({ where: `${kind} ${state}`, state, log, id: root.id });
    }
    if (DECISION_PAGES.includes(name)) {
      for (const [state, c] of Object.entries(decisionStates('D7'))) cases.push({ where: `decision ${state}`, state, log: c.log, decisions: c.decisions, id: 'D7' });
    }
    if (CLOSED_KINDS[name]) cases.push({ where: `${CLOSED_KINDS[name].type} start`, state: 'closed', log: [CLOSED_KINDS[name]], id: CLOSED_KINDS[name].id });
    for (const c of cases) {
      const p = await open(name);
      feedState(p, name, c.log, c.decisions);
      if (c.state === 'closed') p.filter('all');
      const row = p.rowOf(c.id);
      assert.ok(row, `${name} ${c.where}: no row`);
      assertControls(row, c.state === 'working' ? 'working' : c.state, `${name} ${c.where}`);
      if (c.where.startsWith('decision you')) assert.ok(actions(row).some(b => b.textContent === 'Use the default'), `${name} ${c.where}: Use the default`);
      assertSends(p, name, row, c.state, `${name} ${c.where}`);
    }
  });
}

test('the check closes any thread after its undo window, and the accept names the thread', async () => {
  for (const name of Object.keys(KINDS)) {
    const p = await open(name);
    feedState(p, name, [KINDS[name].note]);
    actions(p.rowOf('m1'))[0].click();
    p.tick(6000);
    const sent = p.conv.log().filter(e => e.type === 'accept');
    assert.deepEqual(sent.map(e => e.to), ['m1'], name);
  }
});

test('a worker report on the board starts closed (D10), shown in All with Reopen, and its first sentence stops after the question', async () => {
  const p = await open('board');
  feedState(p, 'board', [CLOSED_KINDS.board]);
  assert.equal(p.rowOf('x1'), undefined);  // not in Open
  p.filter('all');
  assert.match(text(p.rowOf('x1').querySelector('.tgist')), /^Coordinator: Answered: Page speed\.$/);
});

test('the canvas gives a verdict an id, so its thread can be reopened', async () => {
  const p = await open('canvas');
  const thumb = p.document.querySelector('.vbtn[data-v]');
  assert.ok(thumb, 'a thumb on a version');
  thumb.click();
  const [verdict] = p.conv.log().filter(e => e.type === 'verdict');
  assert.match(verdict.id, /^v-/);
  p.filter('all');
  assert.deepEqual(actions(p.rowOf(verdict.id)).map(b => b.textContent), ['Reopen']);
});
