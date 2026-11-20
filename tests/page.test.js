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

test("an answer to a decision nests under it, and so does the coordinator's reply to that answer", () => {
  const t = thread([
    { action: 'decision', id: 'D-1', x: { status: 'pending' } },
    { action: 'answer', id: 'a1', decision: 'D-1', text: 'Use the default.' },
    { action: 'reply', id: 'r1', to: 'a1', text: 'Applied.' },
  ]);
  assert.deepEqual(ids(t.entries), ['D-1']);
  assert.deepEqual(Array.from(t.entries[0].replies, r => r.id), ['a1', 'r1']);
});

test("a page's own rule for what waits for the user puts those entries last", () => {
  const waiting = (c, state) => c.kind === 'decision' ? !c.replies.length : c.kind === 'note' && state[c.e.id] === 'asked';
  const log = [
    { action: 'decision', id: 'D-1', x: {} },
    { action: 'note', id: 'm1', text: 'a question' },
    { action: 'status', to: 'm1', status: 'asked' },
    { action: 'note', id: 'm2', text: 'later' },
  ];
  assert.deepEqual(ids(context.pageThread(log, ITEMS, waiting).entries), ['m2', 'D-1', 'm1']);
  const answered = log.concat([{ action: 'answer', id: 'a1', decision: 'D-1', text: 'yes' }]);
  assert.deepEqual(ids(context.pageThread(answered, ITEMS, waiting).entries), ['D-1', 'm2', 'm1']);
});

test("a message's words are its note, or its text on the board before it shared page.js", () => {
  assert.equal(context.pageWords({ note: 'new' }), 'new');
  assert.equal(context.pageWords({ text: 'old' }), 'old');
});

// ---------- Markdown in messages: pageMarkdownTree, the tree page.js turns into elements ----------
// The tree as plain JSON, so it compares across the vm boundary.
const md = text => JSON.parse(JSON.stringify(context.pageMarkdownTree(text)));
const t = text => ({ text });

test('plain text is one paragraph, and a single line break stays', () => {
  assert.deepEqual(md('hello\nthere'), [{ tag: 'p', children: [t('hello'), { tag: 'br' }, t('there')] }]);
  assert.deepEqual(md('one\n\ntwo').map(b => b.tag), ['p', 'p']);
});

