// Every state the page gives an item, with the words of its progress mark. page.css colours a pin for each of them.
var PAGE_STATES = { new: 'Sent', seen: 'Seen', asked: 'Waiting for you', replied: 'You answered', followup: 'You replied',
  working: 'Working on it', done: 'Done', accepted: 'Accepted', reopened: 'Reopened' };

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
// o.kinds        renderers for the page's own kinds of event: function (c, state) returning the item, or [item, foot]
// o.itemKinds    the user's actions the agent tracks with a state (default comment and note)
// o.agentKinds   the agent's messages the user can reply to (default reply)
// o.steps, o.labels, o.shown(state)   the progress steps the page has, their words, and the step a state shows as
// o.accept       a done item offers Accept (default true); without it, a done item is finished
// o.filter       the thread has Open and All (default true); without it, one list in time order
// o.waiting(c, state)  an entry that waits for the user, shown last (default: the agent's own unanswered question)
// o.latestLast   order the items by their newest message, replies included, so the newest is at the bottom, waiting ones last (default: by first message)
// o.readOnly     a copy of the page to read: no actions
// o.stream       read the log from the server's /events (default true); otherwise the page calls setLog
// o.afterSend()  called once the server saved an action
// o.noteParams() what a message carries besides its words, such as the current slide; the page's events schema must allow it
// o.sendMode()   a function to run instead of sending a message when the Send button is pressed, or null
// o.busy()       the page has something open the user would lose on a reload
// o.beforeReload()  keep the page's place before a new render loads
// o.rendered(state)  called after each redraw with every item's state, to sync the pins
function pageConversation(o) {
  var rpcId = 0, log = [], state = {}, fed = null, itemKinds = o.itemKinds || ['comment', 'note'], kinds = o.kinds || {};
  var agentKinds = o.agentKinds || ['reply'], agent = o.agent || pageRole().replace(/^./, function (c) { return c.toUpperCase(); }), accept = o.accept !== false, filtering = o.filter !== false;
  function el(tag, cls, text) { var x = document.createElement(tag); if (cls) x.className = cls; if (text != null) x.textContent = text; return x; }
  function time(at) { return pageTime(at); }
  if (!filtering) { var seg = document.querySelector('.notes-top .seg'); if (seg) seg.remove(); }
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
    fetch('/rpc', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jsonrpc: '2.0', id: ++rpcId, method: method, params: params }) })
      .then(function (r) { return r.json(); })
      .then(function (r) {
        if (r.error) { var refused = new Error(r.error.message); refused.refused = true; throw refused; }
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

  // ---------- The thread: everything sent and every reply, in order; a comment shows once, in its latest state ----------
  var thread = o.thread || document.querySelector('.thread');
  function body(text) { return pageMarkdown(text); }
  function head(who, at) { var h = el('div', 'head'); h.append(el('span', 'who', who), el('span', 'when', time(at))); return h; }
  // A reply that names the message it answers is shown under that message, so the user sees what was answered.
  function replyBlock(e) {
    var mine = e.type !== 'reply', r = el('div', mine ? 'reply mine' : 'reply'), h = head(mine ? 'You' : agent, e.at);
    if (e.type === 'reopen') h.append(el('span', 'progress reopened', 'Reopened'));
    r.append(h, body(e.text));
    return r;
  }
  var filter = filtering ? 'open' : 'all', scrolledOnce = false;
  document.querySelectorAll('[data-filter]').forEach(function (b) {
    b.addEventListener('click', function () {
      filter = b.dataset.filter;
      document.querySelectorAll('[data-filter]').forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); });
      renderThread();
    });
  });
  var STEPS = o.steps || ['seen', 'working', 'done', 'accepted'],
      LABEL = Object.assign({}, PAGE_STATES, o.labels || {});
  // The box for an answer or a reply, under the item. The button that opened it hides in place while it is open, and
  // the box goes only once the message is sent. By default it sends a note under the item; onSend(text, done) sends
  // something else, such as the answer to a decision.
  function reasonBox(li, id, label, from, onSend) {
    if (li.querySelector('.why')) return li.querySelector('.why textarea').focus();
    var box = el('div', 'why'), ta = el('textarea'), row = el('div', 'row2'),
        ok = el('button', 'btn btn--sm', 'Send'), no = el('button', 'btn btn--quiet btn--sm cancel', 'Cancel');
    ta.setAttribute('aria-label', label); ta.placeholder = label;
    ok.type = no.type = 'button';
    if (from) from.style.visibility = 'hidden';
    // A redraw moves the box into a new item, whose own buttons it hid: show those again, not only the first one.
    function close() {
      var host = box.parentNode; box.remove(); if (from) from.style.visibility = '';
      var again = host ? host.querySelectorAll('.foot .answer, .foot .change') : [];
      again.forEach(function (b) { b.style.visibility = ''; });
      // Focus goes back to the button that opened the box, so a keyboard user who cancels stays at the item. After a
      // redraw that button is gone: its copy in the redrawn item takes the focus instead.
      if (from) { var back = document.contains(from) ? from : again[again.length - 1]; if (back) back.focus({ preventScroll: true }); }
    }
    function sendIt() {
      var r = ta.value.trim(); if (!r) return ta.focus();
      var done = function () { close(); li.setAttribute('tabindex', '-1'); li.focus({ preventScroll: true }); };
      if (onSend) return onSend(r, done);
      send('note', { id: 'm-' + Date.now().toString(36), to: id, text: r }, label === 'Your answer' ? 'Answer' : 'Reply', done);
    }
    ok.addEventListener('click', sendIt); no.addEventListener('click', close);
    ta.addEventListener('keydown', function (k) { if (k.key === 'Enter' && !k.shiftKey) { k.preventDefault(); sendIt(); } if (k.key === 'Escape') close(); });
    row.append(ok, no); box.append(ta, row); li.append(box); box.scrollIntoView({ block: 'nearest' }); ta.focus();
  }
  // The progress mark: a short bar per step fills as the agent sees an item, works on it, finishes it and the user
  // accepts it. Before the agent sets a state, the bars are empty and the word is Sent.
  function progressChip(st) {
    if (st && o.shown) st = o.shown(st);
    var k = !st ? -1 : st === 'asked' || st === 'replied' || st === 'followup' ? 0 : STEPS.indexOf(st), chip = el('span', 'progress' + (st ? ' ' + st : '')), bars = el('span', 'bars');
    bars.setAttribute('aria-hidden', 'true');
    for (var j = 0; j < STEPS.length; j++) bars.append(el('i', j <= k ? 'on' : ''));
    chip.append(bars, el('span', '', st ? LABEL[st] || st : 'Sent'));
    return chip;
  }
  // One entry of the thread; without actions, as in a copy to read or a list elsewhere on the page.
  function entryNode(c, actions) {
    var e = c.e, li, foot;
    if (c.kind === 'comment') {
      li = el('li', 'msg me comment' + (c.deleted ? ' deleted' : ''));
      var h = el('div', 'head');
      if (e.n) h.append(el('span', 'n', e.n));
      h.append(el('span', 'who', 'You'), el('span', 'when', time(e.at) + (c.edited ? ', edited' : '')));
      var it = actions && o.byId && o.byId(e.id);
      if (it && !c.deleted && state[e.id] !== 'done' && state[e.id] !== 'accepted') {
        var where = el('button', 'link', 'Show'), edit = el('button', 'link', 'Edit'), del = el('button', 'link', 'Delete');
        where.type = edit.type = del.type = 'button';
        where.setAttribute('aria-label', o.showLabel(e.n)); edit.setAttribute('aria-label', 'Edit comment ' + e.n); del.setAttribute('aria-label', 'Delete comment ' + e.n);
        where.addEventListener('click', function () { o.reveal(e); });
        edit.addEventListener('click', function () { o.reveal(e); o.edit(it, edit); });
        del.addEventListener('click', function () { o.remove(it); });
        h.append(where, edit, del);
      }
      li.append(h, o.crumb(e), c.deleted ? el('p', 'body', 'Deleted') : o.commentBody(e));
    } else if (c.kind === 'note') {
      li = el('li', 'msg me'); li.append(head('You', e.at), body(e.text));
    } else if (c.kind === 'reply') {
      li = el('li', 'msg agent'); li.append(replyBlock(e));
    } else if (kinds[c.kind]) {
      var made = kinds[c.kind](c, state, actions);
      if (Array.isArray(made)) { li = made[0]; foot = made[1]; } else li = made;
    } else return null;
    c.replies.forEach(function (r) { li.append(replyBlock(r)); });
    if (foot) li.append(foot);
    if (agentKinds.indexOf(c.kind) >= 0 && e.id && actions) {  // the agent's own messages can be answered too; the state row closes them
      var rf = el('div', 'foot'), mine = c.replies.filter(function (r) { return r.type === 'note'; }), last = mine[mine.length - 1];
      if (last) rf.append(progressChip(state[last.id]));
      var rb = el('button', 'btn btn--quiet btn--sm answer', 'Reply'); rb.type = 'button';
      rb.addEventListener('click', function () { reasonBox(li, e.id, 'Your reply', rb); });
      rf.append(rb); li.append(rf);
    }
    // The state and what the user can do with it close the item, after the latest reply, where the eye ends.
    if (itemKinds.indexOf(c.kind) >= 0) {
      var f = el('div', 'foot');
      f.append(progressChip(state[e.id]));
      // A done item is accepted with the brown check next to Reply; replying instead puts it back with the agent.
      if (actions && accept && state[e.id] === 'done') {
        var ok = el('button', 'btn btn--sm answer', '✓'); ok.type = 'button'; ok.title = 'Accept'; ok.setAttribute('aria-label', 'Accept');
        ok.addEventListener('click', function () { send('accept', { to: e.id }, 'Acceptance', function () { li.setAttribute('tabindex', '-1'); li.focus({ preventScroll: true }); }); });
        f.append(ok);
      }
      // Every message can be answered: Answer when the agent asked something, Reply otherwise.
      if (actions) {
        var asked = state[e.id] === 'asked', ans = el('button', 'btn btn--sm answer' + (asked ? '' : ' btn--quiet'), asked ? 'Answer' : 'Reply');
        ans.type = 'button';
        ans.addEventListener('click', function () { reasonBox(li, e.id, asked ? 'Your answer' : 'Your reply', ans); });
        f.append(ans);
      }
      li.append(f);
      if (state[e.id]) li.dataset.state = state[e.id];
    }
    if (e.id) li.dataset.id = e.id;
    return li;
  }
  function renderThread() {
    var stick = thread.scrollHeight - thread.scrollTop - thread.clientHeight < 40;
    var model = pageThread(log, itemKinds, o.waiting, o.latestLast), entries = model.entries, open = model.open;
    state = model.state;
    // A box the user is typing in survives the redraw, with its text and cursor, and keeps its item on the page until
    // it is sent or cancelled, even when the item has left Open meanwhile.
    var kept = {};
    thread.querySelectorAll('li[data-id] > .why').forEach(function (box) {
      var ta = box.querySelector('textarea');
      kept[box.parentNode.dataset.id] = { box: box, focus: document.activeElement === ta, start: ta.selectionStart, end: ta.selectionEnd };
    });
    if (filtering) document.querySelector('[data-filter="open"]').textContent = 'Open (' + open.length + ')';
    if (filter === 'open') entries = entries.filter(function (c) { return open.indexOf(c) >= 0 || (c.e.id && kept[c.e.id]); });
    thread.replaceChildren();
    // Before anything is sent, both views say how to start; after, Open says when nothing is left.
    var started = log.some(function (x) { return x.type && x.type !== 'status'; });
    document.querySelector('.notes .empty').hidden = started;
    entries.forEach(function (c) {
      var li = entryNode(c, !o.readOnly); if (!li) return;
      var k = c.e.id && kept[c.e.id];
      if (k) { li.append(k.box); li.querySelectorAll('.foot .answer, .foot .change').forEach(function (b) { b.style.visibility = 'hidden'; }); }
      thread.appendChild(li);
    });
    // Focus only once the box is back in the page: a detached element cannot take it.
    Object.keys(kept).forEach(function (id) {
      var k = kept[id], ta = k.box.querySelector('textarea');
      if (k.focus && document.contains(ta)) { ta.focus({ preventScroll: true }); ta.setSelectionRange(k.start, k.end); }
    });
    if (filter === 'open' && started && !entries.length) thread.appendChild(el('li', 'sys', 'Nothing open: you accepted everything.'));
    // The conversation opens on its latest message, and follows new ones while the user is at the bottom. The scroll
    // repeats on the next frame and once fonts load, which can make the thread taller after this render.
    if (stick || !scrolledOnce) {
      var bottom = function () { thread.scrollTop = thread.scrollHeight; };
      bottom(); requestAnimationFrame(bottom); if (document.fonts) document.fonts.ready.then(bottom);
      if (log.length) scrolledOnce = true;
    }
    if (o.rendered) o.rendered(state);
  }
  // Reply under a finished item from elsewhere on the page, such as its pin: the item comes into view with the box open.
  function reopen(id) {
    if (filter === 'open' && state[id] === 'accepted') document.querySelector('[data-filter="all"]').click();
    var li = thread.querySelector('li[data-id="' + id + '"]'); if (!li) return;
    li.scrollIntoView({ block: 'nearest' }); reasonBox(li, id, 'Your reply');
  }
  // The page's whole log, when the page reads it itself; KEY is anything else the entries show, such as a deadline.
  // The thread is redrawn only when either changed, so focus and selection stay put between polls.
  function setLog(events, key) {
    var next = JSON.stringify([events, key]);
    if (next === fed) return;
    fed = next; log = events.slice(); renderThread();
  }
  // The user's items that match, without actions, such as the comments on one question.
  function nodes(match) {
    return pageThread(log, itemKinds, o.waiting, o.latestLast).entries
      .filter(function (c) { return itemKinds.indexOf(c.kind) >= 0 && match(c.e); })
      .map(function (c) { return entryNode(c, false); });
  }

  // ---------- The message box ----------
  var noteBox = document.querySelector('#note'), noteBtn = document.querySelector('.notes .send .btn');
  function sendNote() {
    var note = noteBox.value.trim();
    if (!note) { noteBox.focus(); return; }
    send('note', Object.assign({ id: 'm-' + Date.now().toString(36), text: note, to: null }, o.noteParams ? o.noteParams() : {}), 'Message', function () { noteBox.value = ''; });
  }
  function mode() { return o.sendMode ? o.sendMode() : null; }
  if (noteBox && !o.readOnly) {
    noteBtn.addEventListener('click', function (e) { e.preventDefault(); (mode() || sendNote)(); });
    noteBox.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey && !mode()) { e.preventDefault(); sendNote(); } });
  }

  // ---------- Live updates ----------
  function busy() {
    return !!noteBox.value.trim() || (o.busy && o.busy()) ||
      Array.prototype.some.call(document.querySelectorAll('.why textarea'), function (t) { return !!t.value.trim(); });
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
      fetch('/old').then(function (r) { return r.json(); }).then(function (n) { oldNote(Number(n) || 0); })
        .catch(function () {}).then(function () { setTimeout(count, 5000); });
    })();
    // After two failed polls in a row, a strip under the bar says the agent's server stopped; it goes when it answers again.
    // A page that streams events counts the stream's polls; one that does not (stream: false) counts the /listening polls.
    var offline = document.querySelector('.offline'), misses = 0, streaming = o.stream !== false;
    function connected(on) { misses = on ? 0 : misses + 1; offline.hidden = on || misses < 2; }
    if (streaming) (function stream(after) {
      fetch('/events?after=' + after).then(function (r) { return r.json(); }).then(function (r) {
        connected(true);
        r.events.forEach(function (e) { log.push(e); if (o.apply) o.apply(e, false); });
        // A new reply from the agent is announced once, in the toast, which screen readers read as a status.
        if (after > 0) r.events.forEach(function (e) { if (e.type === 'reply') flash(agent + ': ' + pageMarkdownText(e.text).slice(0, 120), 'ok'); });
        if (r.events.length) renderThread();
        stream(r.total);
      }).catch(function () { connected(false); setTimeout(function () { stream(after); }, 2000); });
    })(0);
    // A new render from the agent loads by itself, as soon as the user is not typing: a comment, a message or an answer
    // in progress would be lost. The page keeps its place through o.beforeReload.
    var rev = null;
    if (streaming) (function poll() {
      fetch('/rev').then(function (r) { return r.text(); }).then(function (t) {
        if (rev === null) rev = t;
        else if (t !== rev && !busy()) {
          try { if (o.beforeReload) o.beforeReload(); } catch (e) {}
          location.reload();
        }
      }).catch(function () {}).then(function () { setTimeout(poll, 2000); });
    })();
    // Once the agent has used `wait`, a note above the message box says when no `wait` is connected: what the user
    // sends then reaches the agent only when it next looks. While the server is down, the offline strip says more.
    var unwatched = document.querySelector('.unwatched');
    (function watch() {
      fetch('/listening').then(function (r) { return r.json(); }).then(function (on) {
        unwatched.hidden = on !== false;
        if (!streaming) connected(true);
      }).catch(function () { unwatched.hidden = true; if (!streaming) connected(false); }).then(function () { setTimeout(watch, 2000); });
    })();
  }

  return {
    send: send, say: say, flash: flash, reopen: reopen, render: renderThread, start: start, setLog: setLog, nodes: nodes,
    box: reasonBox, progress: progressChip, noteBox: noteBox, noteBtn: noteBtn,
    log: function () { return log; }, state: function () { return state; }
  };
}

