// Every state the page gives a pin, from its thread (pageThreads), with its words. page.css colours a pin for each.
var PAGE_PIN_STATES = { new: 'Agent’s turn, not seen', seen: 'Agent’s turn, seen', working: 'Agent’s turn, working',
  asked: 'Your turn', done: 'Done', accepted: 'Closed' };

// The page token. `serve` gives it in the fragment of the address it opens (#t=...), which a browser never sends. The page
// keeps it for the tab, so a reload still has it, and takes it out of the address bar. Every request to /rpc, /data,
// /events and /wait goes through pageFetch, which sends it; the server answers a page without it as out of date. The
// page then drops the token it saved: a reload cannot fix it, only the address the agent gave.
var PAGE_STALE = 'page out of date: open the address the agent gave', pageIsStale = false;
var pageToken = (function () {
  var found = typeof location === 'undefined' ? null : /[#&]t=([\w-]+)/.exec(location.hash || '');
  try {
    if (found) { sessionStorage.setItem('pageToken', found[1]); history.replaceState(null, '', location.pathname + location.search); }
    return found ? found[1] : sessionStorage.getItem('pageToken') || '';
  } catch (e) { return found ? found[1] : ''; }
})();
function pageStale() {
  var strip = document.querySelector('.offline');
  pageIsStale = true; pageToken = '';
  try { sessionStorage.removeItem('pageToken'); } catch (e) {}
  if (strip) { strip.textContent = PAGE_STALE; strip.hidden = false; }
  var stale = new Error(PAGE_STALE);
  stale.stale = true;
  return stale;
}
function pageFetch(url, init) {
  if (pageIsStale) return Promise.reject(pageStale());  // the server refused this page's token: asking again cannot help
  init = Object.assign({}, init);
  init.headers = Object.assign({}, init.headers, { 'X-Page-Token': pageToken });
  return fetch(url, init).then(function (r) {
    if (r.status !== 401) return r;
    throw pageStale();
  });
}

function pagePollAgain(poll, delay) { if (!pageIsStale) setTimeout(poll, delay); }

function pageWatchRevision(onChange) {
  var rev = null;
  (function poll() {
    pageFetch('/rev').then(function (r) { return r.text(); }).then(function (t) {
      if (pageIsStale) return;
      if (rev === null) rev = t;
      else if (t !== rev) onChange();
    }).catch(function () {}).then(function () { pagePollAgain(poll, 2000); });
  })();
}

// The element-comment layer. A page supplies its target metadata, pin coordinates and navigation;
// this owns the editor, the numbered pins and their actions.
function pageElementComments(o) {
  var pop = o.pop, draft = null, opener = null, state = {};
  var input = pop.querySelector('textarea'), ok = pop.querySelector('.ok'), del = pop.querySelector('.remove');

  function open(data, item, from, position) {
    draft = data;
    pop.querySelector('.target').replaceChildren(o.crumb(data));
    input.value = item ? item.text || '' : '';
    if (o.prepare) o.prepare(data);
    del.hidden = !item;
    ok.textContent = item ? 'Update' : 'Send';
    pop.hidden = false;
    opener = from;
    var point = position(pop);
    pop.style.left = point.x + 'px';
    pop.style.top = point.y + 'px';
    input.focus();
  }
  function close() {
    pop.hidden = true;
    draft = null;
    if (opener && document.contains(opener)) opener.focus();
    opener = null;
  }
  function remove(it) { o.send('delete', { to: it.id }, 'Deletion of comment ' + it.n); }
  function submit() {
    var text = input.value.trim();
    if (!draft || (!text && !(o.allowEmpty && o.allowEmpty(draft)))) { input.focus(); return; }
    var it = draft.item, n = it ? it.n : o.nextNumber();
    var id = it ? it.id : 'c' + n + '-' + Date.now().toString(36);
    var params = Object.assign({ id: id, n: n }, o.params(draft, text));
    // The box stays open, with its text, until the server has saved the comment: a refusal leaves it to fix.
    // An update reuses the comment's id, so the agent replaces the earlier version.
    ok.disabled = true;
    o.send('comment', params, 'Comment ' + n + (it ? ' (updated)' : ''),
      function () { ok.disabled = false; close(); }, function () { ok.disabled = false; input.focus(); });
  }
  pop.querySelector('.cancel').addEventListener('click', close);
  del.addEventListener('click', function () { var it = draft && draft.item; close(); if (it) remove(it); });
  input.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); } });
  ok.addEventListener('click', submit);

  function findPin(root, id) { return root && root.querySelector('.' + o.pinClass + '[data-id="' + CSS.escape(id) + '"]'); }
  function updatePin(pin, it) {
    pin.textContent = it.n;
    pin.dataset.state = state[it.id] || 'new';
  }
  function placePin(root, it) {
    var pin = findPin(root, it.id);
    if (!pin) {
      pin = root.ownerDocument.createElement('span');
      pin.className = o.pinClass;
      pin.dataset.id = it.id;
      root.appendChild(pin);
    }
    updatePin(pin, it);
    return pin;
  }
  function removePin(root, id) { var pin = findPin(root, id); if (pin) pin.remove(); }
  function flashPin(pin, cls) { pin.classList.remove(cls); void pin.offsetWidth; pin.classList.add(cls); }
  function click(e, start, edit) {
    var pin = e.target.closest && e.target.closest('.' + o.pinClass);
    if (pin) {
      e.preventDefault();
      if (o.stopPinPropagation) e.stopPropagation();
      var it = o.byId(pin.dataset.id), st = state[pin.dataset.id];
      if (it && (st === 'done' || st === 'accepted')) o.reopen(it.id);
      else if (it) edit(it, pin);
      return true;
    }
    if (!o.commenting()) return false;
    e.preventDefault();
    e.stopPropagation();
    if (!pop.hidden) close();
    else start();
    return true;
  }

  return {
    open: open, close: close, remove: remove, click: click,
    draft: function () { return draft; },
    findPin: findPin, placePin: placePin, updatePin: updatePin, removePin: removePin, flashPin: flashPin,
    state: function (next) { if (next) state = next; return state; }
  };
}

// Anchor at the nearest ID that is unique across the document. Otherwise use a positional path
// from body, or a path relative to the supplied root for a page with multiple commentable regions.
function pageElementSelector(node, root) {
  var doc = node.ownerDocument, counts = pageIdCounts(doc), parts = [];
  while (node && node.nodeType === 1 && node !== root && node !== doc.body && node !== doc.documentElement) {
    if (node.id && counts[node.id] === 1) return ['#' + CSS.escape(node.id)].concat(parts).join(' > ');
    var tag = node.tagName.toLowerCase(), n = 1, sib = node;
    while ((sib = sib.previousElementSibling)) if (sib.tagName === node.tagName) n++;
    parts.unshift(tag + ':nth-of-type(' + n + ')');
    node = node.parentElement;
  }
  return (root ? parts : ['body'].concat(parts)).join(' > ');
}
function pageIdCounts(doc) {
  var counts = Object.create(null);
  doc.querySelectorAll('[id]').forEach(function (el) { counts[el.id] = (counts[el.id] || 0) + 1; });
  return counts;
}
function pageElementDescription(node, root, text, limit) {
  return { tag: node.tagName.toLowerCase(), text: (text || '').replace(/\s+/g, ' ').trim().slice(0, limit),
           selector: pageElementSelector(node, root) };
}

function pageCommentPosition(x, y, pop) {
  return { x: Math.max(12, Math.min(x + 12, innerWidth - pop.offsetWidth - 12)),
           y: Math.max(12, Math.min(y + 12, innerHeight - pop.offsetHeight - 12)) };
}

