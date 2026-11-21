// Like render-board-payloads.js, but with the real pageConversation from page.js, so each item's thread is built from the
// conversation events in the payload. Run by tests/test_board_formats.py: `node tests/render-board-thread.js payloads.json`,
// where the file holds [{label, data}]; it fails on any payload whose page or thread throws.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const skill = path.join(__dirname, '..', 'skills', 'research-better', 'scripts');
const stand = () => new Proxy(function () {}, {
  get: (_t, k) => (k === Symbol.toPrimitive ? () => '' : k === 'length' ? 0 : stand()),
  apply: () => stand(),
  set: () => true,
});
const shared = { document: stand(), setTimeout: () => 0, clearTimeout: () => {}, requestAnimationFrame: () => 0,
  fetch: () => new Promise(() => {}), addEventListener: () => {}, getComputedStyle: () => stand(), console };
vm.runInNewContext(fs.readFileSync(path.join(skill, 'page.js'), 'utf8'), shared);
const code = fs.readFileSync(path.join(skill, 'board.js'), 'utf8').replace('__SNAPSHOT__', 'null').split('let fails = 0;')[0];
const make = new Function('document', 'pageConversation', 'pageMarkdown', 'pageMarkdownText', 'pageTime', 'addEventListener',
  'innerWidth', 'innerHeight', 'getComputedStyle', 'fetch', 'setInterval',
  code + '; return {render, conv, showLoaded};');
const page = make(stand(), shared.pageConversation, shared.pageMarkdown, shared.pageMarkdownText, shared.pageTime, () => {},
  1000, 800, stand(), () => new Promise(() => {}), () => {});

const payloads = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const failed = [];
for (const { label, data } of payloads) {
  try {
    data.now = data.now || 1e9;
    page.render(data);
    page.conv.render();
  } catch (error) {
    failed.push(`${label}: ${error.stack.split('\n').slice(0, 3).join(' | ')}`);
  }
}
if (failed.length) { console.error(failed.slice(0, 40).join('\n')); process.exit(1); }
console.log(`${payloads.length} payloads drawn`);
