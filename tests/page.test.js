// The shared page.js (src/better_ai/page/): the thread model (pageThreads), which turns the log into each thread's one
// state; Markdown in messages; the conversation's sending; the pin colours in page.css. Run with
// `node --test tests/*.test.js`. The dashboard's and the research board's own code is tested in their own files.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { read, loadPage } = require('./harness');

const context = loadPage();
const ITEMS = ['comment', 'note'];
const TABLE = JSON.parse(fs.readFileSync(__dirname + '/fixtures/threads.json', 'utf8'));

// The one state machine of every thread (.design/conversation-panel/states.md). `all_items` and `pending` in
// src/better_ai/page/__init__.py give the same threads, with the same states, for every log in the table.
const shape = t => ({ id: t.id, state: t.state, step: t.step, closedByUser: t.closedByUser });
test('the shared table of logs gives each thread the state `pending` gives it', () => {
  for (const { name, log, threads: expected, items } of TABLE) {
    const got = Array.from(context.pageThreads(log, items || ITEMS)).filter(t => !t.deleted);
    assert.deepEqual(got.map(shape), expected.map(shape), name);
    expected.forEach((t, k) => { if (t.since) assert.equal(got[k].since, t.since, name + ': since of ' + t.id); });
  }
});

test('a thread holds its messages, the latest form of its first one, and the index of your latest event', () => {
  const log = [
    { type: 'comment', id: 'c1', n: 1, text: 'first', by: 'user' },
    { type: 'reply', id: 'r1', to: 'c1', text: 'ok', by: 'coordinator' },
    { type: 'note', id: 'm1', to: 'r1', text: 'more', by: 'user' },
    { type: 'comment', id: 'c1', n: 1, text: 'edited', by: 'user' },
    { type: 'comment', id: 'c2', n: 2, text: 'gone', by: 'user' },
    { type: 'delete', to: 'c2', by: 'user' },
  ];
  const [c1, c2] = Array.from(context.pageThreads(log, ITEMS));
  assert.equal(c1.root.text, 'edited');
  assert.deepEqual(Array.from(c1.messages, m => m.id), ['c1', 'r1', 'm1']);
  assert.equal(c1.userAt, 2);
  assert.equal(c2.deleted, true);
});

test("a decision from the records is a thread: waiting is your turn, your answer is the agent's, and read counts in the log's own order", () => {
  const decisions = [{ id: 'D-1', at: '2026-11-28T10:00:00Z', asked: 'Which?', status: 'waiting' },
    { id: 'D-2', at: '2026-11-28T09:00:00Z', asked: 'Old', status: 'decided' }];
  const log = [
    { type: 'note', id: 'm1', to: null, text: 'hi', by: 'user', at: '2026-11-28T11:00:00Z' },
    { type: 'answer', id: 'a1', decision: 'D-1', text: 'A', default: false, by: 'user', at: '2026-11-28T11:05:00Z' },
  ];
  const states = l => Array.from(context.pageThreads(context.pageDecisionEvents(decisions, l), ITEMS), t => [t.id, t.state, t.step]);
  assert.deepEqual(states([]), [['D-2', 'done', 'new'], ['D-1', 'you', 'new']]);
  assert.deepEqual(states(log), [['D-2', 'done', 'new'], ['D-1', 'agent', 'new'], ['m1', 'agent', 'new']]);
  // read 0 is the note, the first line of the log: it does not cover the answer, the second.
  const stale = log.concat([{ type: 'status', to: 'a1', status: 'done', read: 0, by: 'coordinator', at: '2026-11-28T11:06:00Z' }]);
  assert.deepEqual(states(stale), [['D-2', 'done', 'new'], ['D-1', 'agent', 'new'], ['m1', 'agent', 'seen']]);
  const fresh = log.concat([{ type: 'status', to: 'a1', status: 'done', read: 1, by: 'coordinator', at: '2026-11-28T11:06:00Z' }]);
  assert.deepEqual(states(fresh), [['D-2', 'done', 'new'], ['D-1', 'done', 'new'], ['m1', 'agent', 'seen']]);
});

