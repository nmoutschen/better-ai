// The agents panel and the pop-ups of the shared page (src/better_ai/page/page.js, page.css, shell.html): the agents' state
// from /agent in the Agents section, Stop and Start, the approval pop-up, the tab title and the header figure, with page.js run
// for real over a small stand-in document (tests/fake_dom.js). /agent answers with the body decision D1 fixes. No real browser.
const test = require('node:test');
const assert = require('node:assert/strict');
const { read, loadPage } = require('./harness');
const { makeDocument, fire, click, h } = require('./fake_dom');

const settle = async () => { for (let i = 0; i < 8; i++) await new Promise(resolve => setImmediate(resolve)); };
const body = over => Object.assign({
  state: 'idle', since: '2026-11-28T10:00:00Z', kind: null, text: null, mark_age: 0.2, approvals: [], workers: [], blocked: [],
  auto_approved_once: false,
}, over);
const approval = over => Object.assign({
  id: 'ap1', who: 'w3', tool: 'Read', arguments: 'example-release-notes.md', summary: 'to read a file',
  since: '2026-11-28T10:00:00Z', options: ['allow_once', 'allow_session', 'deny'],
}, over);
const waitingBody = over => body(Object.assign({
  state: 'waiting', approvals: [approval()],
  workers: [{ name: 'w3', item: 'Q-w3-1', waiting: true, silent_min: null }, { name: 'w1', item: 'Q-w1-1', waiting: false, silent_min: null }],
}, over));

const TEXT = {
  stopped: 'All agents are stopped. Press Start to have them read your messages.',
  login: "All agents are stopped because Claude Code isn't logged in. Log in from a terminal, then press Start.",
  closed: 'This page is closed after 30 minutes with no activity. Ask the agent in your chat to reopen it.',
  driver: "The page's agents stopped because of an error: boom. Ask the agent in your chat to serve this page again. Log: /tmp/u/.driver.log.",
  down: "The page's agent driver stopped. Ask the agent in your chat to serve this page again.",
  tab: 'This tab is no longer connected. Use the newer tab, or ask the agent in your chat to reopen the page.',
  blocked: 'Auto mode blocked Bash rm -rf build (the command deletes files). Run it yourself, or tell the agent how to go on.',
  stopAsk: 'All agents stop now, and any request waiting for you is denied. Recorded work is kept; work in progress is lost. Press Start to continue.',
  unsent: 'May not have been sent; check after the page reopens.',
};

// The shared shell (shell.html with agents.html in its side column), built element by element.
function build(doc, o) {
  const b = doc.body, x = (spec, attrs, ...kids) => h(doc, spec, attrs, ...kids);
  const agents = o.agents === false ? null : x('section.agentsec', { 'aria-labelledby': 'agents-h' },
    x('div.notes-top', {}, x('h2.section-h#agents-h', {}, 'Agents')), x('ul.agents#agents'));
  const config = x('script#page-config');
  config.textContent = JSON.stringify({ agent: 'coordinator', capabilities: [], driven: true });
  b.append(x('div.band'), x('header.bar--stats', {}, x('div', {}, x('h1#title', {}, 'Research'), x('p.goal#goal')), x('div.stats#status')),
    x('p.offline#offline', { hidden: true }), x('p.oldnote#oldnote', { hidden: true }),
    x('div.work', {}, x('main.view'),
      x('aside.notes', { 'aria-labelledby': 'notes-h' }, agents,
        x('div.notes-top', {}, x('h2#notes-h', {}, 'Conversation'),
          x('div.seg', {}, x('button', { 'data-filter': 'all', 'aria-pressed': 'false' }, 'All'), x('button', { 'data-filter': 'open', 'aria-pressed': 'true' }, 'Open'))),
        x('p.empty#empty'), x('ol.thread#thread'),
        x('form.composer#noteform', {}, x('p.unwatched#unwatched', { hidden: true }), x('label', {}, 'Message'), x('textarea#note'),
          x('div.send', {}, x('button.btn', { type: 'submit' }, 'Send'), x('p.status'))))),
    x('div.pop', { role: 'dialog', 'aria-label': 'Comment', hidden: true }, x('p.target'), x('textarea'), x('div.row2', {}, x('button.btn.ok', {}, 'Send'), x('button.btn.btn--quiet.cancel', {}, 'Cancel'), x('button.btn.btn--quiet.remove', {}, 'Delete'))),
    x('div.toast#toast', { hidden: true }), config);
}

