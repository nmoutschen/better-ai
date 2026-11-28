// What the research board's page (board.js) writes: for a record whose field is null, and how it shapes the new record
// fields. board.js runs against stand-in elements, up to its polling (tests/harness.js); the pop-up's text
// is read from the element it fills. Run with `node --test tests/*.test.js`.
const test = require('node:test');
const assert = require('node:assert/strict');
const { read, stand, marked, between, loadPage, loadBoard } = require('./harness');

const { pageEscape: realEsc, pageShowErrors } = loadPage();
const NOTE = loadBoard('{ERRORS_NOTE}').ERRORS_NOTE;

// All of board.js, to its end, on a document whose #page-data holds SNAPSHOT (none for a served page): what the page
// asked of the conversation, and what it wrote to the errors band.
function wholeBoard(snapshot) {
  const seen = { conversation: null, bands: [] };
  const page = loadPage();
  const document = new Proxy(stand(), { get: (t, k) => (k === 'getElementById' ? id => (id === 'page-data' ? (snapshot ? { textContent: JSON.stringify(snapshot) } : null) : stand()) : t[k]) });
  const env = { document, pageConversation: o => { seen.conversation = o; return stand(); }, pageDecision: page.pageDecision, pageDecisionEvents: page.pageDecisionEvents, pageOpenDecisions: page.pageOpenDecisions,
    pageMarkdown: t => ({ outerHTML: String(t) }), pageMarkdownText: String, pageTime: page.pageTime, pageEscape: page.pageEscape, pageAgents: page.pageAgents, pagePopup: page.pagePopup,
    pageShowErrors: (band, errors, note) => seen.bands.push([errors, note]), addEventListener: () => {}, innerWidth: 1000, innerHeight: 800,
    getComputedStyle: stand(), pageFetch: () => new Promise(() => {}), setInterval: () => {} };
  new Function(...Object.keys(env), read('research', 'board.js'))(...Object.values(env));
  return seen;
}

// The page with `getElementById('pop')` giving one element that keeps what is written into it.
function page() {
  const pop = { innerHTML: '', querySelector: s => (s === 'ul.thread' ? { append() {} } : null), remove() {}, style: {}, setAttribute() {} };
  const own = { getElementById: id => (id === 'pop' ? pop : stand()), activeElement: null, contains: () => false };
  const document = new Proxy(stand(), { get: (t, k) => (k in own ? own[k] : t[k]) });
  const loaded = loadBoard('{prepare, decisions, waitingCount, setBoard: d => { D = prepare(d); }, open: (kind, id) => { OPEN = {kind, id, anchor: null}; fillPop(); }}',
    { document, pageDecision: () => stand(), pageDecisionEvents: () => [] });
  return { ...loaded, html: () => pop.innerHTML };
}

const board = source => ({
  brief: {}, logs: {}, decisions: [], conversation: [],
  sources: [source],
  questions: [{ id: 'Q-1', status: 'answered', title: 'Page speed', priority: 'high', origin: { type: 'user' }, question: 'q?', summary: 's' }],
  claims: [{ id: 'C-w2-1', question: 'Q-1', source: 'S-w2-2', status: 'verified', claim: 'It got slower.' }],
});

test('a source is cited by its date and category, and by its category alone, never as null, when it has no date', () => {
  const cited = date => {
    const p = page();
    p.setBoard(board({ id: 'S-w2-2', author: 'Frontend guild', date, category: 'grey', title: 'Checkout page speed' }));
    p.open('question', 'Q-1');
    return p.html().match(/<li dir="auto">.*?<\/li>/s)[0];
  };
  const none = cited(null);
  assert.match(none, /Frontend guild/);
  assert.match(none, /\(grey\)/);
  assert.doesNotMatch(none, /null/);
  assert.match(cited('2026-03'), /\(2026-03, grey\)/);
});

// The decisions the board reads: a waiting one counts as open until the user answers it on the page; one written before
// this change has the old words and is read as the new ones.
const decision = (id, status, over) => ({ type: 'decision', id, status, asked: 'Login?', default: 'Go on', deadline: '2026-11-21T10:30:00Z', ...over });

test('a waiting decision counts as open until the user answers it', () => {
  const p = page();
  const d = { decisions: [decision('D1', 'waiting'), decision('D2', 'waiting'), decision('D3', 'defaulted'), decision('D4', 'decided', { decision: 'x' })],
    conversation: [{ type: 'answer', id: 'a-1', decision: 'D2', text: 'go', default: false, by: 'user' }] };
  assert.equal(p.waitingCount(d), 1);
  assert.equal(p.waitingCount({ ...d, conversation: [] }), 2);
});

