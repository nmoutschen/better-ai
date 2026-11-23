// The shared page.js (src/better_ai/page/): the thread model, which turns the log into each item's state, the entries and
// what Open lists; Markdown in messages; the conversation's sending; the pin colours in page.css. Run with
// `node --test tests/*.test.js`. The dashboard's and the research board's own code is tested in their own files.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { read, loadPage } = require('./harness');

const context = loadPage();
const ITEMS = ['comment', 'note'];
const thread = (log, items) => context.pageThread(log, items || ITEMS);
// Arrays made inside the vm context have that context's prototype, which deepStrictEqual rejects: copy them out.
const ids = list => Array.from(list, c => c.e.id);

// The items the agent has to work on, with their state, from the model of a log: the user's items that are not done or
// accepted, and the answers to the agent's own messages. `pending` in page/__init__.py gives the same for the same log.
function work(log) {
  const model = thread(log), found = [];
  model.entries.forEach(c => {
    if (ITEMS.includes(c.kind)) { if (!c.deleted) found.push(c.e.id); }
    else c.replies.forEach(r => { if (r.type === 'note' && r.to === c.e.id) found.push(r.id); });
  });
  const first = id => log.findIndex(e => e.id === id);
  return found.filter(id => !['done', 'accepted'].includes(model.state[id])).sort((a, z) => first(a) - first(z))
    .map(id => [id, model.state[id] || 'new']);
}

test('the shared table of logs gives the open items and states that `pending` gives', () => {
  for (const { name, log, work: expected } of JSON.parse(fs.readFileSync(__dirname + '/fixtures/threads.json', 'utf8'))) {
    assert.deepEqual(work(log), expected, name);
  }
});

test('every state the page gives an item has a pin colour in page.css', () => {
  const css = read('page', 'page.css');
  for (const state of Object.keys(context.PAGE_STATES)) assert.ok(css.includes(`.pin[data-state="${state}"]`), state);
});

test("the user's answer ends the agent's wait", () => {
  const t = thread([
    { type: 'note', id: 'm1', text: 'hi' },
    { type: 'status', to: 'm1', status: 'asked' },
    { type: 'note', id: 'm2', to: 'm1', text: 'this one' },
  ]);
  assert.equal(t.state.m1, 'replied');
  assert.deepEqual(ids(t.entries), ['m1']);  // the answer is part of the item, not a new one
  assert.deepEqual(Array.from(t.entries[0].replies, r => r.id), ['m2']);
});

test("the agent's own message waits for the user until the user answers it or the agent closes it", () => {
  const log = [
    { type: 'reply', id: 'r1', text: 'Which size?', to: null },
    { type: 'note', id: 'm1', text: 'later', to: null },
  ];
  assert.deepEqual(ids(thread(log).open), ['m1', 'r1']);
  assert.deepEqual(ids(thread(log).entries), ['m1', 'r1']);  // waiting: last, next to the message box
  for (const status of ['done', 'accepted']) {
    const closed = thread(log.concat([{ type: 'status', to: 'r1', status }]));
    assert.deepEqual(ids(closed.open), ['m1'], status);
    assert.deepEqual(ids(closed.entries), ['r1', 'm1'], status);  // back in its place
  }
  const answered = thread(log.concat([{ type: 'note', id: 'm2', text: 'large', to: 'r1' }]));
  assert.deepEqual(ids(answered.open), ['m1']);
});

test('Open lists items not yet accepted, and not deleted comments', () => {
  const t = thread([
    { type: 'note', id: 'm1', text: 'open' },
    { type: 'note', id: 'm2', text: 'accepted' },
    { type: 'accept', to: 'm2' },
    { type: 'comment', id: 'c1', n: 1, text: 'gone' },
    { type: 'delete', to: 'c1' },
    { type: 'note', id: 'm3', text: 'done' },
    { type: 'status', to: 'm3', status: 'done' },
  ]);
  assert.deepEqual(ids(t.open), ['m1', 'm3']);
});

