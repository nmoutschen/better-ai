// The discover-better page's own script (src/better_ai/discover/page.js): the counting of open questions, the chips, the
// escaping, the choose and remove events, the agents at work, and the text of every control. Run with
// `node --test tests/*.test.js`. The script's pure part, up to its start marker, runs here with the shared page.js.
const test = require('node:test');
const assert = require('node:assert/strict');
const { read, between, loadPage, stand } = require('./harness');

const shared = loadPage();
const source = read('discover', 'page.js');
const NOW = Date.parse('2026-11-23T12:00:00Z') / 1000;
const ago = minutes => new Date((NOW - minutes * 60) * 1000).toISOString().slice(0, 19) + 'Z';

function pure(returns, over = {}) {
  const env = Object.assign({
    document: stand(), pageEscape: shared.pageEscape, pageThread: shared.pageThread, pageDecisionEvents: shared.pageDecisionEvents,
    pageDecision: shared.pageDecision, pageAgents: shared.pageAgents, pageTime: shared.pageTime,
    pageMarkdown: t => ({ outerHTML: '<p>' + shared.pageEscape(t) + '</p>' }), pageMarkdownText: String,
  }, over);
  return new Function(...Object.keys(env), `${between(source, '', '// ---------- Start ----------')}; return ${returns};`)(...Object.values(env));
}
const waitingOf = () => shared.pageDecision({ conversation: { progress: () => stand() }, now: () => NOW, md: String, esc: shared.pageEscape, id: p => p }).waiting;
const api = () => pure('{TABS, openQuestions, aboutTab, badges, tabLabel, stateChip, safeLink, idLink, firstSentence, agentRows, ' +
  'chooseParams, removeFor, pendingChoose, headerHTML, movesPanel, itemsTable, evidencePanel, optionsPanel, testsPanel, briefPanel, ' +
  'choosePanel, addEvidenceForm, resultForm, removeForm, changeForm, atWork, briefLabel}');

