// What the research board's page (board.js) writes for a record whose field is null. Run with `node --test tests/*.test.js`.
// board.js runs against stand-in elements, up to its polling; the pop-up's text is read from the element it fills.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const src = path.join(__dirname, '..', 'src', 'better_ai');
const shared = {};
vm.runInNewContext(fs.readFileSync(path.join(src, 'page', 'page.js'), 'utf8'), shared);
const code = fs.readFileSync(path.join(src, 'research', 'board.js'), 'utf8').split('const bands = ')[0];

const stand = () => new Proxy(function () {}, {
  get: (_t, k) => (k === Symbol.toPrimitive ? () => '' : k === 'length' ? 0 : stand()),
  apply: () => stand(),
  set: () => true,
});

// The page with `getElementById('pop')` giving one element that keeps what is written into it.
function page() {
  const pop = { innerHTML: '', querySelector: s => (s === 'ul.thread' ? { append() {} } : null), remove() {}, style: {}, setAttribute() {} };
  const own = { getElementById: id => (id === 'pop' ? pop : stand()), activeElement: null, contains: () => false };
  const document = new Proxy(stand(), { get: (t, k) => (k in own ? own[k] : t[k]) });
  const make = new Function('document', 'pageConversation', 'pageDecision', 'pageDecisionEvents', 'pageMarkdown', 'pageMarkdownText', 'pageTime', 'addEventListener',
    'innerWidth', 'innerHeight', 'getComputedStyle', 'fetch', 'setInterval',
    code + '; return {prepare, decisions, waitingCount, setBoard: d => { D = prepare(d); }, open: (kind, id) => { OPEN = {kind, id, anchor: null}; fillPop(); }};');
  const loaded = make(document, () => stand(), () => stand(), () => [], t => ({ outerHTML: String(t) }), String, shared.pageTime, () => {},
    1000, 800, stand(), () => new Promise(() => {}), () => {});
  return { ...loaded, html: () => pop.innerHTML };
}

const board = source => ({
  brief: {}, logs: {}, decisions: [], conversation: [],
  sources: [source],
  questions: [{ id: 'Q-1', status: 'answered', title: 'Page speed', priority: 'high', origin: { type: 'user' }, question: 'q?', summary: 's' }],
  claims: [{ id: 'C-w2-1', question: 'Q-1', source: 'S-w2-2', status: 'verified', claim: 'It got slower.' }],
});

test('a source with no date is cited by its category alone, never as null', () => {
  const p = page();
  p.setBoard(board({ id: 'S-w2-2', author: 'Frontend guild', date: null, category: 'grey', title: 'Checkout page speed' }));
  p.open('question', 'Q-1');
  const item = p.html().match(/<li dir="auto">.*?<\/li>/s)[0];
  assert.match(item, /Frontend guild/);
  assert.match(item, /\(grey\)/);
  assert.doesNotMatch(item, /null/);
});

test('a source with a date and a category is cited by both', () => {
  const p = page();
  p.setBoard(board({ id: 'S-w2-2', author: 'Frontend guild', date: '2026-03', category: 'grey', title: 'Checkout page speed' }));
  p.open('question', 'Q-1');
  assert.match(p.html().match(/<li dir="auto">.*?<\/li>/s)[0], /\(2026-03, grey\)/);
});

// The decisions the board reads: a waiting one counts as open until the user answers it on the page; one written before
// this change has the old words and is read as the new ones.
const decision = (id, status, over) => ({ type: 'decision', id, status, asked: 'Login?', default: 'Go on', deadline: '2026-11-21T10:30:00Z', ...over });

test('a waiting decision counts as open until the user answers it', () => {
  const p = page();
  const d = { decisions: [decision('D1', 'waiting'), decision('D2', 'waiting'), decision('D3', 'defaulted'), decision('D4', 'decided', { decision: 'x' })],
    conversation: [{ type: 'answer', id: 'a-1', decision: 'D2', text: 'go', default: false }] };
  assert.equal(p.waitingCount(d), 1);
  assert.equal(p.waitingCount({ ...d, conversation: [] }), 2);
});

test('a decision in the old format is read as the new words, and a new one is left as it is', () => {
  const p = page();
  const read = p.decisions({ decisions: [
    decision('D1', 'pending', { _old: true }), decision('D2', 'default', { _old: true }), decision('D3', 'changed', { _old: true }),
    decision('D4', 'waiting') ] });
  assert.deepEqual(Array.from(read, x => x.status), ['waiting', 'defaulted', 'answered', 'waiting']);
  assert.equal(p.waitingCount({ decisions: [decision('D1', 'pending', { _old: true })], conversation: [] }), 1);
});