test("the agent's own question is open and last until the user answers it", () => {
  const log = [
    { type: 'reply', id: 'r1', to: null, text: 'Which size?' },
    { type: 'note', id: 'm1', text: 'later message' },
  ];
  let t = thread(log);
  assert.deepEqual(ids(t.entries), ['m1', 'r1']);
  assert.deepEqual(ids(t.open), ['m1', 'r1']);
  t = thread(log.concat([{ type: 'note', id: 'm2', to: 'r1', text: 'Large' }]));
  assert.deepEqual(ids(t.open), ['m1']);
  assert.deepEqual(ids(t.entries), ['r1', 'm1']);  // answered, it goes back to its place in time
  assert.deepEqual(ids(thread([{ type: 'reply', to: null, text: 'FYI' }]).open), []);  // a reply without an id is not a question
});

test('an edited comment shows once, in its latest form', () => {
  const t = thread([
    { type: 'comment', id: 'c1', n: 1, text: 'first' },
    { type: 'comment', id: 'c1', n: 1, text: 'second' },
  ]);
  assert.equal(t.entries.length, 1);
  assert.equal(t.entries[0].e.text, 'second');
  assert.equal(t.entries[0].edited, true);
});

test('replies nest under the item they answer, and an answer to a reply finds the same item', () => {
  const t = thread([
    { type: 'comment', id: 'c1', n: 1, text: 'x' },
    { type: 'reply', id: 'r1', to: 'c1', text: 'why?' },
    { type: 'note', id: 'm1', to: 'r1', text: 'because' },
    { type: 'reopen', to: 'c1', text: 'not fixed' },
  ]);
  assert.equal(t.entries.length, 1);
  assert.deepEqual(Array.from(t.entries[0].replies, r => r.type), ['reply', 'note', 'reopen']);
  assert.equal(t.state.c1, 'reopened');
});

test("a page's own item kinds count under Open", () => {
  const log = [{ type: 'decide', id: 'd1', option: 'A' }, { type: 'verdict', version: 'A', verdict: 'up' }];
  assert.deepEqual(ids(thread(log).open), []);
  assert.deepEqual(ids(thread(log, ['comment', 'note', 'decide']).open), ['d1']);
});

test("an answer to a decision nests under it, and so does the coordinator's reply to that answer", () => {
  const t = thread([
    { type: 'decision', id: 'D-1', x: { status: 'pending' } },
    { type: 'answer', id: 'a1', decision: 'D-1', text: 'Use the default.' },
    { type: 'reply', id: 'r1', to: 'a1', text: 'Applied.' },
  ]);
  assert.deepEqual(ids(t.entries), ['D-1']);
  assert.deepEqual(Array.from(t.entries[0].replies, r => r.id), ['a1', 'r1']);
});

test("a page's own rule for what waits for the user puts those entries last", () => {
  const waiting = (c, state) => c.kind === 'decision' ? !c.replies.length : c.kind === 'note' && state[c.e.id] === 'asked';
  const log = [
    { type: 'decision', id: 'D-1', x: {} },
    { type: 'note', id: 'm1', text: 'a question' },
    { type: 'status', to: 'm1', status: 'asked' },
    { type: 'note', id: 'm2', text: 'later' },
  ];
  assert.deepEqual(ids(context.pageThread(log, ITEMS, waiting).entries), ['m2', 'D-1', 'm1']);
  const answered = log.concat([{ type: 'answer', id: 'a1', decision: 'D-1', text: 'yes' }]);
  assert.deepEqual(ids(context.pageThread(answered, ITEMS, waiting).entries), ['D-1', 'm2', 'm1']);
});

// ---------- Markdown in messages: pageMarkdownTree, the tree page.js turns into elements ----------
// The tree as plain JSON, so it compares across the vm boundary.
const md = text => JSON.parse(JSON.stringify(context.pageMarkdownTree(text)));
const t = text => ({ text });

test('plain text is one paragraph, and a single line break stays', () => {
  assert.deepEqual(md('hello\nthere'), [{ tag: 'p', children: [t('hello'), { tag: 'br' }, t('there')] }]);
  assert.deepEqual(md('one\n\ntwo').map(b => b.tag), ['p', 'p']);
});

