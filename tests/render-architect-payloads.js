// Draws the architecture page's sections for each payload architect.py produced, and fails on any that throws. Run by
// tests/test_architect_formats.py: `node tests/render-architect-payloads.js payloads.json`, where the file holds
// [{label, data}]. The page's own code, architect.js, runs against stand-in elements.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'skills', 'architect-better', 'scripts', 'architect.js'), 'utf8');
// An element, a document or any other object the page only pokes at: every property and call gives another one.
const stand = () => new Proxy(function () {}, {
  get: (_t, k) => (k === Symbol.toPrimitive ? () => '' : stand()),
  apply: () => stand(),
  set: () => true,
});
const context = {fetch: () => new Promise(() => {}), document: stand(), sessionStorage: stand(), setTimeout: () => {}, URLSearchParams};
vm.createContext(context);
vm.runInContext(source, context);

const payloads = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const failed = [];
for (const {label, data} of payloads) {
  try {
    context.data = data;
    const draw = expression => vm.runInContext(expression, context);
    draw('requirementRows(data.requirements).join("")');
    draw('decisionRecords(data.decisions)');
    draw('perspectiveTables(data.perspectives, data.findings, data.parts, true, data.removed_labels)');
    draw('perspectiveTables(data.perspectives, data.findings, data.parts, false, data.removed_labels)');
    draw('controls(data.perspectives, data.reviews.at(-1))');
    draw('specTables(data.spec)');
    draw('errorsHTML(data.errors)');
    draw('figures(data.containers)');
    draw('data.flows.map(flow => figures(flow.versions)).join("")');
    draw('reviewSummary(data.since.map(key => data.change_labels[key]), data.rerun.map(id => nameOf(data.perspectives, id)))');
  } catch (error) {
    failed.push(`${label}: ${error.stack.split('\n').slice(0, 2).join(' ')}`);
  }
}
if (failed.length) { console.error(failed.slice(0, 20).join('\n')); process.exit(1); }
console.log(`${payloads.length} payloads drawn`);