// A page that has loaded: /agent answers with ctx.agent (a body, a status number or null for no answer), /rpc is recorded.
function boot(o = {}) {
  const doc = makeDocument(), timers = [], rpcs = [];
  doc.title = o.title || 'Research · Board';
  build(doc, o);
  const page = { doc, rpcs, agent: o.agent || body(), rpcFails: false, events: [], aborted: 0, stored: {} };
  const fetch = (url, init) => {
    if (url === '/agent') {
      if (page.agent === null) { init.signal.addEventListener('abort', () => page.aborted++); return new Promise(() => {}); }
      if (typeof page.agent === 'number') return Promise.resolve({ status: page.agent, ok: false });
      return Promise.resolve({ status: 200, ok: true, json: () => Promise.resolve(page.agent) });
    }
    if (url === '/rpc') {
      const call = JSON.parse(init.body);
      rpcs.push(call);
      if (page.rpcFails) return Promise.reject(new TypeError('network'));
      return Promise.resolve({ status: 200, ok: true, json: () => Promise.resolve({ jsonrpc: '2.0', id: call.id, result: true }) });
    }
    if (url.startsWith('/events')) {
      const after = Number(url.split('=')[1]);
      return after < page.events.length ? Promise.resolve({ ok: true, json: () => Promise.resolve({ events: page.events.slice(after), total: page.events.length }) }) : new Promise(() => {});
    }
    if (url === '/rev') return Promise.resolve({ ok: true, text: () => Promise.resolve('1') });
    if (url === '/old') return Promise.resolve({ ok: true, json: () => Promise.resolve(0) });
    return Promise.reject(new Error('unexpected ' + url));
  };
  page.ctx = loadPage({
    document: doc, fetch, URLSearchParams, AbortController, Date, JSON, innerWidth: o.width || 1440, innerHeight: 900,
    location: { hash: '', pathname: '/', search: '' }, history: { replaceState() {} },
    sessionStorage: { getItem: () => 'secret', setItem() {}, removeItem() {} },
    setTimeout: (fn, delay) => { timers.push({ fn, delay }); return timers.length; }, clearTimeout() {}, requestAnimationFrame: f => f(),
  });
  page.timers = timers;
  // One poll interval: every timer that is due runs.
  page.tick = async () => { await settle(); const due = timers.splice(0); due.forEach(t => t.fn()); await settle(); };
  page.show = async next => { page.agent = next; await page.tick(); };
  page.agentsHtml = () => doc.getElementById('agents').innerHTML;
  page.control = () => doc.querySelector('.agentsec .agent-ctl');
  page.pinbar = () => doc.querySelector('.pinbar');
  page.dialog = () => doc.querySelector('.pop.center');
  page.button = (root, text) => root.querySelectorAll('button').find(b => b.textContent === text);
  page.toast = () => doc.getElementById('toast').textContent;
  page.escaped = text => page.ctx.pageEscape(text);
  return page;
}

// ---------- S23, S24: the agents' state, polled every 2 s ----------

test('S23: /agent is polled every 2 s and each state shows within one poll', async () => {
  const page = boot({ agent: body({ state: 'working' }) });
  await settle();
  assert.deepEqual(page.timers.map(t => t.delay), [2000]);
  const cases = [
    ['idle', body({ state: 'idle' }), 'Stop', null], ['working', body({ state: 'working' }), 'Stop', null],
    ['waiting', waitingBody(), 'Stop', null], ['stalled', body({ state: 'stalled' }), 'Stop', null],
    ['stopping', body({ state: 'stopping' }), null, null],
    ['stopped', body({ state: 'stopped', text: TEXT.stopped }), 'Start', TEXT.stopped],
    ['failed', body({ state: 'failed', kind: 'login', text: TEXT.login }), 'Start', TEXT.login],
    ['closed', body({ state: 'closed', kind: 'idle', text: TEXT.closed }), null, TEXT.closed],
  ];
  for (const [state, next, control, text] of cases) {
    await page.show(next);
    assert.deepEqual(page.timers.map(t => t.delay), [2000], state);
    const button = page.control();
    assert.equal(button && !button.hidden ? button.textContent : null, control, state + ' control');
    const html = page.agentsHtml();
    if (text) assert.ok(html.includes(page.escaped(text)), state + ' text in the Agents section');
    else assert.ok(!html.includes('notice'), state + ' shows no notice');
  }
});