test('inline marks: bold, italic, strikethrough, code, links; marks nest and meet', () => {
  assert.deepEqual(md('*a **b** c*')[0].children, [{ tag: 'em', children: [t('a '), { tag: 'strong', children: [t('b')] }, t(' c')] }]);  // bold inside italics
  assert.deepEqual(md('***x***')[0].children, [{ tag: 'strong', children: [{ tag: 'em', children: [t('x')] }] }]);  // bold and italic together
  assert.deepEqual(md('*it***b**')[0].children, [{ tag: 'em', children: [t('it')] }, { tag: 'strong', children: [t('b')] }]);  // italics close right before bold
  assert.deepEqual(md('**b** *i* _u_ ~~s~~ `x*y*`')[0].children, [
    { tag: 'strong', children: [t('b')] }, t(' '), { tag: 'em', children: [t('i')] }, t(' '),
    { tag: 'em', children: [t('u')] }, t(' '), { tag: 'del', children: [t('s')] }, t(' '),
    { tag: 'code', children: [t('x*y*')] }]);
  assert.deepEqual(md('[docs](https://x.dev/a) and https://y.dev.')[0].children, [
    { tag: 'a', href: 'https://x.dev/a', children: [t('docs')] }, t(' and '),
    { tag: 'a', href: 'https://y.dev', children: [t('https://y.dev')] }, t('.')]);
});

test('words that only look like marks stay as written', () => {
  assert.deepEqual(md('snake_case_name and 2 * 3 * 4')[0].children, [t('snake_case_name and 2 * 3 * 4')]);
  assert.deepEqual(md('\\*not italic\\*')[0].children, [t('*not italic*')]);
});

test('a link to anything but http, https or mailto is not a link', () => {
  assert.deepEqual(md('[x](javascript:alert(1))')[0].children.some(c => c.tag === 'a'), false);
  assert.deepEqual(md('[x](javascript:void)')[0].children, [t('[x](javascript:void)')]);
});

test('HTML in a message is text', () => {
  assert.deepEqual(md('<img src=x onerror=alert(1)>'), [{ tag: 'p', children: [t('<img src=x onerror=alert(1)>')] }]);
});

test('lists: bullets, numbers with their start, nesting, and a list right after a line of text', () => {
  const [p, ul] = md('Steps:\n- one\n- two\n  - nested\n- three');
  assert.equal(p.tag, 'p');
  assert.equal(ul.tag, 'ul');
  assert.deepEqual(ul.children.map(li => li.children[0].text), ['one', 'two', 'three']);
  assert.equal(ul.children[1].children[1].tag, 'ul');
  assert.deepEqual(md('3. c\n4. d')[0], { tag: 'ol', start: 3, children: [{ tag: 'li', children: [t('c')] }, { tag: 'li', children: [t('d')] }] });
});

test('headings, quotes, rules and code blocks', () => {
  assert.deepEqual(md('## Plan\n> quoted\n\n---\n```js\nif (a < b) **x**\n```').map(b => b.tag), ['p', 'blockquote', 'hr', 'pre']);
  assert.deepEqual(md('```\n**x**\n\n<b>\n```')[0], { tag: 'pre', children: [{ tag: 'code', children: [t('**x**\n\n<b>')] }] });
});

test('tables: a head, rows, alignment and missing cells', () => {
  const [table] = md('| a | b |\n|:-|-:|\n| 1 | **2** |\n| 3 |');
  assert.equal(table.tag, 'table');
  const [head, body] = table.children;
  assert.deepEqual(head.children[0].children.map(c => [c.tag, c.align]), [['th', ''], ['th', 'right']]);
  assert.deepEqual(body.children[0].children[1].children, [{ tag: 'strong', children: [t('2')] }]);
  assert.deepEqual(body.children[1].children[1].children, []);
});

test('an escaped mark neither opens nor closes italics', () => {
  assert.deepEqual(md('\\_x\\_')[0].children, [t('_x_')]);
  assert.deepEqual(md('*a\\*')[0].children, [t('*a*')]);
});

