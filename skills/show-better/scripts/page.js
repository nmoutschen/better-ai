// The conversation between a served page and the agent: sending, the thread with its items, states and replies, the
// message box, and the live updates. Each skill whose page talks to the agent carries an identical copy of this file,
// as it does page.css and page.py, and the Scripts workflow fails if the copies differ: change it in one skill, then
// copy it to the others. The page's own script calls pageConversation with what only that page has, such as its pins.
//
// Every action is sent as it happens, as one JSON-RPC call, and the server keeps a log of them with the agent's
// replies. The page streams that log and rebuilds the conversation from it, so a reload or a new render loses nothing.
// State changes are also applied at once, and applying the same event twice changes nothing.
//
// o.served       the page is served over http; otherwise actions stay on the page (o.unsent says what to do with them)
// o.name         what the page is called in errors, such as 'canvas'
// o.apply(e, fresh)  apply one event to the page's own model, such as its pins; fresh when the user just sent it
// o.byId(id)     the page's own model of a comment, or nothing once it is deleted
// o.crumb(e)     where a comment was made; o.commentBody(e) what it says
// o.reveal(e), o.edit(it, button), o.remove(it), o.showLabel(n)   the comment's Show, Edit and Delete
// o.kinds        renderers for the page's own kinds of event, such as { decide: function (c) { return li; } }
// o.itemKinds    the user's actions the agent tracks with a state (default comment and note)
// o.noteParams() what a message carries besides its words, such as the current slide
// o.sendMode()   a function to run instead of sending a message when the Send button is pressed, or null
// o.busy()       the page has something open the user would lose on a reload
// o.beforeReload()  keep the page's place before a new render loads
// o.rendered(state)  called after each redraw with every item's state, to sync the pins
function pageConversation(o) {
  var rpcId = 0, log = [], state = {}, itemKinds = o.itemKinds || ['comment', 'note'], kinds = o.kinds || {};
  function el(tag, cls, text) { var x = document.createElement(tag); if (cls) x.className = cls; if (text != null) x.textContent = text; return x; }
  function time(at) { return (at || '').slice(11, 16); }
  var status = document.querySelector('.notes .status');
  function say(text, error) { status.textContent = text; status.classList.toggle('error', !!error); }
  // Every action shows a toast at the bottom of the window: sending, then sent or failed.
  var toast = document.querySelector('.toast'), toastTimer = null;
  function flash(text, kind) {
    clearTimeout(toastTimer);
    toast.textContent = text; toast.className = 'toast ' + (kind || ''); toast.hidden = false;
    if (kind !== 'error' && kind !== 'busy') toastTimer = setTimeout(function () { toast.hidden = true; }, 2500);
  }
  function send(method, params, what, done) {
    var event = Object.assign({ action: method, at: new Date().toISOString().slice(0, 19) }, params);
    o.apply(event, true);
    if (!o.served) { log.push(event); renderThread(); flash(what + ' saved on this page. ' + (o.unsent || ''), 'ok'); if (done) done(); return; }
    flash('Sending ' + what.toLowerCase() + '…', 'busy');
    fetch('/rpc', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jsonrpc: '2.0', id: ++rpcId, method: method, params: params }) })
      .then(function (r) { return r.json(); })
      .then(function (r) { if (r.error) throw new Error(r.error.message);
        flash('✓ ' + what + ' sent to the agent', 'ok'); say(''); if (done) done(); })
      .catch(function () { flash('Not sent: ' + what.toLowerCase() + '. The ' + o.name + ' is closed.', 'error');
        say('Not sent: the ' + o.name + ' is closed. Ask the agent to restart it.', true); });
  }

  // ---------- The thread: everything sent and every reply, in order; a comment shows once, in its latest state ----------
  var thread = document.querySelector('.thread');
  // A reply that names the message it answers is shown under that message, so the user sees what was answered.
  function replyBlock(e) {
    var mine = e.action === 'reopen' || e.action === 'note', r = el('div', mine ? 'reply mine' : 'reply'), h = el('div', 'head');
    h.append(el('span', 'who', mine ? 'You' : 'Agent'), el('span', 'when', time(e.at)));
    if (e.action === 'reopen') h.append(el('span', 'progress reopened', 'Reopened'));
    r.append(h, el('p', 'body', e.action === 'reopen' ? e.reason : e.action === 'note' ? e.note : e.text));
    return r;
  }
  var filter = 'open', scrolledOnce = false;
  document.querySelectorAll('[data-filter]').forEach(function (b) {
    b.addEventListener('click', function () {
      filter = b.dataset.filter;
      document.querySelectorAll('[data-filter]').forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); });
      renderThread();
    });
  });
  var STEPS = ['seen', 'working', 'done', 'accepted'],
      LABEL = { seen: 'Seen', asked: 'Waiting for you', replied: 'You answered', followup: 'You replied', working: 'Working on it', done: 'Done', accepted: 'Accepted', reopened: 'Reopened' };
  // The box for an answer or a reply, under the item. The button that opened it hides in place while it is open, and
  // the box goes only once the message is sent.
  function reasonBox(li, id, label, from) {
    if (li.querySelector('.why')) return li.querySelector('.why textarea').focus();
    var box = el('div', 'why'), ta = el('textarea'), row = el('div', 'row2'),
        ok = el('button', 'btn btn--sm', 'Send'), no = el('button', 'btn btn--quiet btn--sm', 'Cancel');
    ta.setAttribute('aria-label', label); ta.placeholder = label;
    ok.type = no.type = 'button';
    if (from) from.style.visibility = 'hidden';
    function close() { box.remove(); if (from) from.style.visibility = ''; }
    function sendIt() {
      var r = ta.value.trim(); if (!r) return ta.focus();
      send('note', { id: 'm-' + Date.now().toString(36), to: id, note: r }, label === 'Your answer' ? 'Answer' : 'Reply', function () {
        close(); li.setAttribute('tabindex', '-1'); li.focus({ preventScroll: true });
      });
    }
    ok.addEventListener('click', sendIt); no.addEventListener('click', close);
    ta.addEventListener('keydown', function (k) { if (k.key === 'Enter' && !k.shiftKey) { k.preventDefault(); sendIt(); } if (k.key === 'Escape') close(); });
    row.append(ok, no); box.append(ta, row); li.append(box); box.scrollIntoView({ block: 'nearest' }); ta.focus();
  }
  // The progress mark: four short bars fill as the agent sees an item, works on it, finishes it and the user accepts it.
  // Before the agent sets a state, the bars are empty and the word is Sent.
  function progressChip(st) {
    var k = !st ? -1 : st === 'asked' || st === 'replied' || st === 'followup' ? 0 : STEPS.indexOf(st), chip = el('span', 'progress' + (st ? ' ' + st : '')), bars = el('span', 'bars');
    for (var j = 0; j < 4; j++) bars.append(el('i', j <= k ? 'on' : ''));
    chip.append(bars, el('span', '', st ? LABEL[st] : 'Sent'));
    return chip;
  }
  function renderThread() {
    var stick = thread.scrollHeight - thread.scrollTop - thread.clientHeight < 40;
    var model = pageThread(log, itemKinds), entries = model.entries, open = model.open;
    state = model.state;
    // A box the user is typing in survives the redraw, with its text and cursor, and keeps its item on the page until
    // it is sent or cancelled, even when the item has left Open meanwhile.
    var kept = {};
    thread.querySelectorAll('li[data-id] > .why').forEach(function (box) {
      var ta = box.querySelector('textarea');
      kept[box.parentNode.dataset.id] = { box: box, focus: document.activeElement === ta, start: ta.selectionStart, end: ta.selectionEnd };
    });
    document.querySelector('[data-filter="open"]').textContent = 'Open (' + open.length + ')';
    if (filter === 'open') entries = entries.filter(function (c) { return open.indexOf(c) >= 0 || (c.e.id && kept[c.e.id]); });
    thread.replaceChildren();
    // Before anything is sent, both views say how to start; after, Open says when nothing is left.
    var started = log.some(function (x) { return x.action && x.action !== 'status'; });
    document.querySelector('.notes .empty').hidden = started;
    entries.forEach(function (c) {
      var e = c.e, li, head;
      if (c.kind === 'comment') {
        li = el('li', 'msg me comment' + (c.deleted ? ' deleted' : ''));
        head = el('div', 'head'); head.append(el('span', 'n', e.n || '?'), el('span', 'who', 'You'), el('span', 'when', time(e.at) + (c.edited ? ', edited' : '')));
        var it = o.byId(e.id);
        if (it && !c.deleted && state[e.id] !== 'done' && state[e.id] !== 'accepted') {
          var where = el('button', 'link', 'Show'), edit = el('button', 'link', 'Edit'), del = el('button', 'link', 'Delete');
          where.type = edit.type = del.type = 'button';
          where.setAttribute('aria-label', o.showLabel(e.n)); edit.setAttribute('aria-label', 'Edit comment ' + e.n); del.setAttribute('aria-label', 'Delete comment ' + e.n);
          where.addEventListener('click', function () { o.reveal(e); });
          edit.addEventListener('click', function () { o.reveal(e); o.edit(it, edit); });
          del.addEventListener('click', function () { o.remove(it); });
          head.append(where, edit, del);
        }
        li.append(head, o.crumb(e), c.deleted ? el('p', 'body', 'Deleted') : o.commentBody(e));
      } else if (c.kind === 'note') {
        li = el('li', 'msg me'); head = el('div', 'head'); head.append(el('span', 'who', 'You'), el('span', 'when', time(e.at)));
        li.append(head, el('p', 'body', e.note));
      } else if (c.kind === 'reply') {
        li = el('li', 'msg agent'); li.append(replyBlock(e));
      } else if (kinds[c.kind]) {
        li = kinds[c.kind](c);
      } else return;
      c.replies.forEach(function (r) { li.append(replyBlock(r)); });
      if (c.kind === 'reply' && e.id) {  // the agent's own messages can be answered too; the state row closes them
        var rf = el('div', 'foot'), mine = c.replies.filter(function (r) { return r.action === 'note'; }), last = mine[mine.length - 1];
        if (last) rf.append(progressChip(state[last.id]));
        var rb = el('button', 'btn btn--quiet btn--sm answer', 'Reply'); rb.type = 'button';
        rb.addEventListener('click', function () { reasonBox(li, e.id, 'Your reply', rb); });
        rf.append(rb); li.append(rf);
      }
      // The state and what the user can do with it close the item, after the latest reply, where the eye ends.
      if (itemKinds.indexOf(c.kind) >= 0) {
        var foot = el('div', 'foot');
        foot.append(progressChip(state[e.id]));
        // A done item is accepted with the brown check next to Reply; replying instead puts it back with the agent.
        if (state[e.id] === 'done') {
          var ok = el('button', 'btn btn--sm answer', '✓'); ok.type = 'button'; ok.title = 'Accept'; ok.setAttribute('aria-label', 'Accept');
          ok.addEventListener('click', function () { send('accept', { to: e.id }, 'Acceptance', function () { li.setAttribute('tabindex', '-1'); li.focus({ preventScroll: true }); }); });
          foot.append(ok);
        }
        // Every message can be answered: Answer when the agent asked something, Reply otherwise.
        var asked = state[e.id] === 'asked', ans = el('button', 'btn btn--sm answer' + (asked ? '' : ' btn--quiet'), asked ? 'Answer' : 'Reply');
        ans.type = 'button';
        ans.addEventListener('click', function () { reasonBox(li, e.id, asked ? 'Your answer' : 'Your reply', ans); });
        foot.append(ans);
        li.append(foot);
        if (state[e.id]) li.dataset.state = state[e.id];
      }
      if (e.id) {
        li.dataset.id = e.id;
        var k = kept[e.id];
        if (k) { li.append(k.box); li.querySelectorAll('.foot .answer').forEach(function (b) { b.style.visibility = 'hidden'; }); }
      }
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

  // ---------- The message box ----------
  var noteBox = document.querySelector('#note'), noteBtn = document.querySelector('.notes .send .btn');
  function sendNote() {
    var note = noteBox.value.trim();
    if (!note) { noteBox.focus(); return; }
    send('note', Object.assign({ id: 'm-' + Date.now().toString(36), note: note }, o.noteParams ? o.noteParams() : {}), 'Message', function () { noteBox.value = ''; });
  }
  function mode() { return o.sendMode ? o.sendMode() : null; }
  noteBtn.addEventListener('click', function () { (mode() || sendNote)(); });
  noteBox.addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey && !mode()) { e.preventDefault(); sendNote(); } });

  // ---------- Live updates ----------
  function busy() {
    return !!noteBox.value.trim() || (o.busy && o.busy()) ||
      Array.prototype.some.call(document.querySelectorAll('.why textarea'), function (t) { return !!t.value.trim(); });
  }
  function start() {
    renderThread();
    if (!o.served) return;
    // After two failed polls in a row, a strip under the bar says the agent's server stopped; it goes when it answers again.
    var offline = document.querySelector('.offline'), misses = 0;
    function connected(on) { misses = on ? 0 : misses + 1; offline.hidden = on || misses < 2; }
    (function stream(after) {
      fetch('/events?after=' + after).then(function (r) { return r.json(); }).then(function (r) {
        connected(true);
        r.events.forEach(function (e) { log.push(e); o.apply(e, false); });
        // A new reply from the agent is announced once, in the toast, which screen readers read as a status.
        if (after > 0) r.events.forEach(function (e) { if (e.action === 'reply') flash('Agent: ' + e.text.slice(0, 120), 'ok'); });
        if (r.events.length) renderThread();
        stream(r.total);
      }).catch(function () { connected(false); setTimeout(function () { stream(after); }, 2000); });
    })(0);
    // A new render from the agent loads by itself, as soon as the user is not typing: a comment, a message or an answer
    // in progress would be lost. The page keeps its place through o.beforeReload.
    var rev = null;
    (function poll() {
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
      }).catch(function () { unwatched.hidden = true; }).then(function () { setTimeout(watch, 2000); });
    })();
  }

  return {
    send: send, say: say, flash: flash, reopen: reopen, render: renderThread, start: start, noteBox: noteBox, noteBtn: noteBtn,
    log: function () { return log; }, state: function () { return state; }
  };
}