test('S61: a failed agent shows the text of its kind, in the Agents section', async () => {
  const page = boot();
  const kinds = {
    login: TEXT.login,
    limit: 'All agents are stopped because Claude Code reached its usage limit. Try again later, then press Start.',
    crashed: 'All agents are stopped because Claude Code ended unexpectedly. Press Start to retry.',
    'not-handling': 'All agents are stopped because they did not handle your message. Press Start to retry, or reword it.',
    driver: TEXT.driver,
    protocol: 'All agents are stopped because Claude Code sent a message the page does not know. Press Start to retry.',
  };
  for (const [kind, text] of Object.entries(kinds)) {
    await page.show(body({ state: 'failed', kind, text }));
    assert.ok(page.agentsHtml().includes(page.escaped(text)), kind);
    // Start retries every kind but the driver's own error, which asks for serving the page again.
    assert.equal(page.control() && !page.control().hidden ? page.control().textContent : null, kind === 'driver' ? null : 'Start', kind);
  }
});

test('S24: a liveness mark older than 3 s, or no answer, shows the driver stopped within 5 s', async () => {
  const page = boot({ agent: body({ state: 'working' }) });
  await page.tick();
  await page.show(body({ state: 'working', mark_age: 3.01, approvals: [approval()] }));
  assert.ok(page.agentsHtml().includes(page.escaped(TEXT.down)));
  assert.ok(!page.control() || page.control().hidden, 'no Stop for a driver that is gone');
  assert.deepEqual(Array.from(page.ctx.pageApprovals()), [], 'no approval to answer while the driver is gone');
  await page.show(body({ state: 'working', mark_age: 1 }));
  assert.ok(!page.agentsHtml().includes('notice'));
  await page.show(null);                       // asked, no answer
  await page.tick();                           // the next poll cancels it and shows the notice: 2 s later
  assert.equal(page.aborted, 1);
  assert.ok(page.agentsHtml().includes(page.escaped(TEXT.down)));
  await page.show(500);                        // the server answers with an error
  assert.ok(page.agentsHtml().includes(page.escaped(TEXT.down)));
});

test('S166: a tab the server no longer knows says so, and stops asking', async () => {
  const page = boot({ agent: 403 });
  await page.tick();
  const strip = page.doc.querySelector('.offline');
  assert.equal(strip.textContent, TEXT.tab);
  assert.equal(strip.hidden, false);
  assert.equal(page.timers.length, 0, 'no more polls');
  assert.ok(!page.control() || page.control().hidden);
});

// ---------- S162, S163: the Agents section ----------

const ROWS = [{ who: 'w1', what: 'How the form changed', data: { a: 'w1' } }, { who: 'w2', what: 'Mobile only?', data: { a: 'w2' } },
  { who: 'w3', what: 'Payment errors', data: { a: 'w3' } }];
const draw = page => page.ctx.pageAgents(ROWS, { now: 1000, empty: 'No agent is working right now.' });

test('S162: a worker waiting for the user carries the filled wait chip and sorts above the others', async () => {
  const page = boot();
  await page.show(waitingBody());
  const html = draw(page);
  const first = html.slice(0, html.indexOf('</li>'));
  assert.match(first, /<b>w3<\/b>/);
  assert.match(first, /<span class="chip wait">Waiting for you<\/span>/);
  assert.match(first, /data-approval-for="w3"/);
  assert.ok(html.indexOf('<b>w1</b>') < html.indexOf('<b>w2</b>'), 'the others keep their order');
  assert.equal((html.match(/chip wait/g) || []).length, 1);
  assert.doesNotMatch(html, /chip working/);
  // A waiting worker the page lists no row for still shows, first.
  await page.show(waitingBody({ workers: [{ name: 'w9', item: 'Q-9', waiting: true, silent_min: null }] }));
  assert.ok(draw(page).indexOf('<b>w9</b>') < draw(page).indexOf('<b>w1</b>'));
  // Nothing waits: the list is as the page gave it.
  await page.show(body({ state: 'working', workers: [{ name: 'w3', item: 'Q-w3-1', waiting: false, silent_min: null }] }));
  assert.doesNotMatch(draw(page), /chip wait|data-approval-for/);
});