test('a blank line inside a list item stays, as in code under a step', () => {
  const [ul] = md('- step\n  ```\n  a\n\n  b\n  ```');
  assert.deepEqual(ul.children[0].children[1], { tag: 'pre', children: [{ tag: 'code', children: [t('a\n\nb')] }] });
  assert.deepEqual(md('- a\n\n  second')[0].children[0].children.map(c => c.tag || 'text'), ['text', 'p']);
});

test('a URL as link text is not a second link', () => {
  assert.deepEqual(md('[https://a.com](https://b.com)')[0].children, [{ tag: 'a', href: 'https://b.com', children: [t('https://a.com')] }]);
});

test('a line with a bar over a rule is not a table unless the cells match', () => {
  assert.deepEqual(md('Results: a | b\n---\nnext').map(b => b.tag), ['p', 'hr', 'p']);
  assert.ok(!md('a|b\n-').some(b => b.tag === 'table'));
});

test('nesting past the limit shows as written instead of overflowing', () => {
  assert.doesNotThrow(() => md('>'.repeat(4000) + ' x'));
  assert.doesNotThrow(() => md('- '.repeat(4000) + 'x'));
});

test('a list can start at 0', () => {
  assert.equal(md('0. zero\n1. one')[0].start, 0);
});

test('with latestLast, an item whose reply is the newest message comes last, so the newest message is at the bottom', () => {
  const log = [
    { type: 'note', id: 'm1', text: 'first' },
    { type: 'note', id: 'm2', text: 'second' },
    { type: 'reply', id: 'r1', to: 'm1', text: 'answer to the first' },
  ];
  assert.deepEqual(ids(context.pageThread(log, ITEMS, null, true).entries), ['m2', 'm1']);
  assert.deepEqual(ids(context.pageThread(log, ITEMS).entries), ['m1', 'm2']);  // the other pages keep their order
  const later = log.concat({ type: 'note', id: 'm3', text: 'third' });
  assert.deepEqual(ids(context.pageThread(later, ITEMS, null, true).entries), ['m2', 'm1', 'm3']);
});

test('with latestLast, threads sort by their latest message and a question waiting for the user stays at the bottom', () => {
  const log = [
    { type: 'reply', id: 'q1', to: null, text: 'Which size?' },
    { type: 'note', id: 'm2', text: 'newer' },
  ];
  const waiting = c => c.e.id === 'q1';
  assert.deepEqual(ids(context.pageThread(log, ITEMS, waiting).entries), ['m2', 'q1']);
  const t = context.pageThread(log, ITEMS, waiting, true);
  assert.deepEqual(ids(t.entries), ['m2', 'q1']);  // the newer message does not push the question up
  assert.ok(ids(t.open).includes('q1'));  // it still counts as open
  const more = log.concat([{ type: 'note', id: 'm3', text: 'third' }, { type: 'reply', id: 'r1', to: 'm2', text: 'answer' }]);
  assert.deepEqual(ids(context.pageThread(more, ITEMS, waiting, true).entries), ['m3', 'm2', 'q1']);  // the rest by latest message
});

test('links with parentheses, as on Wikipedia, keep their whole address', () => {
  const w = 'https://en.wikipedia.org/wiki/Rust_(programming_language)';
  assert.deepEqual(md(`[Rust](${w})`)[0].children, [{ tag: 'a', href: w, children: [t('Rust')] }]);
  assert.deepEqual(md(`See ${w} for more.`)[0].children, [t('See '), { tag: 'a', href: w, children: [t(w)] }, t(' for more.')]);
  assert.deepEqual(md('(see https://a.com/x)')[0].children, [t('(see '), { tag: 'a', href: 'https://a.com/x', children: [t('https://a.com/x')] }, t(')')]);
});

test('no link inside a link, however deep', () => {
  assert.deepEqual(md('[**https://a.com**](https://b.com)')[0].children,
    [{ tag: 'a', href: 'https://b.com', children: [{ tag: 'strong', children: [t('https://a.com')] }] }]);
});

test('a year at the start of a line does not start a list mid-paragraph', () => {
  assert.deepEqual(md('Released in\n2024. Then more.').map(b => b.tag), ['p']);
  assert.deepEqual(md('Steps:\n1. a\n2. b').map(b => b.tag), ['p', 'ol']);
});

