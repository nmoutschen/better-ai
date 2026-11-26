// Run the shared browser code with a controlled clock and HTTP replies.
const assert = require('node:assert/strict');
const test = require('node:test');
const { loadPage, stand } = require('./harness');
const settle = () => new Promise(resolve => setImmediate(resolve));

test('driver status polls every two seconds and detects a stale or unresponsive driver', async () => {
  const timer = [], aborts = [];
  const elements = {
    'page-config': { textContent: '{"driven":true}' },
    'agent-status': { textContent: '', hidden: true },
    'agent-controls': { hidden: true },
  };
  let answer = { state: 'idle', age: 0 };
  const poll = () => {
    const [next, delay] = timer.shift();
    assert.equal(delay, 2000);
    next();
    return settle();
  };
  loadPage({
    document: { getElementById: id => elements[id] },
    location: { hash: '' }, sessionStorage: stand(), URLSearchParams, AbortController,
    setTimeout: (...args) => timer.push(args),
    fetch: (path, init) => {
      assert.equal(path, '/agent');
      if (!answer) {
        init.signal.addEventListener('abort', () => aborts.push(path));
        return new Promise(() => {});
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve(answer) });
    },
  });
  await settle();
  const status = elements['agent-status'];
  assert.equal(status.textContent, 'Idle');
  assert.equal(status.hidden, false);
  for (const [state, text] of [
    ['working', /^Working$/], ['stopping', /^Stopping$/], ['stopped', /^Stopped$/], ['stalled', /^Stalled/],
  ]) {
    answer = { state, age: 0 };
    await poll();
    assert.match(status.textContent, text);
  }
  answer = { state: 'idle', age: 3.01 };
  await poll();
  assert.match(status.textContent, /driver stopped.*serve this page again/);
  assert.equal(elements['agent-controls'].hidden, true);
  answer = { state: 'idle', age: 0 };
  await poll();
  assert.equal(status.textContent, 'Idle');
  answer = null;
  await poll();
  await poll();
  assert.deepEqual(aborts, ['/agent']);
  assert.match(status.textContent, /driver stopped.*serve this page again/);
});

test('failed kinds render as text, with the details needed to recover', () => {
  const { pageDriverText } = loadPage();
  for (const kind of ['login', 'not-installed', 'version', 'limit', 'crashed', 'unsafe-mode', 'no-approvals']) {
    const text = pageDriverText({ state: 'failed', kind, message: 'details', action: 'try again' });
    assert.equal(text, kind + ' · details · try again');
  }
  const text = pageDriverText({
    state: 'failed', kind: 'not-handling', items: ['m-1'],
    final_message: 'last answer', denied: [{ tool: 'Command', reason: 'denied' }], log: '/tmp/.driver.log',
  });
  for (const details of [/m-1/, /last answer/, /Command \(denied\)/, /\/tmp\/\.driver\.log/, /Start retries/]) {
    assert.match(text, details);
  }
  assert.match(pageDriverText({ state: 'failed', kind: 'driver' }), /driver stopped.*serve this page again/);
});