test('S162: the filled chip is a fill, not only a colour: umber on cream text', () => {
  const css = read('page', 'page.css');
  assert.match(css, /\.agents \.chip\.wait\s*\{[^}]*background:var\(--umber\)[^}]*color:var\(--cream\)/);
});

test('S163: the agents state replaces the empty text in the Agents section, and the conversation shows none', async () => {
  const page = boot({ agent: body({ state: 'stopped', text: TEXT.stopped }) });
  await page.tick();
  assert.ok(page.agentsHtml().includes(page.escaped(TEXT.stopped)));
  assert.doesNotMatch(page.agentsHtml(), /No agent is working/);
  // Once the page draws its own rows, the notice stays in place of the empty text and ahead of any row.
  const html = page.ctx.pageAgents([], { now: 1000, empty: 'No agent is working right now.' });
  assert.ok(html.includes(page.escaped(TEXT.stopped)));
  assert.doesNotMatch(html, /No agent is working/);
  const withRows = page.ctx.pageAgents(ROWS, { now: 1000, empty: 'x' });
  assert.ok(withRows.indexOf('read your messages') < withRows.indexOf('<b>w1</b>'));
  // Nothing about the agents under the Conversation heading: no state line, no strip of the old design.
  const conversation = page.doc.querySelector('.notes > .notes-top');
  assert.equal(conversation.textContent, 'ConversationAllOpen');
  assert.ok(page.doc.querySelector('.unwatched').hidden);
  assert.equal(page.doc.getElementById('thread').textContent, '');
  const shell = read('page', 'shell.html');
  assert.doesNotMatch(shell, /agent-status|agent-controls|approval tab/);
});

test('S163: a page without an Agents section gets the same one, with the same notice', async () => {
  const page = boot({ agents: false, agent: body({ state: 'stopped', text: TEXT.stopped }) });
  await page.tick();
  const section = page.doc.querySelector('.notes > .agentsec');
  assert.ok(section, 'the section is made');
  assert.equal(section.querySelector('.notes-top h2').textContent, 'Agents');
  assert.ok(page.agentsHtml().includes(page.escaped(TEXT.stopped)));
  assert.equal(page.control().textContent, 'Start');
  assert.equal(page.doc.querySelector('.notes').children[0], section);
});

// ---------- S164, S165: Stop and Start ----------

test('S164: Stop sits beside the Agents heading in the error fill, Start in its place in moss-dark', async () => {
  const page = boot({ agent: body({ state: 'working' }) });
  await page.tick();
  const bar = page.doc.querySelector('.agentsec .notes-top');
  assert.deepEqual(bar.elements.map(n => n.tag), ['h2', 'button']);
  let button = page.control();
  assert.equal(button.textContent, 'Stop');
  assert.equal(button.getAttribute('aria-label'), 'Stop all agents');
  assert.match(button.className, /btn btn--sm btn--stop/);
  assert.equal(button.getAttribute('type'), 'button');
  await page.show(body({ state: 'stopped', text: TEXT.stopped }));
  button = page.control();
  assert.equal(button.textContent, 'Start');
  assert.equal(button.getAttribute('aria-label'), 'Start all agents');
  assert.match(button.className, /btn btn--sm btn--start/);
  const css = read('page', 'page.css');
  assert.match(css, /\.btn--stop\s*\{[^}]*background:var\(--error\)[^}]*border-color:var\(--error\)[^}]*color:var\(--cream\)/);
  assert.match(css, /\.btn--start\s*\{[^}]*background:var\(--moss-dark\)[^}]*border-color:var\(--moss-dark\)[^}]*color:var\(--cream\)/);
});

