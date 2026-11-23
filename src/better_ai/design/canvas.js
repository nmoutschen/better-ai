// The canvas page: the versions at each screen size, built from the unit's data (the server's /data, or the data a
// rendered page carries), with comments pinned in each version, thumbs, and Approve. The conversation is page.js's.
(function () {
  function icon(path) { return '<svg viewBox="0 0 24 24" aria-hidden="true">' + path + '</svg>'; }
  var ICONS = {
    Desktop: icon('<rect x="2" y="4" width="20" height="13" rx="1"/><path d="M8 21h8M12 17v4"/>'),
    Tablet: icon('<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M11 18h2"/>'),
    Mobile: icon('<rect x="7" y="2" width="10" height="20" rx="2"/><path d="M11 18h2"/>'),
    side: icon('<rect x="3" y="4" width="8" height="16"/><rect x="13" y="4" width="8" height="16"/>'),
    'switch': icon('<rect x="5" y="4" width="14" height="16"/><path d="M9 12h6M13 9l3 3-3 3"/>'),
    up: icon('<path d="M7 10v11H3V10zM7 10l4-8a3 3 0 0 1 3 3v4h6a2 2 0 0 1 2 2.3l-1.4 8A2 2 0 0 1 18.6 21H7"/>'),
    down: icon('<path d="M17 14V3h4v11zM17 14l-4 8a3 3 0 0 1-3-3v-4H4a2 2 0 0 1-2-2.3l1.4-8A2 2 0 0 1 5.4 3H17"/>')
  };
  function node(tag, cls, text, attrs) {
    var x = document.createElement(tag);
    if (cls) x.className = cls;
    if (text != null) x.textContent = text;
    Object.keys(attrs || {}).forEach(function (k) { x.setAttribute(k, attrs[k]); });
    return x;
  }
  function iconButton(attrs, svg, text) {
    var b = node('button', 'ico', null, Object.assign({ type: 'button' }, attrs));
    b.innerHTML = svg; b.append(node('span', null, text));
    return b;
  }
  // One version at one screen size, with its label and buttons. Full size shows it alone, so it needs another button.
  function figure(i, v, size, verdicts, full) {
    var fig = node('figure', null, null, { 'data-i': i }), label = node('div', 'label'), acts = node('span', 'acts');
    label.append(node('b', null, v.label, { title: v.label }), acts);
    if (verdicts) [['up', 'Good'], ['down', 'Not good']].forEach(function (p) {
      var b = node('button', 'vbtn', null, { type: 'button', 'data-v': i, 'data-verdict': p[0], 'aria-pressed': 'false', 'aria-label': p[1] + ': ' + v.label });
      b.innerHTML = ICONS[p[0]]; acts.append(b);
    });
    // Keyboard users comment on a whole version with this button; it shows only when focused.
    acts.append(node('button', 'vcomment', 'Comment on ' + v.label, { type: 'button', 'data-v': i }));
    if (full) acts.append(node('button', 'full', 'Full size', { type: 'button' }));
    var frame = node('iframe', null, null, { 'data-i': i, title: v.label + ', ' + size.w + ' × ' + size.h + ' px', width: size.w, height: size.h });
    if (v.src) frame.setAttribute('src', v.src); else frame.srcdoc = v.srcdoc || '';
    var screen = node('div', 'screen'); screen.append(frame);
    var stage = node('div', 'stage'); stage.append(screen);
    fig.append(label, stage);
    return fig;
  }
  // The controls that depend on the sizes and versions, and the frames. The rest of the controls are in canvas.html.
  function build(data, main, controls) {
    var versions = data.versions, sizes = data.sizes, verdicts = versions.length > 2, mode = controls.firstElementChild;
    var names = sizes.map(function (s) { return s.name; });
    if (names.some(function (n, k) { return names.indexOf(n) !== k; })) names = sizes.map(function (s) { return s.w + ' × ' + s.h; });
    function cycle(label) { return node('div', 'seg cycle', null, { role: 'group', 'aria-label': label }); }
    if (sizes.length > 1) {
      var screens = cycle('Screen');
      sizes.forEach(function (s, k) {
        var title = names[k] + ', ' + s.w + ' × ' + s.h + ' px';
        screens.append(iconButton({ 'data-size': k, 'aria-pressed': String(k === 0), title: title, 'aria-label': title }, ICONS[names[k]] || '', names[k]));
      });
      controls.insertBefore(screens, mode);
    }
    if (versions.length > 1) {
      var views = cycle('View');
      views.append(iconButton({ 'data-view': 'side', 'aria-pressed': 'true', title: 'Side by side', 'aria-label': 'Side by side' }, ICONS.side, 'Side by side'),
        iconButton({ 'data-view': 'switch', 'aria-pressed': 'false', title: 'Switch in place (Space)', 'aria-label': 'Switch in place' }, ICONS['switch'], 'Switch'));
      controls.insertBefore(views, mode);
      // In switch view, the version shown is picked from tabs inside the viewer, so the toolbar keeps its layout.
      var tabs = node('div', 'seg pick', null, { role: 'group', 'aria-label': 'Version shown', hidden: '' });
      versions.forEach(function (v, i) { tabs.append(node('button', null, v.label, { type: 'button', 'data-pick': i, 'aria-pressed': 'false' })); });
      main.append(tabs);
    }
    sizes.forEach(function (s, k) {
      var sec = node('section', null, null, { 'data-size': k, 'aria-label': 'Screen ' + s.w + ' × ' + s.h + ' px' }), row = node('div', 'row');
      if (k) sec.hidden = true;
      row.style.setProperty('--n', versions.length);
      versions.forEach(function (v, i) { row.append(figure(i, v, s, verdicts, versions.length > 1)); });
      sec.append(row); main.append(sec);
    });
  }

  function boot(data) {
  var main = document.querySelector('main'), controls = document.getElementById('controls');
  document.title = data.title;
  document.getElementById('title').textContent = data.title;
  if (data.question) { var goal = document.getElementById('goal'); goal.textContent = data.question; goal.hidden = false; }
  if (data.error) {
    var problem = document.getElementById('canvas-problem'); problem.textContent = data.error; problem.hidden = false;
    document.getElementById('status').textContent = '';
    watchForChange();
    return;
  }
  build(data, main, controls);
  // The controls sit in the header, where the stats of the other pages are.
  var status = document.getElementById('status'); status.replaceChildren(controls); controls.hidden = false;
  var labels = data.versions.map(function (v) { return v.label; }), current = 0;
  var viewButtons = document.querySelectorAll('[data-view]'), pickButtons = document.querySelectorAll('[data-pick]');
  // In the bar, a two-option setting shows only its current option; clicking it picks the other one.
  document.querySelectorAll('.controls > .seg.cycle').forEach(function (seg) {
    seg.addEventListener('click', function (e) {
      var b = e.target.closest('button'); if (!b || b.getAttribute('aria-pressed') !== 'true' || seg.dataset.cycling) return;
      var other = Array.prototype.filter.call(seg.querySelectorAll('button'), function (x) { return x !== b; })[0];
      if (!other) return;
      e.stopImmediatePropagation(); seg.dataset.cycling = '1'; other.click(); delete seg.dataset.cycling; other.focus();
    }, true);
  });
  // Every setting in the toolbar is one segmented choice between options; the chosen one is filled.
  var pick = document.querySelector('.pick'), linked = true, scrollSeg = document.querySelector('.scroll-setting');
  // Scrolling together needs two versions.
  if (labels.length < 2) scrollSeg.hidden = true;
  function choose(attr, value) {
    document.querySelectorAll('button[' + attr + ']').forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute(attr) === value)); });
  }
  document.querySelectorAll('button[data-scroll]').forEach(function (b) {
    b.addEventListener('click', function () { linked = b.dataset.scroll === 'linked'; choose('data-scroll', b.dataset.scroll); });
  });
  // Each render fills the space it has: scaled down to fit the width, and as tall as the stage, so it scrolls inside
  // its own frame while the page itself does not scroll.
  function fit() {
    document.querySelectorAll('main > section:not([hidden]) .stage').forEach(function (stage) {
      var frame = stage.querySelector('iframe'), box = stage.firstElementChild, w = +frame.getAttribute('width');
      var sw = stage.clientWidth, sh = stage.clientHeight;
      if (sw <= 0 || sh <= 0) return;
      var scale = Math.min(1, (sw - 2) / w);
      frame.style.width = w + 'px';
      frame.style.height = Math.floor((sh - 2) / scale) + 'px';
      frame.style.transform = 'scale(' + scale + ')';
      box.style.width = Math.ceil(w * scale + 2) + 'px';
      box.style.height = sh + 'px';
      try { frame.contentDocument.documentElement.style.setProperty('--db-s', String(1 / scale)); } catch (e) {}
      if (typeof movePins === 'function') movePins(frame);
    });
  }
  // The Display menu opens under its button and closes on a click outside it or on Escape.
  var moreBtn = document.querySelector('.morebtn'), menu = document.querySelector('.menu');
  function openMenu(on) { menu.hidden = !on; moreBtn.setAttribute('aria-expanded', String(on)); }
  moreBtn.addEventListener('click', function (e) { e.stopPropagation(); openMenu(menu.hidden); });
  document.addEventListener('click', function (e) { if (!menu.hidden && !menu.contains(e.target)) openMenu(false); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !menu.hidden) { openMenu(false); moreBtn.focus(); } });
  // Background behind the versions, kept for the next visit.
  function setBg(c) {
    main.style.setProperty('--surround', c);
    main.classList.toggle('on-dark', c === '#1E1E1E');
    document.querySelectorAll('.sw').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.bg === c)); });
    try { localStorage.setItem('canvas-bg', c); } catch (e) {}
  }
  document.querySelectorAll('.sw').forEach(function (b) { b.addEventListener('click', function () { setBg(b.dataset.bg); }); });
  try { var savedBg = localStorage.getItem('canvas-bg'); if (savedBg && document.querySelector('.sw[data-bg="' + savedBg + '"]')) setBg(savedBg); } catch (e) {}
  // Screen size: one size at a time, chosen in the top bar. The page opens on the first size the agent gave, or on
  // the size the user last chose on this page, which a reload keeps.
  var SIZE_KEY = 'canvas-size:' + location.pathname;
  document.querySelectorAll('button[data-size]').forEach(function (b) {
    b.addEventListener('click', function () {
      document.querySelectorAll('button[data-size]').forEach(function (o) { o.setAttribute('aria-pressed', String(o === b)); });
      document.querySelectorAll('main > section').forEach(function (sec) { sec.hidden = sec.dataset.size !== b.dataset.size; });
      try { sessionStorage.setItem(SIZE_KEY, b.getAttribute('aria-label')); } catch (e) {}
      fit();
    });
  });
  try {
    // Kept by its label, such as "Mobile, 375 × 760 px", so it survives the agent reordering the sizes.
    var savedSize = sessionStorage.getItem(SIZE_KEY), sizeBtn = savedSize && Array.prototype.find.call(
      document.querySelectorAll('button[data-size]'), function (b) { return b.getAttribute('aria-label') === savedSize; });
    if (sizeBtn && sizeBtn.getAttribute('aria-pressed') !== 'true') sizeBtn.click();
  } catch (e) {}
  // Scrolling: frames of one screen size scroll together. The position is matched between elements with the
  // same id in both versions, such as headings, so versions of different length stay on the same section.
  // This works only for versions embedded from files; a page loaded from an address cannot be followed.
  // An id counts only where it is unique in its document: versions can repeat an id, and the first match is then
  // often the wrong element.
  var quietUntil = new WeakMap();
  function tops(win, ids) {
    var doc = win.document, end = doc.documentElement.scrollHeight;
    var marks = [{ id: '', top: 0 }];
    ids.forEach(function (id) {
      var el = doc.getElementById(id);
      if (el) marks.push({ id: id, top: el.getBoundingClientRect().top + win.scrollY });
    });
    marks.push({ id: '', top: end });
    return marks;
  }
  function sharedIds(a, b) {
    var inA = pageIdCounts(a.document), inB = pageIdCounts(b.document);
    return Array.prototype.map.call(a.document.querySelectorAll('[id]'), function (el) { return el.id; })
      .filter(function (id) { return id && inA[id] === 1 && inB[id] === 1; });
  }
  function match(from, to) {
    try {
      var src = from.contentWindow, dst = to.contentWindow, ids = sharedIds(src, dst);
      var a = tops(src, ids), b = tops(dst, ids), y = src.scrollY, k = 0;
      while (k < a.length - 2 && a[k + 1].top <= y) k++;
      var p = (y - a[k].top) / Math.max(1, a[k + 1].top - a[k].top);
      quietUntil.set(to, Date.now() + 150);
      dst.scrollTo(0, b[k].top + p * (b[k + 1].top - b[k].top));
    } catch (e) {}
  }
  function follow(frame) {
    if (!linked || (quietUntil.get(frame) || 0) > Date.now()) return;
    frame.closest('.row').querySelectorAll('iframe').forEach(function (other) { if (other !== frame) match(frame, other); });
  }
  function bind(frame) {
    try { frame.contentWindow.addEventListener('scroll', function () { follow(frame); }); } catch (e) { if (scrollSeg) scrollSeg.hidden = true; }
  }
  var bound = new WeakSet();
  function bindOnce(frame) {
    var win; try { win = frame.contentWindow; } catch (e) { return; }
    if (!win || bound.has(win)) return;
    bound.add(win); bind(frame);
  }
  document.querySelectorAll('main iframe').forEach(function (frame) {
    frame.addEventListener('load', function () { bindOnce(frame); });
    try { if (frame.contentDocument.readyState === 'complete' && frame.contentDocument.body.childElementCount) bindOnce(frame); } catch (e) {}
  });
  function show(i) {
    var previous = current;
    current = i;
    document.querySelectorAll('main figure').forEach(function (f) { f.classList.toggle('current', +f.dataset.i === i); });
    pickButtons.forEach(function (b) { b.setAttribute('aria-pressed', String(+b.dataset.pick === i)); });
    fit();
    if (main.classList.contains('switch') && previous !== i) document.querySelectorAll('main .row').forEach(function (row) {
      match(row.querySelector('figure[data-i="' + previous + '"] iframe'), row.querySelector('figure[data-i="' + i + '"] iframe'));
    });
  }
  function view(name) {
    main.classList.toggle('switch', name === 'switch');
    viewButtons.forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.view === name)); });
    if (pick) pick.hidden = name !== 'switch';
    document.querySelectorAll('figure .full').forEach(function (b) { b.textContent = name === 'switch' ? 'Side by side' : 'Full size'; });
    show(current);
  }
  viewButtons.forEach(function (b) { b.addEventListener('click', function () { view(b.dataset.view); }); });
  pickButtons.forEach(function (b) { b.addEventListener('click', function () { show(+b.dataset.pick); }); });
  document.addEventListener('keydown', function (e) {
    if (!main.classList.contains('switch')) return;
    // Space and the arrows switch versions only outside fields, so the user can type and pick options.
    if (e.target.closest('input, textarea, select, [contenteditable]')) return;
    if (e.key === ' ' || e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
      if (e.target.tagName === 'BUTTON' && e.key === ' ') return;
      show((current + 1) % labels.length); e.preventDefault();
    }
  });
  // Full size is the switch view opened on that version: one version fills the viewer, the tabs pick another,
  // and the same button, now Side by side, brings the others back.
  document.querySelectorAll('figure .full').forEach(function (b) {
    b.addEventListener('click', function () {
      if (main.classList.contains('switch')) view('side');
      else { current = +b.closest('figure').dataset.i; view('switch'); }
    });
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && main.classList.contains('switch') && pop.hidden && !e.target.closest('textarea')) view('side');
  });
  window.addEventListener('resize', fit);
  // Four or more versions side by side are too small to read: start by switching between them in place.
  // Side by side when each version stays at half size or more; otherwise one at a time, switched in place.
  var firstFrame = document.querySelector('main iframe'), perVersion = (main.clientWidth - 20 * (labels.length - 1)) / labels.length;
  view(labels.length > 3 || (labels.length > 1 && firstFrame && perVersion / +firstFrame.getAttribute('width') < 0.5) ? 'switch' : 'side');

  // Feedback goes through the conversation in page.js, shared with the other pages that talk to the agent. The canvas
  // keeps its own model of comments, for the pins in each version, and of the verdicts, for the thumbs.
  var served = location.protocol === 'http:', seq = 0, items = [], verdicts = {};
  function apply(e, fresh) {
    if (e.type === 'comment') {
      var it = byId(e.id), on = e.on || {};
      if (!it) {
        it = { id: e.id, n: e.n || seq + 1, version: on.version, screen: on.screen, target: on.target || {}, spot: on.spot || { fx: 0.5, fy: 0.5 } };
        seq = Math.max(seq, it.n); items.push(it);
        document.querySelectorAll('iframe[data-i="' + labels.indexOf(it.version) + '"]').forEach(function (f) { placePin(f, it, fresh); });
      }
      it.verdict = e.verdict || null; it.text = e.text || null;
    } else if (e.type === 'delete') {
      items = items.filter(function (x) { return x.id !== e.to; });
      document.querySelectorAll('iframe').forEach(function (f) { try { comments.removePin(f.contentDocument.body, e.to); } catch (x) {} });
    } else if (e.type === 'verdict') { verdicts[e.version] = e.verdict || null; syncVersionButtons(); }
  }
  // Empty the model, its pins and the thumbs, for the conversation to refill them from the log when the server refused an event.
  function reset() {
    items = []; seq = 0; verdicts = {};
    document.querySelectorAll('iframe').forEach(function (f) { try { f.contentDocument.querySelectorAll('.db-pin').forEach(function (p) { p.remove(); }); } catch (x) {} });
    syncVersionButtons();
  }
  function byId(id) { return items.filter(function (x) { return x.id === id; })[0]; }
  function syncVersionButtons() {
    document.querySelectorAll('.vbtn[data-v]').forEach(function (b) {
      var v = labels[+b.dataset.v];
      b.setAttribute('aria-pressed', String(verdicts[v] === b.dataset.verdict));
    });
  }
  document.querySelectorAll('.vbtn[data-v]').forEach(function (b) {
    b.addEventListener('click', function () {
      var v = labels[+b.dataset.v];
      { var d = verdicts[v] === b.dataset.verdict ? null : b.dataset.verdict;
        send('verdict', { version: v, verdict: d }, d ? (d === 'up' ? 'Thumbs up' : 'Thumbs down') + ' for ' + v : 'Verdict on ' + v + ' withdrawn'); }
    });
  });

  // Comment mode: hovering a version outlines the element under the pointer; a click opens the comment box for it.
  var commenting = true, pop = document.querySelector('.pop');
  // The comment box has the thumbs too: a comment can be only a verdict.
  var thumbs = node('div', 'verdicts');
  [['up', 'Good'], ['down', 'Not good']].forEach(function (p) {
    var b = node('button', 'vbtn', null, { type: 'button', 'data-verdict': p[0], 'aria-pressed': 'false', 'aria-label': p[1] });
    b.innerHTML = ICONS[p[0]]; thumbs.append(b);
  });
  pop.insertBefore(thumbs, pop.querySelector('textarea'));
  var comments = pageElementComments({
    pop: pop, pinClass: 'db-pin', byId: byId, send: send,
    commenting: function () { return commenting; }, stopPinPropagation: true,
    reopen: function (id) { conv.reopen(id); },
    nextNumber: function () { return seq + 1; },
    crumb: function (data) { return crumb(data.version, data.target); },
    prepare: syncCommentVerdict,
    allowEmpty: function (data) { return data.verdict; },
    params: function (data, text) {
      var anchor = data.item || data;
      var params = { on: { version: anchor.version, screen: anchor.screen, target: anchor.target, spot: anchor.spot }, text: text || null };
      if (data.verdict) params.verdict = data.verdict;  // the schema allows a verdict only when there is one
      return params;
    }
  });
  function setMode(on) {
    commenting = on; choose('data-mode', on ? 'comment' : 'use'); main.classList.toggle('commenting', on);
    document.querySelectorAll('iframe').forEach(function (f) { try { f.contentDocument.documentElement.classList.toggle('db-commenting', on); } catch (e) {} });
  }
  main.classList.add('commenting');
  document.querySelectorAll('button[data-mode]').forEach(function (b) {
    b.addEventListener('click', function () { setMode(b.dataset.mode === 'comment'); });
  });
  // C switches between commenting and using the versions, and Escape closes the comment box. A click in a version
  // moves the focus into its frame, so each version's document listens too (see instrument).
  function shortcut(e) {
    if (e.defaultPrevented) return;  // the version handled the key itself
    // composedPath()[0] is the field itself when it sits inside a web component's shadow root.
    var t = e.composedPath ? e.composedPath()[0] : e.target, typing = t && (/INPUT|TEXTAREA|SELECT/.test(t.tagName) || t.isContentEditable);
    if ((e.key === 'c' || e.key === 'C') && !typing && !e.metaKey && !e.ctrlKey && !e.altKey) setMode(!commenting);
    if (e.key === 'Escape' && !pop.hidden) comments.close();
  }
  document.addEventListener('keydown', shortcut);
  // What a click points at, in enough detail for the agent to find it without the user picking an exact element:
  // the element and its parents, the words under the pointer, an image's source, and where the click fell.
  function elementText(x) {
    return x.getAttribute('aria-label') || x.getAttribute('alt') || x.getAttribute('placeholder') || x.innerText || x.value || '';
  }
  function brief(x) {
    return { tag: x.tagName.toLowerCase(), id: x.id || null, cls: (x.getAttribute('class') || '').trim() || null,
             text: elementText(x).replace(/\s+/g, ' ').trim().slice(0, 120) };
  }
  function wordsAt(doc, x, y) {
    var r = doc.caretRangeFromPoint ? doc.caretRangeFromPoint(x, y) : null;
    if (!r && doc.caretPositionFromPoint) { var c = doc.caretPositionFromPoint(x, y); if (c) { r = doc.createRange(); r.setStart(c.offsetNode, c.offset); } }
    if (!r || r.startContainer.nodeType !== 3) return null;
    var text = r.startContainer.textContent, i = r.startOffset, a = i, b = i;
    while (a > 0 && !/[.!?\n]/.test(text[a - 1])) a--;
    while (b < text.length && !/[.!?\n]/.test(text[b])) b++;
    return text.slice(a, b + 1).replace(/\s+/g, ' ').trim().slice(0, 200) || null;
  }
  // Where the clicked element sits, in words: version › parents › the element and what it says.
  var ROLE = { h1: 'Heading', h2: 'Heading', h3: 'Heading', h4: 'Heading', h5: 'Heading', h6: 'Heading', p: 'Paragraph',
    img: 'Image', svg: 'Image', picture: 'Image', button: 'Button', a: 'Link', input: 'Field', textarea: 'Field', select: 'Menu',
    label: 'Label', table: 'Table', tr: 'Row', td: 'Cell', th: 'Column heading', ul: 'List', ol: 'List', li: 'List item',
    header: 'Header', footer: 'Footer', nav: 'Navigation', main: 'Main', aside: 'Sidebar', section: 'Section',
    article: 'Article', form: 'Form', figure: 'Figure', figcaption: 'Caption', blockquote: 'Quote', span: 'Text' };
  // Two lines: the path to the element, small and muted, then what the element is and what it says.
  function crumb(version, t) {
    // The path: the version, the section's heading, and the element's place, such as "Row 2, Status".
    var said = t.image ? (t.image.alt || 'no alt text') : (t.words || t.text || '');
    var path = [version];
    if (t.heading && t.heading !== said) path.push(t.heading.length > 40 ? t.heading.slice(0, 40) + '…' : t.heading);
    if (t.place) path.push(t.place);
    var box = document.createElement('span'), a = document.createElement('span'), b = document.createElement('span'), r = document.createElement('span');
    box.className = 'crumb'; a.className = 'path'; b.className = 'el'; r.className = 'role';
    a.textContent = path.join(' › ');
    r.textContent = ROLE[t.tag] || 'Block';
    b.append(r, said ? ' “' + said.slice(0, 90) + (said.length > 90 ? '…' : '') + '”' : '');
    box.append(a, b);
    return box;
  }
  // Where an element sits among its peers, in the words a person would use: "Row 2, Status" in a table,
  // "Item 3" in a list. Empty when position adds nothing.
  function placeOf(el) {
    var cell = el.closest('td, th');
    if (cell) {
      var row = cell.parentElement, table = cell.closest('table');
      var body = Array.prototype.filter.call(table.rows, function (r) { return !r.closest('thead') && !r.querySelector('th:only-child, th:first-child:last-child'); });
      var head = table.tHead ? table.tHead.rows[0] : table.rows[0].querySelector('th') ? table.rows[0] : null;
      var name = head && head.cells[cell.cellIndex] ? head.cells[cell.cellIndex].innerText.trim() : '';
      var n = body.indexOf(row) + 1;
      if (row.closest('thead')) return 'Column ' + (name || cell.cellIndex + 1);
      return 'Row ' + n + ', ' + (name || 'column ' + (cell.cellIndex + 1));
    }
    var li = el.closest('li');
    if (li && li.parentElement) return 'Item ' + (Array.prototype.indexOf.call(li.parentElement.children, li) + 1);
    return '';
  }
  function describe(el, cx, cy) {
    var doc = el.ownerDocument, win = doc.defaultView, r = el.getBoundingClientRect(), d = pageElementDescription(el, null, elementText(el), 120);
    // The nearest heading above the element in reading order, or the element itself if it is a heading.
    var heading = null;
    doc.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(function (x) {
      if (x === el || x.contains(el) || (x.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING)) heading = x.innerText.trim();
    });
    var parents = [], up = el.parentElement;
    while (up && up.tagName !== 'BODY' && parents.length < 4) { parents.push(brief(up)); up = up.parentElement; }
    var img = el.tagName === 'IMG' ? el : null, image = null;
    if (img) image = { src: (img.currentSrc || img.getAttribute('src') || '').slice(0, 300), alt: img.getAttribute('alt') };
    else { var bg = win.getComputedStyle(el).backgroundImage; if (bg && bg !== 'none') image = { src: bg.slice(0, 300), alt: null }; }
    return { selector: d.selector, tag: d.tag, text: d.text, heading: heading, words: wordsAt(doc, cx, cy), image: image,
             place: placeOf(el),
             parents: parents, point: { x: Math.round(cx + win.scrollX), y: Math.round(cy + win.scrollY) },
             box: { x: Math.round(r.left + win.scrollX), y: Math.round(r.top + win.scrollY), w: Math.round(r.width), h: Math.round(r.height) } };
  }
  // The pin colours are the page's own table (pagePinCss, from page.css), with the page's colour variables filled in:
  // the version's document has none of them.
  function pinCss() {
    var root = getComputedStyle(document.documentElement);
    return 'html.db-commenting, html.db-commenting *{cursor:crosshair!important}' +
      '.db-pin{position:absolute;z-index:2147483647;width:24px;height:24px;margin:-12px 0 0 -12px;border-radius:50%;' +
      'background:#E8725C;color:#1C1A17;font:700 12px/24px sans-serif;text-align:center;box-shadow:0 0 0 2px #FFFCF7;cursor:pointer;transform:scale(var(--db-s,1))}' +
      '.db-pin.db-new{animation:db-pulse 1.2s ease-out 2}' +
      pagePinCss(document.styleSheets, 'db-pin', function (name) { return root.getPropertyValue(name).trim(); }) +
      '.db-pin[data-state=working]{animation:db-pulse 1.4s ease-out infinite}' +
      // An accepted comment's pin goes away; showing it from the conversation brings it back for a moment.
      '.db-pin.db-flash{display:block!important;animation:db-pulse .9s ease-out 3!important}' +
      '@media (prefers-reduced-motion: reduce){.db-pin{animation:none!important}}' +
      '@keyframes db-pulse{0%{box-shadow:0 0 0 2px #FFFCF7,0 0 0 0 rgba(232,114,92,.9)}100%{box-shadow:0 0 0 2px #FFFCF7,0 0 0 18px rgba(232,114,92,0)}}';
  }
  function instrument(frame) {
    var doc; try { doc = frame.contentDocument; } catch (e) { return; }
    if (!doc || !doc.body || doc.documentElement.dataset.dbReady) return;
    doc.documentElement.dataset.dbReady = '1';
    var style = doc.createElement('style'); style.textContent = pinCss(); doc.head.appendChild(style);
    doc.documentElement.classList.toggle('db-commenting', commenting);
    doc.addEventListener('keydown', shortcut);
    doc.addEventListener('click', function (e) {
      if (!menu.hidden) openMenu(false);
      // With a comment box open, a click elsewhere closes it instead of starting another comment.
      if (!pop.hidden) { e.preventDefault(); e.stopPropagation(); comments.close(); return; }
      comments.click(e, function () {
        var el = e.target, r = el.getBoundingClientRect();
        openPop(frame, el, { fx: (e.clientX - r.left) / Math.max(1, r.width), fy: (e.clientY - r.top) / Math.max(1, r.height) }, e.clientX, e.clientY);
      }, function (it) { openPop(frame, null, null, e.clientX, e.clientY, it); });
    }, true);
    items.forEach(function (it) { placePin(frame, it); });
    fit();
  }
  document.querySelectorAll('main iframe').forEach(function (frame) {
    frame.addEventListener('load', function () { instrument(frame); });
    try { if (frame.contentDocument.readyState === 'complete') instrument(frame); } catch (e) {}
  });
  function openPop(frame, el, at, cx, cy, existing) {
    var box = frame.getBoundingClientRect(), scale = box.width / +frame.getAttribute('width');
    var data = existing ? { item: existing, version: existing.version, target: existing.target, verdict: existing.verdict }
      : { version: labels[+frame.dataset.i], screen: frame.getAttribute('width') + 'x' + frame.getAttribute('height'),
          target: describe(el, cx, cy), spot: at, verdict: null };
    comments.open(data, existing, document.activeElement !== document.body ? document.activeElement : null, function () {
      return pageCommentPosition(box.left + cx * scale, box.top + cy * scale, pop);
    });
  }
  document.addEventListener('mousedown', function (e) { if (!pop.hidden && !pop.contains(e.target)) comments.close(); });
  document.querySelectorAll('.vcomment').forEach(function (b) {
    b.addEventListener('click', function () {
      var frame = document.querySelector('main > section:not([hidden]) iframe[data-i="' + b.dataset.v + '"]');
      try { openPop(frame, frame.contentDocument.body, { fx: 0.5, fy: 0 }, 24, 24); } catch (e) {}
    });
  });
  function openEdit(it, from) {
    var r = from.getBoundingClientRect();
    comments.open({ item: it, version: it.version, target: it.target, verdict: it.verdict }, it, from, function () {
      return { x: Math.max(12, r.right - pop.offsetWidth),
               y: Math.max(12, Math.min(r.bottom + 8, innerHeight - pop.offsetHeight - 12)) };
    });
  }
  function syncCommentVerdict(data) {
    pop.querySelectorAll('.vbtn').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.verdict === data.verdict)); });
  }
  pop.querySelectorAll('.vbtn').forEach(function (b) {
    b.addEventListener('click', function () {
      var draft = comments.draft();
      draft.verdict = draft.verdict === b.dataset.verdict ? null : b.dataset.verdict;
      syncCommentVerdict(draft);
    });
  });
  function movePins(frame) {
    var doc; try { doc = frame.contentDocument; } catch (e) { return; }
    if (!doc) return;
    doc.querySelectorAll('.db-pin').forEach(function (pin) {
      var it = byId(pin.dataset.id);
      var el = it && doc.querySelector(it.target.selector); if (!el) return;
      positionPin(pin, frame, el, it.spot);
    });
  }
  function positionPin(pin, frame, el, spot) {
    var r = el.getBoundingClientRect(), win = frame.contentWindow;
    pin.style.left = (r.left + win.scrollX + spot.fx * r.width) + 'px';
    pin.style.top = (r.top + win.scrollY + spot.fy * r.height) + 'px';
  }
  function placePin(frame, it, fresh) {
    if (labels[+frame.dataset.i] !== it.version) return;
    var doc; try { doc = frame.contentDocument; } catch (e) { return; }
    if (!doc || !doc.documentElement.dataset.dbReady || comments.findPin(doc.body, it.id)) return;
    var el; try { el = doc.querySelector(it.target.selector); } catch (e) { return; }
    if (!el) return;
    var pin = comments.placePin(doc.body, it);
    if (fresh) pin.classList.add('db-new');
    pin.title = 'Comment ' + it.n + ': open to change or delete';
    positionPin(pin, frame, el, it.spot);
  }
  // ---------- The conversation: page.js, shared with the other pages; the canvas adds verdicts and Approve ----------
  function el(tag, cls, text) { var x = document.createElement(tag); if (cls) x.className = cls; if (text != null) x.textContent = text; return x; }
  function time(at) { return pageTime(at); }
  // Show a comment where it was made: its screen size, its version, scrolled to its pin, which flashes.
  function reveal(e) {
    var on = e.on || e;
    var sec = Array.prototype.filter.call(document.querySelectorAll('main > section'), function (x) {
      var f = x.querySelector('iframe'); return f && f.getAttribute('width') + 'x' + f.getAttribute('height') === on.screen;
    })[0];
    if (sec && sec.hidden) { var sb = document.querySelector('button[data-size="' + sec.dataset.size + '"]'); if (sb) sb.click(); }
    var i = labels.indexOf(on.version); if (i < 0) return;
    if (main.classList.contains('switch')) show(i);
    var frame = (sec || main).querySelector('iframe[data-i="' + i + '"]'); if (!frame) return;
    var doc; try { doc = frame.contentDocument; } catch (x) { return; }
    var pin = comments.findPin(doc && doc.body, e.id); if (!pin) return;
    comments.flashPin(pin, 'db-flash');
    frame.contentWindow.scrollTo({ top: Math.max(0, parseFloat(pin.style.top) - frame.contentWindow.innerHeight / 3), behavior: 'smooth' });
    setTimeout(function () { pin.classList.remove('db-flash'); }, 2800);
  }
  var STATE_WORD = { asked: 'waiting for you', replied: 'answered, back with the agent', followup: 'you replied, back with the agent', seen: 'seen', working: 'being worked on', done: 'done, waiting for you', accepted: 'accepted', reopened: 'reopened' };
  function syncPins() {
    document.querySelectorAll('iframe').forEach(function (f) {
      try { f.contentDocument.querySelectorAll('.db-pin').forEach(function (pin) {
        var it = byId(pin.dataset.id); if (!it) return;
        comments.updatePin(pin, it);
        var st = pin.dataset.state;
        pin.title = 'Comment ' + (it ? it.n : '') + ': ' + (STATE_WORD[st] || 'new') + '. Click to open it.';
      }); } catch (e) {}
    });
  }
  function commentBody(e) {
    var body = el('p', 'body');
    if (e.verdict) body.append(el('span', 'verdict ' + e.verdict, e.verdict === 'up' ? 'Good' : 'Not good'));
    if (e.text) body.append(e.text);
    return body;
  }
  function approvalItem(c) {
    var e = c.e, li = el('li', 'msg me decision'), head = el('div', 'head');
    head.append(el('span', 'who', 'You approved'), el('span', 'when', time(e.at)));
    var d = el('p', 'body'); d.append(el('strong', '', e.label || e.option));
    if (e.carries && e.carries.length) d.append(el('span', 'with', ' with comments ' + e.carries.map(function (id) { var x = conv.log().filter(function (y) { return y.id === id; })[0]; return x && x.n ? x.n : '?'; }).join(', ')));
    li.append(head, d); if (e.text) li.append(el('p', 'body', e.text));
    return li;
  }
  function verdictItem(c) {
    var e = c.e, t = (e.verdict ? (e.verdict === 'up' ? 'Thumbs up for ' : 'Thumbs down for ') + e.version : 'You withdrew your verdict on ' + e.version);
    return el('li', 'sys', t + ', ' + time(e.at));
  }
  // New versions from the agent load on the same view and version; the screen size is kept by SIZE_KEY above.
  var KEY = 'canvas-view:' + location.pathname, deciding = false;
  var conv = pageConversation({
    served: served, agent: 'Agent', unsent: 'Use Copy all to paste it in the chat.', apply: apply, reset: reset, byId: byId,
    reveal: reveal, edit: openEdit, remove: comments.remove,
    showLabel: function (n) { return 'Show where comment ' + n + ' is'; },
    crumb: function (e) { var on = e.on || e; return crumb(on.version, on.target || {}); }, commentBody: commentBody,
    kinds: { approve: approvalItem, verdict: verdictItem }, itemKinds: ['comment', 'note', 'approve'],
    sendMode: function () { return deciding ? sendApproval : null; },
    busy: function () { return !pop.hidden; },
    beforeReload: function () {
      sessionStorage.setItem(KEY, JSON.stringify({ view: main.classList.contains('switch') ? 'switch' : 'side', current: current }));
    },
    rendered: function (state) { comments.state(state); syncPins(); }
  });
  function send(method, params, what, done, fail) { conv.send(method, params, what, done, fail); }
  var say = conv.say, noteBox = conv.noteBox, noteBtn = conv.noteBtn;
  function asText() {
    var lines = [], log = conv.log();
    var dec = log.filter(function (x) { return x.type === 'approve'; }).pop();
    if (dec) lines.push('I approve: ' + (dec.label || dec.option) + (dec.carries && dec.carries.length ? ', with comments ' +
      dec.carries.map(function (id) { var x = byId(id); return x ? x.n : '?'; }).join(', ') : '') + '.' + (dec.text ? ' ' + dec.text : ''));
    labels.forEach(function (v) { if (verdicts[v]) lines.push(v + ': ' + (verdicts[v] === 'up' ? 'good' : 'not good') + '.'); });
    items.forEach(function (it) {
      var t = it.target || {};
      lines.push(it.n + '. ' + it.version + ', ' + (t.words || t.text ? '"' + (t.words || t.text).slice(0, 60) + '"' : t.selector) + ': ' +
                 (it.verdict ? (it.verdict === 'up' ? 'good' : 'not good') + (it.text ? ', ' : '') : '') + (it.text || ''));
    });
    log.forEach(function (e) { if (e.type === 'note') lines.push(e.text); });
    return lines.join('\n');
  }
  // Without a server, nothing reaches the agent: Copy all copies the feedback as text to paste in the chat.
  if (!served) {
    var copyBtn = el('button', 'btn btn--quiet copy', 'Copy all'); copyBtn.type = 'button';
    document.querySelector('.notes .send').insertBefore(copyBtn, document.querySelector('.notes .send .status'));
    copyBtn.addEventListener('click', function () {
      navigator.clipboard.writeText(asText()).then(function () { say('Copied. Paste it in the chat with the agent.'); },
        function () { say('Could not copy. Select the conversation and copy it by hand.', true); });
    });
  }
  // Approve: one confirmed approval, sent with the open comments that come with it and the message as its note. The
  // Send button becomes Confirm while the panel is open, so the same place sends both. page.js opens and closes the panel.
  var panel = el('div', 'approval'), approveBtn = el('button', 'btn btn--quiet', 'Approve…');
  approveBtn.type = 'button'; approveBtn.setAttribute('aria-expanded', 'false'); panel.hidden = true;
  panel.append(el('p', 'menu-h', 'Your approval'), el('div', 'dopts'), el('div', 'carry'));
  panel.querySelector('.dopts').setAttribute('role', 'radiogroup'); panel.querySelector('.dopts').setAttribute('aria-label', 'Approval');
  document.querySelector('.notes .composer').insertBefore(panel, document.querySelector('.notes .composer label'));
  noteBtn.parentElement.insertBefore(approveBtn, noteBtn.nextSibling);
  var beforeAfter = labels.length === 2 && labels[0].toLowerCase() === 'before' && labels[1].toLowerCase() === 'after';
  var OPTIONS = beforeAfter ? [['Ship After', 'After'], ['Keep Before', 'Before']]
    : labels.map(function (l) { return ['Build ' + l, l]; }).concat([['Combine versions (say how below)', 'combine']]);
  OPTIONS.push(['None of these (say why below)', 'none']);
  function openItems() {
    var pinState = comments.state();
    return items.filter(function (it) { return pinState[it.id] !== 'accepted' && pinState[it.id] !== 'done'; });
  }
  function approval() {
    var pick = panel.querySelector('input[name="approval"]:checked'), note = noteBox.value.trim();
    return { option: pick.value, label: pick.parentElement.textContent.trim(),
             carries: openItems().map(function (it) { return it.id; }), text: note || null };
  }
  function fillPanel(on) {
    deciding = on;
    approveBtn.textContent = on ? 'Cancel' : 'Approve…';
    noteBtn.textContent = on ? 'Confirm approval' : 'Send';
    if (!on) return;
    var box = panel.querySelector('.dopts'); box.replaceChildren();
    OPTIONS.forEach(function (o, k) {
      var lab = el('label', 'dopt'), r = el('input'); r.type = 'radio'; r.name = 'approval'; r.value = o[1]; if (!k) r.checked = true;
      lab.append(r, ' ' + o[0]); box.append(lab);
    });
    var open = openItems(), carry = panel.querySelector('.carry'); carry.replaceChildren();
    if (open.length) {
      carry.append(el('p', 'menu-h', 'Comes with your open comments'));
      open.forEach(function (it) { carry.append(el('p', 'carried', it.n + '. ' + (it.text || (it.verdict === 'up' ? 'Good' : 'Not good')))); });
    }
    noteBox.focus();
  }
  var approve = pageApprove({ button: approveBtn, panel: panel, label: 'Approval', params: approval, onToggle: fillPanel });
  function sendApproval() {
    var pick = approval();
    if ((pick.option === 'combine' || pick.option === 'none') && !pick.text) { say('Say how to combine them, or why none fits, in the message.', true); return noteBox.focus(); }
    approve.send(conv, function () { noteBox.value = ''; });
  }
  conv.start();
  if (served) {
    try {
      var kept = JSON.parse(sessionStorage.getItem(KEY) || 'null');
      sessionStorage.removeItem(KEY);
      if (kept) {
        if (kept.current < labels.length) current = kept.current;
        view(labels.length > 1 ? kept.view : 'side'); show(current);
      }
    } catch (e) {}
  }
  }

  // A page whose unit cannot be read still reloads once the unit is fixed.
  function watchForChange() {
    var rev = null;
    (function poll() {
      fetch('/rev').then(function (r) { return r.text(); }).then(function (v) {
        if (rev === null) rev = v; else if (v !== rev) location.reload();
      }).catch(function () {}).then(function () { setTimeout(poll, 2000); });
    })();
  }
  var carried = document.getElementById('page-data');
  if (carried) boot(JSON.parse(carried.textContent));
  else fetch('/data').then(function (r) { return r.json(); }).then(boot).catch(function () {
    var problem = document.getElementById('canvas-problem');
    problem.textContent = 'The page could not load its versions: ask the agent to restart it.'; problem.hidden = false;
  });
})();