test('a decision the coordinator asked back about after the answer counts as open again, as on every page', () => {
  const p = page();
  const d = { decisions: [decision('D1', 'waiting', { at: '2026-11-21T10:00:00Z' })],
    conversation: [{ type: 'answer', id: 'a-1', decision: 'D1', text: 'go', default: false, by: 'user', at: '2026-11-21T10:05:00Z' },
      { type: 'status', to: 'a-1', status: 'asked', by: 'coordinator', at: '2026-11-21T10:06:00Z' }] };
  assert.equal(p.waitingCount(d), 1);
  assert.equal(p.waitingCount({ ...d, conversation: d.conversation.slice(0, 1) }), 0);
});

test('a decision in the old format is read as the new words, and a new one is left as it is', () => {
  const p = page();
  const read = p.decisions({ decisions: [
    decision('D1', 'pending', { _old: true }), decision('D2', 'default', { _old: true }), decision('D3', 'changed', { _old: true }),
    decision('D4', 'waiting') ] });
  assert.deepEqual(Array.from(read, x => x.status), ['waiting', 'defaulted', 'answered', 'waiting']);
  assert.equal(p.waitingCount({ decisions: [decision('D1', 'pending', { _old: true })], conversation: [] }), 1);
});

// The research board's page: how it shapes the new record fields, and its errors band (page.js's). Both are read out of board.js,
// between marker comments and between `const has =` and the map's layout, so the test runs the shipped code.
const boardJs = read('research', 'board.js');
const { notValid } = new Function('esc', marked(boardJs, 'invalid') + '; return {notValid};')(realEsc);
const { prepare } = new Function('const has =' + between(boardJs, 'const has =', '// ---------- Slices') + '; return {prepare};')();

test("the board's map reads the new fields: claims by question, merged and withdrawn records, where a question was raised", () => {
  const q = (id, over) => ({ id, status: 'open', title: id, priority: 'high', origin: { type: 'user' }, _born: 1, ...over });
  const c = (id, question, status, source) => ({ id, question, source: source || 'S-1', status });
  const d = prepare({ brief: {}, logs: { w2: { searches: [{ question: 'Q-1', query: 'a', new_terms: [] }, { question: 'Q-1', query: 'b', new_terms: ['x'] }] } },
    sources: [], decisions: [],
    questions: [q('Q-1'), q('Q-2', { kind: 'frontier', raised_in: 'Q-1' }), q('Q-3', { status: 'merged', merged_into: 'Q-1' }),
      q('Q-4', { origin: { type: 'source', source: 'S-9' } })],
    claims: [c('C-1', 'Q-1', 'verified'), c('C-2', 'Q-3', 'unchecked'), c('C-3', 'Q-1', 'withdrawn'), c('C-4', 'Q-1', 'checking', 'S-8'), c('C-5', 'Q-1', 'unchecked', 'S-9')] });
  assert.deepEqual(d.qs.map(x => x.id), ['Q-1', 'Q-2', 'Q-4']);
  assert.deepEqual(d.byId['Q-1'].claimsList.map(x => x.id), ['C-1', 'C-2', 'C-4', 'C-5']);
  assert.equal(d.byId['Q-2'].parent, 'Q-1');
  assert.equal(d.byId['Q-4'].parent, 'Q-1');  // the question of the first claim that cites its source
  assert.equal(d.byId['Q-1'].searches, 2);
});

test('searches on a merged question count for the question it was merged into', () => {
  const q = (id, over) => ({ id, status: 'open', title: id, priority: 'high', origin: { type: 'user' }, _born: 1, ...over });
  const d = prepare({ brief: {}, sources: [], decisions: [], claims: [],
    logs: { w2: { searches: [{ question: 'Q-3', query: 'a', new_terms: [] }, { question: 'Q-1', query: 'b', new_terms: [] }] } },
    questions: [q('Q-1'), q('Q-3', { status: 'merged', merged_into: 'Q-1' })] });
  assert.equal(d.byId['Q-1'].searches, 2);
});