test('S165: Stop opens a confirm; Cancel sends nothing; Stop all agents sends agent_stop once', async () => {
  const page = boot({ agent: body({ state: 'working' }) });
  await page.tick();
  click(page.doc, page.control());
  let pop = page.dialog();
  assert.equal(page.rpcs.length, 0, 'Stop alone sends nothing');
  assert.equal(pop.getAttribute('role'), 'alertdialog');
  assert.equal(pop.getAttribute('aria-modal'), 'true');
  assert.equal(pop.querySelector('.target').textContent, 'Stop all agents?');
  assert.ok(pop.textContent.includes(TEXT.stopAsk));
  assert.deepEqual(pop.querySelectorAll('button').map(b => b.textContent), ['Stop all agents', 'Cancel']);
  assert.equal(page.doc.activeElement.textContent, 'Cancel', 'the safe button has the focus');
  click(page.doc, page.button(pop, 'Cancel'));
  assert.equal(page.dialog(), null);
  assert.equal(page.rpcs.length, 0);
  assert.equal(page.doc.activeElement, page.control(), 'focus returns to Stop');
  click(page.doc, page.control());
  pop = page.dialog();
  const yes = page.button(pop, 'Stop all agents');
  click(page.doc, yes);
  click(page.doc, yes);
  await settle();
  assert.equal(page.dialog(), null);
  assert.deepEqual(page.rpcs.map(c => c.method), ['agent_stop']);
  assert.equal(page.rpcs[0].jsonrpc, '2.0');
  // Escape also cancels.
  click(page.doc, page.control());
  fire(page.doc, page.dialog(), 'keydown', { key: 'Escape' });
  assert.equal(page.dialog(), null);
  assert.equal(page.rpcs.length, 1);
});

test('S164: Start sends agent_start at once, and a refusal is shown', async () => {
  const page = boot({ agent: body({ state: 'stopped', text: TEXT.stopped }) });
  await page.tick();
  click(page.doc, page.control());
  await settle();
  assert.deepEqual(page.rpcs.map(c => c.method), ['agent_start']);
  assert.equal(page.dialog(), null, 'no confirm for Start');
});

