// Draws the dashboard's task tables, each task's pop-up and the decision items for each payload the dashboard's `load` produced, and
// fails on any that throws. Run by tests/test_dashboard_formats.py: `node tests/render-payloads.js payloads.json`, where
// the file holds [{label, data}]. The page's own code is read out of src/better_ai/code/dashboard.js, run against
// stand-in elements, with the shared page.js (the decision question and the log) run for real.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = path.join(__dirname, '..', 'src', 'better_ai');
// An element, a document or any other object the page only pokes at: every property and call gives another one.
const stand = () => new Proxy(function () {}, {
  get: (_t, k) => (k === Symbol.toPrimitive ? () => '' : stand()),
  apply: () => stand(),
  set: () => true,
});
const shared = {};
vm.runInNewContext(fs.readFileSync(path.join(source, 'page', 'page.js'), 'utf8'), Object.assign(shared, { document: stand() }));

const code = fs.readFileSync(path.join(source, 'code', 'dashboard.js'), 'utf8').split('// ---------- Render ----------')[0];
const names = ['tablesHTML', 'popupHTML', 'decisionItem', 'errorsHTML', 'isDone'];
const make = new Function('document', 'pageConversation', 'pageMarkdown', 'pageMarkdownText', 'pageTime', 'pageDecision',
  'addEventListener', 'innerWidth', 'innerHeight', 'getComputedStyle',
  code + `; return {${names.join(', ')}, set: d => { D = d; }};`);
const page = make(stand(), () => stand(), t => ({ outerHTML: String(t) }), String, shared.pageTime, shared.pageDecision,
  () => {}, 1000, 800, stand());

const payloads = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const failed = [];
for (const { label, data } of payloads) {
  try {
    const d = { now: 1764000000, ...data };
    page.set(d);
    for (const range of ['1h', '2h', 'all']) page.tablesHTML(d, range);
    for (const t of Array.isArray(d.tasks) ? d.tasks : []) if (t && typeof t === 'object') page.popupHTML(t, d);
    shared.pageDecisionEvents(data.decisions, data.conversation);
    page.errorsHTML(data.errors);
    data.tasks.filter(page.isDone);
    for (const x of data.decisions) page.decisionItem({ e: { x }, replies: [] }, {}, true);
  } catch (error) {
    failed.push(`${label}: ${error.stack.split('\n').slice(0, 2).join(' ')}`);
  }
}
if (failed.length) { console.error(failed.join('\n')); process.exit(1); }
console.log(`${payloads.length} payloads drawn`);