test('D14: a decision you answered is closed; one the agent decided or that defaulted stays in Open, done, until your check; waiting is your turn', () => {
  const at = m => `2026-11-28T10:${String(m).padStart(2, '0')}:00Z`;
  const decisions = [
    { id: 'W', at: at(0), asked: 'Which?', status: 'waiting' },
    { id: 'A', at: at(1), asked: 'Which?', status: 'answered', answer: { type: 'chat', text: 'B' } },
    { id: 'AE', at: at(2), asked: 'Which?', status: 'answered', default: null, deadline: null, answer: { type: 'page', event: 'a1' } },
    { id: 'P', at: at(3), asked: 'Which?', status: 'decided', decision: 'C' },
    { id: 'F', at: at(4), asked: 'Which?', status: 'defaulted', default: 'D' },
    { id: 'AW', at: at(5), asked: 'Which?', status: 'waiting' },
  ];
  const log = [
    { type: 'answer', id: 'a1', decision: 'AE', text: 'A', default: false, by: 'user', at: at(10) },
    { type: 'answer', id: 'a2', decision: 'AW', text: 'A', default: false, by: 'user', at: at(11) },
  ];
  const states = l => Object.fromEntries(Array.from(context.pageThreads(context.pageDecisionEvents(decisions, l), ITEMS),
    t => [t.id, [t.state, t.closedByUser]]));
  assert.deepEqual(states(log), {
    W: ['you', false], A: ['done', true], AE: ['done', true], P: ['done', false], F: ['done', false], AW: ['agent', false],
  });
  // Your check closes one the agent settled; your note under an answered one gives it back to the agent.
  const more = log.concat([{ type: 'accept', to: 'P', by: 'user', at: at(12) },
    { type: 'note', id: 'n1', to: 'a1', text: 'And also this.', by: 'user', at: at(13) }]);
  const after = states(more);
  assert.deepEqual([after.P, after.AE], [['done', true], ['agent', false]]);
  // A later answer of yours, to change your mind or to answer the agent's ask-back, is the agent's to apply.
  const later = log.concat([{ type: 'answer', id: 'a3', decision: 'AE', text: 'B after all', default: false, by: 'user', at: at(14) }]);
  assert.deepEqual(states(later).AE, ['agent', false]);
  const askback = log.concat([{ type: 'reply', id: 'r9', to: 'a1', text: 'A for both?', by: 'coordinator', at: at(15) },
    { type: 'status', to: 'a1', status: 'asked', by: 'coordinator', at: at(15) },
    { type: 'answer', id: 'a4', decision: 'AE', text: 'Yes', default: false, by: 'user', at: at(16) }]);
  assert.deepEqual(states(askback).AE, ['agent', false]);
});

