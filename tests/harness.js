// What every JS test and render script shares: reading a page's source out of src/better_ai/, a stand-in for the
// elements a page only pokes at, the shared page.js run for real, and the dashboard's and the research board's own code
// cut out at the markers it has. A marker that is not there throws, so a renamed one fails the test and does not leave
// it testing nothing. Used by tests/*.test.js and by the tests/render-*.js scripts the Python tests run.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const read = (...parts) => fs.readFileSync(path.join(__dirname, '..', 'src', 'better_ai', ...parts), 'utf8');

// An element, a document or any other object the page only pokes at: every property and call gives another one, and
// its length is 0.
const stand = () => new Proxy(function () {}, {
  get: (_t, k) => (k === Symbol.toPrimitive ? () => '' : k === 'length' ? 0 : stand()),
  apply: () => stand(),
  set: () => true,
});

// The part of `text` after the marker FROM and before TO (the end, when TO is not given). Throws when one is missing.
function between(text, from, to) {
  let start = 0;
  if (from) {
    start = text.indexOf(from);
    if (start < 0) throw new Error(`slice marker not found: ${from}`);
    start += from.length;
  }
  let end = text.length;
  if (to) {
    end = text.indexOf(to, start);
    if (end < 0) throw new Error(`slice marker not found: ${to}`);
  }
  return text.slice(start, end);
}

// The code a file has between `// NAME:begin` and `// NAME:end`.
const marked = (text, name) => between(text, `// ${name}:begin`, `// ${name}:end`);

// page.js run in a new context that has GLOBALS (a document of stand-ins when none is given); returns the context.
function loadPage(globals) {
  const context = Object.assign({ document: stand() }, globals);
  vm.runInNewContext(read('page', 'page.js'), context);
  return context;
}

// Code that is a page's own, run with ENV for what the page has (names to values), returning the expression RETURNS.
const run = (code, returns, env) => new Function(...Object.keys(env), `${code}; return ${returns};`)(...Object.values(env));

// The research board's code, up to its polling, with the shared page.js for what it uses. OVER replaces any name of the
// environment: the document, pageConversation, pageMarkdown and so on.
function loadBoard(returns, over = {}) {
  const page = loadPage();
  const env = Object.assign({
    document: stand(), pageConversation: () => stand(), pageDecision: page.pageDecision, pageDecisionEvents: page.pageDecisionEvents, pageOpenDecisions: page.pageOpenDecisions,
    pageMarkdown: t => ({ outerHTML: String(t) }), pageMarkdownText: String, pageTime: page.pageTime,
    pageEscape: page.pageEscape, pageAgents: page.pageAgents, pageApprovals: page.pageApprovals, pageOpenApproval: page.pageOpenApproval, pagePopup: page.pagePopup, pageShowErrors: page.pageShowErrors,
    addEventListener: () => {}, innerWidth: 1000, innerHeight: 800, getComputedStyle: stand(),
    pageFetch: () => new Promise(() => {}), setInterval: () => {},
  }, over);
  return run(between(read('research', 'board.js'), '', '// ---------- Polling ----------'), returns, env);
}

// The dashboard's code, up to where it draws, in the same way.
function loadDashboard(returns, over = {}) {
  const page = loadPage();
  const env = Object.assign({
    document: stand(), pageConversation: () => stand(), pageMarkdown: t => ({ outerHTML: String(t) }), pageMarkdownText: String,
    pageTime: page.pageTime, pageDecision: page.pageDecision, addEventListener: () => {}, innerWidth: 1000, innerHeight: 800,
    getComputedStyle: stand(),
  }, over);
  return run(between(read('code', 'dashboard.js'), '', '// ---------- Render ----------'), returns, env);
}

module.exports = { read, stand, between, marked, loadPage, loadBoard, loadDashboard };