test('marks can span a line break, which stays a break', () => {
  assert.deepEqual(md('**bold\nacross** end')[0].children,
    [{ tag: 'strong', children: [t('bold'), { tag: 'br' }, t('across')] }, t(' end')]);
  assert.deepEqual(md('`a\nb`')[0].children, [{ tag: 'code', children: [t('a b')] }]);
});

test('an indented fence takes its indentation off the code', () => {
  assert.deepEqual(md('  ```\n  x\n    y\n  ```')[0].children[0].children, [t('x\n  y')]);
  assert.deepEqual(md('- a\n\t```\n\tx\n\t```')[0].children[0].children[1].children[0].children, [t('x')]);
});

test('headings drop their closing #s only after a space', () => {
  assert.deepEqual(md('## Plan ##')[0].children[0].children, [t('Plan')]);
  assert.deepEqual(md('# C#')[0].children[0].children, [t('C#')]);
});

test("a notice shows the message's words without marks", () => {
  assert.equal(context.pageMarkdownText('## Done\n- **b**old `x`\n- [spec](https://a.com)'), 'Done bold x spec');
});

test('long messages with unclosed marks stay fast', () => {
  for (const text of ['**a '.repeat(50000), '# a' + ' '.repeat(50000), '_a '.repeat(50000), '`'.repeat(100000)]) {
    const start = Date.now();
    md(text);
    assert.ok(Date.now() - start < 500, `${JSON.stringify(text.slice(0, 6))}… took ${Date.now() - start} ms`);
  }
});

test('a numbered list right after a bullet list is its own list', () => {
  assert.deepEqual(md('- a\n- b\n2. Then').map(b => [b.tag, b.start]), [['ul', undefined], ['ol', 2]]);
});

test("a notice keeps a space between nested blocks' words", () => {
  assert.equal(context.pageMarkdownText('- a\n  - b'), 'a b');
});

test('element selectors use the nearest document-unique id in a page or slide', () => {
  // The simple fixture IDs need no escaping. The stub also checks which IDs are passed to CSS.escape.
  const escaped = [];
  context.CSS = { escape: id => { escaped.push(id); return id; } };
  const doc = { querySelectorAll: () => [outside, section, first, second, name].filter(node => node.id) };
  const element = (tagName, id, parentElement, previousElementSibling) =>
    ({ nodeType: 1, ownerDocument: doc, tagName, id, parentElement, previousElementSibling });
  doc.documentElement = element('HTML');
  doc.body = element('BODY', '', doc.documentElement);
  const outside = element('DIV', 'repeat', doc.body);
  const section = element('SECTION', 'anchor', doc.body, outside);
  const first = element('P', '', section);
  const second = element('P', 'repeat', section, first);
  const name = element('SPAN', 'name', second);

  assert.equal(context.pageElementSelector(name), '#name');
  assert.equal(context.pageElementSelector(second), '#anchor > p:nth-of-type(2)');
  assert.equal(context.pageElementSelector(second, section), 'p:nth-of-type(2)');
  section.id = '';
  assert.equal(context.pageElementSelector(second), 'body > section:nth-of-type(1) > p:nth-of-type(2)');
  assert.deepEqual(escaped, ['name', 'anchor']);
});

// ---------- Sending: what the user sees when the server refuses an event, as against when it cannot be reached ----------
// pageConversation runs here against a stub document and fetch: the elements are plain objects that keep what the page
// sets on them, so the test reads the toast, the status line and the message box as the user would.
const stubElement = extra => Object.assign({
  value: '', textContent: '', className: '', hidden: false, dataset: {}, listeners: {}, style: {},
  classList: { toggle() {}, add() {}, remove() {} },
  addEventListener(type, handler) { this.listeners[type] = handler; },
  querySelector() { return stubElement(); }, querySelectorAll() { return []; },
  replaceChildren() {}, append() {}, appendChild() {}, focus() {}, setAttribute() {},
}, extra);
const nextTick = () => new Promise(resolve => setTimeout(resolve, 0));

