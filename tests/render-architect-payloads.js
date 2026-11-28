// Draws the architecture page's sections for each payload the architect package produced, and fails on any that throws. Run by
// tests/test_architect_formats.py: `node tests/render-architect-payloads.js payloads.json`, where the file holds
// [{label, data}]. The shared page.js and the page's own code, architect/page.js, run against stand-in elements.
const fs = require('node:fs');
const vm = require('node:vm');
const { read, stand } = require('./harness');

const context = {fetch: () => new Promise(() => {}), document: stand(), sessionStorage: stand(), setTimeout: () => {}, URLSearchParams};
vm.createContext(context);
vm.runInContext(read('page', 'page.js'), context);
vm.runInContext(read('architect', 'page.js'), context);

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
    draw('controls(data.perspectives, data.reviews.at(-1), data.versions)');
    draw('alternativeTable(data.alternatives) + alternativeCards(data.alternatives)');
    draw('specTables(data.spec)');
    draw('pageErrors(data.errors)');
    draw('figures(data.containers, data.versions)');
    draw('data.flows.map(flow => flowMarks(flow.status) + figures(flow.versions, data.versions)).join("")');
    draw('reviewSummary(data.since, data.change_labels, data.rerun.map(id => nameOf(data.perspectives, id)))');
    draw('changeList(data.since, data.change_labels, data.removed)');
    const list = draw('agentList(data.agents)'), running = (data.agents || []).length;
    if (/chip|min</.test(list)) throw new Error('the agents list shows a state or an age: ' + list);
    if (running && (list.match(/<li>/g) || []).length !== running) throw new Error('one row per running agent: ' + list);
    if (!running && !/No agent is working/.test(list)) throw new Error('no agent, but the list says otherwise: ' + list);
  } catch (error) {
    failed.push(`${label}: ${error.stack.split('\n').slice(0, 2).join(' ')}`);
  }
}
if (failed.length) { console.error(failed.slice(0, 20).join('\n')); process.exit(1); }
console.log(`${payloads.length} payloads drawn`);