test('every state the page gives a pin has a colour in page.css, and words for its title', () => {
  const css = read('page', 'page.css');
  assert.deepEqual(Object.keys(context.PAGE_PIN_STATES), ['new', 'seen', 'working', 'asked', 'done', 'accepted']);
  for (const state of Object.keys(context.PAGE_PIN_STATES)) assert.ok(css.includes(`.pin[data-state="${state}"]`), state);
});
test('an edited comment is one thread, in its latest form, marked edited', () => {
  const [t] = Array.from(context.pageThreads([
    { type: 'comment', id: 'c1', n: 1, text: 'first', by: 'user' },
    { type: 'comment', id: 'c1', n: 1, text: 'second', by: 'user' },
  ], ITEMS));
  assert.equal(t.root.text, 'second');
  assert.equal(t.messages.length, 1);
  assert.equal(t.edited, true);
});
test('replies join the thread they answer, an answer to a reply finds the same thread, and a reopen puts it back with the agent', () => {
  const [t] = Array.from(context.pageThreads([
    { type: 'comment', id: 'c1', n: 1, text: 'x', by: 'user' },
    { type: 'reply', id: 'r1', to: 'c1', text: 'why?', by: 'agent' },
    { type: 'status', to: 'c1', status: 'done', by: 'agent' },
    { type: 'note', id: 'm1', to: 'r1', text: 'because', by: 'user' },
    { type: 'status', to: 'm1', status: 'done', by: 'agent' },
    { type: 'reopen', to: 'c1', text: 'not fixed', by: 'user' },
  ], ITEMS));
  assert.deepEqual(Array.from(t.messages, m => m.type), ['comment', 'reply', 'note', 'reopen']);
  assert.deepEqual([t.state, t.step], ['agent', 'new']);
});
test("a page's own item kinds are the agent's turn; a verdict, no message to the agent, starts closed (D8)", () => {
  const log = [{ type: 'decide', id: 'd1', option: 'A', by: 'user' }, { type: 'verdict', version: 'A', verdict: 'up', by: 'user' }];
  const shape = items => Array.from(context.pageThreads(log, items), t => [t.id, t.state, t.closedByUser]);
  assert.deepEqual(shape(['comment', 'note', 'decide']), [['d1', 'agent', false], [null, 'done', true]]);
  assert.deepEqual(shape(ITEMS), [['d1', 'done', true], [null, 'done', true]]);
});
test("an answer to a decision joins its thread, and so does the coordinator's reply to that answer", () => {
  const ts = Array.from(context.pageThreads([
    { type: 'decision', id: 'D-1', x: { status: 'waiting' } },
    { type: 'answer', id: 'a1', decision: 'D-1', text: 'Use the default.', by: 'user' },
    { type: 'reply', id: 'r1', to: 'a1', text: 'Applied.', by: 'coordinator' },
  ], ITEMS));
  assert.deepEqual(ts.map(t => t.id), ['D-1']);
  assert.deepEqual(Array.from(ts[0].messages, m => m.id), ['D-1', 'a1', 'r1']);
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

test('when the server cannot be reached the page says the send may not have arrived, and keeps the text too', async () => {
  const { els, resets } = conversationOn(unreachable);
  els['#note'].value = 'my words';
  els['.notes .send .btn'].listeners.click({ preventDefault() {} });
  await nextTick();
  assert.equal(els['#note'].value, 'my words');
  assert.equal(els['.toast'].textContent, 'May not have been sent; check after the page reopens.');
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

test('delete, accept and reopen point at their thread with to, and reopen carries its words in text', () => {
  const [c1, c2] = Array.from(context.pageThreads([
    { type: 'comment', id: 'c1', n: 1, text: 'x', by: 'user' },
    { type: 'comment', id: 'c2', n: 2, text: 'y', by: 'user' },
    { type: 'delete', to: 'c1', by: 'user' },
    { type: 'status', to: 'c2', status: 'done', by: 'agent' },
    { type: 'reopen', to: 'c2', text: 'still wrong', by: 'user' },
  ], ITEMS));
  assert.equal(c1.deleted, true);
  assert.equal(c2.state, 'agent');
  assert.deepEqual(Array.from(c2.messages.slice(1), r => r.text), ['still wrong']);
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
const openIds = (decisions, log) => Array.from(context.pageOpenDecisions(decisions, log), x => x.id);

test('a waiting decision is open until the user answers it, and open again when the agent asks back about the answer', () => {
  const decisions = [dec('D1', 'waiting'), dec('D2', 'waiting'), dec('D3', 'defaulted'), dec('D4', 'decided', { decision: 'x' })];
  const answer = { type: 'answer', id: 'a-1', decision: 'D2', text: 'go', default: false, by: 'user', at: '2026-11-21T10:05:00Z' };
  assert.deepEqual(openIds(decisions, []), ['D1', 'D2']);
  assert.deepEqual(openIds(decisions, [answer]), ['D1']);
  const askedBack = { type: 'status', to: 'a-1', status: 'asked', by: 'coordinator', at: '2026-11-21T10:06:00Z' };
  assert.deepEqual(openIds(decisions, [answer, askedBack]), ['D1', 'D2']);
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

// ---------- A send that is repeated keeps its id (S127) ----------
// The reply to the first send is lost; the user presses Send again. Every path makes its id when the user clicks, so the
// page keeps the id of a send the server has not confirmed, and the server stores the event once.
const lostThenSaved = () => { let n = 0; return () => (++n === 1 ? unreachable() : saved()); };
const ticking = () => { let t = 1000; context.Date = class extends Date { static now() { return ++t; } }; return () => { delete context.Date; }; };

test('a note sent again after a lost reply carries the same id, and a note after a saved one a new id', async () => {
  const restore = ticking();
  try {
    const { els, sent } = conversationOn(lostThenSaved());
    els['#note'].value = 'my words';
    els['.notes .send .btn'].listeners.click({ preventDefault() {} });
    await nextTick();
    els['.notes .send .btn'].listeners.click({ preventDefault() {} });
    await nextTick();
    assert.equal(sent.length, 2);
    assert.equal(sent[0].params.id, sent[1].params.id);
    els['#note'].value = 'my words';
    els['.notes .send .btn'].listeners.click({ preventDefault() {} });
    await nextTick();
    assert.notEqual(sent[2].params.id, sent[1].params.id);
  } finally { restore(); }
});

for (const [method, params] of [
  ['comment', { n: 3, text: 'x', on: { slide: 1, part: null } }],
  ['answer', { decision: 'D1', text: 'yes', default: false }],
  ['approve', { option: 'a', text: 'ok' }],
  ['confirm', { requirement: 'R1', wording: 'w', text: 'ok' }],
  ['note', { to: 'm-1', text: 'a reply' }],
]) {
  test(`a ${method} sent again after a lost reply carries the same id`, async () => {
    const { conv, sent } = conversationOn(lostThenSaved());
    let made = 0;
    const click = () => conv.send(method, Object.assign({ id: `fresh-${++made}` }, params), 'Send');  // a new id on each click
    click();
    await nextTick();
    click();
    await nextTick();
    assert.equal(sent.length, 2);
    assert.equal(sent[0].params.id, sent[1].params.id);
    click();
    await nextTick();
    assert.notEqual(sent[2].params.id, sent[1].params.id, 'once saved, the next send is a new event');
  });
}

test('once the log shows a send the server saved without answering, the same text later is a new event with a new id', async () => {
  // verifier-t2b B3: the reply to "yes" is lost, but the server saved it; the user later sends "yes" again, for a new question.
  const restore = ticking();
  try {
    const { conv, sent } = conversationOn(lostThenSaved());
    conv.send('note', { id: 'm-first', text: 'yes', to: null }, 'Send');
    await nextTick();
    context.document.createElement = () => stubElement();
    context.document.createTextNode = () => stubElement();
    conv.setLog([{ type: 'note', id: 'm-first', text: 'yes', to: null, at: '2026-11-28T15:00:00Z' }], 'k1');
    conv.send('note', { id: 'm-later', text: 'yes', to: null }, 'Send');
    await nextTick();
    assert.equal(sent.length, 2);
    assert.equal(sent[1].params.id, 'm-later', 'the saved send is not reused');
  } finally { restore(); }
});

test('a different text is a different send, with its own id', async () => {
  const { conv, sent } = conversationOn(unreachable);
  conv.send('note', { id: 'a', text: 'one', to: null }, 'Message');
  await nextTick();
  conv.send('note', { id: 'b', text: 'two', to: null }, 'Message');
  await nextTick();
  assert.deepEqual(sent.map(s => s.params.id), ['a', 'b']);
});