// The conversation between a served page and the agent: sending, the thread with its items, states and replies, the
// message box, and the live updates. This file is bundled once, from src/better_ai/page/, into every
// skill's better.pyz, with page.css and the server. The page's own script calls pageConversation with what only that page has, such as its pins.
//
// Every action is sent as it happens, as one JSON-RPC call, and the server keeps a log of them with the agent's
// replies. The page sends only the fields of its own kind of event (the server sets `type`, `by` and `at`), and the
// server checks them against the page's schemas: what it refuses stays in the box, with its reason, and is undone on
// the page. The page streams the log, or feeds it with setLog, and rebuilds the conversation from it, so a reload or a
// new render loses nothing. State changes are also applied at once, and applying the same event twice changes nothing.
//
// o.served       the page is served over http; otherwise actions stay on the page (o.unsent says what to do with them)
// o.agent        what the agent is called in the thread (default: the page's role name from its config, capitalised)
// o.apply(e, fresh)  apply one event to the page's own model, such as its pins; fresh when the user just sent it
// o.reset()      empty that model and its pins; the page then replays the log through apply, to undo an event the server refused
// o.byId(id)     the page's own model of a comment, which offers Show, Edit and Delete; nothing when it offers none
// o.crumb(e)     where a comment was made; o.commentBody(e) what it says (its text)
// o.reveal(e), o.edit(it, button), o.remove(it), o.showLabel(n)   the comment's Show, Edit and Delete
// o.kinds        renderers for the page's own kinds of event: function (c, state, actions) returning the item, or [item, foot].
//                C is the thread's first event as an entry: { kind, e (the event), replies (the rest of the thread),
//                thread (from pageThreads) }; STATE is each user item's pin state. The item's content is the thread's
//                first message; the buttons of FOOT, if any, are the row's buttons.
// o.itemKinds    the user's kinds that start a thread with the agent (default comment and note)
// o.readOnly     a copy of the page to read: no actions
// o.stream       read the log from the server's /events (default true); otherwise the page calls setLog
// o.afterSend()  called once the server saved an action
// o.noteParams() what a message carries besides its words, such as the current slide; the page's events schema must allow it
// o.sendMode()   a function to run instead of sending a message when the Send button is pressed, or null
// o.busy()       the page has something open the user would lose on a reload
// o.beforeReload()  keep the page's place before a new render loads
// o.rendered(state)  called after each redraw with the state of every user item, by id, for its pin: new, seen,
//                working, asked (your turn), done, accepted (you closed it); PAGE_PIN_STATES words them
// o.stats        where the top bar's "N your turn" figure goes: an element, or a function that gives it (default the
//                header's #status). A page that rewrites its own figures calls figure() after, to put it back.
function pageConversation(o) {
  var rpcId = 0, log = [], state = {}, fed = null, itemKinds = o.itemKinds || ['comment', 'note'], kinds = o.kinds || {};
  var agent = o.agent || pageRole().replace(/^./, function (c) { return c.toUpperCase(); });
  function el(tag, cls, text) { var x = document.createElement(tag); if (cls) x.className = cls; if (text != null) x.textContent = text; return x; }
  function time(at) { return pageTime(at); }
  var status = document.querySelector('.notes .status');
  function say(text, error) { if (!status) return; status.textContent = text; status.classList.toggle('error', !!error); }
  // Every action shows a toast at the bottom of the window: sending, then sent or failed.
  var toast = document.querySelector('.toast'), toastTimer = null;
  function flash(text, kind) {
    clearTimeout(toastTimer);
    toast.textContent = text; toast.className = 'toast ' + (kind || ''); toast.hidden = false;
    if (kind !== 'error' && kind !== 'busy') toastTimer = setTimeout(function () { toast.hidden = true; }, 2500);
  }
  // DONE runs once the server saved the action; FAIL when it did not, such as to enable a button again. The user's text
  // stays where it was typed: DONE is what clears it. A refusal by the server, such as an event its schema rejects, shows
  // the server's reason; only an unreachable server is shown as closed.
  function send(method, params, what, done, fail) {
    if (o.readOnly) return;
    var event = Object.assign({ type: method, at: new Date().toISOString().slice(0, 19) + 'Z', by: 'user' }, params);
    if (o.apply) o.apply(event, true);
    if (!o.served) { log.push(event); renderThread(); flash(what + ' saved on this page. ' + (o.unsent || ''), 'ok'); if (done) done(); return; }
    flash('Sending ' + what.toLowerCase() + '…', 'busy');
    pageFetch('/rpc', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jsonrpc: '2.0', id: ++rpcId, method: method, params: params }) })
      .then(function (r) { return r.json(); })
      .then(function (r) {
        if (r.error) { if (r.error.code === -32001) pageStale(); var refused = new Error(r.error.message); refused.refused = true; throw refused; }
        return r;
      })
      .then(function () {
        flash('✓ ' + what + ' sent to the ' + agent.toLowerCase(), 'ok'); say(''); if (done) done(); if (o.afterSend) o.afterSend();
      }, function (error) {
        undo();
        var refused = error && error.refused;
        flash('Not sent: ' + what.toLowerCase() + '. ' + (refused ? error.message : 'The page is closed.'), 'error');
        say(refused ? 'Not sent: ' + error.message : 'Not sent: the page is closed. Ask the ' + pageRole() + ' to restart it.', true);
        if (fail) fail();
      });
  }
  // An event that was applied at once but not saved goes: the page's model is rebuilt from the log, which it never reached.
  function undo() {
    if (!o.reset) return;
    o.reset();
    log.forEach(function (e) { if (o.apply) o.apply(e, false); });
    renderThread();
  }

  // ---------- The panel: one row per thread, each in the one state every thread has (pageThreads) ----------
  // A row: the state (Your turn and how long it has waited; the agent's turn with its progress; or Done), who started
  // the thread and its first sentence, the triangle, how many messages and when the last came, and the buttons of its
  // state. The whole head opens and folds the thread. Open lists what you have not closed: done first, then the agent's
  // turn, then your turn last, next to the message box; All lists every thread in time order.
  var thread = o.thread || document.querySelector('.thread');
  var filter = 'open', scrolledOnce = false, threads = [];
  // What the user has open or typed, by thread key, kept across every redraw: the threads they opened, the one box
  // (an answer, a reply or why they reopen it), drafts and errors by box, the closes in their undo window, the closes
  // sent but not yet in the log, and the control to focus once the next redraw is done.
  var expanded = {}, box = null, drafts = {}, errors = {}, closing = {}, closed = {}, focusAfter = null;
  var CLOSE_MS = 6000, BARS = ['seen', 'working', 'done'], STEP_WORDS = { new: 'Not seen', seen: 'Seen', working: 'Working', done: 'Done' };
  var PLAIN = ['comment', 'note', 'reply'];
  document.querySelectorAll('[data-filter]').forEach(function (b) {
    b.addEventListener('click', function () {
      filter = b.dataset.filter;
      document.querySelectorAll('[data-filter]').forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); });
      renderThread();
    });
  });
  function keyOf(t) { return t.id != null ? String(t.id) : 'at-' + threads.indexOf(t); }
  function whoOf(e) { return e.by === 'user' ? 'You' : agent; }
  function day(at) {
    var d = new Date(at);
    if (isNaN(d)) return '';
    return d.getDate() + ' ' + ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][d.getMonth()] + ', ' + time(at);
  }
  // How long a state has held, in the words of the row.
  function age(at) {
    var s = Math.max(0, (Date.now() - Date.parse(at)) / 1000);
    if (isNaN(s)) return '';
    if (s < 90) return 'just now';
    if (s < 3600) return Math.round(s / 60) + ' min';
    if (s < 36 * 3600) return Math.round(s / 3600) + ' h';
    return Math.round(s / 86400) + ' days';
  }
  function aged(words, at) { var a = age(at); return a ? words + ', ' + a : words; }
  // The first sentence of the message that started the thread, without its marks; nobody names threads.
  function rootText(e) { return e.type === 'decision' ? (e.x && e.x.asked) || '' : e.text || e.label || e.option || ''; }
  function gist(text) {
    var t = pageMarkdownText(text || ''), s = t.split(/(?<=[.?!])\s/)[0];
    return s.length > 120 ? s.slice(0, 117).replace(/\s+\S*$/, '') + '…' : s;
  }
  // A control the redraw can find again: KEY names it, such as "toggle:<thread>".
  function keyed(x, key) { x.dataset.fk = key; return x; }
  function find(key) {
    var all = thread.querySelectorAll('[data-fk]');
    for (var i = 0; i < all.length; i++) if (all[i].dataset.fk === key) return all[i];
    return null;
  }
  function button(text, cls, on, label) {
    var b = el('button', 'btn btn--sm' + (cls ? ' ' + cls : ''), text); b.type = 'button';
    if (label) b.setAttribute('aria-label', label);
    b.addEventListener('click', on);
    return b;
  }
  function stateChip(t) { return t.state === 'you' ? el('span', 'chip wait', 'Your turn') : el('span', 'chip', 'Agent’s turn'); }
  // The agent's progress: a bar per step it reached, seen, working and done (green); none before it has seen your message.
  function progress(t) {
    var step = t.state === 'done' ? 'done' : t.step, k = BARS.indexOf(step);
    var chip = el('span', 'progress' + (step === 'new' ? '' : ' ' + step)), bars = el('span', 'bars');
    bars.setAttribute('aria-hidden', 'true');
    for (var j = 0; j < BARS.length; j++) bars.append(el('i', j <= k ? 'on' : ''));
    chip.append(bars, el('span', '', aged(STEP_WORDS[step], t.since)));
    return chip;
  }
  function body(text) { return pageMarkdown(text); }
  // One message of an open thread, flat across the row: yours on white, the agent's on linen.
  function message(e, t) {
    var m = el('div', 'tmsg ' + (e.by === 'user' ? 'mine' : 'agent')), h = el('div', 'head');
    if (e.type === 'comment' && e.n) h.append(el('span', 'n', e.n));
    h.append(el('span', 'who', whoOf(e)), el('span', 'when', day(e.at) + (e.type === 'comment' && t.edited ? ', edited' : '')));
    if (e.type === 'reopen') h.append(el('span', 'tag', 'Reopened'));
    m.append(h);
    if (e.type === 'comment') {
      var crumb = o.crumb && o.crumb(e), said = o.commentBody ? o.commentBody(e) : body(e.text);
      if (crumb) m.append(crumb);
      if (said) m.append(said);
    } else m.append(body(e.text));
    return m;
  }
  // A page's own kind of first message, drawn by its renderer: its content becomes the first message, and the buttons
  // of its foot, without its own progress (the row says the state once), become the row's buttons.
  function kindParts(t, actions) {
    if (!kinds[t.root.type]) return null;
    var c = { kind: t.root.type, e: t.root, replies: t.messages.slice(1), thread: t };
    var made = kinds[c.kind](c, state, actions), item = Array.isArray(made) ? made[0] : made, foot = Array.isArray(made) ? made[1] : null;
    if (!item) return null;
    var m = el('div', 'tmsg ' + (t.root.by === 'user' ? 'mine' : 'agent') + ' ' + String(item.className || '').replace(/\bopen-q\b/, '').trim());
    Array.prototype.slice.call(item.childNodes).forEach(function (n) { m.append(n); });
    var buttons = foot ? Array.prototype.filter.call(foot.children, function (b) { return b.tagName === 'BUTTON'; }) : [];
    return { node: m, buttons: buttons, openQ: /\bopen-q\b/.test(item.className || ''), d: item.dataset && item.dataset.d, text: blockText(m).replace(/\s+/g, ' ').trim() };
  }
  // What a page's kind says, for the row's first sentence: its words without its head (who and when), a space between
  // blocks, so words of two paragraphs never run together.
  var BLOCK = /^(P|DIV|LI|UL|OL|H[1-6]|BLOCKQUOTE|PRE|TABLE|TR|TD|TH|BR)$/;
  function blockText(n) {
    if (n.nodeType === 3) return n.textContent;
    if (n.nodeType !== 1 || (n.classList && n.classList.contains('head'))) return '';
    var inner = Array.prototype.map.call(n.childNodes, blockText).join('');
    return BLOCK.test(n.tagName) ? ' ' + inner + ' ' : inner;
  }
  // The box under an open thread: your answer or reply, or why you reopen it. Its text survives every redraw. ONSEND,
  // from a page's own kind, sends something else, such as the answer to a decision.
  function writeBox(t, k) {
    var mode = box.mode, dk = k + ':' + mode, f = el('div', 'why'), domId = 'tbox-' + k.replace(/[^\w-]/g, '_');
    var words = box.label || (mode === 'reopen' ? 'Why reopen it?' : t.state === 'you' ? 'Your answer' : 'Your reply');
    var lab = el('label', '', words), ta = keyed(el('textarea'), 'box:' + k), err = el('p', 'err', errors[dk] || '');
    ta.id = domId; lab.htmlFor = domId; ta.rows = 3; ta.value = drafts[dk] || '';
    err.id = domId + '-err'; err.hidden = !errors[dk];
    if (errors[dk]) { ta.setAttribute('aria-invalid', 'true'); ta.setAttribute('aria-describedby', err.id); }
    ta.addEventListener('input', function () {
      drafts[dk] = ta.value;
      if (errors[dk]) { errors[dk] = null; err.hidden = true; ta.removeAttribute('aria-invalid'); }
    });
    var from = box.from, onSend = box.onSend, row = el('div', 'row2');
    var ok = button(mode === 'reopen' ? 'Reopen' : 'Send', '', submit), no = button('Cancel', 'btn--quiet', cancel);
    function cancel() { box = null; focusAfter = from; renderThread(); }
    function submit() {
      var text = ta.value.trim();
      if (!text) {
        errors[dk] = mode === 'reopen' ? 'Say why you reopen it.' : 'Write your ' + (/answer/i.test(words) ? 'answer' : 'reply') + ' first.';
        focusAfter = 'box:' + k; renderThread(); return;
      }
      var done = function () {
        drafts[dk] = ''; errors[dk] = null;
        if (box && box.key === k) box = null;
        focusAfter = 'toggle:' + k; renderThread();
      };
      if (onSend) return onSend(text, done);
      if (mode === 'reopen') send('reopen', { to: t.id, text: text }, 'Reopen', done);
      else send('note', { id: 'm-' + Date.now().toString(36), to: t.id, text: text }, /answer/i.test(words) ? 'Answer' : 'Reply', done);
    }
    ta.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { e.preventDefault(); cancel(); }
      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); submit(); }
    });
    row.append(ok, no); f.append(lab, ta, err, row);
    return f;
  }
  function openBox(t, mode, more) {
    var k = keyOf(t);
    box = Object.assign({ key: k, mode: mode, from: 'act:' + mode + ':' + k }, more);
    expanded[k] = true; focusAfter = 'box:' + k; renderThread();
  }
  // Close is recorded once its 6-second window is over. Meanwhile the row stays in place as Closed with its own Undo,
  // so closing several threads in a row keeps an Undo for each, next to what it undoes.
  function close(t, first) {
    var k = keyOf(t);
    closing[k] = { first: first, timer: setTimeout(function () {
      delete closing[k]; closed[k] = true;
      send('accept', { to: t.id }, 'Close', null, function () { delete closed[k]; renderThread(); });
      renderThread();
    }, CLOSE_MS) };
    focusAfter = 'undo:' + k; renderThread();
  }
  function closedRow(t, k) {
    var li = el('li', 'trow closing'), c = closing[k], p = el('div', 'tclosed'), g = el('span', 'tgist');
    li.dataset.state = 'done'; li.dataset.id = k;
    g.append(el('span', 'twho', whoOf(t.root) + ': '), c.first);
    p.append(el('span', 'chip ok', 'Closed'), g);
    var u = keyed(button('Undo', 'btn--quiet', function () {
      clearTimeout(c.timer); delete closing[k]; focusAfter = 'toggle:' + k; renderThread();
    }, 'Undo closing: ' + c.first), 'undo:' + k);
    li.append(p, u);
    return li;
  }
  function row(t, actions, forceOpen) {
    var k = keyOf(t);
    if (closing[k] && actions) return closedRow(t, k);
    var kind = kindParts(t, actions);
    if (!kind && PLAIN.indexOf(t.root.type) < 0) return null;
    var first = gist(t.root.type === 'decision' || PLAIN.indexOf(t.root.type) >= 0 || t.root.text ? rootText(t.root) : (kind && kind.text) || rootText(t.root)), open = forceOpen || !!expanded[k], li = el('li', 'trow');
    li.dataset.state = t.state === 'you' ? 'asked' : t.state === 'done' ? 'done' : t.step === 'working' ? 'working' : 'seen';
    if (t.id != null) li.dataset.id = t.id;
    if (kind && kind.openQ) li.classList.add('open-q');
    if (kind && kind.d) li.dataset.d = kind.d;
    // The head opens and folds the thread: one native button, as wide as the row. A row shown elsewhere, open and
    // without actions (nodes), has nothing to fold: its head is plain.
    var plainHead = !actions && forceOpen;
    var head = plainHead ? el('div', 'thead plain') : keyed(el('button', 'thead'), 'toggle:' + k), top = el('span', 'ttop'), chips = el('span', 'tchips');
    if (!plainHead) { head.type = 'button'; head.setAttribute('aria-expanded', String(open)); }
    var said = t.state === 'you' ? 'Your turn' : t.state === 'done' ? 'Done' : 'Agent’s turn, ' + STEP_WORDS[t.step].toLowerCase();
    if (t.state !== 'done') chips.append(stateChip(t));
    if (t.state === 'you') chips.append(el('span', 'tage', aged('Waiting', t.since)));
    else chips.append(progress(t));
    // A drawn equilateral triangle, sharp as the n14n style has it: down to open, up to fold.
    top.append(chips);
    if (!plainHead) {
      var fold = el('span', 'tfold'); fold.setAttribute('aria-hidden', 'true');
      fold.innerHTML = '<svg width="16" height="13.86" viewBox="0 0 16 13.86"><polygon points="' +
        (open ? '0,13.86 8,0 16,13.86' : '0,0 16,0 8,13.86') + '" fill="currentColor"/></svg>';
      top.append(fold);
      head.setAttribute('aria-label', said + '. ' + whoOf(t.root) + ': ' + first.replace(/[.?!…]$/, '') + '. ' + (open ? 'Fold the thread' : 'Open the thread'));
      head.addEventListener('click', function () { expanded[k] = !open; focusAfter = 'toggle:' + k; renderThread(); });
    }
    head.append(top);
    if (!open) { var g = el('span', 'tgist'); g.append(el('span', 'twho', whoOf(t.root) + ': '), first); head.append(g); }
    li.append(head);
    if (open) {
      var b = el('div', 'tbody');
      t.messages.forEach(function (e, i) { b.append(i === 0 && kind ? kind.node : message(e, t)); });
      li.append(b);
    }
    var editing = actions && box && box.key === k;
    if (editing) li.append(writeBox(t, k));
    var foot = el('div', 'tfoot'), left = el('span', 'tleft'), acts = el('span', 'tacts'), n = t.messages.length;
    left.append(el('span', 'tmeta', (n === 1 ? '1 message' : n + ' messages') + ', last ' + day(t.last)));
    // A comment keeps Show, Edit and Delete while it is not done.
    var it = actions && t.root.type === 'comment' && o.byId && o.byId(t.root.id), e0 = t.root;
    if (it && t.state !== 'done') {
      var link = function (words, label, on) { var x = el('button', 'link', words); x.type = 'button'; x.setAttribute('aria-label', label); x.addEventListener('click', on); return x; };
      left.append(link('Show', o.showLabel ? o.showLabel(e0.n) : 'Show comment ' + e0.n, function () { o.reveal(e0); }),
        link('Edit', 'Edit comment ' + e0.n, function (ev) { o.reveal(e0); o.edit(it, ev && ev.target); }),
        link('Delete', 'Delete comment ' + e0.n, function () { o.remove(it); }));
    }
    function act(b, name) { acts.append(keyed(b, 'act:' + name + ':' + k)); }
    if (actions && !editing && t.id != null) {
      if (kind && kind.buttons.length) {
        // A done thread can be confirmed and reopened, whatever its kind; ✓ comes first, Reopen last, as on every row.
        if (t.state === 'done' && !t.closedByUser) act(button('✓', 'btn--quiet close', function () { close(t, first); }, 'Confirm done: ' + first), 'close');
        // The page's own controls, such as a decision's use-the-default check and Answer.
        kind.buttons.forEach(function (b, j) { acts.append(keyed(b, /\bchange\b/.test(b.className) ? 'act:reply:' + k : 'kind:' + j + ':' + k)); });
        if (t.state === 'done') act(button('Reopen', 'btn--quiet', function () { openBox(t, 'reopen'); }, 'Reopen: ' + first), 'reopen');
      } else {
        if (!t.closedByUser) act(button('✓', 'btn--quiet close', function () { close(t, first); }, (t.state === 'done' ? 'Confirm done: ' : 'Close: ') + first), 'close');
        if (t.state === 'you') act(button('Answer', 'primary', function () { openBox(t, 'reply'); }, 'Answer: ' + first), 'reply');
        if (t.state === 'agent') act(button('Reply', 'btn--quiet', function () { openBox(t, 'reply'); }, 'Reply: ' + first), 'reply');
        if (t.state === 'done') act(button('Reopen', 'btn--quiet', function () { openBox(t, 'reopen'); }, 'Reopen: ' + first), 'reopen');
      }
    }
    foot.append(left, acts); li.append(foot);
    return li;
  }
  // The threads as the page shows them: a close sent but not yet in the log already counts as closed.
  function current() {
    threads = pageThreads(log, itemKinds);
    var shown = threads.filter(function (t) {
      var k = keyOf(t);
      if (closed[k] && t.closedByUser) delete closed[k];
      else if (closed[k]) { t.state = 'done'; t.closedByUser = true; }
      return !t.deleted && (PLAIN.indexOf(t.root.type) >= 0 || kinds[t.root.type]);
    });
    state = pinStates();
    return shown;
  }
  // Each user item's state, for its pin.
  function pinStates() {
    var s = {};
    threads.forEach(function (t) {
      var v = t.closedByUser ? 'accepted' : t.state === 'done' ? 'done' : t.state === 'you' ? 'asked' : t.step;
      t.messages.forEach(function (m) { if (m.by === 'user' && m.id != null && itemKinds.indexOf(m.type) >= 0) s[m.id] = v; });
    });
    return s;
  }
  // What has focus in the list, so a redraw puts it back, with the caret; when it is gone, the head of the row now at
  // its place takes it.
  function focusKey() {
    var a = document.activeElement;
    if (!a || !thread.contains || !thread.contains(a)) return null;
    var li = a.closest && a.closest('li.trow'), rows = Array.prototype.slice.call(thread.querySelectorAll('li.trow'));
    return { key: a.dataset && a.dataset.fk, index: rows.indexOf(li), start: a.selectionStart, end: a.selectionEnd };
  }
  function renderThread() {
    var kept = focusKey(), stick = thread.scrollHeight - thread.scrollTop - thread.clientHeight < 40;
    var all = current(), actions = !o.readOnly;
    var live = all.filter(function (t) { return closing[keyOf(t)] || !t.closedByUser; });
    var yours = live.filter(function (t) { return t.state === 'you'; });
    var shown = filter === 'open' ? live.filter(function (t) { return t.state === 'done'; })
      .concat(live.filter(function (t) { return t.state === 'agent'; }), yours) : all;
    // A box the user is typing in keeps its thread on the page until it is sent or cancelled.
    if (box && filter === 'open' && !shown.some(function (t) { return keyOf(t) === box.key; })) {
      shown = shown.concat(all.filter(function (t) { return keyOf(t) === box.key; }));
    }
    var openBtn = document.querySelector('[data-filter="open"]'), allBtn = document.querySelector('[data-filter="all"]');
    if (openBtn) openBtn.textContent = 'Open (' + live.length + ')';
    if (allBtn) allBtn.textContent = 'All (' + all.length + ')';
    figure(yours.filter(function (t) { return !closing[keyOf(t)]; }));
    var empty = document.querySelector('.notes .empty');
    if (empty) empty.hidden = !!all.length;
    thread.replaceChildren();
    shown.forEach(function (t) { var li = row(t, actions); if (li) thread.appendChild(li); });
    if (filter === 'open' && all.length && !live.length) thread.appendChild(el('li', 'sys', 'Nothing open: every thread is done and closed.'));
    // The list opens on its end, next to the message box, and follows new rows while the user is at the bottom. The
    // scroll repeats on the next frame and once fonts load, which can make the list taller after this render.
    if (stick || !scrolledOnce) {
      var bottom = function () { thread.scrollTop = thread.scrollHeight; above(); };
      bottom(); requestAnimationFrame(bottom); if (document.fonts) document.fonts.ready.then(bottom);
      if (log.length) scrolledOnce = true;
    }
    if (focusAfter) {
      var target = find(focusAfter); focusAfter = null;
      if (target) { target.focus({ preventScroll: true }); if (target.scrollIntoView) target.scrollIntoView({ block: 'nearest' }); }
    } else if (kept) {
      var back = kept.key && find(kept.key);
      if (!back && kept.index >= 0) {
        var rows = thread.querySelectorAll('li.trow'), r = rows[Math.min(kept.index, rows.length - 1)];
        back = r && (r.querySelector('.thead') || r.querySelector('[data-fk]'));
      }
      if (back) { back.focus({ preventScroll: true }); if (kept.start != null && back.setSelectionRange) back.setSelectionRange(kept.start, kept.end); }
    }
    above();
    if (o.rendered) o.rendered(state);
  }
  // While rows are out of view above, a button says how many and takes the user there.
  var cue = null;
  function above() {
    if (!thread.getBoundingClientRect || !thread.parentNode) return;
    if (!cue) {
      cue = el('button', 'tabove'); cue.type = 'button'; cue.hidden = true;
      cue.addEventListener('click', function () { thread.scrollTo({ top: 0 }); });
      thread.parentNode.insertBefore(cue, thread);
    }
    var top = thread.getBoundingClientRect().top, n = 0;
    thread.querySelectorAll('li.trow').forEach(function (li) { if (li.getBoundingClientRect().top < top - 4) n++; });
    cue.hidden = !n; cue.textContent = '▲ ' + n + (n === 1 ? ' more thread above' : ' more threads above');
  }
  thread.addEventListener('scroll', above);
  // The top bar's figure: how many threads are your turn; a button to the first one's Answer, or plain at none. It goes
  // where the page says (o.stats), else in the header's #status.
  var figureEl = null;
  function figureSlot() {
    if (typeof o.stats === 'function') return o.stats();
    return o.stats || (document.getElementById ? document.getElementById('status') : null);
  }
  function placeFigure() {
    var slot = figureSlot();
    if (!slot || !figureEl) return figureEl;
    if (slot.textContent.trim() === 'Loading…') slot.replaceChildren();
    if (figureEl.parentNode !== slot) slot.append(figureEl);
    return figureEl;
  }
  function figure(yours) {
    if (!figureSlot()) return;
    var tag = yours.length ? 'BUTTON' : 'SPAN';
    if (!figureEl || figureEl.tagName !== tag) {
      if (figureEl) figureEl.remove();
      figureEl = el(tag.toLowerCase(), 'stat');
      if (yours.length) { figureEl.type = 'button'; figureEl.addEventListener('click', goYourTurn); }
    }
    figureEl.replaceChildren(el('b', '', String(yours.length)), ' your turn');
    if (yours.length) figureEl.setAttribute('aria-label', yours.length + ' your turn: go to the first');
    figureEl.first = yours[0];
    placeFigure();
  }
  function goYourTurn() {
    var t = figureEl.first; if (!t) return;
    if (filter !== 'open') document.querySelector('[data-filter="open"]').click();
    var b = find('act:reply:' + keyOf(t)) || find('toggle:' + keyOf(t));
    if (b) { if (b.scrollIntoView) b.scrollIntoView({ block: 'center' }); b.focus(); }
  }
  // The thread an id belongs to: the thread itself, or a message in it.
  function threadOf(id) {
    for (var i = 0; i < threads.length; i++) {
      var t = threads[i];
      if (String(t.id) === String(id) || t.messages.some(function (m) { return m.id != null && String(m.id) === String(id); })) return t;
    }
    return null;
  }
  // A box under a thread, from a page's own kind, such as a decision's Answer: FROM is the button that opened it, and
  // takes the focus back on Cancel; ONSEND(text, done) sends what the box holds.
  function reasonBox(_li, id, label, from, onSend) {
    var t = threadOf(id); if (!t) return;
    openBox(t, 'reply', { label: label, onSend: onSend, from: from && from.dataset ? from.dataset.fk : null });
  }
  // From elsewhere on the page, such as a pin: the thread comes into view, open, with Reopen's box when it is done and
  // the reply box otherwise.
  function reopen(id) {
    var t = threadOf(id); if (!t) return;
    if (filter === 'open' && t.closedByUser) document.querySelector('[data-filter="all"]').click();
    openBox(t, t.state === 'done' ? 'reopen' : 'reply');
  }
  // The page's whole log, when the page reads it itself; KEY is anything else the entries show, such as a deadline.
  // The thread is redrawn only when either changed, so focus and selection stay put between polls.
  function setLog(events, key) {
    var next = JSON.stringify([events, key]);
    if (next === fed) return;
    fed = next; log = events.slice(); renderThread();
  }
  // The rows of the user's threads that match, open and without actions, such as the comments on one task.
  function nodes(match) {
    current();
    return threads.filter(function (t) { return !t.deleted && itemKinds.indexOf(t.root.type) >= 0 && match(t.root); })
      .map(function (t) { return row(t, false, true); }).filter(Boolean);
  }

  // ---------- The message box ----------
  var noteBox = document.querySelector('#note'), noteBtn = document.querySelector('.notes .send .btn');
  function sendNote() {
    var note = noteBox.value.trim();
    if (!note) { say('Write your message first.', true); noteBox.focus(); return; }
    send('note', Object.assign({ id: 'm-' + Date.now().toString(36), text: note, to: null }, o.noteParams ? o.noteParams() : {}), 'Message', function () { noteBox.value = ''; });
  }
  function mode() { return o.sendMode ? o.sendMode() : null; }
  if (noteBox && !o.readOnly) {
    noteBtn.addEventListener('click', function (e) { e.preventDefault(); (mode() || sendNote)(); });
    noteBox.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey && !mode()) { e.preventDefault(); sendNote(); } });
  }

  // ---------- Live updates ----------
  // A close in its undo window counts too: a reload would end its timer, and the close would never be sent.
  function busy() {
    return !!(noteBox && noteBox.value.trim()) || !!(o.busy && o.busy()) || Object.keys(closing).length > 0 ||
      Object.keys(drafts).some(function (k) { return !!(drafts[k] || '').trim(); });
  }
  // Lines in the format before this change are one count under the header, the same on every page: kept as they are.
  function oldNote(count) {
    var note = document.getElementById('oldnote');
    if (!note) return;
    var text = count ? count + (count === 1 ? ' record' : ' records') + ' in the format before this change: kept as is, not converted.' : '';
    note.hidden = !count;
    if (note.textContent !== text) note.textContent = text;
  }
  function start() {
    renderThread();
    if (!o.served) return;
    (function count() {
      pageFetch('/old').then(function (r) { return r.json(); }).then(function (n) {
        if (!pageIsStale) oldNote(Number(n) || 0);
      }).catch(function () {}).then(function () { pagePollAgain(count, 5000); });
    })();
    // After two failed polls in a row, a strip under the bar says the agent's server stopped; it goes when it answers again.
    // A page that streams events counts the stream's polls; one that does not (stream: false) counts the /listening polls.
    var offline = document.querySelector('.offline'), misses = 0, streaming = o.stream !== false;
    // Once a request was refused as out of date the strip stays: no later poll or stream event clears it.
    function connected(on) { misses = on ? 0 : misses + 1; offline.hidden = !pageIsStale && (on || misses < 2); }
    if (streaming) (function stream(after) {
      pageFetch('/events?after=' + after).then(function (r) { return r.json(); }).then(function (r) {
        connected(true);
        r.events.forEach(function (e) { log.push(e); if (o.apply) o.apply(e, false); });
        // A new reply from the agent is announced once, in the toast, which screen readers read as a status.
        if (after > 0) r.events.forEach(function (e) { if (e.type === 'reply') flash(agent + ': ' + pageMarkdownText(e.text).slice(0, 120), 'ok'); });
        if (r.events.length) renderThread();
        stream(r.total);
      }).catch(function (e) { if (e && e.stale) return; connected(false); pagePollAgain(function () { stream(after); }, 2000); });
    })(0);
    // A new render from the agent loads by itself, as soon as the user is not typing: a comment, a message or an answer
    // in progress would be lost. The page keeps its place through o.beforeReload.
    if (streaming) pageWatchRevision(function () {
      if (busy()) return;
      try { if (o.beforeReload) o.beforeReload(); } catch (e) {}
      location.reload();
    });
    // Once the agent has used `wait`, a note above the message box says when no `wait` is connected: what the user
    // sends then reaches the agent only when it next looks. While the server is down, the offline strip says more. It goes
    // through pageFetch like every request: a page out of date shows only that strip, and asks nothing more.
    var unwatched = document.querySelector('.unwatched');
    (function watch() {
      pageFetch('/listening').then(function (r) { return r.json(); }).then(function (on) {
        unwatched.hidden = pageIsStale || on !== false;
        if (!streaming) connected(true);
      }).catch(function () { unwatched.hidden = true; if (!streaming) connected(false); })
        .then(function () { pagePollAgain(watch, 2000); });
    })();
  }

  return {
    send: send, say: say, flash: flash, reopen: reopen, render: renderThread, start: start, setLog: setLog, nodes: nodes,
    box: reasonBox, figure: placeFigure, noteBox: noteBox, noteBtn: noteBtn, busy: busy,
    log: function () { return log; }, state: function () { return state; }
  };
}