const rec = (type, over) => ({ type, at: ago(60), by: 'coord', ...over });
function fixture(over = {}) {
  const item = (id, kind, text, o = {}) => rec('item', { id, kind, text, rests_on: [], risks: [], state: 'unverified', recorded_state: 'unverified', importance: null,
    accepted_risks: [], open_risks: [], ...o });
  const ev = (id, o = {}) => rec('evidence', { id, source: 'S-' + id.slice(2), text: 'We lost a week.', words: { type: 'quote', text: 'We lost a week.' }, kind: 'say',
    about: 'elsewhere', bears_on: [{ item: 'P1', direction: 'for' }], status: 'counts', origin: { type: 'web', url: 'https://example.com/a', read: 'raw' },
    source_title: 'A post', ...o });
  const data = {
    now: NOW, errors: [],
    head: { idea: 'A page that shows where an idea stands.', appetite: 'two weeks', setting: 'external', brought: 'notes', step: '5', status: 'open', coordinator: 'coord' },
    items: [
      item('P1', 'problem', 'People lose track. They forget what they checked.', { state: 'supported', recorded_state: 'supported', importance: 'high' }),
      item('P2', 'problem', 'Nobody pays.', { state: 'checking', recorded_state: 'checking', checker: 'analyst-1', since: ago(12), tries: ['analyst-1'] }),
      item('O1', 'opportunity', 'A weekly digest.'),
      item('B1', 'behaviour', 'Shows state.', { rests_on: ['P1'], testable: { form: 'ears', text: 'When an item changes, the page shall show it.' },
        risks: [{ id: 'R1', kind: 'value', text: 'Nobody reads it.' }] }),
    ],
    changes: [], options: [
      rec('option', { id: 'K1', move: 'test first', text: 'Run the probe.', cost: 'an afternoon', speed: 'a day', upkeep: 'none', undo: 'nothing to undo', note: 'proposed' }),
      rec('option', { id: 'K2', move: 'shrink', text: 'Owners only.', cost: 'a week', speed: 'two days', upkeep: 'low', undo: 'easy', note: null }),
      rec('option', { id: 'K3', move: 'expand', text: 'Everyone.', cost: 'a month', speed: 'a month', upkeep: 'high', undo: 'hard to undo', note: 'ruled out by your appetite' }),
    ],
    moves: [], briefs: [], decisions: [
      rec('decision', { id: 'D1', about: { type: 'item', item: 'P1' }, asked: 'Is P1 the main problem?', default: 'Yes', status: 'waiting', raised_by: 'coord' }),
      rec('decision', { id: 'D2', about: { type: 'risk', item: 'B1', risk: 'R1' }, asked: 'Accept R1?', default: 'Accept the risk', status: 'waiting', raised_by: 'coord' }),
      rec('decision', { id: 'D3', about: { type: 'discovery' }, asked: 'Choose a move.', default: null, status: 'waiting', raised_by: 'coord' }),
      rec('decision', { id: 'D4', about: { type: 'item', item: 'O1' }, asked: 'Keep O1?', default: 'Yes', status: 'answered', raised_by: 'coord',
        answer: { type: 'chat', text: 'Keep it.' }, answered_at: ago(5) }),
    ],
    tests: [
      rec('test', { id: 'X1', what: 'Ask five people.', kind: 'probe', settles: ['P1'], cost: 'an afternoon', rule: 'Stop if fewer than two succeed.', runner: 'you', status: 'planned' }),
      rec('test', { id: 'X2', what: 'Scan the forums.', kind: 'probe', settles: ['P2'], cost: 'an hour', rule: 'Change if none.', runner: 'analyst', status: 'running', checker: 'analyst-2', since: ago(31) }),
    ],
    evidence: [
      ev('E-a1-1'),
      ev('E-coord-1', { about: 'your users', origin: { type: 'you', given: { type: 'chat', text: 'x' } }, source_title: 'You, in the chat' }),
      ev('E-a2-1', { status: 'checking', words: { type: 'quote', text: 'x' }, text: 'x', at: ago(5) }),
      ev('E-a3-1', { status: 'checking', verifier: 'ver-1', tries: ['ver-0', 'ver-1'], since: ago(3) }),
    ],
    sources: [], revisions: { K1: 'r1', K2: 'r2', K3: 'r3' }, chosen: null, conversation: [],
  };
  return Object.assign(data, over);
}
const ctx = (data, over = {}) => {
  const a = api();
  const open = a.openQuestions(data.decisions, data.conversation, waitingOf());
  return Object.assign({ open, now: NOW, pending: null, badges: a.badges(open, data.items) }, over);
};

test('the tabs follow the work, in the designed order', () => {
  assert.deepEqual(api().TABS.map(t => t[1]), ['Moves', 'Problems', 'Opportunities', 'Behaviours', 'Evidence', 'Options', 'Tests', 'Brief']);
});

// ---------- S80, A2, S1: one count ----------
test('S80: the header, the badges and the conversation count open questions through one function; a due move is a waiting decision about the discovery', () => {
  const a = api(), d = fixture();
  const open = a.openQuestions(d.decisions, d.conversation, waitingOf());
  assert.deepEqual(open.map(x => x.id), ['D1', 'D2', 'D3']);
  assert.equal(a.aboutTab(d.decisions[2], d.items), 'moves');
  const badges = a.badges(open, d.items);
  assert.equal(badges.moves, 3);
  assert.equal(badges.problems, 1);
  assert.equal(badges.behaviours, 1);  // D2 is about a risk of B1
  assert.equal(badges.opportunities || 0, 0);  // D4 is answered
  assert.match(a.headerHTML(d, open), /<b>3<\/b>open questions/);
});

