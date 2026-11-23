// Draws the research board's page for each payload board.py produced, and fails on any that throws. Run by
// tests/test_board_formats.py: `node tests/render-board-payloads.js payloads.json`, where the file holds
// [{label, data}]. The page's own code (board.js, up to its polling) runs against stand-in elements.
const fs = require('node:fs');
const { stand, loadPage, loadBoard } = require('./harness');

const shared = loadPage();
const names = ['render', 'showLoaded', 'openPop', 'closedItem', 'decision', 'decisions', 'drawAgents'];
const page = loadBoard(`{${names.join(', ')}, get D() { return D; }}`);

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