test('inline marks: bold, italic, strikethrough, code, links', () => {
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

// The dashboard's decision card: its step comes from the decision file and from the state of the user's latest answer.
// The two helpers are read out of dashboard.html, between their own marker comments, so the test runs the shipped code.
const html = fs.readFileSync(path.join(__dirname, '..', 'skills', 'code-better', 'scripts', 'dashboard.html'), 'utf8');
const stepCode = html.split('// step:begin')[1].split('// item:end')[0];
// The whole decision card is run too, with a minimal DOM stub: the helpers it uses are the shipped ones.
const fakeEl = () => ({ className: '', dataset: {}, html: '', classList: { add(c) { this.list.push(c); }, list: [] },
  set innerHTML(v) { this.html = v; }, get innerHTML() { return this.html; },
  append(n) { this.html += n.html; }, insertAdjacentHTML(_w, v) { this.html += v; } });
const fakeDoc = { createElement: fakeEl };
const fakeConv = { progress: s => ({ html: `<span class="progress">${s}</span>` }) };
const { decisionStep, decisionItem } = new Function('document', 'conv', 'esc', 'has', 'md',
  stepCode + '; return {decisionStep, decisionItem};')(fakeDoc, fakeConv, s => String(s), v => v && v !== 'none', s => String(s));
const STEP_NAME = ['Waiting for you', 'You answered', 'Applied'];
const shows = (status, answer, st) => STEP_NAME[decisionStep(status, answer, st)];

test('a question the coordinator asked back about waits for the user again, until they answer again', () => {
  const a1 = { id: 'a-1', action: 'answer' }, a2 = { id: 'a-2', action: 'answer' };
  assert.equal(shows('waiting', null, {}), 'Waiting for you');
  assert.equal(shows('waiting', a1, {}), 'You answered');
  assert.equal(shows('waiting', a1, { 'a-1': 'seen' }), 'You answered');
  assert.equal(shows('waiting', a1, { 'a-1': 'asked' }), 'Waiting for you');
  assert.equal(shows('waiting', a2, { 'a-1': 'asked' }), 'You answered');  // the latest answer decides
  assert.equal(shows('waiting', a2, { 'a-1': 'asked', 'a-2': 'done' }), 'Applied');
  // The file already says answered: when the coordinator asks back, the latest answer decides, not the file.
  assert.equal(shows('answered', a1, { 'a-1': 'asked' }), 'Waiting for you');
  assert.equal(shows('answered', a2, { 'a-1': 'asked', 'a-2': 'seen' }), 'Applied');  // answered again: the file's word stands
  assert.equal(shows('answered', a2, { 'a-1': 'asked', 'a-2': 'done' }), 'Applied');
  assert.equal(shows('answered', null, {}), 'Applied');  // answered in the chat: no item in the thread
});

test('a decision card renders for a waiting, an answered-then-asked and a decided decision, and its head agrees with its foot', () => {
  const card = (status, answers) => ({ e: { x: { id: 'd1', status, asked: 'Which?', at: '2026-11-20T10:00:00' } },
    replies: answers.map(id => ({ action: 'answer', id })) });
  const run = (status, answers, st) => { const [item, foot] = decisionItem(card(status, answers), st, true); return { head: item.html.match(/class="when">([^<]*)</)[1], foot: foot.html, item }; };
  const waiting = run('waiting', [], {});
  assert.equal(waiting.head, '10:00');  // the time, not a state
  assert.match(waiting.foot, /Waiting for you/);
  assert.ok(waiting.item.classList.list.includes('open-q'));
  const asked = run('waiting', ['a-1'], { 'a-1': 'asked' });
  assert.equal(asked.head, '10:00');
  assert.match(asked.foot, /Waiting for you/);
  const answered = run('waiting', ['a-1'], {});
  assert.equal(answered.head, 'answered, waiting for the coordinator');
  assert.match(answered.foot, /You answered/);
  const applied = run('waiting', ['a-1'], { 'a-1': 'done' });
  assert.equal(applied.head, 'answered by you');
  assert.match(applied.foot, /Applied/);
  const reAsked = run('answered', ['a-1'], { 'a-1': 'asked' });  // the file says answered, the coordinator asked back
  assert.equal(reAsked.head, '10:00');
  assert.match(reAsked.foot, /Waiting for you/);
  assert.ok(reAsked.item.classList.list.includes('open-q'));
  assert.equal(run('answered', ['a-1', 'a-2'], { 'a-1': 'asked', 'a-2': 'seen' }).head, 'answered by you');
  assert.equal(run('answered', ['a-1', 'a-2'], { 'a-2': 'done' }).head, 'answered by you');
  const decided = run('decided', [], {});
  assert.equal(decided.head, 'decided');
  assert.doesNotMatch(decided.foot, /Waiting for you|You answered|Applied/);
});

test('with latestLast, an item whose reply is the newest message comes last, so the newest message is at the bottom', () => {
  const log = [
    { action: 'note', id: 'm1', note: 'first' },
    { action: 'note', id: 'm2', note: 'second' },
    { action: 'reply', id: 'r1', to: 'm1', text: 'answer to the first' },
  ];
  assert.deepEqual(ids(context.pageThread(log, ITEMS, null, true).entries), ['m2', 'm1']);
  assert.deepEqual(ids(context.pageThread(log, ITEMS).entries), ['m1', 'm2']);  // the other pages keep their order
  const later = log.concat({ action: 'note', id: 'm3', note: 'third' });
  assert.deepEqual(ids(context.pageThread(later, ITEMS, null, true).entries), ['m2', 'm1', 'm3']);
});

test("the dashboard's conversation opts in to latestLast", () => {
  assert.match(html, /latestLast: true/);
});

test('with latestLast, threads sort by their latest message and a question waiting for the user stays at the bottom', () => {
  const log = [
    { action: 'reply', id: 'q1', to: null, text: 'Which size?' },
    { action: 'note', id: 'm2', note: 'newer' },
  ];
  const waiting = c => c.e.id === 'q1';
  assert.deepEqual(ids(context.pageThread(log, ITEMS, waiting).entries), ['m2', 'q1']);
  const t = context.pageThread(log, ITEMS, waiting, true);
  assert.deepEqual(ids(t.entries), ['m2', 'q1']);  // the newer message does not push the question up
  assert.ok(ids(t.open).includes('q1'));  // it still counts as open
  const more = log.concat([{ action: 'note', id: 'm3', note: 'third' }, { action: 'reply', id: 'r1', to: 'm2', text: 'answer' }]);
  assert.deepEqual(ids(context.pageThread(more, ITEMS, waiting, true).entries), ['m3', 'm2', 'q1']);  // the rest by latest message
});

test('links with parentheses, as on Wikipedia, keep their whole address', () => {
  const w = 'https://en.wikipedia.org/wiki/Rust_(programming_language)';
  assert.deepEqual(md(`[Rust](${w})`)[0].children, [{ tag: 'a', href: w, children: [t('Rust')] }]);
  assert.deepEqual(md(`See ${w} for more.`)[0].children, [t('See '), { tag: 'a', href: w, children: [t(w)] }, t(' for more.')]);
  assert.deepEqual(md('(see https://a.com/x)')[0].children, [t('(see '), { tag: 'a', href: 'https://a.com/x', children: [t('https://a.com/x')] }, t(')')]);
});

test('bold inside italics', () => {
  assert.deepEqual(md('*a **b** c*')[0].children, [{ tag: 'em', children: [t('a '), { tag: 'strong', children: [t('b')] }, t(' c')] }]);
});

test('no link inside a link, however deep', () => {
  assert.deepEqual(md('[**https://a.com**](https://b.com)')[0].children,
    [{ tag: 'a', href: 'https://b.com', children: [{ tag: 'strong', children: [t('https://a.com')] }] }]);
});

test('a year at the start of a line does not start a list mid-paragraph', () => {
  assert.deepEqual(md('Released in\n2024. Then more.').map(b => b.tag), ['p']);
  assert.deepEqual(md('Steps:\n1. a\n2. b').map(b => b.tag), ['p', 'ol']);
});

test('bold and italic together', () => {
  assert.deepEqual(md('***x***')[0].children, [{ tag: 'strong', children: [{ tag: 'em', children: [t('x')] }] }]);
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

test('italics can close right before bold', () => {
  assert.deepEqual(md('*it***b**')[0].children, [{ tag: 'em', children: [t('it')] }, { tag: 'strong', children: [t('b')] }]);
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
