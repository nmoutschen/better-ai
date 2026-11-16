(function () {
  function el(tag, cls, text) { var x = document.createElement(tag); if (cls) x.className = cls; if (text != null) x.textContent = text; return x; }

  // ---------- Details: a label, mark or row that has a detail opens it under the visual ----------
  // The renderer writes data-d, the detail's number in the slide, on every label, mark and text-version row of an item
  // that has a detail, so two items with the same label keep their own details.
  function attachDetails(slide) {
    slide.querySelectorAll('[data-d]').forEach(function (node) {
      if (node.closest('.sr, .dts')) return;
      node.classList.add('has-detail'); node.dataset.dk = node.getAttribute('data-d');
      // Labels and rows take the keyboard; marks and boxes, drawn next to them, take only the pointer.
      if (node instanceof SVGGeometryElement || node.tagName.toLowerCase() === 'g') return;
      var d = slide.querySelector('.dts > .dt[data-k="' + node.dataset.dk + '"]');
      node.setAttribute('tabindex', '0'); node.setAttribute('role', 'button');
      if (d) node.setAttribute('aria-label', d.dataset.label + ': show detail');
    });
  }
  function openDetail(slide, node) {
    var box = slide.querySelector('.detail'), k = node.dataset.dk, d = slide.querySelector('.dts > .dt[data-k="' + k + '"]');
    if (!box || !d) return;
    var again = !box.hidden && box.dataset.k === k;
    slide.querySelectorAll('.has-detail.sel').forEach(function (x) { x.classList.remove('sel'); });
    if (again) { box.hidden = true; box.dataset.k = ''; return; }
    box.replaceChildren.apply(box, Array.prototype.map.call(d.childNodes, function (c) { return c.cloneNode(true); }));
    box.dataset.k = k; box.hidden = false;
    slide.querySelectorAll('[data-dk="' + k + '"]').forEach(function (x) { x.classList.add('sel'); });
  }
  function detailKeys(root, current, after) {
    root.addEventListener('keydown', function (e) {
      var h = e.target.closest && e.target.closest('[data-dk]');
      if (h && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); e.stopPropagation(); openDetail(current(), h); if (after) after(); }
    });
  }

  // ---------- The exported presentation: the slides alone, one filling the window ----------
  if (document.body.classList.contains('present')) {
    var deck = Array.prototype.slice.call(document.querySelectorAll('.deck > .slide')), at = 0, count = document.querySelector('.pcount');
    deck.forEach(attachDetails);
    var fit = function () {
      var s = deck[at]; s.style.transform = 'translate(-50%, -50%)';
      var k = Math.min(innerWidth / s.offsetWidth, innerHeight / s.offsetHeight) * 0.94;
      s.style.transform = 'translate(-50%, -50%) scale(' + k + ')';
    };
    var show = function (i) {
      at = Math.max(0, Math.min(deck.length - 1, i));
      deck.forEach(function (s, j) { s.classList.toggle('current', j === at); });
      count.textContent = (at + 1) + ' of ' + deck.length;
      history.replaceState(null, '', '#' + (at + 1));
      fit();
    };
    document.addEventListener('keydown', function (e) {
      if (e.target.closest && e.target.closest('[data-dk]') && (e.key === 'Enter' || e.key === ' ')) return;
      if (['ArrowRight', 'ArrowDown', 'PageDown', ' '].indexOf(e.key) >= 0) { e.preventDefault(); show(at + 1); }
      else if (['ArrowLeft', 'ArrowUp', 'PageUp'].indexOf(e.key) >= 0) { e.preventDefault(); show(at - 1); }
      else if (e.key === 'Home') show(0);
      else if (e.key === 'End') show(deck.length - 1);
      else if (e.key === 'f' || e.key === 'F') {
        if (document.fullscreenElement) document.exitFullscreen(); else if (document.documentElement.requestFullscreen) document.documentElement.requestFullscreen();
      }
    });
    detailKeys(document, function () { return deck[at]; }, fit);
    document.addEventListener('click', function (e) {
      var go = e.target.closest('[data-go]');
      if (go) { e.preventDefault(); return show(+go.dataset.go - 1); }
      var h = e.target.closest('[data-dk]');
      if (h) { openDetail(deck[at], h); return fit(); }  // a detail makes the slide taller: fit it again
      if (e.target.closest('a, .detail')) return;
      if (e.clientX < innerWidth / 3) show(at - 1); else if (e.clientX > innerWidth * 2 / 3) show(at + 1);
    });
    window.addEventListener('resize', fit);
    show((parseInt(location.hash.slice(1), 10) || 1) - 1);
    return;
  }

  // ---------- The page: the strip and one slide at a time ----------
  var body = document.body, served = location.protocol === 'http:';
  if (served) body.classList.add('live');
  var slides = Array.prototype.slice.call(document.querySelectorAll('.stage > .slide')), cur = 0;
  slides.forEach(attachDetails);
  var strip = document.querySelector('.strip'), groups = [];
  slides.forEach(function (s, i) {
    var g = groups[groups.length - 1], part = s.dataset.part || '';
    if (g && g.part === part) g.idx.push(i); else groups.push({ part: part, idx: [i] });
  });
  groups.forEach(function (g) {
    var li = el('li', 'grp'), segs = el('span', 'segs');
    li.style.flexGrow = g.idx.length;
    li.append(el('span', 'pname', g.part), segs);
    g.idx.forEach(function (i) {
      var b = el('button', '', String(i + 1)); b.type = 'button';
      b.title = slides[i].dataset.headline;
      b.setAttribute('aria-label', 'Slide ' + (i + 1) + ': ' + slides[i].dataset.headline);
      b.addEventListener('click', function () { go(i); });
      segs.append(b);
    });
    g.el = li; strip.append(li);
  });
  var segButtons = strip.querySelectorAll('.segs button'), prev = document.querySelector('.route .prev'), next = document.querySelector('.route .next');
  var count = document.querySelector('.route .count'), stage = document.querySelector('.stage');
  function go(i) {
    cur = Math.max(0, Math.min(slides.length - 1, i));
    slides.forEach(function (s, j) { s.classList.toggle('current', j === cur); });
    segButtons.forEach(function (b, j) { if (j === cur) b.setAttribute('aria-current', 'step'); else b.removeAttribute('aria-current'); });
    groups.forEach(function (g) { g.el.classList.toggle('on', g.idx.indexOf(cur) >= 0); });
    count.textContent = (cur + 1) + ' of ' + slides.length;
    prev.disabled = cur === 0; next.disabled = cur === slides.length - 1;
    history.replaceState(null, '', '#' + (cur + 1));
    stage.scrollTop = 0;
    if (segButtons[cur].scrollIntoView) segButtons[cur].scrollIntoView({ block: 'nearest', inline: 'nearest' });
  }
  prev.addEventListener('click', function () { go(cur - 1); });
  next.addEventListener('click', function () { go(cur + 1); });
  function typing(t) { return t.closest && t.closest('input, textarea, select, [contenteditable]'); }
  document.addEventListener('keydown', function (e) {
    if (typing(e.target) || !pop.hidden || e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.key === 'ArrowRight' || e.key === 'PageDown') { e.preventDefault(); go(cur + 1); }
    else if (e.key === 'ArrowLeft' || e.key === 'PageUp') { e.preventDefault(); go(cur - 1); }
    else if (e.key === 'Home') { e.preventDefault(); go(0); }
    else if (e.key === 'End') { e.preventDefault(); go(slides.length - 1); }
    else if ((e.key === 'c' || e.key === 'C') && served) setMode(!commenting);
  });
  detailKeys(stage, function () { return slides[cur]; });

  // Export: the slides alone as one HTML presentation, with this page's styles and script, so it works offline
  // apart from the fonts.
  document.querySelector('.export').addEventListener('click', function () {
    var copies = slides.map(function (s) {
      var c = s.cloneNode(true);
      c.querySelectorAll('.pin').forEach(function (p) { p.remove(); });
      c.querySelectorAll('.sel').forEach(function (x) { x.classList.remove('sel'); });
      var d = c.querySelector('.detail'); if (d) { d.hidden = true; d.replaceChildren(); }
      c.classList.remove('current');
      return c.outerHTML;
    }).join('');
    var font = document.querySelector('link[rel="stylesheet"]'), title = document.title;
    var page = '<!DOCTYPE html>\n<html lang="' + document.documentElement.lang + '"><head><meta charset="utf-8">' +
      '<meta name="viewport" content="width=device-width, initial-scale=1"><title></title>' + (font ? font.outerHTML : '') +
      '<style>' + document.querySelector('style').textContent + '</style></head><body class="present"><main class="deck">' + copies +
      '</main><p class="pcount" aria-live="polite"></p><script>' + document.querySelector('script').textContent + '<\/script></body></html>';
    var doc = new DOMParser().parseFromString(page, 'text/html');
    doc.title = title;
    var blob = new Blob(['<!DOCTYPE html>\n' + doc.documentElement.outerHTML], { type: 'text/html' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = (title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 60) || 'slides') + '.html';
    document.body.append(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
    flash('Slides downloaded as one presentation', 'ok');
  });

  // ---------- Read and Comment ----------
  var commenting = false, pop = document.querySelector('.pop'), draft = null, opener = null;
  function choose(attr, value) {
    document.querySelectorAll('button[' + attr + ']').forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute(attr) === value)); });
  }
  // In the bar, a two-option setting shows only its current option; clicking it picks the other one.
  document.querySelectorAll('.controls > .seg.cycle').forEach(function (seg) {
    seg.addEventListener('click', function (e) {
      var b = e.target.closest('button'); if (!b || b.getAttribute('aria-pressed') !== 'true' || seg.dataset.cycling) return;
      var other = Array.prototype.filter.call(seg.querySelectorAll('button'), function (x) { return x !== b; })[0];
      if (!other) return;
      e.stopImmediatePropagation(); seg.dataset.cycling = '1'; other.click(); delete seg.dataset.cycling; other.focus();
    }, true);
  });
  function setMode(on) { commenting = on; choose('data-mode', on ? 'comment' : 'read'); body.classList.toggle('commenting', on); }
  document.querySelectorAll('button[data-mode]').forEach(function (b) {
    b.addEventListener('click', function () { setMode(b.dataset.mode === 'comment'); });
  });
  stage.addEventListener('click', function (e) {
    var slide = e.target.closest('.slide'); if (!slide) return;
    var pin = e.target.closest('.pin');
    if (pin) {  // a pin opens its comment, to read, change or delete it, in either mode
      e.preventDefault();
      var found = byId(pin.dataset.id);
      if (found && (pinState[found.id] === 'done' || pinState[found.id] === 'accepted')) conv.reopen(found.id);
      else if (found) openEdit(found, pin);
      return;
    }
    if (commenting) {
      e.preventDefault(); e.stopPropagation();
      if (!pop.hidden) return closePop();
      return openPop(slide, e.target, e.clientX, e.clientY);
    }
    var goto = e.target.closest('[data-go]');
    if (goto) { e.preventDefault(); return go(+goto.dataset.go - 1); }
    var h = e.target.closest('[data-dk]');
    if (h) openDetail(slide, h);
  }, true);
  function selectorOf(node, root) {
    var parts = [];
    while (node && node.nodeType === 1 && node !== root) {
      if (node.id) { parts.unshift('#' + CSS.escape(node.id)); break; }
      var tag = node.tagName.toLowerCase(), n = 1, sib = node;
      while ((sib = sib.previousElementSibling)) if (sib.tagName === node.tagName) n++;
      parts.unshift(tag + ':nth-of-type(' + n + ')');
      node = node.parentElement;
    }
    return parts.join(' > ');
  }
  // The label of the drawn item nearest the click: its own label when it has a detail, else the closest text.
  function nearestItem(target, x, y) {
    var h = target.closest('[data-dk]'), slide = target.closest('.slide');
    if (h) { var dt = slide.querySelector('.dts > .dt[data-k="' + h.dataset.dk + '"]'); if (dt) return dt.dataset.label; }
    var svg = target.closest('svg'); if (!svg) return null;
    var best = null, dist = Infinity;
    svg.querySelectorAll('text').forEach(function (t) {
      var r = t.getBoundingClientRect(), dx = Math.max(r.left - x, 0, x - r.right), dy = Math.max(r.top - y, 0, y - r.bottom), k = dx * dx + dy * dy;
      if (k < dist && t.textContent.trim()) { dist = k; best = t.textContent.replace(/\s+/g, ' ').trim(); }
    });
    return best;
  }
  function describe(slide, target, x, y) {
    var r = slide.getBoundingClientRect(), n = slides.indexOf(slide) + 1;
    return {
      slide: n, part: slide.dataset.part || '', headline: slide.dataset.headline || '',
      target: { tag: target.tagName.toLowerCase(), text: (target.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 160),
                item: nearestItem(target, x, y), selector: selectorOf(target, slide) },
      // Where the click fell, as fractions of the slide's width and height; yw, the height over the width, places the
      // pin so it stays on its spot when a detail opened below makes the slide taller.
      spot: { fx: Math.round((x - r.left) / Math.max(1, r.width) * 1000) / 1000, fy: Math.round((y - r.top) / Math.max(1, r.height) * 1000) / 1000,
              yw: Math.round((y - r.top) / Math.max(1, r.width) * 1000) / 1000 }
    };
  }
  // Two lines: where the comment is, small and muted, then what was clicked.
  function crumb(c) {
    var box = el('span', 'crumb'), t = c.target || {}, said = t.item || t.text || c.headline || '';
    box.append(el('span', 'path', 'Slide ' + c.slide + (c.part ? ' › ' + c.part : '')),
               el('span', 'el', said ? '“' + said.slice(0, 90) + (said.length > 90 ? '…' : '') + '”' : 'the slide'));
    return box;
  }
  function placePop(x, y) {
    pop.hidden = false;
    pop.style.left = Math.max(12, Math.min(x + 12, innerWidth - pop.offsetWidth - 12)) + 'px';
    pop.style.top = Math.max(12, Math.min(y + 12, innerHeight - pop.offsetHeight - 12)) + 'px';
    pop.querySelector('textarea').focus();
  }
  function openPop(slide, target, x, y) {
    draft = describe(slide, target, x, y);
    opener = document.activeElement !== document.body ? document.activeElement : null;
    pop.querySelector('.target').replaceChildren(crumb(draft));
    pop.querySelector('textarea').value = '';
    pop.querySelector('.remove').hidden = true; pop.querySelector('.ok').textContent = 'Send';
    placePop(x, y);
  }
  function openEdit(it, from) {
    var r = from.getBoundingClientRect();
    draft = { item: it, slide: it.slide, part: it.part, headline: it.headline, target: it.target, spot: it.spot };
    opener = from;
    pop.querySelector('.target').replaceChildren(crumb(it));
    pop.querySelector('textarea').value = it.comment || '';
    pop.querySelector('.remove').hidden = false; pop.querySelector('.ok').textContent = 'Update';
    placePop(r.left, r.bottom);
  }
  function closePop() { pop.hidden = true; draft = null; if (opener && document.contains(opener)) opener.focus(); opener = null; }
  document.addEventListener('mousedown', function (e) { if (!pop.hidden && !pop.contains(e.target) && !e.target.closest('.slide')) closePop(); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !pop.hidden) closePop(); });
  pop.querySelector('.cancel').addEventListener('click', closePop);
  pop.querySelector('.remove').addEventListener('click', function () { var it = draft && draft.item; closePop(); if (it) removeItem(it); });
  pop.querySelector('textarea').addEventListener('keydown', function (e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submitComment(); } });
  pop.querySelector('.ok').addEventListener('click', submitComment);
  function submitComment() {
    var text = pop.querySelector('textarea').value.trim();
    if (!draft || !text) { pop.querySelector('textarea').focus(); return; }
    var it = draft.item, n = it ? it.n : seq + 1, id = it ? it.id : 'c' + n + '-' + Date.now().toString(36);
    var params = { id: id, n: n, slide: draft.slide, part: draft.part, headline: draft.headline, target: draft.target, spot: draft.spot, comment: text };
    closePop();
    // An update reuses the comment's id, so the agent replaces the earlier version of it.
    send('comment', params, 'Comment ' + n + (it ? ' (updated)' : ''));
  }
  function removeItem(it) { send('delete', { id: it.id, n: it.n }, 'Deletion of comment ' + it.n); }

  // ---------- The conversation: page.js, shared with design-better's canvas; this page adds its pins and slides ----------
  var seq = 0, items = [], pinState = {};
  function byId(id) { return items.filter(function (x) { return x.id === id; })[0]; }
  function apply(e, fresh) {
    if (e.action === 'comment') {
      var it = byId(e.id);
      if (!it) { it = { id: e.id, n: e.n || seq + 1 }; seq = Math.max(seq, it.n); items.push(it); }
      Object.assign(it, { slide: e.slide, part: e.part, headline: e.headline, target: e.target || {}, spot: e.spot || { fx: 0.5, fy: 0.5 }, comment: e.comment || '' });
      placePin(it, fresh);
    } else if (e.action === 'delete') {
      items = items.filter(function (x) { return x.id !== e.id; });
      document.querySelectorAll('.pin[data-id="' + e.id + '"]').forEach(function (p) { p.remove(); });
    }
  }
  function placePin(it, fresh) {
    var slide = slides[(it.slide || 1) - 1]; if (!slide) return;
    var pin = slide.querySelector('.pin[data-id="' + it.id + '"]');
    if (!pin) { pin = el('span', 'pin'); pin.dataset.id = it.id; slide.append(pin); }
    pin.textContent = it.n;
    pin.style.left = (it.spot.fx * 100) + '%';
    pin.style.top = it.spot.yw != null ? (it.spot.yw * 100) + 'cqw' : (it.spot.fy * 100) + '%';
    pin.dataset.state = pinState[it.id] || 'new';
    pin.title = 'Comment ' + it.n + ': click to open it';
    if (fresh) { pin.classList.remove('flash'); void pin.offsetWidth; pin.classList.add('flash'); }
  }
  // Show a comment where it was made: its slide, with its pin flashing.
  function reveal(e) {
    go((e.slide || 1) - 1);
    var pin = slides[cur].querySelector('.pin[data-id="' + e.id + '"]'); if (!pin) return;
    pin.classList.remove('flash'); void pin.offsetWidth; pin.classList.add('flash');
    pin.scrollIntoView({ block: 'nearest' });
  }
  var KEY = 'show-mode:' + location.pathname;
  var conv = pageConversation({
    served: served, name: 'page', apply: apply, byId: byId, reveal: reveal, edit: openEdit, remove: removeItem,
    showLabel: function (n) { return 'Show comment ' + n + ' on its slide'; },
    crumb: crumb, commentBody: function (e) { return el('p', 'body', e.comment); },
    noteParams: function () { return { slide: cur + 1, part: slides[cur].dataset.part || '' }; },
    busy: function () { return !pop.hidden; },
    beforeReload: function () { sessionStorage.setItem(KEY, commenting ? 'comment' : 'read'); },
    rendered: function (state) { pinState = state; items.forEach(function (it) { placePin(it, false); }); }
  });
  function send(method, params, what, done) { conv.send(method, params, what, done); }
  function flash(text, kind) { conv.flash(text, kind); }

  try { if (sessionStorage.getItem(KEY) === 'comment' && served) setMode(true); sessionStorage.removeItem(KEY); } catch (e) {}
  go((parseInt(location.hash.slice(1), 10) || 1) - 1);
  if (served) conv.start();
})();