// The time of an event for the user: its UTC time (Z) as their own clock reads it, hours and minutes.
function pageTime(at) {
  if (!/Z$/.test(at || '')) return (at || '').slice(11, 16);
  var d = new Date(at);
  return isNaN(d) ? '' : ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2);
}

// The threads of a LOG, each in one state of the one machine every thread follows (.design/conversation-panel/states.md).
// Kept apart from the drawing so it can be tested without a browser; `threads` in src/better_ai/page/__init__.py gives
// the same threads for the same log, and tests/fixtures/threads.json holds the logs both are run on.
// ITEMKINDS: the user's kinds the agent tracks (comment, note, ...). Each thread, in the order it started:
//   { id, root, messages, state: 'you' | 'agent' | 'done', step: 'new' | 'seen' | 'working', closedByUser, deleted,
//     edited (the user's comment was sent again), since (when the state or step was set), userAt (log index of the user's latest event), last (time of the last
//     message) }
// A thread starts with an event that names no thread: the user's item, the agent's message on its own (a report, done),
// a worker's `closed`, a decision from pageDecisionEvents (your turn while it waits), the user's action that is no
// message to the agent (such as a verdict or a confirmation: closed by the user), or anything else the page shows (done). An answer names its decision; the rest name the thread, or a message in it, in `to`.
// An agent status counts only if its `read` (the log index of the last event the agent was shown) covers the user's
// latest event in the thread; a status without `read` counts (logs before `read`). Indexes are the conversation log's
// own: pageDecisionEvents keeps each event's in `_i`.
var PAGE_CONTROL = ['status', 'accept', 'accepted', 'reopen', 'delete'];
function pageThreads(log, itemKinds) {
  var threads = [], byId = {}, home = {}, agentRead = -1;
  function threadOf(id) { return byId[home[id] || id]; }
  function start(e, i, state) {
    var t = { id: e.id == null ? null : e.id, root: e, messages: [e], state: state, step: 'new', closedByUser: false,
      deleted: false, edited: false, since: e.at, userAt: e.by === 'user' ? i : -1, last: e.at };
    if (e.id != null) byId[e.id] = t;
    threads.push(t);
    return t;
  }
  function seenStep(t, at) {
    if (t.state === 'agent' && t.step === 'new' && agentRead >= t.userAt) { t.step = 'seen'; t.since = at; }
  }
  var n = 0;
  log.forEach(function (e) {
    var i = e._i != null ? e._i : n, read = agentRead;
    if (e.type !== 'decision' || e.x == null) n++;
    if (!e.type) return;  // a line the log could not read keeps its place, and is no event
    var user = e.by === 'user', item = user && itemKinds.indexOf(e.type) >= 0;
    if (!user && typeof e.read === 'number') agentRead = Math.max(agentRead, e.read);
    var target = e.type === 'answer' ? e.decision : e.to, t = target != null ? threadOf(target) : null;
    if (!t && item && e.id != null && byId[e.id] && byId[e.id].root.type === e.type) {
      // The user's item sent again, such as an edited or restored comment: the same thread, in its state.
      t = byId[e.id];
      if (e.type === 'comment') { t.root = e; t.messages[0] = e; t.deleted = false; t.edited = true; }
    } else if (!t) {
      if (PAGE_CONTROL.indexOf(e.type) < 0) {
        var state = item ? 'agent' : e.type === 'decision' && pageDecisionStatus(e.x || {}) === 'waiting' ? 'you' : 'done';
        t = start(e, i, state);
        // The user's action that is no message to the agent, such as a verdict or a confirmation, needs no reply: its
        // thread starts closed by the user, in All and never in Open, until they write in it (D8).
        if (user && !item && e.type !== 'note' && e.type !== 'answer') t.closedByUser = true;
        // Later answers to the same decision join this thread, when the decision is not in the log.
        if (e.type === 'answer' && target != null && !byId[target]) home[target] = t.id;
      }
    } else {
      if (e.id != null) home[e.id] = t.id;
      var fresh = typeof e.read !== 'number' || e.read >= t.userAt;
      if (user && (item || e.type === 'note' || e.type === 'answer' || e.type === 'reopen')) {
        t.messages.push(e); t.last = e.at; t.userAt = i;
        t.state = 'agent'; t.step = 'new'; t.closedByUser = false; t.since = e.at;
      } else if (e.type === 'reply') {
        t.messages.push(e); t.last = e.at;  // the CLI writes the reply's status with it (done by default)
      } else if (e.type === 'delete' && user) {
        t.deleted = true;
      } else if (e.type === 'accept' && user || e.type === 'accepted') {
        // ✓, or the user's words that accept it: closes an open thread, or confirms one the agent finished.
        if (t.state !== 'done') t.since = e.at;
        t.state = 'done'; t.closedByUser = true; t.userAt = i;
      } else if (e.type === 'status' && fresh && !t.closedByUser) {
        // A thread you closed changes only when you act on it again.
        var was = t.state + t.step;
        if (e.status === 'asked') t.state = 'you';
        else if (e.status === 'done') t.state = 'done';
        else if (t.state === 'agent' && (e.status === 'seen' || e.status === 'working')) t.step = e.status;
        if (t.state + t.step !== was) t.since = e.at;
      }
    }
    // Seen follows the agent's reading: a further read can cover the user's latest event of any thread.
    if (agentRead > read) threads.forEach(function (x) { seenStep(x, e.at); });
  });
  return threads;
}