function conversationOn(answer, extra) {
  const els = { '.toast': stubElement({ hidden: true }), '.notes .status': stubElement(), '#note': stubElement(),
    '.notes .send .btn': stubElement(), '.thread': stubElement(), '.notes .empty': stubElement() };
  const sent = [];
  context.document = { querySelector: s => els[s] || stubElement(), querySelectorAll: () => [], contains: () => true };
  context.clearTimeout = clearTimeout;
  context.setTimeout = setTimeout;
  context.requestAnimationFrame = f => f();
  context.fetch = (url, init) => { sent.push(JSON.parse(init.body)); return answer(); };
  const applied = [], resets = [];
  const conv = context.pageConversation(Object.assign({
    served: true, name: 'canvas', apply: (e, fresh) => applied.push([e, fresh]), reset: () => resets.push(1),
  }, extra || {}));
  return { conv, els, sent, applied, resets };
}
const rejection = message => () => Promise.resolve({ json: () => Promise.resolve({ jsonrpc: '2.0', id: 1, error: { code: -32602, message } }) });
const saved = () => Promise.resolve({ json: () => Promise.resolve({ jsonrpc: '2.0', id: 1, result: 'saved' }) });
const unreachable = () => Promise.reject(new TypeError('Failed to fetch'));

test('a message the server rejects stays in the box, and the page shows the server\'s reason, not that it is closed', async () => {
  const { els, sent, applied } = conversationOn(rejection('text: required'));
  els['#note'].value = 'my words';
  els['.notes .send .btn'].listeners.click({ preventDefault() {} });
  await nextTick();
  assert.equal(els['#note'].value, 'my words');
  assert.match(els['.toast'].textContent, /text: required/);
  assert.doesNotMatch(els['.toast'].textContent, /closed/);
  assert.match(els['.toast'].className, /error/);
  assert.match(els['.notes .status'].textContent, /text: required/);
  assert.doesNotMatch(els['.notes .status'].textContent, /closed/);
  // The page sends its words as text and says what the message answers; the server sets the type, the author and the time.
  assert.equal(sent[0].method, 'note');
  assert.deepEqual(Object.keys(sent[0].params).sort(), ['id', 'text', 'to']);
  assert.equal(sent[0].params.text, 'my words');
  assert.equal(applied.length, 1);
});

test('a rejected event is undone on the page: the model is rebuilt from the log, which the event never reached', async () => {
  const { conv, els, applied, resets } = conversationOn(rejection('on.slide: required'));
  conv.send('comment', { id: 'c1', text: 'x', on: {} }, 'Comment 1');
  assert.equal(applied.length, 1);
  assert.equal(applied[0][0].type, 'comment');
  assert.equal(applied[0][0].by, 'user');
  assert.match(applied[0][0].at, /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$/);
  await nextTick();
  assert.equal(resets.length, 1);
  assert.match(els['.toast'].textContent, /on\.slide: required/);
});

test('when the server cannot be reached the page says the page is closed, and keeps the text too', async () => {
  const { els, resets } = conversationOn(unreachable);
  els['#note'].value = 'my words';
  els['.notes .send .btn'].listeners.click({ preventDefault() {} });
  await nextTick();
  assert.equal(els['#note'].value, 'my words');
  assert.match(els['.toast'].textContent, /closed/);
  assert.equal(resets.length, 1);
});

test('a saved message clears the box and is not undone', async () => {
  const { els, resets } = conversationOn(saved);
  els['#note'].value = 'my words';
  els['.notes .send .btn'].listeners.click({ preventDefault() {} });
  await nextTick();
  assert.equal(els['#note'].value, '');
  assert.match(els['.toast'].textContent, /sent/);
  assert.equal(resets.length, 0);
});