test('an invalid record the board still shows is marked with its first message, and the map copes with missing fields', () => {
  assert.equal(notValid({ _errors: ['status: must be one of "a"', 'x: y'] }), 'not valid: status: must be one of "a"');
  assert.equal(notValid({}), '');
  const d = prepare({ brief: {}, sources: [{ id: 'S-1', _errors: ['trust: bad'] }], decisions: [], logs: {},
    questions: [{ id: 'Q-1', _errors: ['status: bad'], status: 'merged' }, { id: 'Q-2', _errors: ['origin: required'] }],
    claims: [{ id: 'C-1', _errors: ['question: required'] }, { id: 'C-2', question: 'Q-2', source: 'S-1' }] });
  assert.deepEqual(d.qs.map(x => x.id), ['Q-1', 'Q-2']);  // merged without merged_into is not hidden
  assert.equal(d.byId['Q-2'].claimsList.length, 1);
});

test('an invalid merge, out-of-scope question or withdrawn claim stays visible, marked, and its claims stay on a drawn question', () => {
  const q = (id, over) => ({ id, status: 'open', title: id, priority: 'high', origin: { type: 'user' }, _born: 1, ...over });
  const c = (id, question, over) => ({ id, question, source: 'S-1', status: 'unchecked', ...over });
  const d = prepare({ brief: {}, sources: [], decisions: [], logs: {},
    questions: [q('Q-w2-4', { status: 'merged', merged_into: 'Q-w9-9', _errors: ['merged_into: dangling'] }),
      q('Q-2', { status: 'merged', merged_into: 'Q-1' }), q('Q-1'),
      q('Q-5', { status: 'out of scope', _errors: ['owner: bad'] }), q('Q-6', { status: 'out of scope' })],
    claims: [c('C-w2-7', 'Q-w2-4'), c('C-w2-8', 'Q-w2-4'), c('C-9', 'Q-1', { status: 'withdrawn', _errors: ['replaced_by: required'] }),
      c('C-10', 'Q-1', { status: 'withdrawn' }), c('C-11', 'Q-2')] });
  assert.deepEqual(d.qs.map(x => x.id), ['Q-w2-4', 'Q-1', 'Q-5']);  // a valid merge or out of scope question is not drawn
  assert.deepEqual(d.byId['Q-w2-4'].claimsList.map(x => x.id), ['C-w2-7', 'C-w2-8']);
  assert.deepEqual(d.byId['Q-1'].claimsList.map(x => x.id), ['C-9', 'C-11']);  // the valid merge sends C-11 to Q-1
});

test('a question merged into itself, or two merged into each other, stay drawn with their claims', () => {
  const q = (id, over) => ({ id, status: 'open', title: id, priority: 'high', origin: { type: 'user' }, _born: 1, ...over });
  const c = (id, question) => ({ id, question, source: 'S-1', status: 'unchecked' });
  const d = prepare({ brief: {}, sources: [], decisions: [], logs: {},
    questions: [q('Q-1', { status: 'merged', merged_into: 'Q-1' }),
      q('Q-2', { status: 'merged', merged_into: 'Q-3' }), q('Q-3', { status: 'merged', merged_into: 'Q-2' }),
      q('Q-4', { status: 'merged', merged_into: 'Q-2' }), q('Q-5'), q('Q-6', { status: 'merged', merged_into: 'Q-5' })],
    claims: [c('C-1', 'Q-1'), c('C-2', 'Q-2'), c('C-3', 'Q-3'), c('C-4', 'Q-4'), c('C-5', 'Q-6')] });
  assert.deepEqual(d.qs.map(x => x.id), ['Q-1', 'Q-2', 'Q-3', 'Q-5']);  // Q-4 is merged into Q-2, which is drawn
  assert.deepEqual(d.byId['Q-1'].claimsList.map(x => x.id), ['C-1']);
  assert.deepEqual(d.byId['Q-2'].claimsList.map(x => x.id), ['C-2', 'C-4']);
  assert.deepEqual(d.byId['Q-3'].claimsList.map(x => x.id), ['C-3']);
  assert.deepEqual(d.byId['Q-5'].claimsList.map(x => x.id), ['C-5']);
});

test('a kept invalid claim with a list for its question does not stop the board from preparing', () => {
  const q = id => ({ id, status: 'open', title: id, priority: 'high', origin: { type: 'user' }, _born: 1 });
  const d = prepare({ brief: {}, sources: [], decisions: [], logs: {}, questions: [q('Q-1')],
    claims: [{ id: 'C-1', question: ['Q-1'], source: ['S-1'], _errors: ['question: expected string, got array'] },
      { id: 'C-2', source: 'S-1', _errors: ['question: required'] }] });
  assert.deepEqual(d.qs.map(x => x.id), ['Q-1']);
  assert.deepEqual(d.byId['Q-1'].claimsList, []);
});

