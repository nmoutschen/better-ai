// The thread model in page.js: how the log becomes each item's state, the entries and what Open lists.
// Run with `node --test tests/*.test.js`. page.js is identical in every skill (the Scripts workflow checks it); this loads
// the shared copy in src/better_ai/page/.
// The timeline shows local times: the tests pin the zone, so a time written in UTC reads the same on every machine.
process.env.TZ = 'UTC';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'src', 'better_ai', 'page', 'page.js'), 'utf8');
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

// The dashboard's own code is read out of src/better_ai/code/dashboard.js, between marker comments, so the test runs the
// shipped code. The decision question itself is the shared one: its tests are in page_shell.test.js.
const html = fs.readFileSync(path.join(__dirname, '..', 'src', 'better_ai', 'code', 'dashboard.js'), 'utf8');

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
const { taskStatus, DONE, isDone } = new Function('esc', statusCode + '; return {taskStatus, DONE, isDone};')(s => String(s));
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

test('a task that did not validate shows as not valid with its first message; an unknown status still shows as written', () => {
  const t = (status, _errors) => { const s = taskStatus({ status, _errors }, []); return [s.key, s.word]; };
  assert.deepEqual(t('built', ['requirements[0]: dangling']), ['other', 'not valid: requirements[0]: dangling']);
  assert.deepEqual(t('blocked', ['reason: required']), ['other', 'not valid: reason: required']);
  assert.deepEqual(t('in review', ['status: must be one of x']), ['other', 'not a status: in review']);
  assert.deepEqual(t('built', []), ['built', 'built']);
});

