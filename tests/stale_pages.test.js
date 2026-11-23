// What a board does once its token is refused (the page is out of date): it shows only the out-of-date message, and
// stops asking. Run with `node --test tests/*.test.js`.
const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const { read, stand, loadPage } = require('./harness');

const staleError = () => Object.assign(new Error('page out of date: open the address the agent gave'), { stale: true });

// All of board.js, polling included, with PAGEFETCH as the page's fetch; the poll and the board's closed state come back.
function wholeBoard(pageFetch) {
  const page = loadPage();
  const env = { document: stand(), pageConversation: () => stand(), pageDecision: page.pageDecision, pageDecisionEvents: page.pageDecisionEvents, pageOpenDecisions: page.pageOpenDecisions,
    pageMarkdown: t => ({ outerHTML: String(t) }), pageMarkdownText: String, pageTime: page.pageTime, pageEscape: page.pageEscape,
    pageAgents: page.pageAgents, pagePopup: page.pagePopup, pageShowErrors: () => {}, addEventListener: () => {}, innerWidth: 1000,
    innerHeight: 800, getComputedStyle: stand(), pageFetch, setInterval: () => {} };
  const body = read('research', 'board.js') + '; return {tick, closed: () => CLOSED_PAGE, setBoard: d => { D = prepare(d); }};';
  return new Function(...Object.keys(env), body)(...Object.values(env));
}

const settle = () => new Promise(resolve => setImmediate(resolve));

const board = {
  brief: {}, logs: {}, decisions: [], conversation: [], sources: [],
  questions: [{ id: 'Q-1', status: 'answered', title: 'Page speed', priority: 'high', origin: { type: 'user' }, question: 'q?', summary: 's' }],
  claims: [],
};

test('the research board does not read as closed when its token is refused', async () => {
  const loaded = wholeBoard(() => Promise.reject(staleError()));
  loaded.setBoard(board);
  await loaded.tick(); await loaded.tick(); await loaded.tick();
  await settle();
  assert.equal(loaded.closed(), false);
});

test('the research board still reads as closed when its server stops answering', async () => {
  const loaded = wholeBoard(() => Promise.reject(new Error('down')));
  loaded.setBoard(board);
  await loaded.tick(); await loaded.tick();
  await settle();
  assert.equal(loaded.closed(), true);
});

test('the architecture page stops asking for its data once its token is refused', async () => {
  const retries = [];
  const status = { textContent: '' };
  const document = new Proxy(stand(), { get: (t, k) => (k === 'getElementById' ? id => (id === 'status' ? status : (id === 'page-data' ? null : stand())) : t[k]) });
  const context = { document, sessionStorage: stand(), URLSearchParams, setTimeout: fn => retries.push(fn), fetch: () => new Promise(() => {}) };
  vm.createContext(context);
  vm.runInContext(read('page', 'page.js'), context);
  context.pageFetch = () => Promise.reject(staleError());
  vm.runInContext(read('architect', 'page.js'), context);
  await settle();
  assert.equal(retries.length, 0);
  assert.doesNotMatch(status.textContent, /Could not load the design/);
});

test('once the page is out of date, pageFetch asks the server nothing more', async () => {
  const sent = [];
  const context = { document: stand(), sessionStorage: stand(), URLSearchParams,
    fetch: url => { sent.push(url); return Promise.resolve({ status: 401 }); } };
  vm.createContext(context);
  vm.runInContext(read('page', 'page.js'), context);
  await assert.rejects(context.pageFetch('/data'), e => e.stale);
  await assert.rejects(context.pageFetch('/data'), e => e.stale);
  await assert.rejects(context.pageFetch('/events'), e => e.stale);
  assert.deepEqual(sent, ['/data']);
});