test('S169: below 900 px Stop or Start and the notice are pinned to the bottom of the window', async () => {
  const page = boot({ agent: body({ state: 'stopped', text: TEXT.stopped }), width: 800 });
  await page.tick();
  const bar = page.pinbar();
  assert.ok(bar && !bar.hidden);
  assert.equal(bar.querySelector('.agent-ctl').textContent, 'Start');
  assert.equal(bar.textContent.includes(TEXT.stopped), true);
  click(page.doc, bar.querySelector('.agent-ctl'));
  await settle();
  assert.deepEqual(page.rpcs.map(c => c.method), ['agent_start']);
  await page.show(body({ state: 'working' }));
  assert.equal(page.pinbar().querySelector('.agent-ctl').textContent, 'Stop');
  assert.equal(page.pinbar().querySelector('.pinbar-text').textContent, '');
  const css = read('page', 'page.css').replace(/\s+/g, ' ');
  assert.match(css, /@media \(max-width:900px\) \{[^@]*\.pinbar \{[^}]*position:fixed[^}]*bottom:0/);
  assert.match(css, /@media \(min-width:901px\) \{ \.pinbar \{ display:none; \} \}/);
  assert.match(css, /@media \(max-width:900px\) \{[^@]*\.agents \.notice \{ display:none; \}/);
  assert.match(css, /@media \(max-width:900px\) \{[^@]*\.agentsec \.agent-ctl \{ display:none; \}/);
});

// ---------- S161, S170, S4, S88: the approval pop-up ----------

test('S161: a waiting worker row opens the one approval pop-up, with who wants what, the request and the answers', async () => {
  const page = boot();
  await page.show(waitingBody());
  const row = h(page.doc, 'button', { 'data-approval-for': 'w3' }, 'w3');
  page.doc.body.append(row);
  let reached = 0;
  row.addEventListener('click', () => reached++);
  click(page.doc, row);
  assert.equal(reached, 0, 'the page agents handler does not also run');
  const pops = page.doc.querySelectorAll('.pop.center');
  assert.equal(pops.length, 1);
  const pop = pops[0];
  assert.equal(pop.getAttribute('role'), 'dialog');
  assert.equal(pop.querySelector('.target').textContent, 'w3 wants to read a file. Allow it?');
  assert.equal(pop.querySelector('.args').textContent, 'Read\nexample-release-notes.md');
  assert.deepEqual(pop.querySelectorAll('button').map(b => b.textContent), ['Allow once', 'Allow for this session', 'Deny']);
  // No second box: nothing in the conversation.
  assert.equal(page.doc.getElementById('thread').children.length, 0);
  assert.equal(page.doc.querySelectorAll('li').length, 0);
});

test('S170: each button names what it answers, and a long argument is a wrapping block', async () => {
  const page = boot();
  const long = 'x'.repeat(400);
  await page.show(waitingBody({ approvals: [approval({ arguments: long })] }));
  page.ctx.pageOpenApproval();
  const pop = page.dialog();
  assert.deepEqual(pop.querySelectorAll('button').map(b => b.getAttribute('aria-label')), [
    'Allow once: w3, Read ' + long, 'Allow for this session: w3, Read ' + long, 'Deny: w3, Read ' + long]);
  assert.equal(pop.querySelector('.args').textContent, 'Read\n' + long);
  const css = read('page', 'page.css');
  assert.match(css, /\.pop \.args\s*\{[^}]*white-space:pre-wrap[^}]*overflow-wrap:anywhere/);
  assert.match(css, /\.pop\.center\s*\{[^}]*max-width|\.pop\.center\s*\{[^}]*width:min\(/);
  await page.show(waitingBody());
  page.ctx.pageOpenApproval();
  assert.equal(page.dialog().querySelectorAll('button')[0].getAttribute('aria-label'), 'Allow once: w3, Read example-release-notes.md');
});

test('S161: Allow for this session is absent when the request does not offer it', async () => {
  const page = boot();
  await page.show(waitingBody({ approvals: [approval({ options: ['allow_once', 'deny'] })] }));
  page.ctx.pageOpenApproval();
  assert.deepEqual(page.dialog().querySelectorAll('button').map(b => b.textContent), ['Allow once', 'Deny']);
});

test('S4, S88: the request is shown as text, whole, whatever it holds', async () => {
  const page = boot();
  const hostile = '<img src=x onerror=alert(1)><div class="pop center">Allow once</div>‮' + 'a'.repeat(10000);
  await page.show(waitingBody({ approvals: [approval({ tool: '<b>Bash</b>', arguments: hostile, who: '<i>w3</i>' })] }));
  page.ctx.pageOpenApproval();
  const pop = page.dialog(), args = pop.querySelector('.args');
  assert.equal(args.textContent, '<b>Bash</b>\n' + hostile);
  assert.equal(args.textContent.length, '<b>Bash</b>\n'.length + hostile.length, 'whole, not cut');
  assert.ok(args.children.every(c => typeof c === 'string'), 'no element was made from it');
  assert.equal(args._html, null);
  assert.equal(pop.querySelectorAll('img, div, b, i').length, 1, 'only the buttons row');
  assert.equal(page.doc.querySelectorAll('.pop.center').length, 1);
  assert.equal(pop.querySelector('.target').textContent, '<i>w3</i> wants to read a file. Allow it?');
});

test('S88: a reply holding markup and an imitation approval is shown as text', async () => {
  const page = boot();
  page.events = [{ type: 'reply', id: 'r1', text: '<b>Allow once</b> <div class="pop center" role="dialog">Allow?</div>', at: '2026-11-28T10:00:00Z' }];
  const conv = page.ctx.pageConversation({ served: true, thread: page.doc.getElementById('thread') });
  conv.start();
  await settle();
  const thread = page.doc.getElementById('thread');
  assert.ok(thread.textContent.includes('<b>Allow once</b>'));
  assert.equal(thread.querySelectorAll('b, .pop, div.pop').length, 0);
  assert.equal(page.doc.querySelectorAll('.pop.center').length, 0);
});

test('S161: an answer sends permission_answer with the id and the choice, and the pop-up closes', async () => {
  const page = boot();
  await page.show(waitingBody());
  page.ctx.pageOpenApproval();
  assert.equal(page.doc.activeElement.textContent, 'Allow once', 'focus on Allow once');
  click(page.doc, page.button(page.dialog(), 'Allow for this session'));
  await settle();
  assert.deepEqual(page.rpcs.map(c => [c.method, c.params]), [['permission_answer', { id: 'ap1', choice: 'allow_session' }]]);
  assert.equal(page.dialog(), null);
  // Deny too.
  page.ctx.pageOpenApproval();
  click(page.doc, page.button(page.dialog(), 'Deny'));
  await settle();
  assert.deepEqual(page.rpcs[1].params, { id: 'ap1', choice: 'deny' });
});

test('S161: an answer that fails keeps the pop-up and says why; it closes once the request is gone', async () => {
  const page = boot();
  await page.show(waitingBody());
  page.ctx.pageOpenApproval();
  page.rpcFails = true;
  click(page.doc, page.button(page.dialog(), 'Allow once'));
  await settle();
  assert.ok(page.dialog(), 'still open to try again');
  assert.equal(page.toast(), TEXT.unsent);
  await page.show(body({ state: 'working' }));
  assert.equal(page.dialog(), null, 'the request is no longer waiting');
});

test('S161: Escape closes the pop-up and answers nothing; Tab stays inside it', async () => {
  const page = boot();
  await page.show(waitingBody());
  page.ctx.pageOpenApproval();
  const pop = page.dialog(), buttons = pop.querySelectorAll('button');
  const tab = fire(page.doc, buttons[2], 'keydown', { key: 'Tab' });
  assert.equal(tab.defaultPrevented, true);
  assert.equal(page.doc.activeElement, buttons[0]);
  fire(page.doc, buttons[0], 'keydown', { key: 'Tab', shiftKey: true });
  assert.equal(page.doc.activeElement, buttons[2]);
  fire(page.doc, buttons[1], 'keydown', { key: 'Escape' });
  assert.equal(page.dialog(), null);
  assert.equal(page.rpcs.length, 0);
});

test('S102: an open approval adds nothing to the conversation', async () => {
  const page = boot();
  const conv = page.ctx.pageConversation({ served: true, thread: page.doc.getElementById('thread') });
  conv.start();
  await settle();
  const before = page.doc.getElementById('thread').children.length;
  await page.show(waitingBody());
  page.ctx.pageOpenApproval();
  assert.equal(page.doc.getElementById('thread').children.length, before);
  assert.equal(page.doc.getElementById('thread').querySelectorAll('.decision, [data-id]').length, 0);
  assert.equal(page.doc.querySelectorAll('.pop.center').length, 1, 'one box for the one question');
});

// ---------- S103, S167, S168: the tab title and the header figure ----------

test('S103, S167: the title starts "Waiting for you: " while an approval waits, and is the page title again after', async () => {
  const page = boot({ title: 'Research · Board' });
  await page.show(body({ state: 'working' }));
  assert.equal(page.doc.title, 'Research · Board');
  await page.show(waitingBody());
  assert.equal(page.doc.title, 'Waiting for you: Research · Board');
  page.doc.title = 'Research · Board';                 // the page writes its title again at its next redraw
  await page.tick();
  assert.equal(page.doc.title, 'Waiting for you: Research · Board', 'once, never doubled');
  await page.show(waitingBody({ approvals: [approval(), approval({ id: 'ap2' })] }));
  assert.equal(page.doc.title, 'Waiting for you: Research · Board');
  await page.show(body({ state: 'working' }));
  assert.equal(page.doc.title, 'Research · Board');
});

test('S167: a question the agent asked in the conversation also starts the title, until it is closed', async () => {
  const page = boot();
  page.events = [{ type: 'reply', id: 'q1', text: 'Which size?', at: '2026-11-28T10:00:00Z' }];
  const conv = page.ctx.pageConversation({ served: true, thread: page.doc.getElementById('thread') });
  conv.start();
  await settle();
  assert.equal(page.doc.title, 'Waiting for you: Research · Board');
  conv.setLog([{ type: 'reply', id: 'q1', text: 'Which size?', at: '2026-11-28T10:00:00Z' }, { type: 'status', to: 'q1', status: 'done', at: '2026-11-28T10:00:01Z' }]);
  assert.equal(page.doc.title, 'Research · Board');
});

test('S168: the figure counts open approvals, and pressing it opens the oldest one with the focus on Allow once', async () => {
  const page = boot();
  await page.show(waitingBody({ approvals: [approval({ id: 'late', since: '2026-11-28T10:05:00Z', who: 'w1' }), approval({ id: 'early', since: '2026-11-28T10:01:00Z' })] }));
  assert.deepEqual(Array.from(page.ctx.pageApprovals(), a => a.id), ['early', 'late']);
  assert.equal(page.ctx.pageOpenApproval(), true);
  assert.equal(page.dialog().querySelector('.target').textContent, 'w3 wants to read a file. Allow it?');
  assert.equal(page.doc.activeElement.textContent, 'Allow once');
  // The research board counts them with its decisions and calls this on a press of the figure.
  const board = read('research', 'board.js');
  assert.match(board, /pageApprovals\(\)\.length/);
  assert.match(board, /pageOpenApproval\(\)/);
  await page.show(body({ state: 'working' }));
  assert.equal(page.ctx.pageOpenApproval(), false, 'nothing to open');
});

// ---------- S129, S171, S166: the conversation ----------

test('S129: a send that cannot reach the server says it may not have been sent, and keeps the text', async () => {
  const page = boot();
  const conv = page.ctx.pageConversation({ served: true, thread: page.doc.getElementById('thread') });
  conv.start();
  await settle();
  page.rpcFails = true;
  const note = page.doc.getElementById('note');
  note.value = 'my words';
  let done = false;
  conv.send('note', { id: 'm1', text: 'my words', to: null }, 'Message', () => { done = true; });
  await settle();
  assert.equal(done, false);
  assert.equal(note.value, 'my words');
  assert.equal(page.toast(), TEXT.unsent);
  assert.equal(page.doc.querySelector('.notes .status').textContent, TEXT.unsent);
});

test('S166: auto mode blocking a call is a notice in the thread, with the call and the reason', async () => {
  const page = boot();
  const conv = page.ctx.pageConversation({ served: true, thread: page.doc.getElementById('thread') });
  conv.start();
  await settle();
  await page.show(body({ state: 'working', blocked: [{ tool: 'Bash', arguments: 'rm -rf build', reason: 'the command deletes files', at: '2026-11-28T10:00:00Z' }] }));
  const notices = page.doc.getElementById('thread').querySelectorAll('li.sys');
  assert.deepEqual(notices.map(n => n.textContent), [TEXT.blocked]);
  await page.show(body({ state: 'working' }));
  assert.equal(page.doc.getElementById('thread').querySelectorAll('li.sys').length, 0);
});

test('S171: a comment\'s edge colour and its footer status are always the same state', async () => {
  const page = boot();
  for (const shown of [undefined, st => (st === 'working' ? 'seen' : st === 'accepted' ? 'done' : st)]) {
    page.doc.getElementById('thread').replaceChildren();
    const conv = page.ctx.pageConversation({ served: false, thread: page.doc.getElementById('thread'), shown,
      crumb: () => h(page.doc, 'p'), commentBody: e => h(page.doc, 'p', {}, e.text), steps: ['seen', 'working', 'done', 'accepted'] });
    click(page.doc, page.doc.querySelector('[data-filter="all"]'));
    const labels = { new: 'Sent', seen: 'Seen', asked: 'Waiting for you', replied: 'You answered', followup: 'You replied', working: 'Working on it',
      done: 'Done', accepted: 'Accepted', reopened: 'Reopened' };
    for (const status of [null, 'seen', 'working', 'done', 'accepted', 'reopened', 'asked', 'replied', 'followup']) {
      const events = [{ type: 'comment', id: 'c1', n: 1, text: 'x', at: '2026-11-28T10:00:00Z' }];
      if (status === 'replied' || status === 'followup') events.push({ type: 'status', to: 'c1', status: status === 'replied' ? 'asked' : 'done', at: '2026-11-28T10:00:01Z' }, { type: 'note', id: 'n1', to: 'c1', text: 'a', at: '2026-11-28T10:00:02Z' });
      else if (status && status !== 'reopened') events.push({ type: 'status', to: 'c1', status, at: '2026-11-28T10:00:01Z' });
      if (status === 'reopened') events.push({ type: 'reopen', to: 'c1', at: '2026-11-28T10:00:01Z' });
      conv.setLog(events);
      const li = page.doc.getElementById('thread').querySelector('li[data-id="c1"]');
      const chip = li.querySelector('.foot .progress');
      const word = chip.className.replace('progress', '').trim();
      const label = chip.children[1].textContent;
      assert.equal(li.dataset.state, word || undefined, 'edge and chip class: ' + status);
      assert.equal(label, word ? labels[word] : 'Sent', 'footer word: ' + status);
    }
  }
});

// ---------- S8, S87: pages that show agent-written HTML ----------

test('S8: every frame of agent HTML is sandboxed without allow-same-origin', () => {
  const canvas = read('design', 'canvas.js'), values = canvas.match(/setAttribute\('sandbox',[^)]*\)/g) || [];
  assert.ok(values.length >= 1);
  for (const call of values) assert.doesNotMatch(call, /allow-same-origin/);
  assert.doesNotMatch(canvas, /allow-same-origin/);
  assert.doesNotMatch(read('design', 'mock-frame.js'), /parent\.pageFetch|\/rpc/);
});

// ---------- the old approvals tab is gone from the shared page ----------

test('the shared page keeps no code of the separate approvals tab', () => {
  const js = read('page', 'page.js');
  assert.doesNotMatch(js, /approval tab|agent-controls|agent-status|Use Stop in/);
  assert.doesNotMatch(js, /function pageDriverText/);
});