// ---------- Markdown in messages ----------
// What the user and the agent write in the conversation is Markdown: paragraphs (a single line break stays a line
// break, as in a chat), headings, lists (nested by indenting), quotes, code spans and blocks, tables, rules, bold,
// italic, strikethrough and links. Anything else shows as written. The text becomes a tree of plain objects, then
// elements whose words are set as text, never as HTML, so a message cannot add markup or scripts to the page; a link
// opens only an http, https or mailto address.
var MD_ITEM = /^( {0,3})([-*+]|\d{1,9}[.)])(?:[ \t]+(.*))?$/, MD_FENCE = /^ {0,3}(`{3,}|~{3,})/, MD_RULE = /^ {0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$/;
var MD_HEADING = /^ {0,3}(#{1,6})(?:[ \t]+(.*))?$/, MD_QUOTE = /^ {0,3}> ?/, MD_TABLE_RULE = /^[ \t]*\|?[ \t]*:?-+:?[ \t]*(\|[ \t]*:?-+:?[ \t]*)*\|?[ \t]*$/;
// A heading's words without the closing #s it may end with. Done by hand: a pattern for it is slow on long runs of spaces.
function mdHeadingText(t) {
  t = (t || '').trim();
  var end = t.length;
  while (end > 0 && t[end - 1] === '#') end--;
  return end < t.length && (end === 0 || /[ \t]/.test(t[end - 1])) ? t.slice(0, end).trim() : t;
}
function mdIndent(line) { return line.match(/^[ \t]*/)[0].replace(/\t/g, '    ').length; }
function mdCells(line) {
  return line.trim().replace(/^\|/, '').replace(/\|$/, '').split(/(?<!\\)\|/).map(function (c) { return c.trim().replace(/\\\|/g, '|'); });
}
function mdTableStart(lines, i) {
  return lines[i].indexOf('|') >= 0 && i + 1 < lines.length && lines[i + 1].indexOf('|') >= 0 && MD_TABLE_RULE.test(lines[i + 1]) &&
    mdCells(lines[i + 1]).length === mdCells(lines[i]).length;
}
// A numbered line starts a list mid-paragraph only from 1, so "in\n2024. Then" stays a sentence.
function mdStarts(lines, i) {
  var l = lines[i], item = l.match(MD_ITEM);
  return MD_FENCE.test(l) || MD_HEADING.test(l) || MD_RULE.test(l) || MD_QUOTE.test(l) || mdTableStart(lines, i) ||
    !!item && (!/\d/.test(item[2]) || parseInt(item[2], 10) === 1);
}
// The words of a block, with their marks. A code span keeps the marks in it as written, and so does a backslash.
var MD_INLINE = /(`+)([^`]|[^`][\s\S]*?[^`])\1(?!`)|\[([^\]]+)\]\(((?:[^()\s]|\([^()\s]*\))+)\)|\*\*\*(?=\S)([\s\S]*?\S)\*\*\*(?!\*)|\*\*(?=\S)([\s\S]*?\S)\*\*|~~(?=\S)([\s\S]*?\S)~~|\*(?=[^\s*])([\s\S]*?[^\s*\\])\*(?:(?!\*)|(?=\*\*[^\s*]))|(^|[^\w\\])_(?=[^\s_])([\s\S]*?[^\s_\\])_(?!\w)|(https?:\/\/(?:[^\s<>()]|\([^\s<>()]*\))*(?:[^\s<>().,;:!?'"\]*_]|\([^\s<>()]*\)))|\\([\\`*_{}\[\]()#+\-.!|~>])/g;
// Link text cannot hold another link, such as a bare URL: keep its words only.
function mdNoLinks(nodes) {
  return nodes.reduce(function (a, n) {
    return a.concat(n.tag === 'a' ? mdNoLinks(n.children) : [n.children ? Object.assign({}, n, { children: mdNoLinks(n.children) }) : n]);
  }, []);
}
// Past MD_INLINE_MAX characters, a block's words show as written: an unclosed mark makes the search slow on long text.
var MD_INLINE_MAX = 10000;
function mdInline(text) {
  if (text.length > MD_INLINE_MAX) return [{ text: text }];
  var out = [], last = 0, m, re = new RegExp(MD_INLINE.source, 'g');
  function words(s) { if (!s) return; var prev = out[out.length - 1]; if (prev && prev.tag == null) prev.text += s; else out.push({ text: s }); }
  while ((m = re.exec(text))) {
    words(text.slice(last, m.index)); last = re.lastIndex;
    if (m[1]) out.push({ tag: 'code', children: [{ text: m[2].replace(/\n/g, ' ').replace(/^ (.*) $/, '$1') }] });
    else if (m[3]) out.push(/^(https?:|mailto:)/i.test(m[4]) ? { tag: 'a', href: m[4], children: mdNoLinks(mdInline(m[3])) } : { text: m[0] });
    else if (m[5]) out.push({ tag: 'strong', children: [{ tag: 'em', children: mdInline(m[5]) }] });
    else if (m[6]) out.push({ tag: 'strong', children: mdInline(m[6]) });
    else if (m[7]) out.push({ tag: 'del', children: mdInline(m[7]) });
    else if (m[8]) out.push({ tag: 'em', children: mdInline(m[8]) });
    else if (m[10]) { words(m[9]); out.push({ tag: 'em', children: mdInline(m[10]) }); }
    else if (m[11]) out.push({ tag: 'a', href: m[11], children: [{ text: m[11] }] });
    else words(m[12]);  // an escaped mark is the mark as written
  }
  words(text.slice(last));
  return out;
}
// Each line break in a paragraph's words as a break element.
function mdBreaks(nodes) {
  return nodes.reduce(function (a, n) {
    if (n.tag == null) n.text.split('\n').forEach(function (t, k) { if (k) a.push({ tag: 'br' }); if (t) a.push({ text: t }); });
    else a.push(n.children && n.tag !== 'code' ? Object.assign({}, n, { children: mdBreaks(n.children) }) : n);
    return a;
  }, []);
}
// The blocks of a message, or of a list item or a quote inside it.
// Past MD_DEPTH quotes or lists inside each other, the rest shows as written: deeper nesting could overflow the stack.
var MD_DEPTH = 20;
function mdBlocks(lines, depth) {
  var out = [], i = 0, m;
  depth = depth || 0;
  if (depth > MD_DEPTH) return lines.join('').trim() ? [{ tag: 'p', children: [{ text: lines.join('\n') }] }] : [];
  while (i < lines.length) {
    var line = lines[i];
    if (!line.trim()) { i++; continue; }
    if ((m = line.match(MD_FENCE))) {
      // The code lines lose as many spaces as the fence is indented.
      var fence = m[1], code = [], strip = new RegExp('^ {0,' + line.match(/^ */)[0].length + '}');
      for (i++; i < lines.length && !(lines[i].trim().indexOf(fence) === 0 && !lines[i].trim().slice(fence.length).trim()); i++) code.push(lines[i].replace(strip, ''));
      i++; out.push({ tag: 'pre', children: [{ tag: 'code', children: [{ text: code.join('\n') }] }] });
    } else if ((m = line.match(MD_HEADING))) {
      out.push({ tag: 'p', cls: 'md-h', children: [{ tag: 'strong', children: mdInline(mdHeadingText(m[2])) }] }); i++;
    } else if (MD_RULE.test(line)) {
      out.push({ tag: 'hr' }); i++;
    } else if (MD_QUOTE.test(line)) {
      var quoted = [];
      for (; i < lines.length && MD_QUOTE.test(lines[i]); i++) quoted.push(lines[i].replace(MD_QUOTE, ''));
      out.push({ tag: 'blockquote', children: mdBlocks(quoted, depth + 1) });
    } else if ((m = line.match(MD_ITEM))) {
      // One list: its items, each with the lines indented under it, which can hold a nested list.
      var ordered = /\d/.test(m[2]), list = { tag: ordered ? 'ol' : 'ul', children: [] }, item = null, base = m[1].length, blank = false;
      if (ordered && parseInt(m[2], 10) !== 1) list.start = parseInt(m[2], 10);
      for (; i < lines.length; i++) {
        var l = lines[i], im = l.match(MD_ITEM), ind = mdIndent(l);
        if (im && ind < base + 2 && /\d/.test(im[2]) === ordered) {
          item = { lines: [im[3] || ''], at: im[1].length + im[2].length + 1 }; list.children.push(item); blank = false;
        } else if (!l.trim()) { blank = true; if (item) item.lines.push(''); }
        else if (ind >= base + 2 || (!blank && !MD_ITEM.test(l) && !mdStarts(lines, i))) {
          item.lines.push(ind >= base + 2 ? l.replace(/\t/g, '    ').slice(Math.min(ind, item.at)) : l); blank = false;
        } else break;
      }
      list.children = list.children.map(function (it) {
        var inner = mdBlocks(it.lines, depth + 1);
        // A short item shows as words, not as a paragraph with its own space.
        if (inner.length && inner[0].tag === 'p' && !inner[0].cls) inner.splice.apply(inner, [0, 1].concat(inner[0].children));
        return { tag: 'li', children: inner };
      });
      out.push(list);
    } else if (mdTableStart(lines, i)) {
      var head = mdCells(line), align = mdCells(lines[i + 1]).map(function (c) {
        return /^:-+:$/.test(c) ? 'center' : /-:$/.test(c) ? 'right' : '';
      }), rows = [];
      for (i += 2; i < lines.length && lines[i].trim() && lines[i].indexOf('|') >= 0; i++) rows.push(mdCells(lines[i]));
      var cell = function (tag) { return function (c, k) { return { tag: tag, align: align[k], children: mdInline(c) }; }; };
      out.push({ tag: 'table', children: [
        { tag: 'thead', children: [{ tag: 'tr', children: head.map(cell('th')) }] },
        { tag: 'tbody', children: rows.map(function (r) { return { tag: 'tr', children: head.map(function (_, k) { return r[k] || ''; }).map(cell('td')) }; }) }] });
    } else {
      // A paragraph runs to a blank line or the start of another block; each line break in it stays.
      // Its marks can span a line break, such as bold over two lines.
      var para = [];
      for (; i < lines.length && lines[i].trim() && !(para.length && mdStarts(lines, i)); i++) para.push(lines[i].trim());
      out.push({ tag: 'p', children: mdBreaks(mdInline(para.join('\n'))) });
    }
  }
  return out;
}
function pageMarkdownTree(text) { return mdBlocks(String(text == null ? '' : text).replace(/\r\n?/g, '\n').split('\n')); }
// The message's words without its marks, on one line, such as for a short notice.
function pageMarkdownText(text) {
  var BLOCK = /^(p|li|pre|blockquote|ul|ol|table|tr|th|td|hr|br)$/;
  function words(n) { return (BLOCK.test(n.tag) ? ' ' : '') + (n.text != null ? n.text : (n.children || []).map(words).join('')) + (BLOCK.test(n.tag) ? ' ' : ''); }
  return pageMarkdownTree(text).map(words).join('').replace(/\s+/g, ' ').trim();
}
// The message as elements: a div of class "body md", with the text direction of its words.
function pageMarkdown(text) {
  function make(n) {
    if (n.tag == null) return document.createTextNode(n.text);
    var x = document.createElement(n.tag);
    if (n.cls) x.className = n.cls;
    if (n.start != null) x.start = n.start;
    if (n.align) x.style.textAlign = n.align;
    if (n.href) { x.href = n.href; x.target = '_blank'; x.rel = 'noopener noreferrer'; }
    (n.children || []).forEach(function (c) { x.append(make(c)); });
    return x;
  }
  var d = document.createElement('div'); d.className = 'body md'; d.dir = 'auto';
  pageMarkdownTree(text).forEach(function (n) { d.append(make(n)); });
  return d;
}

// ---------- The shared capabilities ----------
// The server fills the shell with the page's config (see page/__init__.py, PageSpec): `{agent, title, capabilities}`.
// A page uses a capability only when it declares it; the server refuses the events of one it does not declare.
function pageConfig() {
  var node = typeof document !== 'undefined' && document.getElementById && document.getElementById('page-config');
  try { return node ? JSON.parse(node.textContent) : {}; } catch (e) { return {}; }
}
function pageRole() { return pageConfig().agent || 'agent'; }
function pageCan(name) { return (pageConfig().capabilities || []).indexOf(name) >= 0; }

// One decision question, for every page that shows the agent's decisions (the dashboard and the research board).
// A `waiting` decision is a question to the user: its default and deadline show, with Use the default (the check) and
// Answer. `defaulted`, `answered` and `decided` ones can be replied to. The page supplies the thread's pieces:
//   o.conversation  the page's pageConversation()     o.now()  the page's clock in seconds (the server's)
//   o.md(text)      Markdown to an HTML string        o.esc(text)  HTML-escaped text
//   o.id(prefix)    a new event id
//   o.suggested     true: the default is a suggestion, never applied on a timer: "Suggested default", no deadline words
//   o.next()        the element that waits after the open questions, such as a move that is due (optional)
// The footer of an open question is [✓] [Answer] on one row; each control's name includes the question. After ✓ the focus
// goes to the next open question, then to what waits next.
// pageDecisionEvents(decisions, conversation) is the log the thread draws: each decision as an entry of type `decision`
// (the record in `x`), among the conversation's events, in the order things happened. Nothing comes before what it
// answers: an answer never shows above its decision, a reply never above the answer it replies to.
// A decision's status word, and the user's last answer in its thread (C, the entry the panel gives a page's kind).
function pageDecisionStatus(x) { return String(x.status || 'decided').trim().toLowerCase(); }
function pageDecisionAnswer(c) { return c.replies.filter(function (r) { return r.type === 'answer'; }).pop(); }

// The decisions that wait for the user, for a page's own counts and badges: those whose thread, from DECISIONS and the
// conversation LOG, is the user's turn (pageThreads): waiting and not answered on the page, or asked back about the answer.
// Each is the decision record, in the order of DECISIONS.
function pageOpenDecisions(decisions, log) {
  var yours = {};
  pageThreads(pageDecisionEvents(decisions || [], log || []), []).forEach(function (t) {
    if (t.root.type === 'decision' && t.state === 'you' && !t.deleted) yours[t.id] = true;
  });
  return (decisions || []).filter(function (x) { return yours[x.id]; });
}

function pageDecision(o) {
  var conv = o.conversation;
  var status = pageDecisionStatus, answerOf = pageDecisionAnswer;
  // Where the decision stands, from its thread (C.thread, pageThreads): 0 the user's turn, 1 the user answered and the
  // agent has not applied it, 2 applied, -1 a decision that asked nothing.
  function step(c) {
    var st = status(c.e.x), t = c.thread || {}, answer = answerOf(c);
    if (t.state === 'you') return 0;
    if (st !== 'waiting' && st !== 'answered') return -1;
    return st === 'answered' || t.state === 'done' ? 2 : answer ? 1 : -1;
  }
  function left(x) { var t = Date.parse(x.deadline); return isNaN(t) ? null : t / 1000 - o.now(); }
  function deadlineWords(x) {
    var s = o.suggested ? null : left(x);
    if (s === null) return '';
    return s > 0 ? 'default in ' + (s < 90 ? 'under 2 min' : Math.round(s / 60) + ' min') : 'default due now';
  }
  // What takes the focus after the question FROM is answered, found at the click, before the send: the thread may redraw
  // before the send is done, and the answered question is then gone. It is kept as a name, never as an element, which a
  // redraw replaces: {id} the open question after it, else the first before it; {next} what the page says waits next,
  // asked again at focus time; {asked} another item the agent asked about, found again by its id. Nothing else waits: null.
  function nextWaiting(from) {
    var list = Array.prototype.slice.call(document.querySelectorAll('li.open-q')), i = -1, k;
    for (k = 0; k < list.length; k++) if (list[k].dataset.d === from) i = k;
    var others = list.slice(i + 1).concat(list.slice(0, Math.max(i, 0))).filter(function (q) { return q.dataset.d !== from; });
    if (others.length) return { id: others[0].dataset.d };
    if (o.next && o.next()) return { next: true };
    var asked = Array.prototype.slice.call(document.querySelectorAll('li[data-state="asked"]')).filter(function (q) { return q.dataset.d !== from && !/open-q/.test(q.className); });
    return asked.length && asked[0].dataset.id ? { asked: asked[0].dataset.id } : null;
  }
  function questionEl(id) {
    var list = Array.prototype.slice.call(document.querySelectorAll('li.open-q'));
    for (var k = 0; k < list.length; k++) if (list[k].dataset.d === id) return list[k].querySelector('.use') || list[k].querySelector('.answer') || list[k];
    return null;
  }
  function askedEl(id) {
    var list = Array.prototype.slice.call(document.querySelectorAll('li[data-state="asked"]'));
    for (var k = 0; k < list.length; k++) if (list[k].dataset.id === id) { list[k].setAttribute('tabindex', '-1'); return list[k]; }
    return null;
  }
  // The focus moves on only while it is still on the button that was clicked, on the page or on nothing: where the user
  // went during the send stays. A redraw after the answer replaces the nodes: the question's new ✓ is focused once drawn,
  // under the same rule.
  var want = null;
  function focusFree(from) {
    var now = document.activeElement;
    return !now || now === document.body || now === from || !document.contains(now);
  }
  function focusTarget(n, from) {
    if (!n || !focusFree(from)) return;
    var el = n.id ? questionEl(n.id) : n.next ? (o.next && o.next()) : askedEl(n.asked);
    if (el && el.focus) el.focus({ preventScroll: true });
    want = n.id ? { id: n.id, from: el } : null;
  }
  function head(who, label) {
    return '<div class="head"><span class="who">' + o.esc(who) + '</span><span class="when">' + o.esc(label) + '</span></div>';
  }
  function item(c, _state, actions) {
    var x = c.e.x, st = status(x), n = step(c), asked = n === 0;
    var label = asked ? (x.default ? deadlineWords(x) : '') : n === 1 ? 'answered, waiting for the ' + pageRole()
      : n === 2 ? 'answered by you' : st === 'defaulted' ? 'decided by the default' : st === 'answered' ? 'answered by you' : 'decided';
    var li = document.createElement('li');
    li.className = 'msg decision ' + st + (asked ? ' open-q' : '');
    // The default shows under an open question, as what happens without an answer; the answer the agent copied shows
    // only when the user gave it in the chat: an answer from the page is in the thread.
    var after = x.default && ((st === 'waiting' && n <= 0) || st === 'defaulted') ? '\n\n' + (st === 'waiting' ? (o.suggested ? 'Suggested default: ' : "If you don't answer: ") : 'Default applied: ') + x.default
      : st === 'answered' && x.answer && x.answer.type === 'chat' ? '\n\nYour answer:\n\n' + x.answer.text
      : st === 'decided' && x.decision ? '\n\nDecided:\n\n' + x.decision : '';
    li.innerHTML = head(pageRole().replace(/^./, function (ch) { return ch.toUpperCase(); }), label || pageTime(x.at)) + o.md(String(x.asked || '') + after);
    li.dataset.d = x.id;
    // The row says the state; the foot holds only the buttons, which become the row's.
    var foot = document.createElement('div');
    foot.className = 'foot' + (asked ? ' question' : '');
    var q = pageMarkdownText(x.asked);
    if (actions) {
      if (asked && x.default) {
        var use = document.createElement('button');
        use.type = 'button'; use.className = 'btn btn--sm btn--quiet answer use'; use.textContent = '✓'; use.title = 'Use the default';
        use.setAttribute('aria-label', 'Use the default for: ' + q);
        use.addEventListener('click', function () {
          var target = nextWaiting(x.id);
          use.disabled = true;
          conv.send('answer', { id: o.id('a'), decision: x.id, text: x.default, default: true }, 'Answer',
            function () { focusTarget(target, use); }, function () { use.disabled = false; });
        });
        foot.append(use);
        if (want && want.id === x.id) {
          var from = want.from; want = null;
          Promise.resolve().then(function () {
            var now = document.activeElement;
            if (!now || now === document.body || now === from) use.focus({ preventScroll: true });
          });
        }
      }
      var change = document.createElement('button');
      change.type = 'button'; change.className = 'btn btn--sm answer change' + (asked ? '' : ' btn--quiet');
      change.textContent = asked ? 'Answer' : 'Reply';
      change.setAttribute('aria-label', (asked ? 'Answer: ' : 'Reply to: ') + q);
      change.addEventListener('click', function () {
        conv.box(li, x.id, asked ? 'Your answer' : 'Your reply', change, function (text, done) {
          conv.send('answer', { id: o.id('a'), decision: x.id, text: text, default: false }, 'Answer', done);
        });
      });
      foot.append(change);
    }
    return [li, foot];
  }
  return { item: item, status: status, answerOf: answerOf, step: step };
}

function pageDecisionEvents(decisions, conversation) {
  var entries = (decisions || []).map(function (x) { return { type: 'decision', id: x.id, x: x, at: x.at, _t: Date.parse(x.at) / 1000 || 0 }; });
  var when = {};
  entries.forEach(function (e) { when[e.id] = e._t; });
  var events = (conversation || []).map(function (e, k) {
    var t = Math.max(Date.parse(e.at) / 1000 || 0, when[e.type === 'answer' ? e.decision : e.to] || 0);
    if (e.id) when[e.id] = t;
    // _i: its line in the log, which `read` counts in: the one the page's data gave it (page.log_records), else its place.
    return Object.assign({}, e, { _t: t, _i: e._i != null ? e._i : k });
  });
  return events.concat(entries).sort(function (a, z) { return a._t - z._t || (z.type === 'decision') - (a.type === 'decision'); });
}

// The approve panel, for a page that declares `approve`: a button opens a panel, and one button in it sends the event.
//   o.button, o.panel  the elements       o.params()  the event's fields       o.label  what the toast calls it
// The panel closes once the server has saved the event; a refusal leaves it open. Without the capability it does nothing.
function pageApprove(o) {
  if (!pageCan('approve')) return null;
  var open = false;
  function set(on) {
    open = on; o.panel.hidden = !on; o.button.setAttribute('aria-expanded', String(on));
    if (o.onToggle) o.onToggle(on);
  }
  o.button.addEventListener('click', function () { set(!open); });
  return {
    toggle: set,
    send: function (conversation, done, fail) {
      conversation.send('approve', Object.assign({ id: 'approval-' + Date.now().toString(36) }, o.params()), o.label || 'Approval',
        function () { set(false); if (done) done(); }, fail);
    }
  };
}

// The Approve… panel of a page that asks the user to approve one of several options: one radio per option, the first
// chosen; the open comments that come with the approval; and the message box as its note. While the panel is open, the
// Send button reads Confirm approval and sends the approval; an option marked `note` needs a message first. Only where
// the page declares `approve`; else null. Returns { sendMode, open }: give sendMode to pageConversation's o.sendMode.
// o.conversation  what pageConversation returned
// o.options()     the options, each { label, value, note }
// o.openItems()   the open comments that come with the approval, each { id, n, text }
// o.params()      what the page adds to each approval (optional)
// o.intro(box)    fills a box above the options each time the panel opens (optional)
// o.button        the button's words (default Approve…); o.needs: what to say when a note is missing
function pageApprovalPanel(o) {
  if (!pageCan('approve')) return null;
  var conv = o.conversation, noteBox = conv.noteBox, noteBtn = conv.noteBtn, deciding = false, options = [], carried = [];
  function el(tag, cls, text) { var x = document.createElement(tag); if (cls) x.className = cls; if (text != null) x.textContent = text; return x; }
  var panel = el('div', 'approval'), button = el('button', 'btn btn--quiet', o.button || 'Approve…');
  var intro = el('div', 'approval-intro'), opts = el('div', 'dopts'), carry = el('div', 'carry');
  button.type = 'button'; button.setAttribute('aria-expanded', 'false'); panel.hidden = true;
  opts.setAttribute('role', 'radiogroup'); opts.setAttribute('aria-label', 'Approval');
  panel.append(el('p', 'menu-h', 'Your approval'), intro, opts, carry);
  document.querySelector('.notes .composer').insertBefore(panel, document.querySelector('.notes .composer label'));
  noteBtn.parentElement.insertBefore(button, noteBtn.nextSibling);
  function picked() {
    var radio = opts.querySelector('input[name="approval"]:checked');
    return options.filter(function (x) { return radio && String(x.value) === radio.value; })[0];
  }
  function params() {
    var pick = picked(), note = noteBox.value.trim();
    return Object.assign({ option: pick.value, label: pick.label, carries: carried.map(function (it) { return it.id; }), text: note || null },
      o.params ? o.params() : {});
  }
  function fill(on) {
    deciding = on;
    button.textContent = on ? 'Cancel' : (o.button || 'Approve…');
    noteBtn.textContent = on ? 'Confirm approval' : 'Send';
    if (!on) return;
    intro.replaceChildren(); if (o.intro) o.intro(intro);
    options = o.options(); opts.replaceChildren();
    options.forEach(function (option, k) {
      var label = el('label', 'dopt'), radio = el('input'); radio.type = 'radio'; radio.name = 'approval'; radio.value = option.value;
      if (!k) radio.checked = true;
      label.append(radio, ' ' + option.label); opts.append(label);
    });
    carried = o.openItems(); carry.replaceChildren();
    if (carried.length) {
      carry.append(el('p', 'menu-h', 'Comes with your open comments'));
      carried.forEach(function (it) { carry.append(el('p', 'carried', it.n + '. ' + it.text)); });
    }
    noteBox.focus();
  }
  var approve = pageApprove({ button: button, panel: panel, label: 'Approval', params: params, onToggle: fill });
  function send() {
    if (picked().note && !noteBox.value.trim()) { conv.say(o.needs || 'Say why in the message.', true); return noteBox.focus(); }
    approve.send(conv, function () { noteBox.value = ''; });
  }
  return { sendMode: function () { return deciding ? send : null; }, open: function () { return deciding; } };
}

// An approval in the conversation: what the user approved, the comments that came with it by number, and their note.
function pageApprovalItem(entry, log) {
  var e = entry.e, li = document.createElement('li'), head = document.createElement('div'), who = document.createElement('span');
  var when = document.createElement('span'), body = document.createElement('p'), what = document.createElement('strong');
  li.className = 'msg me decision'; head.className = 'head'; who.className = 'who'; when.className = 'when'; body.className = 'body';
  who.textContent = 'You approved'; when.textContent = pageTime(e.at); what.textContent = e.label || e.option || e.text || '';
  head.append(who, when); body.append(what);
  if (e.carries && e.carries.length) {
    var with_ = document.createElement('span'); with_.className = 'with';
    with_.textContent = ' with comments ' + e.carries.map(function (id) {
      var x = log.filter(function (y) { return y.id === id; })[0]; return x && x.n ? x.n : '?';
    }).join(', ');
    body.append(with_);
  }
  li.append(head, body);
  if (e.label && e.text) { var note = document.createElement('p'); note.className = 'body'; note.textContent = e.text; li.append(note); }
  return li;
}

// The user's confirmation of a requirement, in the wording shown. Only where the page declares `confirm`.
function pageConfirm(conversation, requirement, wording, text, done, fail) {
  if (!pageCan('confirm')) return false;
  conversation.send('confirm', { id: 'confirm-' + Date.now().toString(36), requirement: requirement, wording: wording, text: text },
    'Confirmation', done, fail);
  return true;
}

// Text as HTML: every character that could open markup is written as an entity.
function pageEscape(text) {
  return String(text == null ? '' : text).replace(/[&<>"']/g, function (c) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
  });
}

// The records that did not validate, as the band above the work: how many, then where each is, its field, why, and who
// wrote it. A file can hold anything, so every part is text. The valid records are on the page as usual; this band never
// replaces them. NOTE, if given, says what the page shows of an invalid record. The page has
// `<section class="errors" id="errors" role="status" aria-labelledby="errors-h" hidden></section>`.
function pageErrors(errors, note) {
  if (!errors || !errors.length) return '';
  return '<h2 id="errors-h">' + errors.length + (errors.length === 1 ? ' record is' : ' records are') + ' not valid</h2>' + (note ? '<p>' + pageEscape(note) + '</p>' : '') + '<ul>' +
    errors.map(function (e) {
      return '<li><code>' + pageEscape(e.file) + ':' + pageEscape(e.line) + '</code> <b>' + pageEscape(e.field) + '</b>: ' +
        pageEscape(e.message) + (e.by ? ' <span class="by">written by ' + pageEscape(e.by) + '</span>' : '') + '</li>';
    }).join('') + '</ul>';
}
// Shows the band in EL, and hides it when there is none. It is written only when its text changes: it is a live
// region, and a rewrite at every poll would be read out every time.
function pageShowErrors(el, errors, note) {
  var html = pageErrors(errors, note);
  el.hidden = !html;
  if (el.innerHTML !== html) el.innerHTML = html;
}

// The agents at work, as the list items of `<ul class="agents" id="agents">`: one row for each agent in ROWS, from any
// board; the page reads no log, the board says what each agent does. A row is
//   who      the agent's name            what    what it works on
//   state    the word of its chip, "Working" when none     since   when the work began: the chip adds its age
//   last     when the agent last wrote a record (its last word): from O.quietAfter seconds on, the row says there was no
//            word from it. The threshold is the server's, `quiet_after` in the page's data.
//   second   true for a second try      note    one more line for the row, in the error colour
//   data     data attributes (name to value): the row is then a button that carries them
//   kind     "verifier" for an agent that checks what others wrote: its edge is moss, not terracotta
// A time is an ISO string or a number of milliseconds. O.now is the page's clock in seconds (the server's), O.empty the
// line when there are no rows. Without O.quietAfter no row says it was quiet.
function pageAgents(rows, o) {
  var now = o.now * 1000;
  // The whole minutes since AT, or null when AT or the clock is not a time: the row then leaves that part out.
  function minutes(at) {
    var n = Math.floor((now - (typeof at === 'number' ? at : Date.parse(at))) / 60000);
    return isFinite(n) ? Math.max(0, n) : null;
  }
  if (!rows.length) return '<li class="muted">' + pageEscape(o.empty) + '</li>';
  return rows.map(function (r) {
    var attrs = Object.keys(r.data || {}).map(function (k) { return ' data-' + pageEscape(k) + '="' + pageEscape(r.data[k]) + '"'; }).join('');
    var tag = (r.data ? 'button type="button"' : 'div') + (r.kind ? ' class="' + pageEscape(r.kind) + '"' : '') + attrs;
    var age = r.since != null ? minutes(r.since) : null, quiet = r.last != null ? minutes(r.last) : null;
    return '<li><' + tag + '><b>' + pageEscape(r.who) + '</b><span dir="auto">' + pageEscape(r.what) + '</span>' +
      (age !== null ? '<span class="chip working">' + pageEscape(r.state || 'Working') + ', ' + age + ' min</span>' : '') +
      (r.second ? '<em class="second">second try</em>' : '') +
      (quiet !== null && o.quietAfter > 0 && quiet * 60 >= o.quietAfter ? '<em class="dry">No word from ' + pageEscape(r.who) + ' for ' + quiet + ' min</em>' : '') +
      (r.note ? '<em class="dry">' + pageEscape(r.note) + '</em>' : '') +
      '</' + (r.data ? 'button' : 'div') + '></li>';
  }).join('');
}

// The details pop-up (.qpop) of a page, one at a time, over the page: it opens with its title in focus, keeps Tab inside
// and closes on Escape or on its ×; focus goes back to the element it opened from.
//   o.fill()          writes the pop-up's content into it, and again whenever the page's data changes
//   o.place(anchor)   puts it where it belongs, next to ANCHOR
//   o.modal           it is a modal dialog      o.opened(el), o.closed()   called after it opened and after it closed
// The page calls click(target) first in its click handler and key(event) in its keydown handler: each returns true when
// it took the event. `anchor` is the element the pop-up opened from, which the page may set again after a redraw.
function pagePopup(o) {
  var pop = { anchor: null };
  pop.el = function () { return document.getElementById('pop'); };
  pop.open = function (anchor) {
    pop.close();
    pop.anchor = anchor;
    var el = document.createElement('div');
    el.className = 'qpop'; el.setAttribute('role', 'dialog'); el.id = 'pop';
    if (o.modal) el.setAttribute('aria-modal', 'true');
    document.body.append(el);
    o.fill(); o.place(anchor);
    var h3 = el.querySelector('h3');
    if (h3) { h3.id = 'pop-title'; el.setAttribute('aria-labelledby', 'pop-title'); h3.setAttribute('tabindex', '-1'); h3.focus({ preventScroll: true }); }
    if (o.opened) o.opened(el);
  };
  pop.close = function () {
    var el = pop.el(), back = pop.anchor;
    if (el) el.remove();
    pop.anchor = null;
    if (back && document.contains(back)) back.focus({ preventScroll: true });
    if (o.closed) o.closed();
  };
  pop.click = function (target) {
    if (target.closest('.qpop .x')) { pop.close(); return true; }
    return !!target.closest('.qpop');
  };
  pop.key = function (ev) {
    var el = pop.el();
    if (!el) return false;
    if (ev.key === 'Tab' && el.contains(ev.target)) {
      var f = Array.prototype.slice.call(el.querySelectorAll('button, textarea, [tabindex]')), i = f.indexOf(ev.target);
      if (ev.shiftKey && i <= 0) { ev.preventDefault(); f[f.length - 1].focus(); return true; }
      if (!ev.shiftKey && i === f.length - 1) { ev.preventDefault(); f[0].focus(); return true; }
    }
    if (ev.key === 'Escape' && !(ev.target.closest && ev.target.closest('.why'))) { ev.preventDefault(); pop.close(); return true; }
    return false;
  };
  return pop;
}

// The colours of a pin by state, as page.css sets them, for a page that draws its pins in a document of its own, such
// as a frame: the rules of `.pin[data-state]` with CLASSNAME for `.pin`, and each var(--name) as VALUE(name) gives it.
// SHEETS is document.styleSheets.
function pagePinCss(sheets, className, value) {
  var css = '';
  Array.prototype.forEach.call(sheets, function (sheet) {
    var rules;
    try { rules = sheet.cssRules; } catch (e) { return; }  // a sheet from another origin
    Array.prototype.forEach.call(rules, function (rule) {
      if (rule.selectorText && rule.selectorText.indexOf('.pin[data-state') === 0) {
        css += rule.cssText.split('.pin[').join('.' + className + '[').replace(/var\((--[\w-]+)\)/g, function (_, name) { return value(name); });
      }
    });
  });
  return css;
}
