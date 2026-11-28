// The code-better dashboard's own code (src/better_ai/code/dashboard.js): task status, the errors band, loading, and the
// task timeline. It is read out between marker comments (tests/harness.js), so the test runs the shipped code. The shared
// page.js, which it draws its conversation with, is tested in page.test.js. Run with `node --test tests/*.test.js`.
// The timeline shows local times: the tests pin the zone, so a time written in UTC reads the same on every machine.
process.env.TZ = 'UTC';
const test = require('node:test');
const assert = require('node:assert/strict');
const { read, stand, marked, between, loadPage, loadDashboard } = require('./harness');

const html = read('code', 'dashboard.js');

// The dashboard's task status and agent tag, on the JSON the dashboard now reads: read out of dashboard.html between `// status:begin` and `// status:end`.
const statusCode = marked(html, 'status');
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
  const { tablesHTML } = new Function('esc', statusCode + marked(html, 'timeline') + '; return {tablesHTML};')(realEsc);
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
  const TLb = new Function('esc', statusCode + marked(html, 'timeline') + '; return {tablesHTML, popupHTML};')(realEsc);
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
  const itemCode = between(html, 'function decisionItem', 'function crumb');
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
const shared = loadPage();
const realEsc = shared.pageEscape;
const badRecords = [
  { file: 'tasks.jsonl', line: 2, field: 'status', message: 'must be one of "todo", "building"', by: 'coordinator' },
  { file: 'logs/b1.jsonl', line: 7, field: 'result', message: 'required when type is "handed_back"' },
];

const errors = shared.pageErrors;
test(`the errors band lists each invalid record with its file and line, its field, the reason and who wrote it, and shows markup as text`, () => {
  const band = errors(badRecords);
  assert.match(band, /2 records are not valid/);
  assert.match(band, /tasks\.jsonl:2/);
  assert.match(band, /status/);
  assert.match(band, /must be one of &quot;todo&quot;, &quot;building&quot;/);
  assert.match(band, /coordinator/);
  assert.match(band, /logs\/b1\.jsonl:7/);
  assert.match(errors([badRecords[0]]), /1 record is not valid/);
  assert.equal(errors([]), '');
  assert.equal(errors(undefined), '');
  const markup = errors([{ file: '<b>f</b>', line: 1, field: '<img src=x>', message: '<script>x</script>', by: '<i>' }]);
  assert.doesNotMatch(markup, /<img|<script|<i>|<b>f/);
  assert.match(markup, /&lt;b&gt;f&lt;\/b&gt;/);
});