test('the errors band is written only when its text changes, and the board gives it its note; a rendered board is read-only', () => {
  let writes = 0, html = '';
  const band = { hidden: true, get innerHTML() { return html; }, set innerHTML(v) { writes++; html = v; } };
  const errors = [{ file: 'a.json', line: 1, field: 'x', message: 'bad' }];
  pageShowErrors(band, errors); pageShowErrors(band, errors); pageShowErrors(band, [...errors]);
  assert.equal(writes, 1);
  pageShowErrors(band, []);
  assert.deepEqual([writes, band.hidden], [2, true]);

  pageShowErrors(band, errors, NOTE);
  assert.ok(html.includes('<p>' + NOTE + '</p>'), 'the board says what it shows of an invalid record');

  // The page itself passes that note to the band, and a rendered copy offers no answer, default or reply.
  const rendered = wholeBoard({ ...board({ id: 'S-w2-2' }), errors });
  assert.deepEqual([rendered.conversation.served, rendered.conversation.readOnly], [false, true]);
  assert.deepEqual(rendered.bands, [[errors, NOTE]]);
  const served = wholeBoard(null);
  assert.deepEqual([served.conversation.served, served.conversation.readOnly], [true, false]);
});

test('the board marks an invalid brief like any other record', () => {
  assert.equal(notValid({ title: 'T', _errors: ['stop_at: must be one of "high"'] }), 'not valid: stop_at: must be one of "high"');
});


// The agents at work: the board hands its question owners and checking claims to the shared list.
function agentsList(d) {
  const el = {};
  const document = new Proxy(stand(), { get: (t, k) => (k === 'getElementById' ? id => (id === 'agents' ? el : stand()) : t[k]) });
  loadBoard('{drawAgents}', { document }).drawAgents(d);
  return el.innerHTML;
}
const working = (id, owner) => ({ id, label: id, view: 'in progress', owner });

test('the board lists the owner of each question in progress and each checker of a claim, with what each works on', () => {
  const html = agentsList({ brief: {}, logs: {}, qs: [working('Q-1', 'w2'), working('Q-2', '')], claims: [{ status: 'checking', checker: 'v1' }, { status: 'verified', checker: 'v9' }] });
  assert.match(html, /<button type="button" data-a="w2" data-for="Q-1"><b>w2<\/b><span dir="auto">Q-1<\/span>/);
  assert.match(html, /data-a="unassigned"/);
  assert.match(html, /<b>v1<\/b>.*Checking claims/);
  assert.doesNotMatch(html, /v9/);
});

test('the board says so when no agent works, and when the run has stopped', () => {
  assert.match(agentsList({ brief: {}, logs: {}, qs: [], claims: [] }), /No agent is working right now\./);
  assert.match(agentsList({ brief: { status: 'stopped' }, logs: {}, qs: [], claims: [] }), /The run has stopped\./);
});

test('five searches in a row with nothing new are listed under the agent', () => {
  const searches = n => Array.from({ length: n }, () => ({ new_terms: [] }));
  assert.match(agentsList({ brief: {}, logs: { w2: { searches: searches(5) } }, qs: [working('Q-1', 'w2')], claims: [] }), /5 searches with nothing new/);
  assert.doesNotMatch(agentsList({ brief: {}, logs: { w2: { searches: searches(4) } }, qs: [working('Q-1', 'w2')], claims: [] }), /nothing new/);
});

test('an agent quiet for the threshold of the page says so, from the last word the board gives for it', () => {
  const now = Date.parse('2026-11-23T12:00:00Z') / 1000;
  const d = last => ({ now, quiet_after: 1800, last_word: { w2: last, v1: '2026-11-23T11:55:00Z' }, brief: {}, logs: {},
    qs: [working('Q-1', 'w2')], claims: [{ status: 'checking', checker: 'v1' }] });
  assert.match(agentsList(d('2026-11-23T11:20:00Z')), /No word from w2 for 40 min/);
  assert.doesNotMatch(agentsList(d('2026-11-23T11:40:00Z')), /No word/);
});

