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
    document: stand(), pageEscape: shared.pageEscape, pageThreads: shared.pageThreads, pageDecisionEvents: shared.pageDecisionEvents, pageOpenDecisions: shared.pageOpenDecisions,
    pageDecision: shared.pageDecision, pageAgents: shared.pageAgents, pageTime: shared.pageTime,
    pageMarkdown: t => ({ outerHTML: '<p>' + shared.pageEscape(t) + '</p>' }), pageMarkdownText: String,
  }, over);
  return new Function(...Object.keys(env), `${between(source, '', '// ---------- Start ----------')}; return ${returns};`)(...Object.values(env));
}
const api = () => pure('{TABS, openQuestions, aboutTab, badges, tabLabel, stateChip, safeLink, idLink, firstSentence, agentRows, ' +
  'chooseParams, removeFor, nextAfter, riskCounts, riskItem, tabOf, evidenceLabel, evidenceBlock, pendingChoose, headerHTML, movesPanel, itemsTable, evidencePanel, optionsPanel, testsPanel, briefPanel, ' +
  'choosePanel, addEvidenceForm, resultForm, removeForm, changeForm, atWork, briefLabel}');

const rec = (type, over) => ({ type, at: ago(60), by: 'coord', ...over });
function fixture(over = {}) {
  const item = (id, kind, text, o = {}) => rec('item', { id, kind, text, rests_on: [], risks: [], state: 'unverified', recorded_state: 'unverified', importance: null,
    accepted_risks: [], open_risks: [], ...o });
  const ev = (id, o = {}) => rec('evidence', { id, source: 'S-' + id.slice(2), text: 'We lost a week.', words: { type: 'quote', text: 'We lost a week.' }, kind: 'say',
    about: 'elsewhere', bears_on: [{ item: 'P1', direction: 'for' }], status: 'counts', origin: { type: 'web', url: 'https://example.com/a', read: 'raw' },
    source_title: 'A post', ...o });
  const data = {
    now: NOW, quiet_after: 1800, errors: [],
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
  const open = a.openQuestions(data.decisions, data.conversation);
  return Object.assign({ open, now: NOW, pending: null, badges: a.badges(open, data.items) }, over);
};

test('the tabs follow the work, in the designed order', () => {
  assert.deepEqual(api().TABS.map(t => t[1]), ['Moves', 'Problems', 'Opportunities', 'Behaviours', 'Evidence', 'Options', 'Tests', 'Brief']);
});

// ---------- S80, A2, S1: one count ----------
test('S80: the header, the badges and the conversation count open questions through one function; a due move is a waiting decision about the discovery', () => {
  const a = api(), d = fixture();
  const open = a.openQuestions(d.decisions, d.conversation);
  assert.deepEqual(open.map(x => x.id), ['D1', 'D2', 'D3']);
  assert.equal(a.aboutTab(d.decisions[2], d.items), 'moves');
  const badges = a.badges(open, d.items);
  assert.equal(badges.moves, 3);
  assert.equal(badges.problems, 1);
  assert.equal(badges.behaviours, 1);  // D2 is about a risk of B1
  assert.equal(badges.opportunities || 0, 0);  // D4 is answered
  assert.match(a.headerHTML(d), /<span class="yourturn" id="yourturn"><\/span>/);  // page.js's figure counts the threads that are your turn
});

test('S1, A2: an answer from the page drops the question from the header, the Moves badge and the item badge together; so does an answer in the chat', () => {
  const a = api(), d = fixture();
  const answer = { type: 'answer', at: ago(1), by: 'user', id: 'a1', decision: 'D1', text: 'Yes', default: true };
  const open = a.openQuestions(d.decisions, [answer]);
  assert.deepEqual(open.map(x => x.id), ['D2', 'D3']);
  assert.equal(a.badges(open, d.items).moves, 2);
  assert.equal(a.badges(open, d.items).problems || 0, 0);
  const chat = d.decisions.map(x => x.id === 'D2' ? { ...x, status: 'answered', answer: { type: 'chat', text: 'ok' }, answered_at: ago(1) } : x);
  assert.deepEqual(a.openQuestions(chat, [answer]).map(x => x.id), ['D3']);
});

test('A2: a tab with open questions has a badge with an accessible name; with none, no badge', () => {
  const a = api();
  assert.equal(a.tabLabel('Problems', 2), 'Problems, 2 open questions');
  assert.equal(a.tabLabel('Problems', 1), 'Problems, 1 open question');
  assert.equal(a.tabLabel('Problems', 0), 'Problems');
});

test('S106: the header has one figure for what waits for you: the shared "N your turn" (page.js), in the slot it leaves, never its own', () => {
  const a = api(), d = fixture();
  const html = a.headerHTML(d);
  assert.equal((html.match(/id="yourturn"/g) || []).length, 1);
  assert.doesNotMatch(html, /open question|id="questions"/);
  assert.match(source, /stats: \(\) => byId\('yourturn'\)/);
});

test('S2: the header holds figures only: the step of ten, the brief version and the threads that are your turn; never a sentence', () => {
  const a = api(), d = fixture({
    moves: [rec('move', { id: 'M1', option: 'K2', step: '3', why: 'Owners first.', answer: { type: 'page', event: 'c1' } })], chosen: 'K2',
    briefs: [rec('brief', { id: 'v1', move: 'M1', status: 'draft' })],
  });
  const html = a.headerHTML(d);
  const stats = [...html.matchAll(/<b>(.*?)<\/b>([^<]*)/g)].map(m => [m[1].replace(/<[^>]+>/g, ''), m[2]]);
  assert.deepEqual(stats, [['5 / 10', 'step'], ['v1', 'brief']]);  // and the shared "N your turn" figure, in its slot
  assert.doesNotMatch(html, /Owners only|your calls|being written|last move/);
  assert.match(a.headerHTML(fixture()), /<b>–<\/b>brief/);  // no brief yet: a dash, not a sentence
  assert.equal(a.briefLabel(fixture({ moves: d.moves, briefs: [rec('brief', { id: 'v1', move: 'M1', status: 'final' })] })), 'v1, final');
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
  const p = a.chooseParams(d.options[1], 'r2', false);
  assert.deepEqual(Object.keys(p).sort(), ['confirmed', 'id', 'option', 'revision']);
  assert.equal(p.option, 'K2'); assert.equal(p.revision, 'r2'); assert.equal(p.confirmed, false);
  assert.match(p.id, /^c-/);
  assert.equal(a.chooseParams(d.options[2], 'r3', true).confirmed, true);
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
  assert.match(html, /name="option" value="K1" data-revision="r1" checked/);
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

test('S56: a check that has no word for 30 minutes says so; the last word is the one the page data serves', () => {
  const a = api(), d = fixture();
  d.tests[1].since = ago(40);
  d.last_word = { 'analyst-2': ago(5) };  // served by the page's Python, from summary's one rule (L4)
  const quiet = a.agentRows(d, NOW).find(r => r.who === 'analyst-2');
  assert.equal(new Date(quiet.last).toISOString().slice(0, 19) + 'Z', ago(5));
  assert.doesNotMatch(a.atWork(d, NOW), /No word from analyst-2/);
});

test('S56: evidence checking with no verifier reads Queued with its age; a chat act reads recorded from the chat', () => {
  const a = api(), d = fixture();
  assert.match(a.evidencePanel(d, ctx(d)), /Queued, 5 min/);
  assert.match(a.evidencePanel(d, ctx(d)), /Checking, 3 min/);
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

// ---------- #125: risks by kind ----------
const riskFixture = () => {
  const d = fixture();
  const b1 = d.items.find(i => i.id === 'B1');
  b1.risks = [{ id: 'R1', kind: 'value', text: 'Nobody reads it.' }, { id: 'R2', kind: 'usability', text: 'Too noisy.' }, { id: 'R3', kind: 'feasibility', text: 'No retry data.' }];
  b1.accepted_risks = ['R3']; b1.open_risks = ['R1', 'R2'];
  d.changes.push(rec('change', { about: { type: 'item', item: 'B1' }, field: 'risk', risk: 'R3', from: 'open', to: 'accepted', cause: { answer: { type: 'decision', id: 'D9' } } }));
  d.decisions.push(rec('decision', { id: 'D9', about: { type: 'risk', item: 'B1', risk: 'R3' }, asked: 'Accept R3?', default: 'Accept the risk', status: 'answered', raised_by: 'coord', answer: { type: 'chat', text: 'yes' }, answered_at: ago(2) }));
  d.decisions.find(x => x.id === 'D2').asked = 'Will you build B1 without knowing whether people read it? It may be noise.';
  return d;
};
const rowOf = (html, id) => { const at = html.indexOf('id="' + id + '"'); return at < 0 ? '' : html.slice(at, html.indexOf('</tr>', at)); };

test('S6: an item with risks has a bar under it: counts, a question for you, and the kinds with none; it starts closed', () => {
  const a = api(), d = riskFixture();
  const html = a.itemsTable('behaviour', d, ctx(d));
  const bar = rowOf(html, 'bar-B1');
  assert.match(bar, /<button type="button"[^>]*aria-expanded="false"[^>]*aria-controls="risks-B1"[^>]*aria-label="Show risks of B1"/);
  assert.match(bar, /3 risks: 2 open, 1 accepted, 1 question for you/);
  assert.match(bar, /None listed: viability/);
  assert.match(bar, /<span aria-hidden="true">▸<\/span>/);
  assert.doesNotMatch(html, /id="risk-R1"[^>]*>(?![^]*hidden)/);  // the sub-rows are hidden while the bar is closed
  assert.match(html, /<tr class="risk"[^>]*id="risk-R1"[^>]*hidden/);
});

test('S6: the bar\'s counts: one risk, no zero counts, and no question when none waits', () => {
  const a = api();
  assert.equal(a.riskCounts(1, 1, 0, 0), '1 risk, open');
  assert.equal(a.riskCounts(3, 3, 0, 0), '3 risks, all open');
  assert.equal(a.riskCounts(2, 0, 2, 0), '2 risks, both accepted');
  assert.equal(a.riskCounts(1, 0, 1, 0), '1 risk, accepted');
  assert.equal(a.riskCounts(5, 0, 5, 0), '5 risks, all accepted');
  assert.equal(a.riskCounts(3, 2, 1, 1), '3 risks: 2 open, 1 accepted, 1 question for you');
  assert.equal(a.riskCounts(3, 3, 0, 2), '3 risks, all open, 2 questions for you');
});

test('S6: an open bar shows one sub-row per risk: kind then text, Open or Accepted, what settled it, and Change named for the risk', () => {
  const a = api(), d = riskFixture();
  const html = a.itemsTable('behaviour', d, ctx(d, { openRisks: new Set(['B1']) }));
  assert.match(rowOf(html, 'bar-B1'), /aria-expanded="true"[^>]*aria-label="Hide risks of B1"/);
  const r2 = rowOf(html, 'risk-R2'), r3 = rowOf(html, 'risk-R3');
  assert.doesNotMatch(r2, /hidden/);
  assert.match(r2, /<b>Usability:<\/b> Too noisy\./);
  assert.match(r2, />Open</);
  assert.match(r2, /Nothing yet/);
  assert.match(r2, /aria-label="Change R2"/);
  assert.match(r3, />Accepted</);
  assert.match(r3, /<a href="#row-D9" data-goto="D9">D9<\/a>/);
  assert.ok(html.indexOf('id="risk-R1"') < html.indexOf('id="risk-R2"') && html.indexOf('id="risk-R2"') < html.indexOf('id="risk-R3"'));
});

test('S6, A22: a question about a risk sits in its State cell with the question, its default and the shared controls', () => {
  const a = api(), d = riskFixture();
  const r1 = rowOf(a.itemsTable('behaviour', d, ctx(d, { openRisks: new Set(['B1']) })), 'risk-R1');
  assert.match(r1, /<a href="#row-D2" data-goto="D2">D2<\/a>: Will you build B1 without knowing whether people read it\?/);
  assert.doesNotMatch(r1, /It may be noise/);
  assert.match(r1, /Suggested default: Accept the risk/);
  assert.match(r1, /class="btn btn--sm btn--quiet answer" data-use="D2" aria-label="Use the default for D2">Use the default</);  // D11: ✓ only ever closes
  assert.match(r1, /data-answer="D2" aria-label="Answer D2">Answer</);
});

test('A18: Question open on an item counts only questions about the item, not about its risks', () => {
  const a = api(), d = riskFixture();
  assert.doesNotMatch(rowOf(a.itemsTable('behaviour', d, ctx(d)), 'row-B1'), /Question open/);
  assert.match(rowOf(a.itemsTable('problem', d, ctx(d)), 'row-P1'), /Question open/);
});

test('an item with no risk shows No risk listed under its state and has no bar', () => {
  const a = api(), d = riskFixture();
  const html = a.itemsTable('problem', d, ctx(d));
  assert.match(rowOf(html, 'row-P2'), /No risk listed/);
  assert.equal(rowOf(html, 'bar-P2'), '');
  assert.doesNotMatch(html, /<th[^>]*>Risks</);
});

test('A3: a risk ID shown outside its sub-row is a link that goes to it', () => {
  const a = api(), d = riskFixture();
  assert.match(a.movesPanel(d, ctx(d)), /About <a href="#risk-R1" data-goto="R1">R1<\/a> of <a href="#row-B1" data-goto="B1">B1<\/a>/);
  assert.equal(a.tabOf('R1', d), 'behaviours');
  assert.equal(a.riskItem('R1', d), 'B1');
  assert.equal(a.riskItem('R9', d), null);
});

test('the Evidence tab: users, not yet known, elsewhere; Checking quote; not reachable and unverified stay on the row and do not count', () => {
  const a = api(), d = fixture();
  d.evidence.push({ ...d.evidence[0], id: 'E-a9-1', status: 'not reachable', reason: 'HTTP 403' });
  const html = a.evidencePanel(d, ctx(d));
  for (const heading of ['About your users', 'Not yet known for your users', 'From elsewhere']) assert.match(html, new RegExp(heading));
  assert.match(html, /Unreachable/);
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

test('evidence that is still being checked has only its label and age; a move that writes a brief names it on the Brief tab until the brief is there', () => {
  const a = api(), d = fixture();
  assert.doesNotMatch(a.evidencePanel(d, ctx(d)), /does not count/);
  d.moves = [rec('move', { id: 'M2', option: 'K2', step: '5', why: 'x', answer: { type: 'page', event: 'c1' } })];
  assert.match(a.briefPanel(d, ctx(d)), /v1 is being written for <a href="#row-M2"[^>]*>M2<\/a> \(Shrink\)/);
  d.briefs = [rec('brief', { id: 'v1', move: 'M2', status: 'draft', decision: 'Shrink.' })];
  assert.doesNotMatch(a.briefPanel(d, ctx(d)), /is being written for/);
});

// ---------- #126: evidence labels ----------
test('S7, A19: each evidence gets one of eleven labels from its status, origin and kind only, never from its reason', () => {
  const a = api(), d = fixture();
  const web = { origin: { type: 'web', url: 'https://example.com/a', read: 'raw' }, kind: 'say' };
  const you = { origin: { type: 'you', given: { type: 'chat', text: 'x' } }, kind: 'say' };
  const computed = { origin: { type: 'file', path: 'db.csv' }, kind: 'data', text: 'count => 3', words: { type: 'quote', text: 'count => 3' } };
  const cases = [
    [{ ...web, status: 'counts' }, 'Found'], [{ ...you, status: 'counts' }, 'From you'], [{ ...computed, status: 'counts' }, 'Confirmed'],
    [{ ...web, status: 'checking' }, 'Queued'], [{ ...web, status: 'checking', verifier: 'v1', since: ago(2) }, 'Checking'],
    [{ ...computed, status: 'checking' }, 'Needs you'], [{ ...web, status: 'not found', reason: 'not on the page' }, 'Not found'],
    [{ ...web, status: 'not reachable', reason: 'HTTP 403' }, 'Unreachable'], [{ ...web, status: 'unverified', reason: 'page read only as an extraction' }, 'Not checked'],
    [{ ...computed, status: 'unverified', reason: 'not confirmed by you' }, 'Not confirmed'], [{ ...web, status: 'removed', reason: 'm1' }, 'Removed'],
    [{ ...web, status: 'reworded', reason: 'reworded', page_words: 'x' }, 'Checking'],
  ];
  for (const [e, label] of cases) assert.equal(a.evidenceLabel({ id: 'E-x-1', ...e }, d), label, JSON.stringify(e));
  assert.equal(a.evidenceLabel({ id: 'E-x-1', ...web, status: 'unverified', reason: 'not confirmed by you' }, d), 'Not checked');  // the reason never decides
  const body = source.slice(source.indexOf('function evidenceLabel'));
  assert.doesNotMatch(body.slice(0, body.indexOf('\n}\n')), /\.reason/);
});

test('S7: under a label only a reason, never Used, Not used or It does not count', () => {
  const a = api(), d = fixture();
  d.evidence.push({ ...d.evidence[0], id: 'E-a9-1', status: 'not found', reason: 'not on the page' });
  d.evidence.push({ ...d.evidence[0], id: 'E-a9-2', status: 'not reachable', reason: 'The site asks for a login.' });
  const html = a.evidencePanel(d, ctx(d));
  assert.match(rowOf(html, 'row-E-a9-1'), /chip">Not found<\/span><p class="muted">not on the page<\/p>/);
  assert.match(rowOf(html, 'row-E-a9-2'), /Unreachable<\/span><p class="muted">The site asks for a login\.<\/p>/);
  assert.match(rowOf(html, 'row-E-a1-1'), /chip ok">Found<\/span><\/td>/);
  assert.doesNotMatch(html, /Used\.|Not used|does not count/);
});

test('S7: the Evidence intro says which labels count', () => {
  const a = api(), d = fixture();
  assert.match(a.evidencePanel(d, ctx(d)), /Evidence is what you saw or were told, and what research found\. Found, From you and Confirmed count\. Queued, Checking and Needs you don(’|'|&#39;)t count yet\. The rest don(’|'|&#39;)t count\./);
});

test('a stalled Queued or Checking evidence gives the reason No word for n min, past the quiet time', () => {
  const a = api(), d = fixture();
  d.quiet_after = 1800;
  d.evidence.find(e => e.id === 'E-a3-1').since = ago(35);
  d.evidence.find(e => e.id === 'E-a2-1').at = ago(40);
  const html = a.evidencePanel(d, ctx(d));
  assert.match(rowOf(html, 'row-E-a3-1'), /No word for 35 min/);
  assert.match(rowOf(html, 'row-E-a2-1'), /No word for 40 min/);
  assert.doesNotMatch(rowOf(html, 'row-E-a1-1'), /No word/);
});

test('a corrected quote shows the page\'s words, the mark, and the analyst\'s wording under More; the reworded one it corrects is not listed', () => {
  const a = api(), d = fixture();
  d.evidence.push({ ...d.evidence[0], id: 'E-a9-1', status: 'reworded', reason: 'reworded', page_words: 'Over half mute alerts.', text: 'People ignore alerts.', words: { type: 'quote', text: 'People ignore alerts.' } });
  d.evidence.push({ ...d.evidence[0], id: 'E-coord-7', corrects: 'E-a9-1', status: 'counts', text: 'Over half mute alerts.', words: { type: 'quote', text: 'Over half mute alerts.' } });
  const html = a.evidencePanel(d, ctx(d));
  assert.equal(rowOf(html, 'row-E-a9-1'), '');
  const row = rowOf(html, 'row-E-coord-7');
  assert.match(row, /Over half mute alerts\./);
  assert.match(row, /quote corrected to the page(’|'|&#39;)s words/);
  assert.match(row, /<details class="more"><summary>More<\/summary><p>The analyst quoted: “People ignore alerts\.”/);
  const lone = fixture(); lone.evidence.push(d.evidence[d.evidence.length - 2]);
  assert.match(rowOf(a.evidencePanel(lone, ctx(lone)), 'row-E-a9-1'), /Checking[^]*Reworded on the page: being corrected/);
});

test('a reworded quote that waits for its correction counts as checking on its item, as its label says', () => {
  const a = api(), d = fixture();
  assert.match(rowOf(a.itemsTable('problem', d, ctx(d)), 'row-P1'), /2 checking/);  // the fixture's two quotes still checking
  d.evidence.push({ ...d.evidence[0], id: 'E-a9-1', status: 'reworded', reason: 'reworded', page_words: 'x', bears_on: [{ item: 'P1', direction: 'for' }] });
  assert.match(rowOf(a.itemsTable('problem', d, ctx(d)), 'row-P1'), /3 checking/);
});

test('a reworded quote that has a correction no longer counts as checking on its item', () => {
  const a = api(), d = fixture();
  d.evidence = d.evidence.filter(e => e.status !== 'checking');
  d.evidence.push({ ...d.evidence[0], id: 'E-a9-1', status: 'reworded', reason: 'reworded', page_words: 'x', bears_on: [{ item: 'P1', direction: 'for' }] });
  d.evidence.push({ ...d.evidence[0], id: 'E-coord-7', corrects: 'E-a9-1', status: 'counts', bears_on: [{ item: 'P1', direction: 'for' }] });
  assert.doesNotMatch(rowOf(a.itemsTable('problem', d, ctx(d)), 'row-P1'), /checking/);
});

test('A14: after the check on a risk\'s question, the next question is one in an open bar, never one hidden under a closed bar', () => {
  const body = source.slice(source.indexOf("target.matches('[data-use]') && row"));
  assert.match(body.slice(0, 800), /tr\.risk:not\(\[hidden\]\) \.rq/);
});

// ---------- A5 ----------
// The text of every button that sends something to the agent: not a tab, the header's count or a risks bar, which only
// open or close a view; Show and Hide are fine there (the user, on A5).
const buttonLabels = html => [...html.matchAll(/<button\b([^>]*)>([^]*?)<\/button>/g)].filter(m => !/role="tab"|id="questions"|data-risks=/.test(m[1])).map(m => m[2].replace(/<[^>]*>/g, '').trim());

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
  const allowed = /^(Add|Change|Remove|Answer|Choose|Send|Cancel|Use the default|✓)/;  // D11: the default is used with words, not a bare check
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

// ---------- round 2 ----------
test('S37, L1: the revision is the one the picker showed: it is on each radio and each confirming button, and the click does not read the data again', () => {
  const a = api(), d = fixture(), html = a.choosePanel(d, ctx(d));
  assert.match(html, /name="option" value="K2" data-revision="r2"/);
  assert.match(html, /data-confirm-choose="K3" data-revision="r3"/);
  d.revisions.K2 = 'changed-while-open';
  assert.match(html, /value="K2" data-revision="r2"/);  // the built picker keeps what it showed
  assert.doesNotMatch(source, /DATA\.revisions/);  // sendChoose takes the shown one
  assert.equal(a.chooseParams(d.options[1], 'r2', false).revision, 'r2');
});

test('a decision about evidence shows that evidence\'s words and source in the Moves row and in the answered row; its evidence row waits for your confirmation, not a verifier', () => {
  const a = api(), d = fixture();
  d.evidence.push({ ...d.evidence[0], id: 'E-a1-9', status: 'checking', kind: 'data', text: 'count users => 12', words: { type: 'quote', text: 'count users => 12' }, source_title: 'The users table', origin: { type: 'file', path: 'db.csv' }, at: ago(5) });
  d.decisions.push(rec('decision', { id: 'D5', about: { type: 'evidence', evidence: 'E-a1-9' }, asked: 'Is the result of E-a1-9 right?', default: 'Confirm this result', status: 'waiting', raised_by: 'coord' }));
  const c = ctx(d);
  assert.match(a.evidenceBlock(d.decisions[4], d), /count users =&gt; 12/);
  assert.match(a.evidenceBlock(d.decisions[4], d), /db\.csv/);
  assert.equal(a.evidenceBlock(d.decisions[0], d), '');
  const moves = a.movesPanel(d, c);
  assert.match(moves, /Is the result of E-a1-9 right\?[^]*count users =&gt; 12/);
  const answered = fixture(); answered.evidence = d.evidence; answered.decisions = [{ ...d.decisions[4], status: 'answered', answer: { type: 'chat', text: 'yes' }, answered_at: ago(1) }];
  assert.match(a.movesPanel(answered, ctx(answered)), /count users =&gt; 12/);
  const panel = a.evidencePanel(d, c);
  const row = panel.slice(panel.indexOf('id="row-E-a1-9"'));
  assert.doesNotMatch(row.slice(0, row.indexOf('</tr>')), /Queued/);
  assert.match(row.slice(0, row.indexOf('</tr>')), /chip wait">Needs you/);
});

test('A14: after the check the focus goes to the next open question after the current one, wrapping; its Answer when it has no default; the move when none remain', () => {
  const a = api(), q = (id, def) => ({ id, default: def });
  const open = [q('D1', 'Yes'), q('D2', 'Yes'), q('D3', null)];
  assert.deepEqual(a.nextAfter(open, 'D1'), { id: 'D2', use: true });
  assert.deepEqual(a.nextAfter(open, 'D2'), { id: 'D3', use: false });
  assert.deepEqual(a.nextAfter(open, 'D3'), { id: 'D1', use: true });  // wraps
  assert.equal(a.nextAfter([q('D1', 'Yes')], 'D1'), null);
});

test('L2: Waiting for the agent is the agent working: a working chip, never the umber waiting-for-you one', () => {
  const a = api(), d = fixture(), c = ctx(d, { pending: { type: 'choose', id: 'c1', option: 'K2' } });
  const html = a.choosePanel(d, c) + a.optionsPanel(d, c) + a.movesPanel(d, c);
  assert.match(html, /chip working">Waiting for the agent/);
  assert.doesNotMatch(html, /chip wait">Waiting for the agent/);
});

test('the unused stale-minutes constant is gone', () => { assert.doesNotMatch(source, /STALE_MINUTES/); });

// ---- The page's own kinds inside the rows of the shared panel (S24, S25): page.js of discover runs whole on the
// stand-in shell (tests/dom.js), with the shared page.js's real panel.
const { shellDocument, mixedDocument, panelOn, text, actions } = require('./dom');
function liveDiscover(data) {
  const doc = shellDocument(), view = doc.createElement('main');
  view.className = 'view'; doc.body.append(view);  // the page's forms open in its view: none is open
  const live = panelOn(null, null, { document: doc, config: { agent: 'coordinator', capabilities: ['decisions'] } });
  const c = live.context, env = {
    document: mixedDocument(doc), pageConversation: o => c.pageConversation(Object.assign({}, o, { served: false })),
    pageDecision: c.pageDecision, pageDecisionEvents: c.pageDecisionEvents, pageOpenDecisions: c.pageOpenDecisions, pageThreads: c.pageThreads,
    pageMarkdown: c.pageMarkdown, pageMarkdownText: c.pageMarkdownText, pageTime: c.pageTime, pageEscape: c.pageEscape,
    pageAgents: c.pageAgents, pageShowErrors: () => {}, pageFetch: () => new Promise(() => {}), setInterval: () => {},
    addEventListener: () => {}, innerWidth: 1000, innerHeight: 800, getComputedStyle: stand(), CSS: { escape: s => s },
  };
  const page = new Function(...Object.keys(env), source + '; return {paint, conv, setData: d => { DATA = d; }};')(...Object.values(env));
  page.setData(data);
  page.paint();
  return Object.assign(live, page);
}

test('the page draws its kinds inside rows: a decision as your turn with its default and controls, a choose as your message', () => {
  const d = fixture({ conversation: [{ type: 'choose', id: 'ch1', option: 'K2', revision: 'r2', at: ago(2), by: 'user' }] });
  const p = liveDiscover(d);
  const d1 = p.rowOf('D1'), ch = p.rowOf('ch1');
  assert.equal(text(d1.querySelector('.chip')), 'Your turn');
  assert.equal(text(d1.querySelector('.tgist')), 'Coordinator: Is P1 the main problem?');
  assert.deepEqual(actions(d1).map(x => x.textContent), ['✓', 'Use the default', 'Answer']);
  d1.querySelector('.thead').click();
  assert.match(text(p.rowOf('D1').querySelector('.tbody')), /Suggested default: Yes/);
  assert.equal(text(ch.querySelector('.chip')), 'Agent’s turn');
  assert.match(text(ch.querySelector('.tgist')), /^You: Chose Shrink: Owners only\./);
  assert.deepEqual(actions(ch).map(x => x.textContent), ['✓', 'Reply']);
  assert.equal(text(p.$('#status #yourturn')), '3 your turn');
});

test('answering a decision from its row records the answer; the figure counts one fewer', () => {
  const p = liveDiscover(fixture());
  actions(p.rowOf('D1'))[2].click();
  const box = p.rowOf('D1').querySelector('.why textarea');
  box.input('No, P2 is.');
  box.key('Enter', { ctrlKey: true });
  assert.deepEqual(p.conv.log().filter(e => e.type === 'answer').map(e => [e.decision, e.text, e.default]), [['D1', 'No, P2 is.', false]]);
  assert.equal(text(p.rowOf('D1').querySelector('.chip')), 'Agent’s turn');
  assert.equal(text(p.$('#status #yourturn')), '2 your turn');
});