// tick() is read out of dashboard.js between `// load:begin` and `// load:end`, with stubs for what a page has. The closed
// notice is the shared page's: tests/page_shell.test.js.
const loadCode = marked(html, 'load');
function pageWith(answer, isStatic) {
  const drawn = [];
  const body = new Function('pageFetch', 'render', 'STATIC', loadCode + '; return {tick};')(() => answer(), d => drawn.push(d), !!isStatic);
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

// ---------- The task timeline (design: .design/code-better-board/design.md) ----------
// Read out of dashboard.js between `// timeline:begin` and `// timeline:end`, with the status code it builds on.
const timelineCode = marked(html, 'timeline');
const TL = new Function('esc', statusCode + timelineCode +
  '; return {groupOf, statusOf, phasesOf, bucketsOf, laneSVG, marksHTML, rowName, popupHTML, rangeOf, tablesHTML, runningWord};')(realEsc);
const E = s => Date.parse(s) / 1000;
const NOW = E('2026-11-23T10:58:00Z');
const line = (type, at, more) => ({ type, at, text: type, ...more });
// T4: built 09:52–10:20, verified 10:20–10:35 and failed, round 2 build from 10:36 with its last step at 10:40.
// The page's quiet threshold is the server's (page.QUIET_AFTER, 30 minutes); the fixture sets 15 so T4 is quiet at NOW.
const fixture = () => ({
  now: NOW, quiet_after: 15 * 60, start: '2026-11-23T09:30:00Z',
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
      last_word: '2026-11-23T10:40:00Z', lines: [line('start', '2026-11-23T10:36:00Z'), line('step', '2026-11-23T10:40:00Z', { text: 'running the full suite' })] },
    { name: 'builder-t7', role: 'builder', task: 'T7', branch: 'task/t7', at: '2026-11-23T10:25:00Z', state: 'working',
      last_word: '2026-11-23T10:56:00Z', lines: [line('start', '2026-11-23T10:26:00Z'), line('step', '2026-11-23T10:56:00Z', { text: 'fixed the cutoff' })] },
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

test('a build is quiet from the threshold the page is given, after the last word of its agent or the last file change', () => {
  const d = fixture();
  const word = over => TL.statusOf(d.tasks[0], { ...d, ...over }).word;
  assert.equal(word({ quiet_after: 30 * 60 }), 'building');  // 16 min since the file change at 10:42: under the shared 30
  assert.equal(word({ quiet_after: undefined }), 'building');  // no threshold given: nothing to say
  const later = fixture(); later.agents[2].last_word = '2026-11-23T10:50:00Z';  // a record at 10:50, later than the file change
  assert.equal(TL.statusOf(later.tasks[0], later).word, 'building');
  later.agents[2].last_word = '2026-11-23T10:43:00Z';
  assert.equal(TL.statusOf(later.tasks[0], later).word, 'building, quiet 15 min');
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

test('each range spans exactly its hours and ends now, even past the run start; All spans the whole run', () => {
  const d = fixture();  // a run of 88 minutes: longer than 1h, shorter than 2h and 6h
  for (const [range, hours] of [['1h', 1], ['2h', 2], ['6h', 6]]) {
    assert.deepEqual(TL.rangeOf(d, range), [NOW - hours * 3600, NOW], range);
    // the drawn lane is that many minutes wide, so each choice draws a different axis
    assert.match(TL.tablesHTML(d, range), new RegExp(`viewBox="0 0 ${(hours * 60).toFixed(3)} 28"`), range);
  }
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

// A builder the coordinator resumed for the next round keeps its card and its log: each round after a hand-back is a build of its own.
const resumed = () => {
  const d = fixture();
  d.agents.splice(2, 1);  // no second builder: builder-t4 is resumed instead
  d.agents[0].lines.push(line('start', '2026-11-23T10:36:00Z'), line('handed_back', '2026-11-23T10:50:00Z', { result: 'done' }));
  return d;
};
test('a resumed builder shows a build for each round, from its card, the round record and its start and hand-back lines', () => {
  const d = resumed();
  const p = TL.phasesOf(d.tasks[0], d).map(x => [x.kind, x.round, x.agent, x.start, x.end]);
  assert.deepEqual(p, [
    ['b', 1, 'builder-t4', E('2026-11-23T09:52:00Z'), E('2026-11-23T10:20:00Z')],
    ['v', 1, 'verifier-t4', E('2026-11-23T10:20:00Z'), E('2026-11-23T10:35:00Z')],
    ['b', 2, 'builder-t4', E('2026-11-23T10:36:00Z'), E('2026-11-23T10:50:00Z')],
  ]);
  const heads = [...TL.popupHTML(d.tasks[0], d).matchAll(/class="section-h">([^<]+)</g)].map(m => m[1]);
  assert.deepEqual(heads, ['Must make true', 'Build, round 2', 'Verify, round 1: failed', 'Build, round 1', 'Conversation']);
  const [t0, t1] = TL.rangeOf(d, '2h');
  assert.equal((TL.laneSVG(d.tasks[0], d, t0, t1).match(/fill="var\(--sand\)"/g) || []).length, 2);
});

test('a resumed builder that logs a step but no start still opens its next round, and an open round counts as building', () => {
  const d = resumed();
  d.agents[0].lines.splice(-2, 2, line('step', '2026-11-23T10:45:00Z', { text: 'added the header row' }));
  const last = TL.phasesOf(d.tasks[0], d).at(-1);
  assert.deepEqual([last.kind, last.round, last.start, last.end], ['b', 2, E('2026-11-23T10:45:00Z'), null]);
});

test("a later round whose first line has no time starts at its first line that has one", () => {
  const d = resumed();
  d.agents[0].lines.splice(-2, 1, { type: 'start', text: 'no time' });
  const last = TL.phasesOf(d.tasks[0], d).at(-1);
  assert.deepEqual([last.kind, last.start, last.end], ['b', E('2026-11-23T10:50:00Z'), E('2026-11-23T10:50:00Z')]);
});

test('a resumed verifier shows its own findings in each round, never those of its earlier round', () => {
  const d = fixture();
  d.agents[1].lines.push(line('start', '2026-11-23T10:51:00Z'), line('handed_back', '2026-11-23T10:55:00Z', { result: 'passes' }));
  d.agents[2].lines.push(line('handed_back', '2026-11-23T10:50:00Z', { result: 'done' }));
  const v = TL.phasesOf(d.tasks[0], d).filter(x => x.kind === 'v').map(x => [x.round, x.result]);
  assert.deepEqual(v, [[1, 'fails'], [2, 'passes']]);
  const pop = TL.popupHTML(d.tasks[0], d);
  assert.match(pop, /Verify, round 2: passed/);
  assert.equal((pop.match(/Empty export writes no header row/g) || []).length, 1);
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

// ---- The dashboard's own kinds inside the rows of the shared panel (S24, S25): dashboard.js runs whole on the stand-in
// shell (tests/dom.js), with the shared page.js's real panel.
const { shellDocument, mixedDocument, panelOn, text, actions } = require('./dom');
const at = h => new Date(Date.parse('2026-11-28T12:00:00Z') - h * 3600e3).toISOString().slice(0, 19) + 'Z';
function liveDashboard(data) {
  const doc = shellDocument();
  const shared = panelOn(null, null, { document: doc, config: { agent: 'coordinator', capabilities: ['pins', 'decisions'] } });
  const c = shared.context, env = {
    document: mixedDocument(doc), pageConversation: o => c.pageConversation(Object.assign({}, o, { served: false })),
    pageDecision: c.pageDecision, pageDecisionEvents: c.pageDecisionEvents, pageMarkdown: c.pageMarkdown, pageMarkdownText: c.pageMarkdownText,
    pageTime: c.pageTime, pageEscape: c.pageEscape, pageAgents: c.pageAgents, pagePopup: c.pagePopup, pageShowErrors: () => {},
    pageFetch: () => new Promise(() => {}), setInterval: () => {}, addEventListener: () => {}, innerWidth: 1000, innerHeight: 800,
    getComputedStyle: stand(), CSS: { escape: s => s },
  };
  const page = new Function(...Object.keys(env), read('code', 'dashboard.js') + '; return {render, conv};')(...Object.values(env));
  page.render(Object.assign({ now: Date.parse('2026-11-28T12:00:00Z') / 1000, name: 'Panel', tasks: [], agents: [], git: {} }, data));
  return Object.assign(shared, page);
}
const DASH_LOG = {
  decisions: [{ id: 'D1', at: at(3), asked: 'Keep the old endpoint? Clients still call it.', status: 'waiting', default: 'Keep it',
    deadline: '2026-11-28T13:00:00Z', raised_by: 'builder-t4', task: 'T4' }],
  conversation: [
    { type: 'comment', id: 'c1', on: { kind: 'task', id: 'T4', title: 'T4 Six pages' }, text: 'Check the canvas too.', by: 'user', at: at(2) },
    { type: 'reply', id: 'r1', to: 'c1', text: 'Done.', by: 'coordinator', at: at(1) }, { type: 'status', to: 'c1', status: 'done', by: 'coordinator', at: at(1) },
  ],
};

test('the dashboard draws a decision inside its row as your turn, with where it is from and its controls; a comment keeps its crumb', () => {
  const b = liveDashboard(DASH_LOG);
  // The dashboard feeds the panel before it writes its header: the figure is in its slot all the same.
  assert.equal(text(b.$('#status #yourturn')), '1 your turn');
  const d1 = b.rowOf('D1'), c1 = b.rowOf('c1');
  assert.equal(text(d1.querySelector('.chip')), 'Your turn');
  assert.deepEqual(actions(d1).map(x => x.textContent), ['✓', 'Use the default', 'Answer']);
  d1.querySelector('.thead').click();
  const body = text(b.rowOf('D1').querySelector('.tbody'));
  assert.match(body, /From builder-t4, task T4/);
  assert.match(body, /If you don't answer: Keep it/);
  assert.equal(c1.dataset.state, 'done');
  assert.deepEqual(actions(c1).map(x => x.textContent), ['✓', 'Reopen']);
  c1.querySelector('.thead').click();
  assert.equal(text(b.rowOf('c1').querySelector('.crumb .el')), 'T4 Six pages');
  // Open and All, as on every page; the figure in the dashboard's own header.
  assert.equal(text(b.$('[data-filter="open"]')), 'Open (2)');
  assert.equal(text(b.$('#status #yourturn')), '1 your turn');
});

test('the default answers the decision from its row, and the figure goes to 0', () => {
  const b = liveDashboard(DASH_LOG);
  actions(b.rowOf('D1'))[1].click();
  assert.deepEqual(b.conv.log().filter(e => e.type === 'answer').map(e => [e.decision, e.text, e.default]), [['D1', 'Keep it', true]]);
  assert.equal(text(b.rowOf('D1').querySelector('.chip')), 'Agent’s turn');
  assert.equal(text(b.$('#status #yourturn')), '0 your turn');
});

test('the dashboard gives the panel none of the options of the old per-item drawing', () => {
  let o;
  loadDashboard('0', { ...loadPage(), document: stand(), pageConversation: opts => { o = opts; return stand(); } });
  for (const gone of ['steps', 'labels', 'shown', 'accept', 'filter', 'waiting', 'latestLast', 'agentKinds']) assert.ok(!(gone in o), gone);
  assert.deepEqual(Object.keys(o.kinds), ['decision']);
});
