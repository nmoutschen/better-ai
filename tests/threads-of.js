// The threads page.js draws from what a page's data serves, for tests/test_conversation_lines.py:
//   node tests/threads-of.js <payloads.json>
// Each payload is { label, kinds, decisions, conversation, positional }; prints, per payload, [id, state, step] of each
// thread as the page reads them, pageThreads(pageDecisionEvents(decisions, conversation), kinds), from the data it
// serves (`threads`) and from the log read by line position (`positional`).
const fs = require('node:fs');
const { loadPage } = require('./harness');

const context = loadPage();
const states = (p, log) => Array.from(context.pageThreads(context.pageDecisionEvents(p.decisions || [], log), p.kinds),
  t => [t.id, t.state, t.step]);
const out = JSON.parse(fs.readFileSync(process.argv[2], 'utf8')).map(p => ({
  label: p.label, threads: states(p, p.conversation), positional: states(p, p.positional),
}));
process.stdout.write(JSON.stringify(out));