// The thread as the log makes it, without the page: each item's state, the entries in the order they show, with the
// replies under them, and the entries Open lists. Kept apart from the drawing so it can be tested without a browser.
function pageThread(log, itemKinds) {
  var entries = [], byKey = {}, state = {};
  log.forEach(function (e) {
    if (e.action === 'status') state[e.to] = e.status;
    else if (e.action === 'accept') state[e.to] = 'accepted';
    else if (e.action === 'reopen') state[e.to] = 'reopened';
    // The user's answer to a question from the agent ends the wait: the item goes back to the agent.
    else if (e.action === 'note' && e.to && state[e.to] === 'asked') state[e.to] = 'replied';
    // A reply under a finished item is a follow-up: the item goes back to the agent.
    else if (e.action === 'note' && e.to && (state[e.to] === 'done' || state[e.to] === 'accepted')) state[e.to] = 'followup';
  });
  log.forEach(function (e) {
    if (e.action === 'comment' || e.action === 'delete') {
      var c = byKey[e.id];
      if (!c) { if (e.action === 'delete') return; c = byKey[e.id] = { kind: 'comment', e: e, edited: false, deleted: false, replies: [] }; entries.push(c); }
      else if (e.action === 'delete') c.deleted = true;
      else { c.e = e; c.edited = true; c.deleted = false; }
    } else if ((e.action === 'reply' || (e.action === 'reopen' && e.reason) || (e.action === 'note' && e.to)) && e.to && byKey[e.to]) { byKey[e.to].replies.push(e); if (e.id) byKey[e.id] = byKey[e.to]; }
    else if (e.action === 'accept' || e.action === 'reopen' || e.action === 'status') return;
    else { var n = { kind: e.action, e: e, replies: [] }; if (e.id) byKey[e.id] = n; entries.push(n); }
  });
  // A message the agent sent on its own, a question, waits for the user until they answer it: it counts as open and
  // comes last, next to the message box.
  function waiting(c) { return c.kind === 'reply' && !c.e.to && c.e.id && !c.replies.some(function (r) { return r.action === 'note'; }); }
  entries = entries.filter(function (c) { return !waiting(c); }).concat(entries.filter(waiting));
  // Open: the user's items not yet accepted, with what was said under them, and the agent's waiting questions.
  var open = entries.filter(function (c) {
    return (itemKinds.indexOf(c.kind) >= 0 && c.e.id && !c.deleted && state[c.e.id] !== 'accepted') || waiting(c);
  });
  return { state: state, entries: entries, open: open };
}
