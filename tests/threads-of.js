// The threads page.js draws from what a page's data serves, for tests/test_conversation_lines.py:
//   node tests/threads-of.js <payloads.json>
// Each payload is { label, kinds, decisions, conversation }; prints, per payload, [id, state, step] of each thread,
// read as the page reads them: pageThreads(pageDecisionEvents(decisions, conversation), kinds).
const fs = require('node:fs');
const { loadPage } = require('./harness');

const context = loadPage();
const out = JSON.parse(fs.readFileSync(process.argv[2], 'utf8')).map(p => ({
  label: p.label,
  threads: Array.from(context.pageThreads(context.pageDecisionEvents(p.decisions || [], p.conversation), p.kinds),
    t => [t.id, t.state, t.step]),
}));
process.stdout.write(JSON.stringify(out));