test('a comment box stays open with its text until the server has saved the comment', () => {
  const els = { textarea: stubElement(), '.ok': stubElement(), '.remove': stubElement(), '.cancel': stubElement(), '.target': stubElement() };
  const pop = stubElement({ querySelector: s => els[s] || stubElement(), offsetWidth: 10, offsetHeight: 10 });
  context.document = { contains: () => true };
  const calls = [];
  const layer = context.pageElementComments({
    pop, pinClass: 'pin', crumb: () => null, nextNumber: () => 1, params: (d, text) => ({ text, on: {} }),
    send: (method, params, what, done, fail) => calls.push({ method, params, done, fail }),
  });
  layer.open({}, null, null, () => ({ x: 0, y: 0 }));
  els.textarea.value = 'my comment';
  els['.ok'].listeners.click();
  assert.equal(calls.length, 1);
  assert.equal(calls[0].method, 'comment');
  assert.equal(calls[0].params.text, 'my comment');
  assert.equal(pop.hidden, false);  // still open: a rejection leaves the text where the user can fix it
  calls[0].done();
  assert.equal(pop.hidden, true);
});

test('a deletion points at its comment with to', () => {
  const els = { textarea: stubElement(), '.ok': stubElement(), '.remove': stubElement(), '.cancel': stubElement(), '.target': stubElement() };
  const pop = stubElement({ querySelector: s => els[s] || stubElement() });
  context.document = { contains: () => true };
  const calls = [];
  const layer = context.pageElementComments({ pop, pinClass: 'pin', send: (method, params) => calls.push({ method, params }) });
  layer.remove({ id: 'c1', n: 1 });
  assert.deepEqual(JSON.parse(JSON.stringify(calls)), [{ method: 'delete', params: { to: 'c1' } }]);
});

test('delete, accept and reopen point at their item with to, and reopen carries its words in text', () => {
  const t = thread([
    { type: 'comment', id: 'c1', n: 1, text: 'x' },
    { type: 'comment', id: 'c2', n: 2, text: 'y' },
    { type: 'delete', to: 'c1' },
    { type: 'status', to: 'c2', status: 'done' },
    { type: 'reopen', to: 'c2', text: 'still wrong' },
  ]);
  assert.equal(t.entries[0].deleted, true);
  assert.equal(t.state.c2, 'reopened');
  assert.deepEqual(Array.from(t.entries[1].replies, r => r.text), ['still wrong']);
});

// The agents at work (pageAgents): rows of who, what, since and the time of the last record, from any board.
const MIN = 60000, T0 = Date.parse('2026-11-23T12:00:00Z');
const ago = n => new Date(T0 - n * MIN).toISOString();
const agents = (rows, over) => context.pageAgents(rows, { now: T0 / 1000, ...over });

test('an agent row names who and what, and the age of its work in the shared working chip', () => {
  const html = agents([{ who: 'analyst-1', what: 'K2: Slow checkout', state: 'Checking', since: ago(12), last: ago(2) }]);
  assert.match(html, /<b>analyst-1<\/b>/);
  assert.match(html, /K2: Slow checkout/);
  assert.match(html, /<span class="chip working">Checking, 12 min<\/span>/);
  assert.doesNotMatch(html, /No word/);
});

test('a row without since shows no age, and one without a state word says Working', () => {
  assert.doesNotMatch(agents([{ who: 'w2', what: 'Q-1' }]), /chip/);
  assert.match(agents([{ who: 'w2', what: 'Q-1', since: ago(3) }]), />Working, 3 min</);
});

test('the quiet threshold comes from the data: from it on the row says no word came, and a minute less does not', () => {
  const row = (last, quietAfter) => agents([{ who: 'analyst-2', what: 'E4', state: 'Checking', since: ago(90), last }], { quietAfter });
  assert.match(row(ago(40), 1800), /No word from analyst-2 for 40 min/);
  assert.match(row(ago(30), 1800), /No word from analyst-2 for 30 min/);
  assert.doesNotMatch(row(ago(29), 1800), /No word/);
  assert.match(row(ago(10), 600), /No word from analyst-2 for 10 min/);
  assert.doesNotMatch(row(ago(90)), /No word/);  // no threshold given: nothing to say
  assert.doesNotMatch(agents([{ who: 'a', what: 'x', since: ago(90) }], { quietAfter: 1800 }), /No word/);  // no last record given
});