test('S1, A2: an answer from the page drops the question from the header, the Moves badge and the item badge together; so does an answer in the chat', () => {
  const a = api(), d = fixture();
  const answer = { type: 'answer', at: ago(1), by: 'user', id: 'a1', decision: 'D1', text: 'Yes', default: true };
  const open = a.openQuestions(d.decisions, [answer], waitingOf());
  assert.deepEqual(open.map(x => x.id), ['D2', 'D3']);
  assert.equal(a.badges(open, d.items).moves, 2);
  assert.equal(a.badges(open, d.items).problems || 0, 0);
  const chat = d.decisions.map(x => x.id === 'D2' ? { ...x, status: 'answered', answer: { type: 'chat', text: 'ok' }, answered_at: ago(1) } : x);
  assert.deepEqual(a.openQuestions(chat, [answer], waitingOf()).map(x => x.id), ['D3']);
});

test('A2: a tab with open questions has a badge with an accessible name; with none, no badge', () => {
  const a = api();
  assert.equal(a.tabLabel('Problems', 2), 'Problems, 2 open questions');
  assert.equal(a.tabLabel('Problems', 1), 'Problems, 1 open question');
  assert.equal(a.tabLabel('Problems', 0), 'Problems');
});

test('S106: 0 open questions is a plain figure, not a button; with some, the figure is a button that goes to the first', () => {
  const a = api(), d = fixture();
  const none = a.headerHTML(d, []);
  assert.match(none, /<b>0<\/b>open questions/);
  assert.doesNotMatch(none, /<button[^>]*>\s*<b>0/);
  assert.match(a.headerHTML(d, [d.decisions[0]]), /<button type="button" class="stat" id="questions"><b>1<\/b>open question<\/button>/);
});

test('S2: the header names the step, the last move and the brief version', () => {
  const a = api(), d = fixture({
    moves: [rec('move', { id: 'M1', option: 'K2', step: '3', why: 'Owners first.', answer: { type: 'page', event: 'c1' } })], chosen: 'K2',
    briefs: [rec('brief', { id: 'v1', move: 'M1', status: 'draft' })],
  });
  const html = a.headerHTML(d, []);
  assert.match(html, /Step 5: your calls/);
  assert.match(html, /Shrink: Owners only\./);
  assert.match(html, /v1, being written/);
  assert.equal(a.briefLabel(fixture({ moves: d.moves, briefs: [rec('brief', { id: 'v1', move: 'M1', status: 'final' })] })), 'v1, final');
  assert.equal(a.briefLabel(fixture({ briefs: [rec('brief', { id: 'v1', move: 'M9', status: 'draft' })] })), 'v1, draft');
  assert.equal(a.briefLabel(fixture()), 'no brief yet');
});

// ---------- S81 ----------
test('S81: every record field is escaped, wherever it is shown', () => {
  const a = api(), bad = '<img src=x onerror=alert(1)>';
  const d = fixture();
  d.items[0].text = bad;
  d.items[1].risks = [{ id: 'R1', kind: 'value', text: bad }];
  d.items[3].testable.text = bad;
  d.evidence[0].text = bad; d.evidence[0].source_title = bad;
  d.tests[0].what = bad; d.tests[0].rule = bad; d.tests[0].cost = bad;
  d.options[0].text = bad; d.options[1].cost = bad;
  d.decisions[0].asked = bad; d.decisions[0].default = bad;
  d.head.idea = bad; d.head.appetite = bad; d.head.brought = bad;
  d.moves = [rec('move', { id: 'M1', option: 'K1', step: '2', why: bad, answer: { type: 'chat', text: 'x' } })];
  const c = ctx(d);
  const html = [a.movesPanel(d, c), a.itemsTable('problem', d, c), a.itemsTable('behaviour', d, c), a.evidencePanel(d, c), a.optionsPanel(d, c), a.testsPanel(d, c),
    a.choosePanel(d, c), a.headerHTML(d, c.open), a.addEvidenceForm(d)].join('');
  assert.doesNotMatch(html, /<img/);
  assert.match(html, /&lt;img src=x onerror=alert\(1\)&gt;/);
});

