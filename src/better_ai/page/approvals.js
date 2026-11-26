// This origin serves only shipped controls. A tool's name and arguments are always text nodes.
(function () {
  'use strict';
  const el = id => document.getElementById(id);
  const fragment = new URLSearchParams(location.hash.slice(1));
  const token = fragment.get('p');
  history.replaceState(null, '', location.pathname);
  let secret = sessionStorage.getItem('approvalSecret') || '';
  sessionStorage.removeItem('approvalPage');
  let active = true, serial = 0, rendered = '';
  const labels = { allow_once: 'Allow once', allow_session: 'Allow for this session', deny: 'Deny' };
  function fail(message) {
    active = false;
    for (const id of ['page', 'start', 'stop', 'enroll']) el(id).hidden = true;
    el('requests').replaceChildren();
    el('status').textContent = message;
  }
  async function fetchJSON(path, init) {
    const response = await fetch(path, Object.assign({ cache: 'no-store', credentials: 'omit' }, init));
    if (response.status === 403) {
      sessionStorage.removeItem('approvalSecret');
      fail('Opened elsewhere. Open the latest address the agent gave you.');
    }
    if (!response.ok) throw new Error('The page server refused this request.');
    return response.json();
  }
  function post(path, body) {
    return fetchJSON(path, { method: 'POST', headers: {
      'Content-Type': 'application/json', 'X-Page-Token': secret
    }, body: JSON.stringify(body) });
  }
  async function rpc(method, params = {}) {
    const reply = await post('/rpc', { jsonrpc: '2.0', id: ++serial, method, params });
    if (reply.error) throw new Error(reply.error.message);
    return reply.result;
  }
  function decode(text) {
    return Uint8Array.from(atob(text.replace(/-/g, '+').replace(/_/g, '/')), c => c.charCodeAt(0));
  }
  function encode(buffer) {
    return btoa(String.fromCharCode(...new Uint8Array(buffer))).replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_');
  }
  async function credential(opts, register) {
    opts.challenge = decode(opts.challenge);
    if (register) opts.user.id = decode(opts.user.id);
    else opts.allowCredentials.forEach(key => { key.id = decode(key.id); });
    const key = await navigator.credentials[register ? 'create' : 'get']({ publicKey: opts });
    const response = {};
    for (const field of register ? ['clientDataJSON', 'attestationObject'] : ['clientDataJSON', 'authenticatorData', 'signature']) {
      response[field] = encode(key.response[field]);
    }
    return { rawId: encode(key.rawId), type: key.type, response };
  }
  function action(button, run) {
    button.addEventListener('click', async () => {
      button.disabled = true;
      el('error').textContent = '';
      try { await run(); await refresh(); }
      catch (error) { if (active) el('error').textContent = error.message; }
      finally { button.disabled = false; }
    });
  }
  function requests(items) {
    const next = JSON.stringify(items);
    if (next === rendered) return;
    rendered = next;
    el('requests').replaceChildren(...items.map(item => {
      const article = document.createElement('article'), heading = document.createElement('h2'), args = document.createElement('pre');
      heading.textContent = item.tool;
      args.textContent = item.arguments;
      article.append(heading, args);
      for (const choice of item.options) {
        const button = document.createElement('button');
        button.type = 'button';
        button.textContent = labels[choice];
        action(button, async () => {
          let proof = null;
          if (choice !== 'deny') {
            const opts = await rpc('permission_challenge', { id: item.id, choice });
            if (opts) proof = await credential(opts, false);
          }
          await rpc('permission_answer', { id: item.id, choice, proof });
        });
        article.append(button);
      }
      return article;
    }));
  }
  async function refresh() {
    if (!active) return;
    const data = await fetchJSON('/agent', { headers: { 'X-Page-Token': secret } });
    if (!active) return;
    el('status').textContent = data.enrollment_needed ? 'Set up a passkey or security key before the agent starts.' : 'Agent ' + data.state;
    el('enroll').hidden = !data.enrollment_needed;
    el('start').hidden = !data.can_start;
    el('stop').hidden = !data.can_stop;
    el('notice').textContent = data.notice || '';
    el('outcome').textContent = data.last_outcome || data.action || '';
    el('page').hidden = data.state === 'starting';
    requests(data.approvals || []);
  }
  async function poll() {
    try { await refresh(); }
    catch (error) { if (active) el('status').textContent = 'The page agent driver stopped responding.'; }
    if (active) setTimeout(poll, 2000);
  }
  async function boot() {
    if (token) {
      const pair = await post('/pair', { token });
      secret = pair.secret;
      sessionStorage.setItem('approvalSecret', secret);
    }
    if (!secret) { fail('Open the latest address the agent gave you.'); return; }
    const pageLink = el('page');
    pageLink.href = '#page';
    pageLink.addEventListener('click', async event => {
      event.preventDefault();
      if (!active || pageLink.hidden) return;
      el('error').textContent = '';
      // Open during the click so popup blockers see the gesture, then detach before navigating.
      const tab = window.open('about:blank', '_blank');
      if (!tab) { el('error').textContent = 'Allow popups from this page to open the conversation.'; return; }
      try {
        tab.opener = null;
        // A new tab can inherit session storage before its opener is cleared.
        tab.sessionStorage.removeItem('approvalSecret');
      } catch {
        tab.close();
        el('error').textContent = 'Could not open the conversation in a separate tab.';
        return;
      }
      try {
        tab.location.replace(await rpc('open_conversation'));
      } catch (error) {
        tab.close();
        if (active) el('error').textContent = error.message;
      }
    });
    action(el('enroll'), async () => {
      const opts = await rpc('enroll_begin');
      await rpc('enroll_finish', { proof: await credential(opts, true) });
    });
    action(el('stop'), () => rpc('agent_stop'));
    action(el('start'), () => rpc('agent_start'));
    await poll();
  }
  boot().catch(error => { if (active) fail(error.message); });
}());