// The time of an event for the user: its UTC time (Z) as their own clock reads it, hours and minutes.
function pageTime(at) {
  if (!/Z$/.test(at || '')) return (at || '').slice(11, 16);
  var d = new Date(at);
  return isNaN(d) ? '' : ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2);
}

// The thread as the log makes it, without the page: each item's state, the entries in the order they show, with the
// replies under them, and the entries Open lists. Kept apart from the drawing so it can be tested without a browser.
// WAITING(c, state) says which entries wait for the user and come last; by default, the agent's own question.
// LATESTLAST puts the entries in the order of their newest message, replies included, not of their first; the waiting
// ones still come last.
function pageThread(log, itemKinds, waiting, latestLast) {
  var entries = [], byKey = {}, state = {}, items = {}, home = {};
  // The state of each item. A message under a reply belongs to the item that reply is under (HOME). pending in
  // src/better_ai/page/__init__.py follows the same rules; tests/fixtures/threads.json holds the logs both are run on.
  log.forEach(function (e) {
    var to = home[e.to] || e.to;
    if (e.type === 'status') state[e.to] = e.status;
    else if (e.type === 'accept' || e.type === 'accepted') state[e.to] = 'accepted';
    else if (e.type === 'reopen') state[e.to] = 'reopened';
    else if (e.type === 'note' && to) {
      // The user's answer to a question from the agent ends the wait: the item goes back to the agent.
      if (state[to] === 'asked') state[to] = 'replied';
      // A reply under a finished item is a follow-up: the item goes back to the agent.
      else if (state[to] === 'done' || state[to] === 'accepted') state[to] = 'followup';
      // An answer under an item is part of it; an answer to the agent's own message is an item.
      if (e.id) { if (items[to]) home[e.id] = to; else items[e.id] = true; }
    } else if (e.type === 'reply' && to && e.id) home[e.id] = to;
    else if (e.id && itemKinds.indexOf(e.type) >= 0) items[e.id] = true;
  });
  log.forEach(function (e, i) {
    // What an event answers: an answer to a decision names the decision; the rest name it in `to`.
    var to = e.type === 'answer' ? e.decision : e.to;
    if (e.type === 'comment' || e.type === 'delete') {
      var c = byKey[e.type === 'delete' ? e.to : e.id];
      if (!c) { if (e.type === 'delete') return; c = byKey[e.id] = { kind: 'comment', e: e, edited: false, deleted: false, replies: [], last: i }; entries.push(c); }
      else if (e.type === 'delete') c.deleted = true;
      else { c.e = e; c.edited = true; c.deleted = false; }
    } else if ((e.type === 'reply' || e.type === 'answer' || e.type === 'reopen' || (e.type === 'note' && to)) && to && byKey[to]) { byKey[to].replies.push(e); byKey[to].last = i; if (e.id) byKey[e.id] = byKey[to]; }
    else if (e.type === 'accept' || e.type === 'accepted' || e.type === 'reopen' || e.type === 'status') return;
    else { var n = { kind: e.type, e: e, replies: [], last: i }; if (e.id) byKey[e.id] = n; entries.push(n); }
  });
  // A message the agent sent on its own, a question, waits for the user until they answer it: it counts as open and
  // comes last, next to the message box.
  if (latestLast) entries.sort(function (a, z) { return a.last - z.last; });
  var waits = waiting ? function (c) { return waiting(c, state); }
    : function (c) { return c.kind === 'reply' && !c.e.to && c.e.id && !c.replies.some(function (r) { return r.type === 'note'; }); };
  entries = entries.filter(function (c) { return !waits(c); }).concat(entries.filter(waits));
  // Open: the user's items not yet accepted, with what was said under them, and the entries waiting for the user.
  var open = entries.filter(function (c) {
    return (itemKinds.indexOf(c.kind) >= 0 && c.e.id && !c.deleted && state[c.e.id] !== 'accepted') || waits(c);
  });
  return { state: state, entries: entries, open: open };
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
function pageDecision(o) {
  var conv = o.conversation;
  function status(x) { return String(x.status || 'decided').trim().toLowerCase(); }
  function answerOf(c) { return c.replies.filter(function (r) { return r.type === 'answer'; }).pop(); }
  // 0: the user is up (Waiting for you); 1: the user answered, the agent has not applied it; 2: applied; -1: no steps.
  function step(st, answer, state) {
    if (st !== 'waiting' && st !== 'answered') return -1;
    if (answer && state[answer.id] === 'asked') return 0;
    if (st === 'answered') return 2;
    return !answer ? 0 : (state[answer.id] === 'done' || state[answer.id] === 'accepted') ? 2 : 1;
  }
  function waiting(c, state) { return step(status(c.e.x), answerOf(c), state) === 0; }
  function left(x) { var t = Date.parse(x.deadline); return isNaN(t) ? null : t / 1000 - o.now(); }
  function deadlineWords(x) {
    var s = o.suggested ? null : left(x);
    if (s === null) return '';
    return s > 0 ? 'default in ' + (s < 90 ? 'under 2 min' : Math.round(s / 60) + ' min') : 'default due now';
  }
  // The open question after the one with id FROM, else the first before it: its ✓, or its Answer. Else what the page says
  // waits next, else another item the agent asked about. Nothing else waits: null.
  function nextWaiting(from) {
    var list = Array.prototype.slice.call(document.querySelectorAll('li.open-q')), i = -1, k;
    for (k = 0; k < list.length; k++) if (list[k].dataset.d === from) i = k;
    var others = list.slice(i + 1).concat(list.slice(0, Math.max(i, 0))).filter(function (q) { return q.dataset.d !== from; });
    if (others.length) { var q = others[0]; return { id: q.dataset.d, el: q.querySelector('.use') || q.querySelector('.answer') || q }; }
    var page = o.next && o.next();
    if (page) return { el: page };
    var asked = Array.prototype.slice.call(document.querySelectorAll('li[data-state="asked"]')).filter(function (q) { return q.dataset.d !== from && !/open-q/.test(q.className); });
    if (!asked.length) return null;
    asked[0].setAttribute('tabindex', '-1');
    return { el: asked[0] };
  }
  // The redraw after an answer replaces the nodes: the question to focus is focused again once it is drawn.
  var want = null;
  function focusNext(from) {
    var n = nextWaiting(from);
    if (!n) return;
    if (n.el.focus) n.el.focus({ preventScroll: true });
    if (n.id) want = n.id;
  }
  function head(who, label) {
    return '<div class="head"><span class="who">' + o.esc(who) + '</span><span class="when">' + o.esc(label) + '</span></div>';
  }
  function item(c, state, actions) {
    var x = c.e.x, st = status(x), answer = answerOf(c), n = step(st, answer, state), asked = n === 0;
    var steps = [['asked', 'Waiting for you'], ['replied', 'You answered'], ['done', 'Applied']], STEP = steps[n];
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
    li.dataset.state = STEP ? STEP[0] : '';
    var foot = document.createElement('div');
    foot.className = 'foot' + (asked ? ' question' : '');
    var q = String(x.asked || '').replace(/\s+/g, ' ').trim();
    if (STEP) foot.insertAdjacentHTML('beforeend', '<span class="progress ' + STEP[0] + '"><span class="bars" aria-hidden="true">' +
      [0, 1, 2].map(function (i) { return '<i class="' + (i <= n ? 'on' : '') + '"></i>'; }).join('') + '</span><span>' + STEP[1] + '</span></span>');
    else if (answer) foot.append(conv.progress(state[answer.id]));
    if (actions) {
      if (asked && x.default) {
        var use = document.createElement('button');
        use.type = 'button'; use.className = 'btn btn--sm answer use'; use.textContent = '✓'; use.title = 'Use the default';
        use.setAttribute('aria-label', 'Use the default for: ' + q);
        use.addEventListener('click', function () {
          use.disabled = true;
          conv.send('answer', { id: o.id('a'), decision: x.id, text: x.default, default: true }, 'Answer',
            function () { focusNext(x.id); }, function () { use.disabled = false; });
        });
        foot.append(use);
        if (want === x.id) { want = null; Promise.resolve().then(function () { use.focus({ preventScroll: true }); }); }
      }
      var change = document.createElement('button');
      change.type = 'button'; change.className = 'btn btn--sm btn--quiet answer change';
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
  return { item: item, waiting: waiting, status: status, answerOf: answerOf, step: step };
}

function pageDecisionEvents(decisions, conversation) {
  var entries = (decisions || []).map(function (x) { return { type: 'decision', id: x.id, x: x, at: x.at, _t: Date.parse(x.at) / 1000 || 0 }; });
  var when = {};
  entries.forEach(function (e) { when[e.id] = e._t; });
  var events = (conversation || []).map(function (e) {
    var t = Math.max(Date.parse(e.at) / 1000 || 0, when[e.type === 'answer' ? e.decision : e.to] || 0);
    if (e.id) when[e.id] = t;
    return Object.assign({}, e, { _t: t });
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
