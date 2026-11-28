// The six live pages run whole on the stand-in shell (tests/dom.js), each with its own script and the shared page.js's
// real panel, in one context: what each page gives pageConversation is kept, and the panel is not served, so what a
// row sends goes to the panel's own log. livePage(name, data) returns the panel helpers of panelOn, with `opts` (the
// page's options to the panel), `context` (to run more of the page's code) and `feed(log)` to give the page a log the
// way it reads one. Used by tests/*.test.js.
const vm = require('node:vm');
const { read, stand } = require('./harness');
const { shellDocument, mixedDocument, panelOn } = require('./dom');

const NOW = Date.parse('2026-11-28T12:00:00Z');
const at = h => new Date(NOW - h * 3600e3).toISOString().slice(0, 19) + 'Z';

// Each page: its script, its role and capabilities as its page spec declares them, the elements the shell lacks that
// its script needs, and how a log reaches it.
const PAGES = {
  canvas: { file: ['design', 'canvas.js'], agent: 'agent', capabilities: ['pins', 'accept', 'approve'] },
  show: { file: ['show', 'show.js'], agent: 'agent', capabilities: ['pins', 'accept'] },
  architect: { file: ['architect', 'page.js'], agent: 'architect', capabilities: ['pins', 'accept', 'confirm', 'approve'] },
  dashboard: { file: ['code', 'dashboard.js'], agent: 'coordinator', capabilities: ['decisions', 'accept'] },
  board: { file: ['research', 'board.js'], agent: 'coordinator', capabilities: ['decisions', 'accept'] },
  discover: { file: ['discover', 'page.js'], agent: 'coordinator', capabilities: ['decisions', 'accept'] },
};

// The smallest data each page draws from: enough for its script to run to its conversation.
const DATA = {
  canvas: { title: 'Versions', question: 'Which one?', sizes: [{ name: 'Desktop', w: 1440, h: 900 }],
    versions: [{ label: 'A', srcdoc: '<p>a</p>' }, { label: 'B', srcdoc: '<p>b</p>' }, { label: 'C', srcdoc: '<p>c</p>' }] },
  show: { title: 'Deck', slides: '' },
  dashboard: { now: NOW / 1000, name: 'Change', tasks: [], agents: [], git: {} },
  board: { now: NOW / 1000, brief: { title: 'Speed', status: 'running' }, logs: {}, sources: [], claims: [],
    questions: [{ id: 'Q-1', status: 'answered', title: 'Page speed', priority: 'high', origin: { type: 'user' }, question: 'q?', summary: 'Faster.' }] },
};

function livePage(name, data = {}) {
  const page = PAGES[name], doc = shellDocument(), view = doc.createElement('main');
  view.className = 'view'; doc.body.append(view);  // a page's forms open in its view: none is open
  let opts = null, served = null;
  const globals = {
    setInterval: () => 0, addEventListener: () => {}, window: { addEventListener() {}, scrollTo() {} }, innerWidth: 1440, innerHeight: 900, getComputedStyle: () => stand(),
    location: { hash: '', pathname: '/', search: '', protocol: 'file:', reload() {} }, navigator: stand(), URLSearchParams,
    fetch: url => (url === '/data' && served ? Promise.resolve({ status: 200, ok: true, json: () => Promise.resolve(served) }) : new Promise(() => {})),
  };
  const p = panelOn(null, null, { document: doc, config: { agent: page.agent, capabilities: page.capabilities }, globals });
  const ctx = p.context, real = ctx.pageConversation;
  ctx.document = mixedDocument(doc);
  // The page's options are kept; the panel is never served here, so a row's sends stay in its own log.
  ctx.pageConversation = o => { opts = o; p.conv = real(Object.assign({}, o, { served: false, stream: false })); return p.conv; };
  const merged = Object.assign({}, DATA[name], data);
  if (name === 'canvas' || name === 'architect') {
    const carried = doc.createElement('script'); carried.id = 'page-data'; carried.textContent = JSON.stringify(merged); doc.body.append(carried);
  }
  if (name === 'show') served = merged;
  vm.runInContext(read(...page.file), ctx);
  const run = code => vm.runInContext(code, ctx);
  // How the page reads a log: from its own data, or (the pages fed by their stream) through the panel.
  const feed = (log, more = {}) => {
    if (name === 'dashboard' || name === 'board') { ctx.__d = Object.assign({}, merged, { conversation: log }, more); run('render(__d)'); }
    else if (name === 'discover') { ctx.__d = Object.assign({}, merged, { conversation: log }, more); run('DATA = __d; paint()'); }
    else p.conv.setLog(log);
  };
  return Object.assign(p, { opts: () => opts, run, feed });
}

// What the architecture page and the discovery page need besides the defaults, for a test that only reads their rows.
const LIVE_DATA = {
  architect: { title: 'Design', versions: [], alternatives: [], perspectives: [], reviews: [], rerun: [], overlays: [], requirements: [],
    accepted: [], errors: [], since: [], change_labels: {}, removed: [], findings: [], parts: {}, containers: [], flows: [], decisions: [], spec: [] },
  discover: { now: NOW / 1000, quiet_after: 1800, errors: [], head: { idea: 'An idea.', step: '5', status: 'open', setting: 'external' },
    items: [], changes: [], moves: [], briefs: [], tests: [], evidence: [], sources: [], revisions: { K2: 'r2' }, chosen: null,
    options: [{ type: 'option', id: 'K2', move: 'shrink', text: 'Owners only.', cost: 'a week', speed: 'two days', upkeep: 'low', undo: 'easy', note: null, at: at(9), by: 'coord' }] },
};

module.exports = { livePage, at, NOW, LIVE_DATA };
