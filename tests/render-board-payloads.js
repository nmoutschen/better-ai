// Draws the research board's page for each payload board.py produced, and fails on any that throws. Run by
// tests/test_board_formats.py: `node tests/render-board-payloads.js payloads.json`, where the file holds
// [{label, data}]. The page's own code (board.js, up to its polling) runs against stand-in elements.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const src = path.join(__dirname, '..', 'src', 'better_ai');
// An element, a document or any other object the page only pokes at: every property and call gives another one.
const stand = () => new Proxy(function () {}, {
  get: (_t, k) => (k === Symbol.toPrimitive ? () => '' : stand()),
  apply: () => stand(),
  set: () => true,
});
const shared = { document: stand() };
vm.runInNewContext(fs.readFileSync(path.join(src, 'page', 'page.js'), 'utf8'), shared);

const code = fs.readFileSync(path.join(src, 'research', 'board.js'), 'utf8').split('const bands = ')[0];
const names = ['render', 'showLoaded', 'openPop', 'closedItem', 'decision', 'decisions', 'drawAgents'];
const make = new Function('document', 'pageConversation', 'pageDecision', 'pageDecisionEvents', 'pageMarkdown', 'pageMarkdownText', 'pageTime', 'addEventListener',
  'innerWidth', 'innerHeight', 'getComputedStyle', 'fetch', 'setInterval',
  code + `; return {${names.join(', ')}, get D() { return D; }};`);
const page = make(stand(), () => stand(), shared.pageDecision, shared.pageDecisionEvents, t => ({ outerHTML: String(t) }), String, shared.pageTime, () => {}, 1000, 800, stand(),
  () => new Promise(() => {}), () => {});

const payloads = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const failed = [];
for (const { label, data } of payloads) {
  try {
    data.now = data.now || 1e9;
    page.showLoaded(data, { errors: stand(), old: stand() });
    page.render(data);
    const d = page.D;
    for (const q of d.qs) { page.openPop('question', q.id, stand()); page.closedItem({ e: { question: q.id, by: 'w', status: 'answered' } }); }
    for (const c of d.claims) if (c.checker) page.openPop('agent', c.checker, stand());
    page.openPop('agent', 'w2', stand());
    for (const x of page.decisions(data)) page.decision.item({ e: { x }, replies: [] }, {}, true);
    shared.pageDecisionEvents(page.decisions(data), data.conversation);
    page.drawAgents(d);
  } catch (error) {
    failed.push(`${label}: ${error.stack.split('\n').slice(0, 2).join(' ')}`);
  }
}
if (failed.length) { console.error(failed.slice(0, 40).join('\n')); process.exit(1); }
console.log(`${payloads.length} payloads drawn`);