test('S81: a source address is a link only for http and https', () => {
  const a = api();
  assert.match(a.safeLink('https://example.com/a?x=1&y="2"', 'A post'), /^<a href="https:\/\/example.com\/a\?x=1&amp;y=&quot;2&quot;"[^>]*>A post<\/a>$/);
  assert.match(a.safeLink('http://example.com', 'x'), /^<a href="http:/);
  for (const url of ['javascript:alert(1)', 'JaVaScRiPt:alert(1)', ' javascript:alert(1)', 'data:text/html,x', 'file:///etc/passwd', '//evil.example', 'ftp://x', '', null, 5]) {
    const out = a.safeLink(url, 'A <b>post</b>');
    assert.doesNotMatch(out, /<a /, String(url));
    assert.match(out, /A &lt;b&gt;post&lt;\/b&gt;/);
  }
  const d = fixture();
  d.evidence[0].origin = { type: 'web', url: 'javascript:alert(1)', read: 'raw' };
  assert.doesNotMatch(api().evidencePanel(d, ctx(d)), /href="javascript/i);
});

// ---------- S103 ----------
test('S103: each state is a chip of its meaning, and the word always says it', () => {
  const a = api();
  const k = (state, o) => a.stateChip(state, o);
  assert.match(k('supported'), /class="chip ok">Supported</);
  assert.match(k('contradicted'), /class="chip error">Contradicted</);
  assert.match(k('checking', { minutes: 12 }), /class="chip working">Checking, 12 min</);
  assert.match(k('waiting for you'), /class="chip wait">Waiting for you</);
  assert.match(k('proposed'), /class="chip wait">Proposed</);
  assert.match(k('being written', { version: 'v2' }), /class="chip working">v2 being written</);
  for (const [state, word] of [['needs a test', 'Needs a test'], ['unverified', 'Unverified'], ['risk accepted', 'Risk accepted'], ['chosen', 'Chosen'], ['alternative', 'Alternative idea']]) {
    assert.match(k(state), new RegExp('class="chip">' + word + '<'), state);
  }
});

test('S103: red means only Contradicted: no other chip is an error chip', () => {
  const a = api(), d = fixture();
  d.evidence.push({ ...d.evidence[0], id: 'E-a9-1', status: 'not reachable', reason: 'HTTP 403' }, { ...d.evidence[0], id: 'E-a9-2', status: 'unverified', reason: 'reworded' });
  const html = [a.movesPanel(d, ctx(d)), a.itemsTable('problem', d, ctx(d)), a.evidencePanel(d, ctx(d)), a.optionsPanel(d, ctx(d)), a.testsPanel(d, ctx(d))].join('');
  assert.doesNotMatch(html, /chip error/);
  d.items[0].state = 'contradicted';
  assert.match(a.itemsTable('problem', d, ctx(d)), /chip error">Contradicted/);
});

// ---------- S37, S104, S105, S57 ----------
test('S37: the choose event holds an id, the option, the revision as shown, and confirmed', () => {
  const a = api(), d = fixture();
  const p = a.chooseParams(d.options[1], d.revisions, false);
  assert.deepEqual(Object.keys(p).sort(), ['confirmed', 'id', 'option', 'revision']);
  assert.equal(p.option, 'K2'); assert.equal(p.revision, 'r2'); assert.equal(p.confirmed, false);
  assert.match(p.id, /^c-/);
  assert.equal(a.chooseParams(d.options[2], d.revisions, true).confirmed, true);
});

test('S104: Remove on evidence from you, or in an internal discovery, posts redact; elsewhere it posts remove with the reason', () => {
  const a = api(), d = fixture();
  const yours = d.evidence[1], web = d.evidence[0];
  assert.deepEqual(a.removeFor(yours, d.head, 'wrong person'), { method: 'redact', params: { evidence: 'E-coord-1' } });
  assert.deepEqual(a.removeFor(web, d.head, 'old'), { method: 'remove', params: { record: 'E-a1-1', reason: 'old' } });
  assert.equal(a.removeFor(web, { ...d.head, setting: 'internal' }, 'old').method, 'redact');
  assert.deepEqual(a.removeFor(d.tests[0], d.head, 'not needed'), { method: 'remove', params: { record: 'X1', reason: 'not needed' } });
});

test('S105, S57: after a choose event the option shows Waiting for the agent and Choose is off; once it is done with no move, Choose is on again', () => {
  const a = api(), d = fixture();
  const sent = { type: 'choose', at: ago(1), by: 'user', id: 'c1', option: 'K2', revision: 'r2', confirmed: false };
  assert.equal(a.pendingChoose([sent], {}, d.moves).id, 'c1');
  assert.equal(a.pendingChoose([sent], { c1: 'seen' }, d.moves).id, 'c1');
  assert.equal(a.pendingChoose([sent], { c1: 'done' }, d.moves), null);  // done with no move: the user may choose again
  const moved = [rec('move', { id: 'M1', option: 'K2', step: '5', why: 'x', answer: { type: 'page', event: 'c1' } })];
  assert.equal(a.pendingChoose([sent], {}, moved), null);  // recorded: nothing is waiting
  const c = ctx(d, { pending: sent });
  const html = a.choosePanel(d, c) + a.optionsPanel(d, c);
  assert.match(html, /Waiting for the agent/);
  assert.match(a.choosePanel(d, c), /<button[^>]*disabled[^>]*>Choose this move/);
  assert.doesNotMatch(a.choosePanel(d, ctx(d)), /<button[^>]*disabled[^>]*>Choose this move/);
});

test('A13, A15: the picker groups options by move with the proposal chosen; a costly move has a confirming step; the open-question line is live', () => {
  const a = api(), d = fixture(), html = a.choosePanel(d, ctx(d));
  assert.match(html, /name="option" value="K1" checked/);
  assert.match(html, /data-confirm-for="K3"/);  // expand
  assert.doesNotMatch(html, /data-confirm-for="K2"/);  // shrink needs no second click
  assert.match(html, /3 questions are still open: answer them first, or take their defaults/);
  const none = a.choosePanel(d, { ...ctx(d), open: [] });
  assert.match(none, /id="open-line"[^>]*hidden/);
  assert.match(html, /ruled out by your appetite/i);
  for (const word of ['an afternoon', 'a day', 'none', 'nothing to undo']) assert.match(html, new RegExp(word));
});

// ---------- S56, S84, S102 ----------
test('S102, S84: the at-work list has a row for each item and test with a checker and each evidence with a verifier, aged from since', () => {
  const a = api(), d = fixture();
  const rows = a.agentRows(d, NOW);
  assert.deepEqual(rows.map(r => r.who).sort(), ['analyst-1', 'analyst-2', 'ver-1']);
  const verifier = rows.find(r => r.who === 'ver-1');
  assert.equal(verifier.kind, 'verifier');
  assert.equal(verifier.second, true);  // two tries
  assert.equal(rows.find(r => r.who === 'analyst-1').since, ago(12));
  assert.equal(rows.find(r => r.who === 'analyst-1').data.goto, 'P2');
  const html = a.atWork(d, NOW);
  assert.match(html, /Checking, 12 min/);
  assert.match(html, /second try/);
  assert.match(html, /No word from analyst-2 for 31 min/);
});

test('S56: a check that has no word for 30 minutes says so; the last word is the latest record that carries the agent', () => {
  const a = api(), d = fixture();
  d.tests[1].since = ago(40);
  d.evidence.push(rec('evidence', { id: 'E-analyst-2-1', by: 'analyst-2', at: ago(5), source: 'S-x', words: { type: 'quote', text: 'q' }, text: 'q', kind: 'say', about: 'elsewhere', bears_on: [], status: 'checking' }));
  const quiet = a.agentRows(d, NOW).find(r => r.who === 'analyst-2');
  assert.equal(new Date(quiet.last).toISOString().slice(0, 19) + 'Z', ago(5));
  assert.doesNotMatch(a.atWork(d, NOW), /No word from analyst-2/);
});

test('S56: evidence checking with no verifier reads Waiting for a verifier with its age; a chat act reads recorded from the chat', () => {
  const a = api(), d = fixture();
  assert.match(a.evidencePanel(d, ctx(d)), /Waiting for a verifier, 5 min/);
  assert.match(a.evidencePanel(d, ctx(d)), /Checking quote/);
  assert.match(a.evidencePanel(d, ctx(d)), /recorded from the chat/);
  d.moves = [rec('move', { id: 'M1', option: 'K1', step: '5', why: 'Probe first.', answer: { type: 'chat', text: 'go' } })];
  assert.match(a.movesPanel(d, ctx(d)), /recorded from the chat/);
  d.moves[0].answer = { type: 'page', event: 'c1' };
  d.decisions = d.decisions.filter(x => x.id !== 'D4');  // answered in the chat too
  assert.doesNotMatch(a.movesPanel(d, ctx(d)), /recorded from the chat/);
});

// ---------- the panels ----------
test('A3: an ID shown outside its own row is a link that goes to its row; an unknown ID is plain text', () => {
  const a = api(), d = fixture();
  const html = a.itemsTable('behaviour', d, ctx(d));
  assert.match(html, /<a href="#row-P1" data-goto="P1">P1<\/a>/);  // B1 rests on P1
  assert.match(html, /id="row-B1"/);
  assert.match(a.evidencePanel(d, ctx(d)), /<a href="#row-P1" data-goto="P1">P1<\/a>/);
  assert.match(a.testsPanel(d, ctx(d)), /<a href="#row-P1" data-goto="P1">P1<\/a>/);
  assert.match(a.movesPanel(d, ctx(d)), /<a href="#row-P1" data-goto="P1">P1<\/a>/);  // D1 is about P1
  assert.equal(a.idLink('P9', new Set(['P1'])), 'P9');
});

test('the item tables: first sentence, then More; importance, state, evidence for and against here and elsewhere; Question open; Alternative idea', () => {
  const a = api(), d = fixture();
  d.items[3].alternative = { type: 'move', move: 'M1' };
  const html = a.itemsTable('problem', d, ctx(d));
  assert.match(html, /People lose track\./);
  assert.match(html, /<details[^>]*><summary>More<\/summary>[^]*They forget what they checked\./);
  assert.match(html, /Question open/);  // D1 is about P1
  assert.match(html, /1 for/);
  assert.match(a.itemsTable('behaviour', d, ctx(d)), /Alternative idea/);
  assert.match(a.itemsTable('behaviour', d, ctx(d)), /When an item changes, the page shall show it\./);  // the testable form
  assert.match(a.itemsTable('opportunity', fixture({ items: [] }), ctx(fixture())), /No opportunities yet\. The draft may not need one\./);
  assert.match(html, /Checking, 12 min/);  // the age on the item chip
});

test('risks by kind show only under an item\'s More (issue 125)', () => {
  const a = api(), d = fixture();
  const html = a.itemsTable('behaviour', d, ctx(d));
  const before = html.slice(0, html.indexOf('<details'));
  assert.doesNotMatch(before, /Nobody reads it/);
  assert.match(html, /<details[^>]*>[^]*Nobody reads it\./);
});

test('the Evidence tab: users, not yet known, elsewhere; Checking quote; not reachable and unverified stay on the row and do not count', () => {
  const a = api(), d = fixture();
  d.evidence.push({ ...d.evidence[0], id: 'E-a9-1', status: 'not reachable', reason: 'HTTP 403' });
  const html = a.evidencePanel(d, ctx(d));
  for (const heading of ['About your users', 'Not yet known for your users', 'From elsewhere']) assert.match(html, new RegExp(heading));
  assert.match(html, /Source not reachable/);
  assert.match(html, /Remove…/);
  assert.match(html, /Add evidence…/);
  assert.match(a.evidencePanel(fixture({ evidence: [] }), ctx(fixture())), /No evidence yet\./);
});

test('the Options tab: before the evidence is in, a plain line; after, one row per option with its note and Chosen', () => {
  const a = api(), d = fixture();
  assert.match(a.optionsPanel(d, ctx(d)), /Run the probe\./);
  assert.match(a.optionsPanel(d, ctx(d)), /chip wait">Proposed/);
  assert.match(a.optionsPanel(d, ctx(d)), /ruled out by your appetite/i);
  assert.match(a.optionsPanel(fixture({ options: [] }), ctx(fixture())), /Options appear once the evidence is in\./);
  const chosen = fixture({ chosen: 'K2' });
  assert.match(a.optionsPanel(chosen, ctx(chosen)), /chip">Chosen/);
});

test('the Tests tab: run order, Running with who runs it, a result with holds or changes the decision, removed tests with their reason', () => {
  const a = api(), d = fixture();
  let html = a.testsPanel(d, ctx(d));
  assert.match(html, /Running/); assert.match(html, /analyst/); assert.match(html, /Add result…/);
  d.tests.push(rec('test', { id: 'X3', what: 'Pilot.', kind: 'pilot', settles: ['P1'], cost: 'a week', rule: 'r', runner: 'you', status: 'done', result: { text: 'Nobody came.', outcome: 'changes', evidence: [] } }),
    rec('test', { id: 'X4', what: 'Old.', kind: 'probe', settles: ['P1'], cost: 'c', rule: 'r', runner: 'you', status: 'removed', reason: 'No longer needed.' }));
  html = a.testsPanel(d, ctx(d));
  assert.match(html, /changes the decision/);
  assert.match(html, /Removed tests/); assert.match(html, /No longer needed\./);
  assert.match(a.testsPanel(fixture({ tests: [] }), ctx(fixture())), /No tests planned\./);
});

test('the Moves tab: the idea, Waiting for you with defaults and the item, Answered, the decision log, the setting with Change', () => {
  const a = api(), d = fixture();
  d.moves = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map(n => rec('move', { id: 'M' + n, option: 'K2', step: '3', why: 'Why ' + n, answer: { type: 'page', event: 'c' + n } }));
  const html = a.movesPanel(d, ctx(d));
  assert.match(html, /A page that shows where an idea stands\./);
  assert.match(html, /Waiting for you/);
  assert.match(html, /Suggested default: Yes/);
  assert.match(html, /Answered/); assert.match(html, /Default taken|Your answer/);
  assert.match(html, /Decision log/);
  assert.match(html, /Earlier moves \(2\)/);  // the last 10 show
  assert.match(html, /Why 12/);
  for (const w of ['Appetite', 'Setting', 'Brought']) assert.match(html, new RegExp(w));
  assert.equal((html.match(/>Change</g) || []).length, 3);
  assert.match(api().movesPanel(fixture({ decisions: [], moves: [] }), ctx(fixture({ decisions: [] }))), /Nothing waits for you\./);
  assert.match(api().movesPanel(fixture({ decisions: [], moves: [] }), ctx(fixture({ decisions: [] }))), /No move yet\./);
});

test('the Brief tab: the current version and the earlier ones behind a disclosure', () => {
  const a = api(), d = fixture({ briefs: [rec('brief', { id: 'v1', move: 'M1', status: 'final', text: '# One' }), rec('brief', { id: 'v2', move: 'M2', status: 'final', text: '# Two' })] });
  const html = a.briefPanel(d, ctx(d));
  assert.match(html, /v2/);
  assert.match(html, /Earlier versions \(1\)/);
  assert.match(a.briefPanel(fixture(), ctx(fixture())), /No brief yet/);
});

test('evidence that is still being checked says it does not count; a move that writes a brief names it on the Brief tab until the brief is there', () => {
  const a = api(), d = fixture();
  assert.match(a.evidencePanel(d, ctx(d)), /It does not count until the check passes\./);
  d.moves = [rec('move', { id: 'M2', option: 'K2', step: '5', why: 'x', answer: { type: 'page', event: 'c1' } })];
  assert.match(a.briefPanel(d, ctx(d)), /v1 is being written for <a href="#row-M2"[^>]*>M2<\/a> \(Shrink\)/);
  d.briefs = [rec('brief', { id: 'v1', move: 'M2', status: 'draft', decision: 'Shrink.' })];
  assert.doesNotMatch(a.briefPanel(d, ctx(d)), /is being written for/);
});

// ---------- A5 ----------
// The text of every button that is not a tab or the header's count.
const buttonLabels = html => [...html.matchAll(/<button\b([^>]*)>([^]*?)<\/button>/g)].filter(m => !/role="tab"|id="questions"/.test(m[1])).map(m => m[2].replace(/<[^>]*>/g, '').trim());

test('A5: the page\'s own controls use five verbs, plus Send and Cancel, and the exit action reads Choose a move…', () => {
  const a = api(), d = fixture();
  d.moves = [rec('move', { id: 'M1', option: 'K1', step: '5', why: 'x', answer: { type: 'chat', text: 'go' } })];
  d.briefs = [rec('brief', { id: 'v1', move: 'M1', status: 'final', text: '# One' })];
  const c = ctx(d);
  const html = [a.movesPanel(d, c), ...['problem', 'opportunity', 'behaviour'].map(k => a.itemsTable(k, d, c)), a.evidencePanel(d, c), a.optionsPanel(d, c), a.testsPanel(d, c),
    a.briefPanel(d, c), a.choosePanel(d, c)].join('');
  const forms = a.addEvidenceForm(d) + a.resultForm(d.tests[0]) + a.removeForm(d.items[0], d.head) + a.changeForm('item', 'P1');
  const labels = buttonLabels(html + forms);
  assert.ok(labels.length > 10);
  const allowed = /^(Add|Change|Remove|Answer|Choose|Send|Cancel|✓)/;
  for (const label of labels) assert.match(label, allowed, label);
  assert.ok(labels.includes('Choose a move…'), 'the exit action reads Choose a move…');
  assert.doesNotMatch(html, /Reopen|Edit|Delete|Update|Save|Submit|Create|Approve|Reply/);
});

test('A4: every form field has a visible label tied to it', () => {
  const a = api(), d = fixture(), html = a.addEvidenceForm(d) + a.resultForm(d.tests[0]) + a.removeForm(d.items[0], d.head) + a.changeForm('item', 'P1') + a.changeForm('', 'discovery', 'setting');
  const fields = [...html.matchAll(/<(textarea|input|select)\b([^>]*)>/g)].filter(m => !/type="(radio|checkbox|hidden)"/.test(m[2]));
  assert.ok(fields.length >= 6);
  for (const [, , attrs] of fields) {
    const id = /\bid="([^"]+)"/.exec(attrs);
    assert.ok(id, 'a field has an id: ' + attrs);
    assert.match(html, new RegExp('<label[^>]*for="' + id[1] + '"'), id[1]);
  }
});

test('A1: tabs are the first thing in the page and follow the tabs pattern', () => {
  const html = read('discover', 'page.html');
  assert.match(html, /class="tabs tabs--wrap" role="tablist"/);
  for (const [i, key] of ['moves', 'problems', 'opportunities', 'behaviours', 'evidence', 'options', 'tests', 'brief'].entries()) {
    assert.match(html, new RegExp('role="tab" id="tab-' + key + '" aria-selected="' + (i === 0) + '" aria-controls="panel-' + key + '"' + (i ? ' tabindex="-1"' : '')));
    assert.match(html, new RegExp('role="tabpanel" aria-labelledby="tab-' + key + '"'));
  }
  assert.match(source, /ArrowLeft/); assert.match(source, /Home/); assert.match(source, /End/);
});
