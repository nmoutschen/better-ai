// Draws the dashboard's task list, agent cards and decision items for each payload dashboard.py produced, and fails on
// any that throws. Run by tests/test_dashboard_formats.py: `node tests/render-payloads.js payloads.json`, where the file
// holds [{label, data}]. The page's own code is read out of dashboard.html, run against stand-in elements.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const skill = path.join(__dirname, '..', 'skills', 'code-better', 'scripts');
const html = fs.readFileSync(path.join(skill, 'dashboard.html'), 'utf8');
const pageJs = fs.readFileSync(path.join(skill, 'page.js'), 'utf8');
const shared = {};
vm.runInNewContext(pageJs, shared);

// An element, a document or any other object the page only pokes at: every property and call gives another one.
const stand = () => new Proxy(function () {}, {
  get: (_t, k) => (k === Symbol.toPrimitive ? () => '' : stand()),
  apply: () => stand(),
  set: () => true,
});
const code = html.split('<script>')[1].split('// ---------- Render ----------')[0].replace('/*__PAGE_JS__*/', '');
const names = ['drawAgents', 'drawTasks', 'decisionItem', 'events', 'errorsHTML', 'isDone', 'taskLabel'];
const make = new Function('document', 'pageConversation', 'pageMarkdown', 'pageMarkdownText', 'pageTime', 'addEventListener',
  'innerWidth', 'innerHeight', 'getComputedStyle',
  code + `; return {${names.join(', ')}, set: d => { D = d; }};`);
const page = make(stand(), () => stand(), t => ({ outerHTML: String(t) }), String, shared.pageTime, () => {}, 1000, 800, stand());

const payloads = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const failed = [];
for (const { label, data } of payloads) {
  try {
    page.set(data);
    page.drawAgents(data);
    page.drawTasks(data);
    page.events(data);
    page.errorsHTML(data.errors);
    data.tasks.filter(page.isDone);
    for (const x of data.decisions) page.decisionItem({ e: { x }, replies: [] }, {}, true);
  } catch (error) {
    failed.push(`${label}: ${error.stack.split('\n').slice(0, 2).join(' ')}`);
  }
}
if (failed.length) { console.error(failed.join('\n')); process.exit(1); }
console.log(`${payloads.length} payloads drawn`);
