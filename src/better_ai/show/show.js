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
  // Served, the page is the shared shell and the slides come from /data; opened as a file, they are in the page and
  // there is no conversation.
  var served = !!document.getElementById('page-config');
  if (!served) document.body.classList.add('static');
  var slides = [], cur = 0, commenting = false, comments = null, conv = null, items = [], seq = 0;
  var stage = document.querySelector('.stage'), pop = document.querySelector('.pop');
  var strip = document.querySelector('.strip'), prev = document.querySelector('.route .prev'), next = document.querySelector('.route .next');
  var count = document.querySelector('.route .count'), segButtons = [], groups = [];
  function popOpen() { return !!pop && !pop.hidden; }
  function say(text, kind) { if (conv) conv.flash(text, kind); else showToast(text); }
  function showToast(text) {
    var toast = document.querySelector('.toast'); if (!toast) return;
    toast.textContent = text; toast.className = 'toast ok'; toast.hidden = false;
    setTimeout(function () { toast.hidden = true; }, 2500);
  }

  function build() {
    slides = Array.prototype.slice.call(document.querySelectorAll('.stage > .slide'));
    slides.forEach(attachDetails);
    strip.replaceChildren(); groups = [];
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
    segButtons = strip.querySelectorAll('.segs button');
  }
  function go(i) {
    if (!slides.length) return;
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
    if (typing(e.target) || popOpen() || e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.key === 'ArrowRight' || e.key === 'PageDown') { e.preventDefault(); go(cur + 1); }
    else if (e.key === 'ArrowLeft' || e.key === 'PageUp') { e.preventDefault(); go(cur - 1); }
    else if (e.key === 'Home') { e.preventDefault(); go(0); }
    else if (e.key === 'End') { e.preventDefault(); go(slides.length - 1); }
    else if ((e.key === 'c' || e.key === 'C') && served) setMode(!commenting);
  });
  detailKeys(stage, function () { return slides[cur]; });

  // The controls in the bar: Read and Comment when served, and Export.
  var controls = el('div', 'controls'), status = document.getElementById('status');
  if (served) {
    var seg = el('div', 'seg cycle'); seg.setAttribute('role', 'group'); seg.setAttribute('aria-label', 'Mode');
    seg.innerHTML =
      '<button type="button" class="ico" data-mode="read" aria-pressed="true" title="Click a label or a mark to see its detail (C)"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 3l14 8-6 2-3 6z"/></svg><span>Read</span></button>' +
      '<button type="button" class="ico" data-mode="comment" aria-pressed="false" title="Click any part of a slide to comment on it (C)"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h16v12H9l-5 4z"/></svg><span>Comment</span></button>';
    controls.append(seg);
  }
  var exportButton = el('button', 'tool export');
  exportButton.type = 'button'; exportButton.title = 'Download the slides alone as one presentation';
  exportButton.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4v11M7 10l5 5 5-5M5 20h14"/></svg><span>Export</span>';
  controls.append(exportButton);
  if (status) { status.className = 'controls'; status.replaceChildren.apply(status, controls.childNodes); }

  // Export: the slides alone as one HTML presentation, with this page's styles and script, so it works offline
  // apart from the fonts. A served page links its styles and script, so they are fetched first.
  function textOf(node) {
    if (node.tagName === 'STYLE' || (node.tagName === 'SCRIPT' && !node.src)) return Promise.resolve(node.textContent);
    return fetch(node.href || node.src).then(function (r) { return r.text(); });
  }
  exportButton.addEventListener('click', function () {
    var copies = slides.map(function (s) {
      var c = s.cloneNode(true);
      c.querySelectorAll('.pin').forEach(function (p) { p.remove(); });
      c.querySelectorAll('.sel').forEach(function (x) { x.classList.remove('sel'); });
      var d = c.querySelector('.detail'); if (d) { d.hidden = true; d.replaceChildren(); }
      c.classList.remove('current');
      return c.outerHTML;
    }).join('');
    var font = document.querySelector('link[rel="stylesheet"][href^="https://fonts"]'), title = document.title;
    var styles = Array.prototype.slice.call(document.querySelectorAll('style, link[rel="stylesheet"][href^="/"]'));
    var mine = document.getElementById('show-js') || document.querySelector('script[src="/show.js"]');
    Promise.all(styles.map(textOf).concat([textOf(mine)])).then(function (texts) {
      var code = texts.pop();
      var page = '<!DOCTYPE html>\n<html lang="' + document.documentElement.lang + '"><head><meta charset="utf-8">' +
        '<meta name="viewport" content="width=device-width, initial-scale=1"><title></title>' + (font ? font.outerHTML : '') +
        '<style>' + texts.join('\n') + '</style></head><body class="present"><main class="deck">' + copies +
        '</main><p class="pcount" aria-live="polite"></p><script>' + code + '<\/script></body></html>';
      var doc = new DOMParser().parseFromString(page, 'text/html');
      doc.title = title;
      var blob = new Blob(['<!DOCTYPE html>\n' + doc.documentElement.outerHTML], { type: 'text/html' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = (title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 60) || 'slides') + '.html';
      document.body.append(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
      say('Slides downloaded as one presentation', 'ok');
    }, function () { say('The slides could not be exported', 'error'); });
  });

  // ---------- Read and Comment (served only) ----------
  function choose(attr, value) {
    document.querySelectorAll('button[' + attr + ']').forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute(attr) === value)); });
  }
  function setMode(on) { commenting = on; choose('data-mode', on ? 'comment' : 'read'); document.body.classList.toggle('commenting', on); }
  stage.addEventListener('click', function (e) {
    var slide = e.target.closest('.slide'); if (!slide) return;
    if (comments && comments.click(e, function () { openPop(slide, e.target, e.clientX, e.clientY); }, openEdit)) return;
    var goto = e.target.closest('[data-go]');
    if (goto) { e.preventDefault(); return go(+goto.dataset.go - 1); }
    var h = e.target.closest('[data-dk]');
    if (h) openDetail(slide, h);
  }, true);
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
    var description = pageElementDescription(target, slide, target.textContent, 160);
    description.item = nearestItem(target, x, y);
    return {
      slide: n, part: slide.dataset.part || '', headline: slide.dataset.headline || '',
      target: description,
      // Where the click fell, as fractions of the slide's width and height; yw, the height over the width, places the
      // pin so it stays on its spot when a detail opened below makes the slide taller.
      spot: { fx: Math.round((x - r.left) / Math.max(1, r.width) * 1000) / 1000, fy: Math.round((y - r.top) / Math.max(1, r.height) * 1000) / 1000,
              yw: Math.round((y - r.top) / Math.max(1, r.width) * 1000) / 1000 }
    };
  }
  // Two lines: where the comment is, small and muted, then what was clicked.
  function crumb(event) {
    var c = event.on || event, box = el('span', 'crumb'), t = c.target || {}, said = t.item || t.text || c.headline || '';
    box.append(el('span', 'path', 'Slide ' + c.slide + (c.part ? ' \u203a ' + c.part : '')),
               el('span', 'el', said ? '\u201c' + said.slice(0, 90) + (said.length > 90 ? '\u2026' : '') + '\u201d' : 'the slide'));
    return box;
  }
  function openPop(slide, target, x, y) {
    comments.open(describe(slide, target, x, y), null, document.activeElement !== document.body ? document.activeElement : null,
      function () { return pageCommentPosition(x, y, pop); });
  }
  function openEdit(it, from) {
    var r = from.getBoundingClientRect();
    var data = { item: it, slide: it.slide, part: it.part, headline: it.headline, target: it.target, spot: it.spot };
    comments.open(data, it, from, function () { return pageCommentPosition(r.left, r.bottom, pop); });
  }

  // ---------- The conversation: page.js; this page adds its pins and slides ----------
  function byId(id) { return items.filter(function (x) { return x.id === id; })[0]; }
  function apply(e, fresh) {
    if (e.type === 'comment') {
      var it = byId(e.id), on = e.on || {};
      if (!it) { it = { id: e.id, n: e.n || seq + 1 }; seq = Math.max(seq, it.n); items.push(it); }
      Object.assign(it, { slide: on.slide, part: on.part, headline: on.headline, target: on.target || {}, spot: on.spot || { fx: 0.5, fy: 0.5 }, text: e.text || '' });
      placePin(it, fresh);
    } else if (e.type === 'delete') {
      items = items.filter(function (x) { return x.id !== e.to; });
      slides.forEach(function (slide) { comments.removePin(slide, e.to); });
    }
  }
  // Empty the model and its pins, for the conversation to refill it from the log when the server refused an event.
  function reset() {
    items = []; seq = 0;
    slides.forEach(function (slide) { slide.querySelectorAll('.pin').forEach(function (p) { p.remove(); }); });
  }
  function placePin(it, fresh) {
    var slide = slides[(it.slide || 1) - 1]; if (!slide) return;
    var pin = comments.placePin(slide, it);
    pin.style.left = (it.spot.fx * 100) + '%';
    pin.style.top = it.spot.yw != null ? (it.spot.yw * 100) + 'cqw' : (it.spot.fy * 100) + '%';
    pin.title = 'Comment ' + it.n + ': click to open it';
    if (fresh) comments.flashPin(pin, 'flash');
  }
  // Show a comment where it was made: its slide, with its pin flashing.
  function reveal(e) {
    go(((e.on || e).slide || 1) - 1);
    var pin = comments.findPin(slides[cur], e.id); if (!pin) return;
    comments.flashPin(pin, 'flash');
    pin.scrollIntoView({ block: 'nearest' });
  }
  function send(method, params, what, done, fail) { conv.send(method, params, what, done, fail); }
  var KEY = 'show-mode:' + location.pathname;
  function converse() {
    comments = pageElementComments({
      pop: pop, pinClass: 'pin', byId: byId, send: send, crumb: crumb,
      commenting: function () { return commenting; },
      reopen: function (id) { conv.reopen(id); },
      nextNumber: function () { return seq + 1; },
      params: function (data, text) {
        return { on: { slide: data.slide, part: data.part, headline: data.headline, target: data.target, spot: data.spot }, text: text };
      }
    });
    document.querySelectorAll('button[data-mode]').forEach(function (b) {
      b.addEventListener('click', function () { setMode(b.dataset.mode === 'comment'); });
    });
    // In the bar, a two-option setting shows only its current option; clicking it picks the other one.
    document.querySelectorAll('.controls > .seg.cycle').forEach(function (group) {
      group.addEventListener('click', function (e) {
        var b = e.target.closest('button'); if (!b || b.getAttribute('aria-pressed') !== 'true' || group.dataset.cycling) return;
        var other = Array.prototype.filter.call(group.querySelectorAll('button'), function (x) { return x !== b; })[0];
        if (!other) return;
        e.stopImmediatePropagation(); group.dataset.cycling = '1'; other.click(); delete group.dataset.cycling; other.focus();
      }, true);
    });
    document.addEventListener('mousedown', function (e) { if (!pop.hidden && !pop.contains(e.target) && !e.target.closest('.slide')) comments.close(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !pop.hidden) comments.close(); });
    conv = pageConversation({
      served: true, name: 'page', apply: apply, reset: reset, byId: byId, reveal: reveal, edit: openEdit, remove: comments.remove,
      showLabel: function (n) { return 'Show comment ' + n + ' on its slide'; },
      crumb: crumb, commentBody: function (e) { return el('p', 'body', e.text); },
      noteParams: function () { return { on: { slide: cur + 1, part: slides[cur] ? slides[cur].dataset.part || null : null } }; },
      busy: function () { return popOpen(); },
      beforeReload: function () { sessionStorage.setItem(KEY, commenting ? 'comment' : 'read'); },
      rendered: function (state) { comments.state(state); items.forEach(function (it) { placePin(it, false); }); }
    });
    try { if (sessionStorage.getItem(KEY) === 'comment') setMode(true); sessionStorage.removeItem(KEY); } catch (e) {}
    conv.start();
  }

  function start() {
    build();
    go((parseInt(location.hash.slice(1), 10) || 1) - 1);
    if (served) converse();
  }
  if (!served) return start();

  // Served: the slides come from the server, drawn from the unit's spec each time the page loads.
  function fill(data) {
    document.documentElement.lang = data.lang || 'en';
    document.title = data.title || document.title;
    var title = document.getElementById('title'), goal = document.getElementById('goal');
    if (title) title.textContent = data.title || '';
    if (goal && data.question) { goal.className = 'question'; goal.textContent = data.question; goal.hidden = false; }
    if (data.style) { var st = el('style'); st.textContent = data.style; document.head.append(st); }
    stage.innerHTML = data.slides;
  }
  pageFetch('/data').then(function (r) { return r.json(); }).then(function (data) {
    if (data.errors) {
      // A spec that fails its checks has no slides; the page still carries the conversation, so the user can say so.
      var box = el('div', 'bad'); box.append(el('p', '', 'The spec has errors. The agent fixes them; this page then loads the slides.'));
      var ul = el('ul'); data.errors.forEach(function (line) { ul.append(el('li', '', line)); }); box.append(ul);
      stage.append(box); prev.disabled = next.disabled = true;
      return converse();
    }
    fill(data); start();
  });
})();
