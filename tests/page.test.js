// The thread model in page.js: how the log becomes each item's state, the entries and what Open lists.
// Run with `node --test tests/*.test.js`. page.js is identical in every skill (the Scripts workflow checks it); this loads
// design-better's copy.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'skills', 'design-better', 'scripts', 'page.js'), 'utf8');
const context = {};
vm.runInNewContext(source, context);
const ITEMS = ['comment', 'note'];
const thread = (log, items) => context.pageThread(log, items || ITEMS);
// Arrays made inside the vm context have that context's prototype, which deepStrictEqual rejects: copy them out.
const ids = list => Array.from(list, c => c.e.id);

test('the agent sets the state of an item', () => {
  const t = thread([
    { action: 'note', id: 'm1', note: 'hi' },
    { action: 'status', to: 'm1', status: 'seen' },
    { action: 'status', to: 'm1', status: 'working' },
  ]);
  assert.equal(t.state.m1, 'working');
});

test("the user's answer ends the agent's wait", () => {
  const t = thread([
    { action: 'note', id: 'm1', note: 'hi' },
    { action: 'status', to: 'm1', status: 'asked' },
    { action: 'note', id: 'm2', to: 'm1', note: 'this one' },
  ]);
  assert.equal(t.state.m1, 'replied');
  assert.deepEqual(ids(t.entries), ['m1']);  // the answer is part of the item, not a new one
  assert.deepEqual(Array.from(t.entries[0].replies, r => r.id), ['m2']);
});

test('a reply under a done or accepted item is a follow-up', () => {
  for (const finished of [{ action: 'status', to: 'm1', status: 'done' }, { action: 'accept', to: 'm1' }]) {
    const t = thread([{ action: 'note', id: 'm1', note: 'hi' }, finished, { action: 'note', id: 'm2', to: 'm1', note: 'more' }]);
    assert.equal(t.state.m1, 'followup');
  }
});

test('Open lists items not yet accepted, and not deleted comments', () => {
  const t = thread([
    { action: 'note', id: 'm1', note: 'open' },
    { action: 'note', id: 'm2', note: 'accepted' },
    { action: 'accept', to: 'm2' },
    { action: 'comment', id: 'c1', n: 1, comment: 'gone' },
    { action: 'delete', id: 'c1' },
    { action: 'note', id: 'm3', note: 'done' },
    { action: 'status', to: 'm3', status: 'done' },
  ]);
  assert.deepEqual(ids(t.open), ['m1', 'm3']);
});

test("the agent's own question is open and last until the user answers it", () => {
  const log = [
    { action: 'reply', id: 'r1', to: null, text: 'Which size?' },
    { action: 'note', id: 'm1', note: 'later message' },
  ];
  let t = thread(log);
  assert.deepEqual(ids(t.entries), ['m1', 'r1']);
  assert.deepEqual(ids(t.open), ['m1', 'r1']);
  t = thread(log.concat([{ action: 'note', id: 'm2', to: 'r1', note: 'Large' }]));
  assert.deepEqual(ids(t.open), ['m1']);
  assert.deepEqual(ids(t.entries), ['r1', 'm1']);  // answered, it goes back to its place in time
});

test('a reply without an id is not a question', () => {
  const t = thread([{ action: 'reply', to: null, text: 'FYI' }]);
  assert.deepEqual(ids(t.open), []);
});

test('an edited comment shows once, in its latest form', () => {
  const t = thread([
    { action: 'comment', id: 'c1', n: 1, comment: 'first' },
    { action: 'comment', id: 'c1', n: 1, comment: 'second' },
  ]);
  assert.equal(t.entries.length, 1);
  assert.equal(t.entries[0].e.comment, 'second');
  assert.equal(t.entries[0].edited, true);
});

test('replies nest under the item they answer, and an answer to a reply finds the same item', () => {
  const t = thread([
    { action: 'comment', id: 'c1', n: 1, comment: 'x' },
    { action: 'reply', id: 'r1', to: 'c1', text: 'why?' },
    { action: 'note', id: 'm1', to: 'r1', note: 'because' },
    { action: 'reopen', to: 'c1', reason: 'not fixed' },
  ]);
  assert.equal(t.entries.length, 1);
  assert.deepEqual(Array.from(t.entries[0].replies, r => r.action), ['reply', 'note', 'reopen']);
  assert.equal(t.state.c1, 'reopened');
});

test("a page's own item kinds count under Open", () => {
  const log = [{ action: 'decide', id: 'd1', option: 'A' }, { action: 'verdict', version: 'A', verdict: 'up' }];
  assert.deepEqual(ids(thread(log).open), []);
  assert.deepEqual(ids(thread(log, ['comment', 'note', 'decide']).open), ['d1']);
});