test('a status or a blocked reason with markup shows as text, never as HTML', () => {
  const realEsc = s => String(s).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const { tablesHTML } = new Function('esc', statusCode + html.split('// timeline:begin')[1].split('// timeline:end')[0] + '; return {tablesHTML};')(realEsc);
  const page = tablesHTML({ now: 1000, tasks: [{ id: 'T1', task: 'x', status: 'blocked', reason: '<img src=x onerror=alert(1)>' }, { id: 'T2', task: 'y', status: '<b>x</b>' }] }, '2h');
  assert.doesNotMatch(page, /<img/);
  assert.match(page, /&lt;b&gt;x&lt;\/b&gt;/);
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

// A kept invalid record can hold any type in any field: the page draws what it can and never throws.
test('a task with a wrongly typed requirements, mode or title still draws the tables', () => {
  const TLb = new Function('esc', statusCode + html.split('// timeline:begin')[1].split('// timeline:end')[0] + '; return {tablesHTML, popupHTML};')(realEsc);
  const bad = { id: 'T2', task: 7, mode: 5, requirements: 'R1', check: 7, status: 'built', _errors: ['requirements: expected array'] };
  const d = { now: 100000, start: null, tasks: [{ id: 'T1', task: 'ok', mode: 'feature', requirements: ['R1'], status: 'todo' }, bad],
    agents: [{ name: 'b', role: 'builder', task: 'T2', branch: 5, at: 3, lines: 'x' }], rounds: 'x', fixes: [{}], git: null, requirements: { R1: 'text' } };
  const out = TLb.tablesHTML(d, '2h');
  assert.match(out, />T1</);
  assert.match(out, />T2</);
  assert.match(out, /not valid: requirements: expected array/);
  assert.doesNotThrow(() => TLb.popupHTML(bad, d));
});

test('a decision that did not validate says so, with its first message, and a question says where it is from', () => {
  const itemCode = html.split('function decisionItem')[1].split('function crumb')[0];
  const shared = () => { const item = { html: '', querySelector: () => ({ insertAdjacentHTML: (_w, h) => { item.html += h; } }) }; return [item, {}]; };
  const decisionItem = new Function('dec', 'esc', 'has', 'function decisionItem' + itemCode + '; return decisionItem;')(
    { item: shared }, s => String(s), v => v && v !== 'none');
  const card = x => ({ e: { x: { id: 'd1', status: 'waiting', asked: 'Which?', at: '2026-11-20T10:00:00Z', ...x } }, replies: [] });
  const [item] = decisionItem(card({ _errors: ['about.task: dangling: "T9"'] }), {}, true);
  assert.match(item.html, /class="what invalid">not valid: about\.task: dangling/);
  const [clean] = decisionItem(card({ _errors: [], raised_by: 'b1', task: 'T2' }), {}, true);
  assert.doesNotMatch(clean.html, /not valid/);
  assert.match(clean.html, /From b1, task T2/);
  const [odd] = decisionItem(card({ asked: 5, raised_by: {}, task: [], _errors: ['asked: expected string'] }), {}, true);
  assert.match(odd.html, /not valid/);
});

test('an invalid task marked done or merged does not count toward the done total', () => {
  assert.equal([{ status: 'done' }, { status: 'merged', _errors: ['x'] }, { status: 'merged', _errors: [] }].filter(isDone).length, 2);
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

// tick() is read out of dashboard.js between `// load:begin` and `// load:end`, with stubs for what a page has. The closed
// notice is the shared page's: tests/page_shell.test.js.
const loadCode = html.split('// load:begin')[1].split('// load:end')[0];
function pageWith(answer, isStatic) {
  const drawn = [];
  const body = new Function('fetch', 'render', 'STATIC', loadCode + '; return {tick};')(() => answer(), d => drawn.push(d), !!isStatic);
  return { ...body, drawn };
}
const served = data => () => Promise.resolve({ ok: true, json: () => Promise.resolve(data) });

test('a folder with invalid records still renders what is valid', async () => {
  const page = pageWith(served({ tasks: [{ id: 'T1' }], agents: [], errors: badRecords, now: 1 }));
  await page.tick();
  await page.tick();
  assert.equal(page.drawn.length, 2);
  assert.equal(page.drawn[0].errors.length, 2);
});

test('a server that cannot be reached draws nothing and does not throw; a page written by render never fetches', async () => {
  const down = pageWith(() => Promise.reject(new Error('down')));
  await down.tick();
  assert.equal(down.drawn.length, 0);
  const fixed = pageWith(() => { throw new Error('fetched'); }, true);
  await fixed.tick();
  assert.equal(fixed.drawn.length, 0);
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

// The research board's page: its errors band and how it shapes the new record fields. Both are read out of board.js,
// between marker comments and between `const has =` and the map's layout, so the test runs the shipped code.
const boardJs = fs.readFileSync(path.join(__dirname, '..', 'src', 'better_ai', 'research', 'board.js'), 'utf8');
const plural = (n, w) => `${n} ${w}${n === 1 ? '' : 's'}`;
const { showLoaded, notValid } = new Function('esc', 'plural', boardJs.split('// errors:begin')[1].split('// errors:end')[0] + '; return {showLoaded, notValid};')(realEsc, plural);
const { prepare } = new Function('const has =' + boardJs.split('const has =')[1].split('// ---------- Slices')[0] + '; return {prepare};')();
const band = () => ({ errors: { hidden: true, innerHTML: '' } });

test('a board with invalid records shows its errors band', () => {
  const els = band();
  showLoaded({ listening: true, errors: [
    { file: 'claims/C-w2-9.json', line: 1, field: 'question', message: 'dangling: "Q-w9-1" is not a question record in ../questions/', by: 'w2' },
    { file: 'logs/w2.jsonl', line: 2, field: 'query', message: 'required' },
  ] }, els);
  assert.equal(els.errors.hidden, false);
  assert.match(els.errors.innerHTML, /2 problems/);
  assert.match(els.errors.innerHTML, /<code>claims\/C-w2-9\.json:1<\/code> question: dangling/);
  assert.match(els.errors.innerHTML, /\(by w2\)/);
  assert.match(els.errors.innerHTML, /<code>logs\/w2\.jsonl:2<\/code> query: required/);
});

test('the errors band is hidden when the board has no errors, and shows a message as text, never as HTML', () => {
  const els = band();
  showLoaded({ listening: true, errors: [] }, els);
  assert.deepEqual([els.errors.hidden, els.errors.innerHTML], [true, '']);
  showLoaded({ listening: true, errors: [{ file: 'a.json', line: 1, field: '<u>', message: '<img src=x>' }] }, els);
  assert.ok(!els.errors.innerHTML.includes('<img'));
  assert.ok(!els.errors.innerHTML.includes('<u>'));
});

test("the board's map reads the new fields: claims by question, merged and withdrawn records, where a question was raised", () => {
  const q = (id, over) => ({ id, status: 'open', title: id, priority: 'high', origin: { type: 'user' }, _born: 1, ...over });
  const c = (id, question, status, source) => ({ id, question, source: source || 'S-1', status });
  const d = prepare({ brief: {}, logs: { w2: { searches: [{ question: 'Q-1', query: 'a', new_terms: [] }, { question: 'Q-1', query: 'b', new_terms: ['x'] }] } },
    sources: [], decisions: [],
    questions: [q('Q-1'), q('Q-2', { kind: 'frontier', raised_in: 'Q-1' }), q('Q-3', { status: 'merged', merged_into: 'Q-1' }),
      q('Q-4', { origin: { type: 'source', source: 'S-9' } })],
    claims: [c('C-1', 'Q-1', 'verified'), c('C-2', 'Q-3', 'unchecked'), c('C-3', 'Q-1', 'withdrawn'), c('C-4', 'Q-1', 'checking', 'S-8'), c('C-5', 'Q-1', 'unchecked', 'S-9')] });
  assert.deepEqual(d.qs.map(x => x.id), ['Q-1', 'Q-2', 'Q-4']);
  assert.deepEqual(d.byId['Q-1'].claimsList.map(x => x.id), ['C-1', 'C-2', 'C-4', 'C-5']);
  assert.equal(d.byId['Q-2'].parent, 'Q-1');
  assert.equal(d.byId['Q-4'].parent, 'Q-1');  // the question of the first claim that cites its source
  assert.equal(d.byId['Q-1'].searches, 2);
});

test('searches on a merged question count for the question it was merged into', () => {
  const q = (id, over) => ({ id, status: 'open', title: id, priority: 'high', origin: { type: 'user' }, _born: 1, ...over });
  const d = prepare({ brief: {}, sources: [], decisions: [], claims: [],
    logs: { w2: { searches: [{ question: 'Q-3', query: 'a', new_terms: [] }, { question: 'Q-1', query: 'b', new_terms: [] }] } },
    questions: [q('Q-1'), q('Q-3', { status: 'merged', merged_into: 'Q-1' })] });
  assert.equal(d.byId['Q-1'].searches, 2);
});

test('the errors band is written only when its text changes, so a screen reader is not read it every poll', () => {
  let writes = 0, html = '';
  const els = { old: { hidden: true, textContent: '' },
    errors: { hidden: true, get innerHTML() { return html; }, set innerHTML(v) { writes++; html = v; } } };
  const d = { listening: true, errors: [{ file: 'a.json', line: 1, field: 'x', message: 'bad' }] };
  showLoaded(d, els); showLoaded(d, els); showLoaded({ ...d }, els);
  assert.equal(writes, 1);
  showLoaded({ listening: true, errors: [] }, els);
  assert.equal(writes, 2);
});

test('an invalid record the board still shows is marked with its first message, and the map copes with missing fields', () => {
  assert.equal(notValid({ _errors: ['status: must be one of "a"', 'x: y'] }), 'not valid: status: must be one of "a"');
  assert.equal(notValid({}), '');
  const d = prepare({ brief: {}, sources: [{ id: 'S-1', _errors: ['trust: bad'] }], decisions: [], logs: {},
    questions: [{ id: 'Q-1', _errors: ['status: bad'], status: 'merged' }, { id: 'Q-2', _errors: ['origin: required'] }],
    claims: [{ id: 'C-1', _errors: ['question: required'] }, { id: 'C-2', question: 'Q-2', source: 'S-1' }] });
  assert.deepEqual(d.qs.map(x => x.id), ['Q-1', 'Q-2']);  // merged without merged_into is not hidden
  assert.equal(d.byId['Q-2'].claimsList.length, 1);
});

test('an invalid merge, out-of-scope question or withdrawn claim stays visible, marked, and its claims stay on a drawn question', () => {
  const q = (id, over) => ({ id, status: 'open', title: id, priority: 'high', origin: { type: 'user' }, _born: 1, ...over });
  const c = (id, question, over) => ({ id, question, source: 'S-1', status: 'unchecked', ...over });
  const d = prepare({ brief: {}, sources: [], decisions: [], logs: {},
    questions: [q('Q-w2-4', { status: 'merged', merged_into: 'Q-w9-9', _errors: ['merged_into: dangling'] }),
      q('Q-2', { status: 'merged', merged_into: 'Q-1' }), q('Q-1'),
      q('Q-5', { status: 'out of scope', _errors: ['owner: bad'] }), q('Q-6', { status: 'out of scope' })],
    claims: [c('C-w2-7', 'Q-w2-4'), c('C-w2-8', 'Q-w2-4'), c('C-9', 'Q-1', { status: 'withdrawn', _errors: ['replaced_by: required'] }),
      c('C-10', 'Q-1', { status: 'withdrawn' }), c('C-11', 'Q-2')] });
  assert.deepEqual(d.qs.map(x => x.id), ['Q-w2-4', 'Q-1', 'Q-5']);  // a valid merge or out of scope question is not drawn
  assert.deepEqual(d.byId['Q-w2-4'].claimsList.map(x => x.id), ['C-w2-7', 'C-w2-8']);
  assert.deepEqual(d.byId['Q-1'].claimsList.map(x => x.id), ['C-9', 'C-11']);  // the valid merge sends C-11 to Q-1
});

test('a question merged into itself, or two merged into each other, stay drawn with their claims', () => {
  const q = (id, over) => ({ id, status: 'open', title: id, priority: 'high', origin: { type: 'user' }, _born: 1, ...over });
  const c = (id, question) => ({ id, question, source: 'S-1', status: 'unchecked' });
  const d = prepare({ brief: {}, sources: [], decisions: [], logs: {},
    questions: [q('Q-1', { status: 'merged', merged_into: 'Q-1' }),
      q('Q-2', { status: 'merged', merged_into: 'Q-3' }), q('Q-3', { status: 'merged', merged_into: 'Q-2' }),
      q('Q-4', { status: 'merged', merged_into: 'Q-2' }), q('Q-5'), q('Q-6', { status: 'merged', merged_into: 'Q-5' })],
    claims: [c('C-1', 'Q-1'), c('C-2', 'Q-2'), c('C-3', 'Q-3'), c('C-4', 'Q-4'), c('C-5', 'Q-6')] });
  assert.deepEqual(d.qs.map(x => x.id), ['Q-1', 'Q-2', 'Q-3', 'Q-5']);  // Q-4 is merged into Q-2, which is drawn
  assert.deepEqual(d.byId['Q-1'].claimsList.map(x => x.id), ['C-1']);
  assert.deepEqual(d.byId['Q-2'].claimsList.map(x => x.id), ['C-2', 'C-4']);
  assert.deepEqual(d.byId['Q-3'].claimsList.map(x => x.id), ['C-3']);
  assert.deepEqual(d.byId['Q-5'].claimsList.map(x => x.id), ['C-5']);
});

test('a kept invalid claim with a list for its question does not stop the board from preparing', () => {
  const q = id => ({ id, status: 'open', title: id, priority: 'high', origin: { type: 'user' }, _born: 1 });
  const d = prepare({ brief: {}, sources: [], decisions: [], logs: {}, questions: [q('Q-1')],
    claims: [{ id: 'C-1', question: ['Q-1'], source: ['S-1'], _errors: ['question: expected string, got array'] },
      { id: 'C-2', source: 'S-1', _errors: ['question: required'] }] });
  assert.deepEqual(d.qs.map(x => x.id), ['Q-1']);
  assert.deepEqual(d.byId['Q-1'].claimsList, []);
});

test('the errors band says which records are shown marked and which are only listed', () => {
  const els = band();
  showLoaded({ listening: true, errors: [{ file: 'a.json', line: 1, field: 'x', message: 'bad' }] }, els);
  assert.match(els.errors.innerHTML, /Questions and the brief are shown marked not valid, claims and sources under the question they name, and messages without the parts that failed; other records are only listed here\./);
});

test('the board marks an invalid brief like any other record', () => {
  assert.equal(notValid({ title: 'T', _errors: ['stop_at: must be one of "high"'] }), 'not valid: stop_at: must be one of "high"');
});

// ---------- The task timeline (design: .design/code-better-board/design.md) ----------
// Read out of dashboard.js between `// timeline:begin` and `// timeline:end`, with the status code it builds on.
const timelineCode = html.split('// timeline:begin')[1].split('// timeline:end')[0];
const TL = new Function('esc', statusCode + timelineCode +
  '; return {groupOf, statusOf, phasesOf, bucketsOf, laneSVG, marksHTML, rowName, popupHTML, rangeOf, tablesHTML, runningWord};')(realEsc);
const E = s => Date.parse(s) / 1000;
const NOW = E('2026-11-23T10:58:00Z');
const line = (type, at, more) => ({ type, at, text: type, ...more });
// T4: built 09:52–10:20, verified 10:20–10:35 and failed, round 2 build from 10:36 with its last step at 10:40.
const fixture = () => ({
  now: NOW, start: '2026-11-23T09:30:00Z',
  requirements: { S1: 'one', S2: 'two', S3: 'three', S4: 'four', S5: 'The export writes one CSV row per late order.', S6: 'six', S7: 'seven', S8: 'eight', S9: 'nine' },
  tasks: [
    { id: 'T4', task: 'CSV export', mode: 'feature', requirements: ['S5'], check: 'pytest tests/test_export.py', status: 'building' },
    { id: 'T7', task: 'Timezone fix', mode: 'bug fix', requirements: ['S1'], check: 'pytest', status: 'building' },
    { id: 'T5', task: 'Email digest', mode: 'feature', requirements: ['S2'], check: 'pytest', status: 'blocked', reason: 'user' },
    { id: 'T6', task: 'Digest unsubscribe', mode: 'feature', requirements: ['S3'], check: 'pytest', status: 'blocked', reason: 'task', waits_on: 'T5' },
    { id: 'T1', task: 'Order query', mode: 'feature', requirements: ['S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8', 'S9'], check: 'pytest', status: 'merged', status_at: '2026-11-23T09:52:00Z' },
    { id: 'T2', task: 'Late flag', mode: 'bug fix', requirements: ['S4'], check: 'pytest', status: 'merged', status_at: '2026-11-23T10:14:00Z' },
  ],
  agents: [
    { name: 'builder-t4', role: 'builder', task: 'T4', branch: 'task/t4', at: '2026-11-23T09:51:00Z', state: 'finished',
      lines: [line('start', '2026-11-23T09:52:00Z'), line('handed_back', '2026-11-23T10:20:00Z', { result: 'done' })] },
    { name: 'verifier-t4', role: 'verifier', task: 'T4', branch: 'task/t4', at: '2026-11-23T10:19:00Z', state: 'finished',
      lines: [line('start', '2026-11-23T10:20:00Z'), line('handed_back', '2026-11-23T10:35:00Z', { result: 'fails' })] },
    { name: 'builder-t4-2', role: 'builder', task: 'T4', branch: 'task/t4', at: '2026-11-23T10:35:30Z', state: 'working',
      lines: [line('start', '2026-11-23T10:36:00Z'), line('step', '2026-11-23T10:40:00Z', { text: 'running the full suite' })] },
    { name: 'builder-t7', role: 'builder', task: 'T7', branch: 'task/t7', at: '2026-11-23T10:25:00Z', state: 'working',
      lines: [line('start', '2026-11-23T10:26:00Z'), line('step', '2026-11-23T10:56:00Z', { text: 'fixed the cutoff' })] },
    { name: 'builder-t5', role: 'builder', task: 'T5', branch: 'task/t5', at: '2026-11-23T09:39:00Z', state: 'waiting',
      lines: [line('start', '2026-11-23T09:40:00Z'), line('asked', '2026-11-23T10:40:00Z', { text: 'which timezone?' })] },
    { name: 'builder-t2', role: 'builder', task: 'T2', branch: 'task/t2', at: '2026-11-23T09:34:00Z', state: 'finished',
      lines: [line('start', '2026-11-23T09:35:00Z'), line('handed_back', '2026-11-23T10:00:00Z', { result: 'done' })] },
    { name: 'verifier-t2', role: 'verifier', task: 'T2', branch: 'task/t2', at: '2026-11-23T09:59:00Z', state: 'finished',
      lines: [line('start', '2026-11-23T10:00:00Z'), line('handed_back', '2026-11-23T10:08:00Z', { result: 'passes' })] },
  ],
  rounds: [{ task: 'T4', round: 1, verifier: 'verifier-t4', at: '2026-11-23T10:35:20Z',
    findings: [{ text: 'Empty export writes no header row', blocking: true }, { text: 'Column order differs', blocking: false }] }],
  fixes: [{ task: 'T2', at: '2026-11-23T10:09:00Z', text: 'renamed the flag' }],
  git: {
    'task/t4': { buckets: [[E('2026-11-23T09:50:00Z'), 80], [E('2026-11-23T09:55:00Z'), 40], [E('2026-11-23T10:00:00Z'), 30], [E('2026-11-23T10:05:00Z'), 20],
      [E('2026-11-23T10:10:00Z'), 10], [E('2026-11-23T10:15:00Z'), 6], [E('2026-11-23T10:35:00Z'), 30], [E('2026-11-23T10:40:00Z'), 12]],
      commits: 3, added: 212, removed: 38, files: 5, last: E('2026-11-23T10:42:00Z') },
    'task/t7': { buckets: [[E('2026-11-23T10:55:00Z'), 20]], commits: 2, added: 164, removed: 41, files: 4, last: E('2026-11-23T10:57:00Z') },
  },
});

test('tasks fall in three tables: working once an agent started, pending before, merged at the end', () => {
  const d = fixture();
  const groups = Object.fromEntries(d.tasks.map(t => [t.id, TL.groupOf(t, d)]));
  assert.deepEqual(groups, { T4: 'working', T7: 'working', T5: 'working', T6: 'pending', T1: 'merged', T2: 'merged' });
  const page = TL.tablesHTML(d, '2h');
  const heads = [...page.matchAll(/<h2[^>]*>([^<]+)<\/h2>/g)].map(m => m[1]);
  assert.deepEqual(heads, ['Working (3)', 'Pending (1)', 'Merged (2)']);
  assert.ok(page.indexOf('>T4<') < page.indexOf('>T7<') && page.indexOf('>T7<') < page.indexOf('>T5<'));  // tasks.jsonl order
});

test('a quiet build says so in the error colour; waiting on you is umber with a question mark; a wait on a task is ink', () => {
  const d = fixture();
  const s = id => TL.statusOf(d.tasks.find(t => t.id === id), d);
  assert.equal(s('T4').word, 'building, quiet 16 min');  // last activity: the file change at 10:42, later than the step at 10:40
  assert.equal(s('T4').cls, 'warn');
  assert.equal(s('T7').word, 'building');
  assert.deepEqual([s('T5').cls, s('T5').word], ['you', 'waiting on you']);
  assert.match(s('T5').icon, /\?/);
  assert.deepEqual([s('T6').cls, s('T6').word], ['', 'waiting on T5']);
  assert.equal(s('T2').cls, 'merged');
});

test('phases come from the cards, the log times and the fix records, in order, with their rounds', () => {
  const d = fixture();
  const p = TL.phasesOf(d.tasks[0], d).map(x => [x.kind, x.round, x.start, x.end, x.result || '']);
  assert.deepEqual(p, [
    ['b', 1, E('2026-11-23T09:52:00Z'), E('2026-11-23T10:20:00Z'), 'done'],
    ['v', 1, E('2026-11-23T10:20:00Z'), E('2026-11-23T10:35:00Z'), 'fails'],
    ['b', 2, E('2026-11-23T10:36:00Z'), null, ''],
  ]);
  const t2 = TL.phasesOf(d.tasks.find(t => t.id === 'T2'), d).map(x => [x.kind, x.start, x.end]);
  assert.deepEqual(t2.at(-1), ['f', E('2026-11-23T10:09:00Z'), E('2026-11-23T10:14:00Z')]);  // a fix ends at the merge
});

test('a build phase takes the lines changed per 5 minutes on its branch, cut at its end, and a bucket with no change is zero', () => {
  const d = fixture();
  const [first, , second] = TL.phasesOf(d.tasks[0], d);
  const b1 = TL.bucketsOf(first, d), b2 = TL.bucketsOf(second, d);
  assert.deepEqual(b1.slice(0, 2), [[E('2026-11-23T09:52:00Z'), E('2026-11-23T09:55:00Z'), 80], [E('2026-11-23T09:55:00Z'), E('2026-11-23T10:00:00Z'), 40]]);
  assert.deepEqual(b1.at(-1), [E('2026-11-23T10:15:00Z'), E('2026-11-23T10:20:00Z'), 6]);  // never past the phase's end
  assert.deepEqual(b2.map(b => b[2]), [30, 12, 0, 0, 0]);
  assert.equal(b2.at(-1)[1], NOW);
});

test('the lane is one SVG in minutes: sand builds, terracotta-dark verifies, umber fixes, one dotted line per quiet stretch', () => {
  const d = fixture();
  const [t0, t1] = TL.rangeOf(d, '2h');
  const t4 = TL.laneSVG(d.tasks[0], d, t0, t1), t2 = TL.laneSVG(d.tasks.find(t => t.id === 'T2'), d, t0, t1);
  assert.match(t4, /^<svg[^>]*aria-hidden="true"/);
  assert.match(t4, /fill="var\(--sand\)"/);
  assert.match(t4, /fill="var\(--terracotta-dark\)"/);
  assert.equal((t4.match(/stroke-dasharray/g) || []).length, 1);  // 10:45 to now is one quiet stretch
  assert.match(t2, /fill="var\(--umber\)"/);
});

test('a failed round is marked R and its number, with its blocking findings on hover and focus; a merge is marked', () => {
  const d = fixture();
  const [t0, t1] = TL.rangeOf(d, '2h');
  const m = TL.marksHTML(d.tasks[0], d, t0, t1);
  assert.match(m, /✕ R1/);
  assert.match(m, /<button[^>]*class="ev fail/);
  assert.match(m, /Empty export writes no header row/);
  assert.doesNotMatch(m, /Column order differs/);  // not blocking: in the pop-up only
  assert.match(TL.marksHTML(d.tasks.find(t => t.id === 'T2'), d, t0, t1), /MERGED/);
  // within the last 7% of the axis, the word goes left of its rule
  const late = fixture(); late.agents[1].lines[1].at = '2026-11-23T10:56:00Z';
  assert.match(TL.marksHTML(late.tasks[0], late, t0, t1), /class="ev fail flip/);
});

test('a row is named for screen readers from the same records as the lane', () => {
  const d = fixture();
  assert.equal(TL.rowName(d.tasks[0], d),
    'T4 CSV export, feature, building, quiet 16 min, round 2, round 1 verify failed at 10:35, last file change 16 min ago');
});

test('the pop-up holds every requirement, the check, each phase newest first with its steps and times, and the findings', () => {
  const d = fixture();
  const t1 = TL.popupHTML(d.tasks.find(t => t.id === 'T1'), d);
  for (const id of ['S1', 'S5', 'S9']) assert.match(t1, new RegExp(`<b>${id}</b>`));
  const pop = TL.popupHTML(d.tasks[0], d);
  assert.match(pop, /Check: <code>pytest tests\/test_export.py<\/code>/);
  const heads = [...pop.matchAll(/class="section-h">([^<]+)</g)].map(m => m[1]);
  assert.deepEqual(heads, ['Must make true', 'Build, round 2', 'Verify, round 1: failed', 'Build, round 1', 'Conversation']);
  assert.match(pop, /<time>10:40<\/time>running the full suite/);
  assert.match(pop, /Blocking/);
  assert.match(pop, /Not blocking: Column order differs/);
  assert.match(pop, /\+212 −38 in 5 files, 3 commits/);
  assert.doesNotMatch(pop, / · /);
});

test('no requirement text is drawn outside the pop-up, so a row stays one row whatever its requirements', () => {
  const d = fixture();
  const page = TL.tablesHTML(d, '2h');
  assert.doesNotMatch(page, /seven|nine/);
});

test('the range ends now, starts at the run start when the run is shorter, and All spans the whole run', () => {
  const d = fixture();
  assert.deepEqual(TL.rangeOf(d, '1h'), [NOW - 3600, NOW]);
  assert.deepEqual(TL.rangeOf(d, '2h'), [E('2026-11-23T09:30:00Z'), NOW]);
  assert.deepEqual(TL.rangeOf(d, 'all'), [E('2026-11-23T09:30:00Z'), NOW]);
  const long = fixture(); long.start = '2026-11-23T05:00:00Z';
  assert.deepEqual(TL.rangeOf(long, '2h'), [NOW - 7200, NOW]);
  assert.match(TL.tablesHTML(long, '1h'), /<button[^>]*data-range="all"[^>]*>Show all<\/button>/);  // T1 and T2 ended before 09:58
});

test('a change without tasks says the coordinator has not split it yet', () => {
  const d = fixture(); d.tasks = []; d.agents = [];
  assert.match(TL.tablesHTML(d, '2h'), /The coordinator has not split the change into tasks yet\./);
});

test('the header says how long the change has run, as research-better does', () => {
  assert.equal(TL.runningWord(fixture()), '1h28m');
  assert.equal(TL.runningWord({ ...fixture(), start: '2026-11-23T10:50:00Z' }), '8m');
  assert.equal(TL.runningWord({ ...fixture(), start: '2026-11-23T10:57:30Z' }), '<2m');
});

test('markup in a title, a step or a finding shows as text', () => {
  const d = fixture();
  d.tasks[0].task = '<img src=x>';
  d.agents[2].lines[1].text = '<script>x</script>';
  d.rounds[0].findings[0].text = '<b>y</b>';
  const [t0, t1] = TL.rangeOf(d, '2h');
  const all = TL.tablesHTML(d, '2h') + TL.popupHTML(d.tasks[0], d) + TL.marksHTML(d.tasks[0], d, t0, t1);
  assert.doesNotMatch(all, /<img|<script|<b>y/);
});

// ---------- Found by the verifier: a fix after the merge, a phase that never handed back, a verifier run again ----------
test('a fix made after the merge ends after it starts, never before', () => {
  const d = fixture();
  d.fixes.push({ task: 'T2', at: '2026-11-23T10:30:00Z', text: 'late wording' });
  const fix = TL.phasesOf(d.tasks.find(t => t.id === 'T2'), d).at(-1);
  assert.equal(fix.kind, 'f');
  assert.ok(fix.end > fix.start);
  const [t0, t1] = TL.rangeOf(d, '2h');
  assert.doesNotMatch(TL.laneSVG(d.tasks.find(t => t.id === 'T2'), d, t0, t1), /width="-/);
  assert.doesNotMatch(TL.popupHTML(d.tasks.find(t => t.id === 'T2'), d), /10:30 to 10:14/);
});

test('a build that never handed back ends where the next phase starts', () => {
  const d = fixture();
  d.agents[2].lines = [line('start', '2026-11-23T10:36:00Z')];  // the round 2 builder, before a second one took over
  d.agents.push({ name: 'builder-t4-3', role: 'builder', task: 'T4', branch: 'task/t4', at: '2026-11-23T10:39:00Z',
    lines: [line('start', '2026-11-23T10:40:00Z')] });
  const p = TL.phasesOf(d.tasks[0], d);
  for (let i = 0; i + 1 < p.length; i++) assert.ok(p[i].end !== null && p[i].end <= p[i + 1].start, `phase ${i} overlaps the next`);
});

test("a failed round takes its number and findings from the round record that names its verifier", () => {
  const d = fixture();
  // a verifier started and stopped before it logged a hand-back, then another one failed the task: the coordinator's record says round 1
  d.agents.splice(1, 0, { name: 'verifier-t4-lost', role: 'verifier', task: 'T4', branch: 'task/t4', at: '2026-11-23T10:19:30Z',
    lines: [line('start', '2026-11-23T10:19:40Z')] });
  const [t0, t1] = TL.rangeOf(d, '2h');
  const m = TL.marksHTML(d.tasks[0], d, t0, t1);
  assert.match(m, /✕ R1/);
  assert.match(m, /Empty export writes no header row/);
  assert.match(TL.popupHTML(d.tasks[0], d), /Verify, round 1: failed/);
});

test("a task's lane opens the task's pop-up, as its label does", () => {
  assert.match(TL.tablesHTML(fixture(), '2h'), /<div class="lane" data-t="T4"/);
});

test('a phase starts when its agent started, even when the page holds only its latest log lines', () => {
  const d = fixture();
  d.agents[0].started = '2026-11-23T09:50:00Z';  // the builder's first line, before the 40 lines the page holds
  assert.equal(TL.phasesOf(d.tasks[0], d)[0].start, E('2026-11-23T09:50:00Z'));
});

test("a verify that passed never shows the findings of another verifier's failed round", () => {
  const d = fixture();
  d.agents.splice(1, 0, { name: 'verifier-t4-a', role: 'verifier', task: 'T4', branch: 'task/t4', at: '2026-11-23T10:19:00Z',
    lines: [line('start', '2026-11-23T10:19:10Z'), line('handed_back', '2026-11-23T10:19:50Z', { result: 'passes' })] });
  const pop = TL.popupHTML(d.tasks[0], d);
  const passed = pop.split('Verify, round 1: passed')[1].split('</div>')[0];
  assert.doesNotMatch(passed, /Empty export/);
});
