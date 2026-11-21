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
    { type: 'note', id: 'm1', text: 'hi' },
    { type: 'status', to: 'm1', status: 'seen' },
    { type: 'status', to: 'm1', status: 'working' },
  ]);
  assert.equal(t.state.m1, 'working');
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

test('a reply under a done or accepted item is a follow-up', () => {
  for (const finished of [{ type: 'status', to: 'm1', status: 'done' }, { type: 'accept', to: 'm1' }]) {
    const t = thread([{ type: 'note', id: 'm1', text: 'hi' }, finished, { type: 'note', id: 'm2', to: 'm1', text: 'more' }]);
    assert.equal(t.state.m1, 'followup');
  }
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
});

test('a reply without an id is not a question', () => {
  const t = thread([{ type: 'reply', to: null, text: 'FYI' }]);
  assert.deepEqual(ids(t.open), []);
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
const { decisionStep, decisionItem } = new Function('document', 'conv', 'esc', 'has', 'md', 'pageTime',
  stepCode + '; return {decisionStep, decisionItem};')(fakeDoc, fakeConv, s => String(s), v => v && v !== 'none', s => String(s), context.pageTime);
const STEP_NAME = ['Waiting for you', 'You answered', 'Applied'];
const shows = (status, answer, st) => STEP_NAME[decisionStep(status, answer, st)];

test('a question the coordinator asked back about waits for the user again, until they answer again', () => {
  const a1 = { id: 'a-1', type: 'answer' }, a2 = { id: 'a-2', type: 'answer' };
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
    replies: answers.map(id => ({ type: 'answer', id })) });
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
    { type: 'note', id: 'm1', text: 'first' },
    { type: 'note', id: 'm2', text: 'second' },
    { type: 'reply', id: 'r1', to: 'm1', text: 'answer to the first' },
  ];
  assert.deepEqual(ids(context.pageThread(log, ITEMS, null, true).entries), ['m2', 'm1']);
  assert.deepEqual(ids(context.pageThread(log, ITEMS).entries), ['m1', 'm2']);  // the other pages keep their order
  const later = log.concat({ type: 'note', id: 'm3', text: 'third' });
  assert.deepEqual(ids(context.pageThread(later, ITEMS, null, true).entries), ['m2', 'm1', 'm3']);
});

