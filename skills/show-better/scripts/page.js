// The conversation between a served page and the agent: sending, the thread with its items, states and replies, the
// message box, and the live updates. Each skill whose page talks to the agent carries an identical copy of this file,
// as it does page.css and page.py, and the Scripts workflow fails if the copies differ: change it in one skill, then
// copy it to the others. The page's own script calls pageConversation with what only that page has, such as its pins.
//
// Every action is sent as it happens, as one JSON-RPC call, and the server keeps a log of them with the agent's
// replies. The page streams that log, or feeds it with setLog, and rebuilds the conversation from it, so a reload or a
// new render loses nothing. State changes are also applied at once, and applying the same event twice changes nothing.
//
// o.served       the page is served over http; otherwise actions stay on the page (o.unsent says what to do with them)
// o.name         what the page is called in errors, such as 'canvas'; o.agent what the agent is called (default Agent)
// o.apply(e, fresh)  apply one event to the page's own model, such as its pins; fresh when the user just sent it
// o.byId(id)     the page's own model of a comment, which offers Show, Edit and Delete; nothing when it offers none
// o.crumb(e)     where a comment was made; o.commentBody(e) what it says
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
// o.noteParams() what a message carries besides its words, such as the current slide
// o.sendMode()   a function to run instead of sending a message when the Send button is pressed, or null
// o.busy()       the page has something open the user would lose on a reload
// o.beforeReload()  keep the page's place before a new render loads
// o.rendered(state)  called after each redraw with every item's state, to sync the pins
function pageConversation(o) {
  var rpcId = 0, log = [], state = {}, fed = null, itemKinds = o.itemKinds || ['comment', 'note'], kinds = o.kinds || {};
  var agentKinds = o.agentKinds || ['reply'], agent = o.agent || 'Agent', accept = o.accept !== false, filtering = o.filter !== false;
  function el(tag, cls, text) { var x = document.createElement(tag); if (cls) x.className = cls; if (text != null) x.textContent = text; return x; }
  function time(at) { return (at || '').slice(11, 16); }
  var status = document.querySelector('.notes .status');
  function say(text, error) { if (!status) return; status.textContent = text; status.classList.toggle('error', !!error); }
  // Every action shows a toast at the bottom of the window: sending, then sent or failed.
  var toast = document.querySelector('.toast'), toastTimer = null;
  function flash(text, kind) {
    clearTimeout(toastTimer);
    toast.textContent = text; toast.className = 'toast ' + (kind || ''); toast.hidden = false;
    if (kind !== 'error' && kind !== 'busy') toastTimer = setTimeout(function () { toast.hidden = true; }, 2500);
  }
  // DONE runs once the server saved the action; FAIL when it could not, such as to enable a button again.
  function send(method, params, what, done, fail) {
    if (o.readOnly) return;
    var event = Object.assign({ action: method, at: new Date().toISOString().slice(0, 19) }, params);
    if (o.apply) o.apply(event, true);
    if (!o.served) { log.push(event); renderThread(); flash(what + ' saved on this page. ' + (o.unsent || ''), 'ok'); if (done) done(); return; }
    flash('Sending ' + what.toLowerCase() + '…', 'busy');
    fetch('/rpc', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jsonrpc: '2.0', id: ++rpcId, method: method, params: params }) })
      .then(function (r) { return r.json(); })
      .then(function (r) { if (r.error) throw new Error(r.error.message);
        flash('✓ ' + what + ' sent to the ' + agent.toLowerCase(), 'ok'); say(''); if (done) done(); if (o.afterSend) o.afterSend(); })
      .catch(function () { flash('Not sent: ' + what.toLowerCase() + '. The ' + o.name + ' is closed.', 'error');
        say('Not sent: the ' + o.name + ' is closed. Ask the agent to restart it.', true); if (fail) fail(); });
  }

  // ---------- The thread: everything sent and every reply, in order; a comment shows once, in its latest state ----------
  var thread = o.thread || document.querySelector('.thread');
  function body(text) { return pageMarkdown(text); }
  function head(who, at) { var h = el('div', 'head'); h.append(el('span', 'who', who), el('span', 'when', time(at))); return h; }
  // A reply that names the message it answers is shown under that message, so the user sees what was answered.
  function replyBlock(e) {
    var mine = e.action !== 'reply', r = el('div', mine ? 'reply mine' : 'reply'), h = head(mine ? 'You' : agent, e.at);
    if (e.action === 'reopen') h.append(el('span', 'progress reopened', 'Reopened'));
    r.append(h, body(e.action === 'reopen' ? e.reason : pageWords(e)));
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
      LABEL = Object.assign({ seen: 'Seen', asked: 'Waiting for you', replied: 'You answered', followup: 'You replied', working: 'Working on it', done: 'Done', accepted: 'Accepted', reopened: 'Reopened' }, o.labels || {});
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
      send('note', { id: 'm-' + Date.now().toString(36), to: id, note: r }, label === 'Your answer' ? 'Answer' : 'Reply', done);
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
      li = el('li', 'msg me'); li.append(head('You', e.at), body(pageWords(e)));
    } else if (c.kind === 'reply') {
      li = el('li', 'msg agent'); li.append(replyBlock(e));
    } else if (kinds[c.kind]) {
      var made = kinds[c.kind](c, state, actions);
      if (Array.isArray(made)) { li = made[0]; foot = made[1]; } else li = made;
    } else return null;
    c.replies.forEach(function (r) { li.append(replyBlock(r)); });
    if (foot) li.append(foot);
    if (agentKinds.indexOf(c.kind) >= 0 && e.id && actions) {  // the agent's own messages can be answered too; the state row closes them
      var rf = el('div', 'foot'), mine = c.replies.filter(function (r) { return r.action === 'note'; }), last = mine[mine.length - 1];
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
    var started = log.some(function (x) { return x.action && x.action !== 'status'; });
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
    send('note', Object.assign({ id: 'm-' + Date.now().toString(36), note: note }, o.noteParams ? o.noteParams() : {}), 'Message', function () { noteBox.value = ''; });
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
  function start() {
    renderThread();
    if (!o.served || o.stream === false) return;
    // After two failed polls in a row, a strip under the bar says the agent's server stopped; it goes when it answers again.
    var offline = document.querySelector('.offline'), misses = 0;
    function connected(on) { misses = on ? 0 : misses + 1; offline.hidden = on || misses < 2; }
    (function stream(after) {
      fetch('/events?after=' + after).then(function (r) { return r.json(); }).then(function (r) {
        connected(true);
        r.events.forEach(function (e) { log.push(e); if (o.apply) o.apply(e, false); });
        // A new reply from the agent is announced once, in the toast, which screen readers read as a status.
        if (after > 0) r.events.forEach(function (e) { if (e.action === 'reply') flash(agent + ': ' + e.text.slice(0, 120), 'ok'); });
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
    send: send, say: say, flash: flash, reopen: reopen, render: renderThread, start: start, setLog: setLog, nodes: nodes,
    box: reasonBox, progress: progressChip, noteBox: noteBox, noteBtn: noteBtn,
    log: function () { return log; }, state: function () { return state; }
  };
}

// A message's words: the canvas and the slides send them as "note", the research board as "text" before it shared this.
function pageWords(e) { return e.note != null ? e.note : e.text; }

// The thread as the log makes it, without the page: each item's state, the entries in the order they show, with the
// replies under them, and the entries Open lists. Kept apart from the drawing so it can be tested without a browser.
// WAITING(c, state) says which entries wait for the user and come last; by default, the agent's own question.
// LATESTLAST puts the entries in the order of their newest message, replies included, not of their first; the waiting
// ones still come last.
function pageThread(log, itemKinds, waiting, latestLast) {
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
  log.forEach(function (e, i) {
    // What an event answers: an answer to a decision names the decision; the rest name it in `to`.
    var to = e.action === 'answer' ? e.decision : e.to;
    if (e.action === 'comment' || e.action === 'delete') {
      var c = byKey[e.id];
      if (!c) { if (e.action === 'delete') return; c = byKey[e.id] = { kind: 'comment', e: e, edited: false, deleted: false, replies: [], last: i }; entries.push(c); }
      else if (e.action === 'delete') c.deleted = true;
      else { c.e = e; c.edited = true; c.deleted = false; }
    } else if ((e.action === 'reply' || e.action === 'answer' || (e.action === 'reopen' && e.reason) || (e.action === 'note' && to)) && to && byKey[to]) { byKey[to].replies.push(e); byKey[to].last = i; if (e.id) byKey[e.id] = byKey[to]; }
    else if (e.action === 'accept' || e.action === 'reopen' || e.action === 'status') return;
    else { var n = { kind: e.action, e: e, replies: [], last: i }; if (e.id) byKey[e.id] = n; entries.push(n); }
  });
  // A message the agent sent on its own, a question, waits for the user until they answer it: it counts as open and
  // comes last, next to the message box.
  if (latestLast) entries.sort(function (a, z) { return a.last - z.last; });
  var waits = waiting ? function (c) { return waiting(c, state); }
    : function (c) { return c.kind === 'reply' && !c.e.to && c.e.id && !c.replies.some(function (r) { return r.action === 'note'; }); };
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
var MD_HEADING = /^ {0,3}(#{1,6})[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$/, MD_QUOTE = /^ {0,3}> ?/, MD_TABLE_RULE = /^[ \t]*\|?[ \t]*:?-+:?[ \t]*(\|[ \t]*:?-+:?[ \t]*)*\|?[ \t]*$/;
function mdIndent(line) { return line.match(/^[ \t]*/)[0].replace(/\t/g, '    ').length; }
function mdCells(line) {
  return line.trim().replace(/^\|/, '').replace(/\|$/, '').split(/(?<!\\)\|/).map(function (c) { return c.trim().replace(/\\\|/g, '|'); });
}
function mdTableStart(lines, i) {
  return lines[i].indexOf('|') >= 0 && i + 1 < lines.length && lines[i + 1].indexOf('|') >= 0 && MD_TABLE_RULE.test(lines[i + 1]) &&
    mdCells(lines[i + 1]).length === mdCells(lines[i]).length;
}
function mdStarts(lines, i) {
  var l = lines[i];
  return MD_FENCE.test(l) || MD_HEADING.test(l) || MD_RULE.test(l) || MD_QUOTE.test(l) || MD_ITEM.test(l) || mdTableStart(lines, i);
}
// The words of a block, with their marks. A code span keeps the marks in it as written, and so does a backslash.
var MD_INLINE = /(`+)([^`]|[^`][\s\S]*?[^`])\1(?!`)|\[([^\]]+)\]\(([^()\s]+)\)|\*\*(?=\S)([\s\S]*?\S)\*\*|~~(?=\S)([\s\S]*?\S)~~|\*(?=[^\s*])([\s\S]*?[^\s*\\])\*|(^|[^\w\\])_(?=[^\s_])([\s\S]*?[^\s_\\])_(?!\w)|(https?:\/\/[^\s<>]*[^\s<>.,;:!?'")\]*_])|\\([\\`*_{}\[\]()#+\-.!|~>])/g;
function mdInline(text) {
  var out = [], last = 0, m, re = new RegExp(MD_INLINE.source, 'g');
  function words(s) { if (!s) return; var prev = out[out.length - 1]; if (prev && prev.tag == null) prev.text += s; else out.push({ text: s }); }
  while ((m = re.exec(text))) {
    words(text.slice(last, m.index)); last = re.lastIndex;
    if (m[1]) out.push({ tag: 'code', children: [{ text: m[2].replace(/^ (.*) $/, '$1') }] });
    else if (m[3]) out.push(/^(https?:|mailto:)/i.test(m[4]) ? { tag: 'a', href: m[4], children: mdInline(m[3]).reduce(function (a, n) { return a.concat(n.tag === 'a' ? n.children : [n]); }, []) } : { text: m[0] });
    else if (m[5]) out.push({ tag: 'strong', children: mdInline(m[5]) });
    else if (m[6]) out.push({ tag: 'del', children: mdInline(m[6]) });
    else if (m[7]) out.push({ tag: 'em', children: mdInline(m[7]) });
    else if (m[9]) { words(m[8]); out.push({ tag: 'em', children: mdInline(m[9]) }); }
    else if (m[10]) out.push({ tag: 'a', href: m[10], children: [{ text: m[10] }] });
    else words(m[11]);  // an escaped mark is the mark as written
  }
  words(text.slice(last));
  return out;
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
      var fence = m[1], code = [];
      for (i++; i < lines.length && !(lines[i].trim().indexOf(fence) === 0 && !lines[i].trim().slice(fence.length).trim()); i++) code.push(lines[i]);
      i++; out.push({ tag: 'pre', children: [{ tag: 'code', children: [{ text: code.join('\n') }] }] });
    } else if ((m = line.match(MD_HEADING))) {
      out.push({ tag: 'p', cls: 'md-h', children: [{ tag: 'strong', children: mdInline(m[2]) }] }); i++;
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
        else if (ind >= base + 2 || (!blank && !mdStarts(lines, i))) {
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
      var para = [];
      for (; i < lines.length && lines[i].trim() && !(para.length && mdStarts(lines, i)); i++) {
        if (para.length) para.push({ tag: 'br' });
        para.push.apply(para, mdInline(lines[i].trim()));
      }
      out.push({ tag: 'p', children: para });
    }
  }
  return out;
}
function pageMarkdownTree(text) { return mdBlocks(String(text == null ? '' : text).replace(/\r\n?/g, '\n').split('\n')); }
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