// The questions open for the user, one rule for every page: a decision waits until the user answers it on the page, and
// again once the agent asked back about that answer; any other entry waits when the page's WAITING says so.
const dec = (id, status, more) => ({ type: 'decision', id, status, asked: 'Login?', default: 'Go on', deadline: '2026-11-21T10:30:00Z', at: '2026-11-21T10:00:00Z', ...more });
const openIds = (decisions, log, kinds, waiting) => Array.from(context.pageOpenDecisions(decisions, log, kinds, waiting), c => c.e.id);

test('a waiting decision is open until the user answers it, and open again when the agent asks back about the answer', () => {
  const decisions = [dec('D1', 'waiting'), dec('D2', 'waiting'), dec('D3', 'defaulted'), dec('D4', 'decided', { decision: 'x' })];
  const answer = { type: 'answer', id: 'a-1', decision: 'D2', text: 'go', default: false, at: '2026-11-21T10:05:00Z' };
  assert.deepEqual(openIds(decisions, []), ['D1', 'D2']);
  assert.deepEqual(openIds(decisions, [answer]), ['D1']);
  const askedBack = { type: 'status', to: 'a-1', status: 'asked', at: '2026-11-21T10:06:00Z' };
  assert.deepEqual(openIds(decisions, [answer, askedBack]), ['D1', 'D2']);
});

test('an entry that is not a decision is open only when the page says it waits', () => {
  const log = [{ type: 'comment', id: 'c1', text: 'x', at: '2026-11-21T10:00:00Z' }, { type: 'status', to: 'c1', status: 'asked', at: '2026-11-21T10:01:00Z' },
    { type: 'comment', id: 'c2', text: 'y', at: '2026-11-21T10:02:00Z' }];
  assert.deepEqual(openIds([], log, ['comment']), []);
  assert.deepEqual(openIds([], log, ['comment'], (c, state) => state[c.e.id] === 'asked'), ['c1']);
});

test('a second try says so, and a plain row does not', () => {
  assert.match(agents([{ who: 'a', what: 'x', second: true }]), /second try/);
  assert.doesNotMatch(agents([{ who: 'a', what: 'x' }]), /second try/);
});

test('every part of a row is text, however it is written', () => {
  const html = agents([{ who: '<img src=x>', what: '<script>x</script>', state: '<i>', since: ago(1), note: '<u>', data: { a: '"><s>' } }]);
  assert.doesNotMatch(html, /<img|<script|<i>|<u>|<s>/);
});

test('a row with data is a button carrying it, and one without is not', () => {
  assert.match(agents([{ who: 'w2', what: 'Q-1', data: { a: 'w2', for: 'Q-1' } }]), /<button type="button" data-a="w2" data-for="Q-1">/);
  assert.doesNotMatch(agents([{ who: 'w2', what: 'Q-1' }]), /<button/);
});

test('no rows give the empty text, and a note is listed under its row', () => {
  assert.match(agents([], { empty: 'Nobody is working.' }), /<li class="muted">Nobody is working\.<\/li>/);
  assert.match(agents([{ who: 'a', what: 'x', note: '5 searches with nothing new' }]), /<em class="dry">5 searches with nothing new<\/em>/);
});

test('the age is read from a time in milliseconds or in ISO form, against the clock of the page, and never negative', () => {
  assert.match(agents([{ who: 'a', what: 'x', since: T0 - 5 * MIN }]), /Working, 5 min/);
  assert.match(agents([{ who: 'a', what: 'x', since: ago(-5) }]), /Working, 0 min/);
});

test('a verifier row carries its kind as a class, so its edge is the checker colour', () => {
  assert.match(agents([{ who: 'v1', what: 'Checking claims', kind: 'verifier', data: { a: 'v1' } }]), /<button type="button" class="verifier" data-a="v1">/);
  assert.match(agents([{ who: 'v1', what: 'x', kind: 'verifier' }]), /<div class="verifier">/);
});

test('an unusable time or a missing clock leaves the age out and never shows NaN', () => {
  const bad = agents([{ who: 'a', what: 'x', since: 'not a time', last: 'also not' }]);
  assert.doesNotMatch(bad, /NaN|chip|No word/);
  const noNow = context.pageAgents([{ who: 'a', what: 'x', since: ago(5), last: ago(90) }], {});
  assert.doesNotMatch(noNow, /NaN|chip|No word/);
});
