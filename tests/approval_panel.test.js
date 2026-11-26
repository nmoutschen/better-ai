const assert = require('node:assert/strict');
const test = require('node:test');
const vm = require('node:vm');
const { read } = require('./harness');

test('each click opens a detached tab before obtaining a fresh conversation link', async () => {
  const elements = new Map(), storage = new Map([['approvalSecret', 'approved-tab']]);
  const trace = [];
  const document = {
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, {
        addEventListener(_, callback) { this.click = callback; },
        replaceChildren() {},
      });
      return elements.get(id);
    },
  };
  let count = 0, failRemoval = false;
  const context = {
    document, location: { hash: '', pathname: '/approvals.html' }, history: { replaceState() {} },
    URLSearchParams, setTimeout() {},
    sessionStorage: {
      getItem: key => storage.get(key),
      removeItem: key => storage.delete(key),
      setItem: (key, value) => storage.set(key, value),
    },
    window: {
      open() {
        trace.push('open');
        const childStorage = new Map(storage);
        return {
          sessionStorage: {
            removeItem(key) {
              assert.equal(key, 'approvalSecret');
              assert.equal(childStorage.get(key), 'approved-tab');
              if (failRemoval) throw new Error('Storage unavailable');
              childStorage.delete(key);
              trace.push('clear');
            },
          },
          set opener(value) { assert.equal(value, null); trace.push('detach'); },
          location: { replace(url) { assert.equal(childStorage.has('approvalSecret'), false); trace.push(url); } },
          close() { trace.push('close'); },
        };
      },
    },
    async fetch(path, init) {
      assert.equal(init.headers['X-Page-Token'], 'approved-tab');
      if (path === '/agent') return { ok: true, json: () => ({ state: 'idle' }) };
      assert.equal(path, '/rpc');
      assert.equal(JSON.parse(init.body).method, 'open_conversation');
      trace.push('request');
      return { ok: true, json: () => ({ result: 'http://127.0.0.1:3000/#p=link' + ++count }) };
    },
  };
  vm.runInNewContext(read('page', 'approvals.js'), context);
  await new Promise(resolve => setImmediate(resolve));
  const link = document.getElementById('page');
  assert.equal(link.hidden, false);
  await link.click({ preventDefault() {} });
  await link.click({ preventDefault() {} });
  assert.deepEqual(trace, [
    'open', 'detach', 'clear', 'request', 'http://127.0.0.1:3000/#p=link1',
    'open', 'detach', 'clear', 'request', 'http://127.0.0.1:3000/#p=link2',
  ]);
  failRemoval = true;
  trace.length = 0;
  await link.click({ preventDefault() {} });
  assert.deepEqual(trace, ['open', 'detach', 'close']);
  assert.match(document.getElementById('error').textContent, /could not open/i);
  assert.equal(storage.get('approvalSecret'), 'approved-tab');
});