test('the board has no list of its own: it feeds the shared one', () => {
  assert.match(between(boardJs, 'function drawAgents', '\nfunction setHTML'), /pageAgents\(/);
  assert.doesNotMatch(boardJs, /class="verifier"|class="dry"/);
});

// ---- The board's own kinds inside the rows of the shared panel (S24, S25): board.js runs whole on the stand-in shell
// (tests/dom.js), with the shared page.js's real panel.
const { shellDocument, mixedDocument, panelOn, text, actions } = require('./dom');
const at = h => new Date(Date.parse('2026-11-28T12:00:00Z') - h * 3600e3).toISOString().slice(0, 19) + 'Z';
function liveBoard(data) {
  const doc = shellDocument();
  const shared = panelOn(null, null, { document: doc, config: { agent: 'coordinator', capabilities: ['pins', 'decisions'] } });
  const c = shared.context;
  const page = loadBoard('{render, conv}', {
    document: mixedDocument(doc), pageConversation: o => c.pageConversation(Object.assign({}, o, { served: false })),
    pageDecision: c.pageDecision, pageDecisionEvents: c.pageDecisionEvents, pageOpenDecisions: c.pageOpenDecisions,
    pageMarkdown: c.pageMarkdown, pageMarkdownText: c.pageMarkdownText, pageTime: c.pageTime, pageEscape: c.pageEscape,
  });
  page.render(Object.assign({ now: Date.parse('2026-11-28T12:00:00Z') / 1000, brief: { title: 'Speed', status: 'running' }, logs: {}, sources: [], claims: [],
    questions: [{ id: 'Q-1', status: 'answered', title: 'Page speed', priority: 'high', origin: { type: 'user' }, question: 'q?', summary: 's' }] }, data));
  return Object.assign(shared, page);
}
const BOARD_LOG = {
  decisions: [{ id: 'D1', at: at(3), asked: 'Search the forums too? They are slow.', status: 'waiting', default: 'No', deadline: '2026-11-28T13:00:00Z' }],
  conversation: [
    { type: 'closed', id: 'x1', by: 'worker-2', question: 'Q-1', status: 'answered', at: at(2) },
    { type: 'comment', id: 'c1', on: { kind: 'question', id: 'Q-1', title: 'Page speed' }, text: 'Check mobile too.', by: 'user', at: at(1) },
  ],
};

test('the board draws its kinds inside rows: a decision as your turn with its default and controls, a worker\'s close as a report, a comment with its crumb', () => {
  const b = liveBoard(BOARD_LOG);
  const d1 = b.rowOf('D1'), x1 = b.rowOf('x1'), c1 = b.rowOf('c1');
  assert.equal(text(d1.querySelector('.chip')), 'Your turn');
  assert.equal(text(d1.querySelector('.tgist')), 'Coordinator: Search the forums too?');
  assert.deepEqual(actions(d1).map(x => x.textContent), ['✓', 'Use the default', 'Answer']);
  assert.equal(x1, undefined);  // a worker report starts closed (D10): All only
  assert.equal(text(c1.querySelector('.chip')), 'Agent’s turn');
  assert.deepEqual(actions(c1).map(x => x.textContent), ['✓', 'Reply']);
  b.filter('all');
  assert.deepEqual(actions(b.rowOf('x1')).map(x => x.textContent), ['Reopen']);
  b.rowOf('x1').querySelector('.thead').click();
  assert.match(text(b.rowOf('x1').querySelector('.tbody')), /Answered: Page speed/);
  b.rowOf('D1').querySelector('.thead').click();
  assert.match(text(b.rowOf('D1').querySelector('.tbody')), /If you don't answer: No/);
  b.rowOf('c1').querySelector('.thead').click();
  assert.equal(text(b.rowOf('c1').querySelector('.crumb .el')), 'Page speed');
  // The figure in the board's own header, in the slot it leaves for it.
  assert.equal(text(b.$('#status #yourturn')), '1 your turn');
  assert.equal(b.$('#status #yourturn .stat').tagName, 'BUTTON');
});

test('answering the decision from its row records the answer and makes it the agent\'s turn; the figure says 0', () => {
  const b = liveBoard(BOARD_LOG);
  actions(b.rowOf('D1'))[2].click();
  const box = b.rowOf('D1').querySelector('.why textarea');
  box.input('Yes, the forums too.');
  box.key('Enter', { ctrlKey: true });
  assert.deepEqual(b.conv.log().filter(e => e.type === 'answer').map(e => [e.decision, e.text, e.default]), [['D1', 'Yes, the forums too.', false]]);
  assert.equal(text(b.rowOf('D1').querySelector('.chip')), 'Agent’s turn');
  assert.equal(text(b.$('#status #yourturn')), '0 your turn');
});

test('the board gives the panel none of the options of the old per-item drawing', () => {
  let o;
  loadBoard('0', { pageConversation: opts => { o = opts; return stand(); } });
  for (const gone of ['steps', 'labels', 'shown', 'accept', 'filter', 'waiting', 'latestLast', 'agentKinds']) assert.ok(!(gone in o), gone);
  assert.deepEqual(Object.keys(o.kinds).sort(), ['closed', 'decision']);
});
