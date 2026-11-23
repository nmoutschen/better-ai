// Like render-board-payloads.js, but with the real pageConversation from page.js, so each item's thread is built from the
// conversation events in the payload. Run by tests/test_board_formats.py: `node tests/render-board-thread.js payloads.json`,
// where the file holds [{label, data}]; it fails on any payload whose page or thread throws.
const fs = require('node:fs');
const { stand, loadPage, loadBoard } = require('./harness');

const shared = loadPage({ setTimeout: () => 0, clearTimeout: () => {}, requestAnimationFrame: () => 0,
  fetch: () => new Promise(() => {}), addEventListener: () => {}, getComputedStyle: () => stand(), console });
const page = loadBoard('{render, conv, showLoaded}',
  { pageConversation: shared.pageConversation, pageMarkdown: shared.pageMarkdown, pageMarkdownText: shared.pageMarkdownText });

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