test("the dashboard's conversation opts in to latestLast", () => {
  assert.match(html, /latestLast: true/);
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

// The dashboard's task status and agent tag, on the JSON the dashboard now reads: read out of dashboard.html between `// status:begin` and `// status:end`.
const statusCode = html.split('// status:begin')[1].split('// status:end')[0];
const { taskStatus, agentTag, agentClass, DONE, isDone } = new Function('esc', statusCode + '; return {taskStatus, agentTag, agentClass, DONE, isDone};')(s => String(s));
// A task record is tasks.jsonl's: a blocked task names `reason` (task, user or repair limit) and, for task, `waits_on`.
const blockedFields = by => by === undefined || by === '' ? {} : by === 'user' || by === 'repair limit' ? { reason: by }
  : /^T\d+$/.test(by) ? { reason: 'task', waits_on: by } : { reason: by };
const shown = (status, blocked_by, tasks) => { const s = taskStatus({ status, ...blockedFields(blocked_by) }, tasks || [{ id: 'T2' }]); return [s.key, s.word]; };

test("a task shows the status tasks.jsonl gives it, each of the coordinate mode's stages with its own icon", () => {
  assert.deepEqual(shown('todo'), ['todo', 'to do']);
  assert.deepEqual(shown('building'), ['building', 'building']);
  assert.deepEqual(shown('built'), ['built', 'built']);
  assert.deepEqual(shown('verifying'), ['verifying', 'verifying']);
  assert.deepEqual(shown('changes needed'), ['changes', 'changes needed']);
  assert.deepEqual(shown('verified'), ['verified', 'verified']);
  assert.deepEqual(shown('merged'), ['merged', 'merged']);
  assert.deepEqual(shown('done'), ['done', 'done']);
  assert.deepEqual(shown(' Merged '), ['merged', 'merged']);
  const keys = ['todo', 'building', 'built', 'verifying', 'changes needed', 'verified', 'merged', 'blocked'].map(s => shown(s)[0]);
  assert.equal(new Set(keys).size, keys.length);
});

test('a blocked task says what it waits on, from its reason and waits_on only', () => {
  assert.deepEqual(shown('blocked', 'T2'), ['blocked', 'waiting on T2']);
  assert.deepEqual(shown('blocked', 'user'), ['blocked', 'waiting on you']);
  assert.deepEqual(shown('blocked', 'repair limit'), ['blocked', 'repair limit']);
  assert.deepEqual(shown('blocked', ''), ['blocked', 'blocked']);
  assert.deepEqual(shown('blocked', undefined), ['blocked', 'blocked']);
  // A reason that is not a task of the list, nor one of the two words, shows as written: never guessed into a task.
  assert.deepEqual(shown('blocked', 'T9'), ['blocked', 'blocked: T9']);
  assert.deepEqual(shown('blocked', 'needs a key'), ['blocked', 'blocked: needs a key']);
});

test('a status or a blocked reason with markup shows as text, never as HTML', () => {
  const realEsc = s => String(s).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const { statusLabel } = new Function('esc', statusCode + '; return {statusLabel};')(realEsc);
  assert.doesNotMatch(statusLabel({ status: 'blocked', reason: '<img src=x onerror=alert(1)>' }, []), /<img/);
  assert.match(statusLabel({ status: '<b>x</b>' }, []), /&lt;b&gt;x&lt;\/b&gt;/);
});

test('an unknown status shows as an error, with the status as written', () => {
  assert.deepEqual(shown('in review'), ['other', 'not a status: in review']);
  assert.deepEqual(shown('In Review'), ['other', 'not a status: In Review']);  // as written, casing kept
  assert.deepEqual(shown('Merged'), ['merged', 'merged']);
  assert.deepEqual(shown(''), ['other', 'no status']);
});

test('only merged and done tasks count as done, in any casing', () => {
  assert.deepEqual([...DONE].sort(), ['done', 'merged']);
  assert.equal([{ status: 'Merged' }, { status: ' DONE ' }, { status: 'verified' }, { status: '' }, {}].filter(isDone).length, 2);
});

test('a verifier shows as a verifier, a builder by its mode', () => {
  const v = { role: 'verifier', mode: 'bug fix' }, b = { role: 'builder', mode: 'bug fix' }, n = { mode: 'feature' };
  assert.match(agentTag(v), /class="mode r-verifier"[^>]*>verifier</);
  assert.doesNotMatch(agentTag(v), /bug fix/);
  assert.equal(agentClass(v), 'm-bugfix');  // the card edge is its task's mode colour; the tag says verifier
  assert.match(agentTag(b), /class="mode m-bugfix"[^>]*>bug fix</);
  assert.equal(agentClass(b), 'm-bugfix');
  assert.equal(agentClass(n), 'm-feature');  // no role: shown as a builder
  assert.match(agentTag({ role: ' Verifier ' }), />verifier</);
});

// ---------- The errors band: records that did not validate are listed, and the page stays live ----------
const errorsCode = html.split('// errors:begin')[1].split('// errors:end')[0];
const realEsc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const { errorsHTML } = new Function('esc', errorsCode + '; return {errorsHTML};')(realEsc);
const badRecords = [
  { file: 'tasks.jsonl', line: 2, field: 'status', message: 'must be one of "todo", "building"', by: 'coordinator' },
  { file: 'logs/b1.jsonl', line: 7, field: 'result', message: 'required when type is "handed_back"' },
];

test('the errors band lists each invalid record with its file and line, its field, the reason and who wrote it', () => {
  const band = errorsHTML(badRecords);
  assert.match(band, /2 records are not valid/);
  assert.match(band, /tasks\.jsonl:2/);
  assert.match(band, /status/);
  assert.match(band, /must be one of &quot;todo&quot;, &quot;building&quot;/);
  assert.match(band, /coordinator/);
  assert.match(band, /logs\/b1\.jsonl:7/);
  assert.match(errorsHTML([badRecords[0]]), /1 record is not valid/);
  assert.equal(errorsHTML([]), '');
  assert.equal(errorsHTML(undefined), '');
});

test('markup in an invalid record shows as text in the errors band', () => {
  const band = errorsHTML([{ file: '<b>f</b>', line: 1, field: '<img src=x>', message: '<script>x</script>', by: '<i>' }]);
  assert.doesNotMatch(band, /<img|<script|<i>|<b>f/);
  assert.match(band, /&lt;b&gt;f&lt;\/b&gt;/);
});

// tick() is read out of dashboard.html between `// load:begin` and `// load:end`, with stubs for what a page has.
const loadCode = html.split('// load:begin')[1].split('// load:end')[0];
function pageWith(answer) {
  const els = {};
  const el = id => els[id] || (els[id] = { hidden: true, textContent: '', id });
  const drawn = [];
  const body = new Function('fetch', '$', 'render', 'let D = null, CLOSED_PAGE = false;' + loadCode + '; return {tick, state: () => ({ fails, CLOSED_PAGE })};')(
    () => answer(), el, d => drawn.push(d));
  return { ...body, el, drawn };
}
const served = data => () => Promise.resolve({ ok: true, json: () => Promise.resolve(data) });

test('a folder with invalid records is not a closed dashboard: the page renders what is valid and the closed notice stays hidden', async () => {
  const page = pageWith(served({ tasks: [{ id: 'T1' }], agents: [], errors: badRecords, now: 1 }));
  await page.tick();
  await page.tick();
  assert.equal(page.el('offline').hidden, true);
  assert.equal(page.state().CLOSED_PAGE, false);
  assert.equal(page.drawn.length, 2);
  assert.equal(page.drawn[0].errors.length, 2);
});

test('the closed notice shows when the server cannot be reached', async () => {
  const page = pageWith(() => Promise.reject(new Error('down')));
  await page.tick();
  assert.equal(page.el('offline').hidden, true);  // once is a blip
  await page.tick();
  assert.equal(page.el('offline').hidden, false);
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
