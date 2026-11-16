(function () {
  var main = document.querySelector('main');
  var labels = JSON.parse(main.dataset.labels), current = 0;
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
  // Screen size: one size at a time, chosen in the top bar.
  document.querySelectorAll('button[data-size]').forEach(function (b) {
    b.addEventListener('click', function () {
      document.querySelectorAll('button[data-size]').forEach(function (o) { o.setAttribute('aria-pressed', String(o === b)); });
      document.querySelectorAll('main > section').forEach(function (sec) { sec.hidden = sec.dataset.size !== b.dataset.size; });
      fit();
    });
  });
  // Scrolling: frames of one screen size scroll together. The position is matched between elements with the
  // same id in both versions, such as headings, so versions of different length stay on the same section.
  // This works only for versions embedded from files; a page loaded from an address cannot be followed.
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
    return Array.prototype.map.call(a.document.querySelectorAll('[id]'), function (el) { return el.id; })
      .filter(function (id) { return id && b.document.getElementById(id); });
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
    if (e.action === 'comment') {
      var it = byId(e.id);
      if (!it) {
        it = { id: e.id, n: e.n || seq + 1, version: e.version, screen: e.screen, target: e.target || {}, spot: e.spot || { fx: 0.5, fy: 0.5 } };
        seq = Math.max(seq, it.n); items.push(it);
        document.querySelectorAll('iframe[data-i="' + labels.indexOf(it.version) + '"]').forEach(function (f) { placePin(f, it, fresh); });
      }
      it.verdict = e.verdict || null; it.comment = e.comment || null;
    } else if (e.action === 'delete') {
      items = items.filter(function (x) { return x.id !== e.id; });
      document.querySelectorAll('iframe').forEach(function (f) { try { var p = f.contentDocument.querySelector('.db-pin[data-id="' + e.id + '"]'); if (p) p.remove(); } catch (x) {} });
    } else if (e.action === 'verdict') { verdicts[e.version] = e.verdict || null; syncVersionButtons(); }
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
  var commenting = true, pop = document.querySelector('.pop'), draft = null;
  function setMode(on) {
    commenting = on; choose('data-mode', on ? 'comment' : 'use'); main.classList.toggle('commenting', on);
    document.querySelectorAll('iframe').forEach(function (f) { try { f.contentDocument.documentElement.classList.toggle('db-commenting', on); } catch (e) {} });
  }
  main.classList.add('commenting');
  document.querySelectorAll('button[data-mode]').forEach(function (b) {
    b.addEventListener('click', function () { setMode(b.dataset.mode === 'comment'); });
  });
  document.addEventListener('keydown', function (e) {
    if ((e.key === 'c' || e.key === 'C') && !/INPUT|TEXTAREA/.test(e.target.tagName) && !e.metaKey && !e.ctrlKey) setMode(!commenting);
    if (e.key === 'Escape' && !pop.hidden) closePop();
  });
  function selectorOf(el) {
    var parts = [];
    while (el && el.nodeType === 1 && el.tagName !== 'BODY' && el.tagName !== 'HTML') {
      if (el.id) { parts.unshift('#' + CSS.escape(el.id)); break; }
      var tag = el.tagName.toLowerCase(), n = 1, sib = el;
      while ((sib = sib.previousElementSibling)) if (sib.tagName === el.tagName) n++;
      parts.unshift(tag + ':nth-of-type(' + n + ')');
      el = el.parentElement;
    }
    return parts.join(' > ') || 'body';
  }
  // What a click points at, in enough detail for the agent to find it without the user picking an exact element:
  // the element and its parents, the words under the pointer, an image's source, and where the click fell.
  function brief(x) {
    var t = (x.getAttribute('aria-label') || x.getAttribute('alt') || x.getAttribute('placeholder') ||
             x.innerText || x.value || '').replace(/\s+/g, ' ').trim();
    return { tag: x.tagName.toLowerCase(), id: x.id || null, cls: (x.getAttribute('class') || '').trim() || null, text: t.slice(0, 120) };
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
    var doc = el.ownerDocument, win = doc.defaultView, r = el.getBoundingClientRect(), d = brief(el);
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
    return { selector: selectorOf(el), tag: d.tag, text: d.text, heading: heading, words: wordsAt(doc, cx, cy), image: image,
             place: placeOf(el),
             parents: parents, point: { x: Math.round(cx + win.scrollX), y: Math.round(cy + win.scrollY) },
             box: { x: Math.round(r.left + win.scrollX), y: Math.round(r.top + win.scrollY), w: Math.round(r.width), h: Math.round(r.height) } };
  }
  var PIN_CSS = 'html.db-commenting, html.db-commenting *{cursor:crosshair!important}' +
    '.db-pin{position:absolute;z-index:2147483647;width:24px;height:24px;margin:-12px 0 0 -12px;border-radius:50%;' +
    'background:#E8725C;color:#1C1A17;font:700 12px/24px sans-serif;text-align:center;box-shadow:0 0 0 2px #FFFCF7;cursor:pointer;transform:scale(var(--db-s,1))}' +
    '.db-pin.db-new{animation:db-pulse 1.2s ease-out 2}' +
    // A pin shows its comment's progress in the colours of the conversation panel.
    '.db-pin[data-state=seen],.db-pin[data-state=replied]{background:#C4B69C}' +
    '.db-pin[data-state=asked]{background:#FFFCF7;color:#5C4033;box-shadow:0 0 0 2px #5C4033}' +
    '.db-pin[data-state=working]{background:#E8725C;animation:db-pulse 1.4s ease-out infinite}' +
    '.db-pin[data-state=done]{background:#66795A;color:#FFFCF7}' +
    // An accepted comment's pin goes away; showing it from the conversation brings it back for a moment.
    '.db-pin[data-state=accepted]{display:none;background:#66795A;color:#FFFCF7}' +
    '.db-pin.db-flash{display:block!important;animation:db-pulse .9s ease-out 3!important}' +
    '.db-pin[data-state=reopened]{background:#E8725C;box-shadow:0 0 0 2px #FFFCF7,0 0 0 4px #9A3B2A}' +
    '@media (prefers-reduced-motion: reduce){.db-pin{animation:none!important}}' +
    '@keyframes db-pulse{0%{box-shadow:0 0 0 2px #FFFCF7,0 0 0 0 rgba(232,114,92,.9)}100%{box-shadow:0 0 0 2px #FFFCF7,0 0 0 18px rgba(232,114,92,0)}}';
  function instrument(frame) {
    var doc; try { doc = frame.contentDocument; } catch (e) { return; }
    if (!doc || !doc.body || doc.documentElement.dataset.dbReady) return;
    doc.documentElement.dataset.dbReady = '1';
    var style = doc.createElement('style'); style.textContent = PIN_CSS; doc.head.appendChild(style);
    doc.documentElement.classList.toggle('db-commenting', commenting);
    doc.addEventListener('click', function (e) {
      if (!menu.hidden) openMenu(false);
      // With a comment box open, a click elsewhere closes it instead of starting another comment.
      if (!pop.hidden) { e.preventDefault(); e.stopPropagation(); closePop(); return; }
      var pin = e.target.closest && e.target.closest('.db-pin');
      if (pin) {
        // A pin opens its comment, to read, change or delete it, whether or not comment mode is on.
        e.preventDefault(); e.stopPropagation();
        var found = items.filter(function (x) { return x.id === pin.dataset.id; })[0];
        // A finished comment is not edited: it is reopened, with what is still wrong, from the conversation.
        if (found && (pinState[found.id] === 'done' || pinState[found.id] === 'accepted')) conv.reopen(found.id);
        else if (found) openPop(frame, null, null, e.clientX, e.clientY, found);
        return;
      }
      if (!commenting) return;
      e.preventDefault(); e.stopPropagation();
      var el = e.target, r = el.getBoundingClientRect();
      openPop(frame, el, { fx: (e.clientX - r.left) / Math.max(1, r.width), fy: (e.clientY - r.top) / Math.max(1, r.height) }, e.clientX, e.clientY);
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
    draft = existing ? { item: existing, version: existing.version, target: existing.target, verdict: existing.verdict }
      : { version: labels[+frame.dataset.i], screen: frame.getAttribute('width') + 'x' + frame.getAttribute('height'),
          target: describe(el, cx, cy), spot: at, verdict: null };
    pop.querySelector('.target').replaceChildren(crumb(draft.version, draft.target));
    pop.querySelector('textarea').value = existing ? existing.comment || '' : '';
    pop.querySelectorAll('.vbtn').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.verdict === draft.verdict)); });
    pop.querySelector('.remove').hidden = !existing;
    pop.querySelector('.ok').textContent = existing ? 'Update' : 'Send';
    pop.hidden = false; opener = document.activeElement !== document.body ? document.activeElement : null;
    var x = box.left + cx * scale + 12, y = box.top + cy * scale + 12;
    pop.style.left = Math.max(12, Math.min(x, innerWidth - pop.offsetWidth - 12)) + 'px';
    pop.style.top = Math.max(12, Math.min(y, innerHeight - pop.offsetHeight - 12)) + 'px';
    pop.querySelector('textarea').focus();
  }
  // The comment box returns focus to what opened it, so keyboard users keep their place.
  var opener = null;
  document.addEventListener('mousedown', function (e) { if (!pop.hidden && !pop.contains(e.target)) closePop(); });
  document.querySelectorAll('.vcomment').forEach(function (b) {
    b.addEventListener('click', function () {
      var frame = document.querySelector('main > section:not([hidden]) iframe[data-i="' + b.dataset.v + '"]');
      try { openPop(frame, frame.contentDocument.body, { fx: 0.5, fy: 0 }, 24, 24); } catch (e) {}
    });
  });
  function closePop() { pop.hidden = true; draft = null; if (opener && document.contains(opener)) opener.focus(); opener = null; }
  function openEdit(it, from) {
    var r = from.getBoundingClientRect();
    draft = { item: it, version: it.version, target: it.target, verdict: it.verdict };
    pop.querySelector('.target').replaceChildren(crumb(it.version, it.target));
    pop.querySelector('textarea').value = it.comment || '';
    pop.querySelectorAll('.vbtn').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.verdict === draft.verdict)); });
    pop.querySelector('.remove').hidden = false; pop.querySelector('.ok').textContent = 'Update';
    pop.hidden = false; opener = from;
    pop.style.left = Math.max(12, r.right - pop.offsetWidth) + 'px';
    pop.style.top = Math.max(12, Math.min(r.bottom + 8, innerHeight - pop.offsetHeight - 12)) + 'px';
    pop.querySelector('textarea').focus();
  }
  pop.querySelectorAll('.vbtn').forEach(function (b) {
    b.addEventListener('click', function () {
      draft.verdict = draft.verdict === b.dataset.verdict ? null : b.dataset.verdict;
      pop.querySelectorAll('.vbtn').forEach(function (o) { o.setAttribute('aria-pressed', String(o.dataset.verdict === draft.verdict)); });
    });
  });
  pop.querySelector('.cancel').addEventListener('click', closePop);
  pop.querySelector('.remove').addEventListener('click', function () { var it = draft && draft.item; closePop(); if (it) removeItem(it); });
  pop.querySelector('textarea').addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submitComment(); }
  });
  pop.querySelector('.ok').addEventListener('click', submitComment);
  function submitComment() {
    var text = pop.querySelector('textarea').value.trim();
    if (!draft || (!text && !draft.verdict)) { pop.querySelector('textarea').focus(); return; }
    var it = draft.item, id = it ? it.id : 'c' + (seq + 1) + '-' + Date.now().toString(36), n = it ? it.n : seq + 1;
    var params = it ? { id: id, n: n, version: it.version, screen: it.screen, target: it.target, spot: it.spot }
                    : { id: id, n: n, version: draft.version, screen: draft.screen, target: draft.target, spot: draft.spot };
    params.verdict = draft.verdict; params.comment = text || null;
    closePop();
    // An update reuses the comment's id, so the agent replaces the earlier version of it.
    send('comment', params, 'Comment ' + n + (it ? ' (updated)' : ''));
  }
  function removeItem(it) { send('delete', { id: it.id, n: it.n }, 'Deletion of comment ' + it.n); }
  function movePins(frame) {
    var doc; try { doc = frame.contentDocument; } catch (e) { return; }
    if (!doc) return;
    doc.querySelectorAll('.db-pin').forEach(function (pin) {
      var it = items.filter(function (x) { return x.id === pin.dataset.id; })[0];
      var el = it && doc.querySelector(it.target.selector); if (!el) return;
      var r = el.getBoundingClientRect(), win = frame.contentWindow;
      pin.style.left = (r.left + win.scrollX + it.spot.fx * r.width) + 'px';
      pin.style.top = (r.top + win.scrollY + it.spot.fy * r.height) + 'px';
    });
  }
  function placePin(frame, it, fresh) {
    if (labels[+frame.dataset.i] !== it.version) return;
    var doc; try { doc = frame.contentDocument; } catch (e) { return; }
    if (!doc || !doc.documentElement.dataset.dbReady || doc.querySelector('.db-pin[data-id="' + it.id + '"]')) return;
    var el; try { el = doc.querySelector(it.target.selector); } catch (e) { return; }
    if (!el) return;
    var r = el.getBoundingClientRect(), win = frame.contentWindow, pin = doc.createElement('span');
    pin.className = 'db-pin' + (fresh ? ' db-new' : ''); pin.dataset.id = it.id; pin.textContent = it.n;
    pin.dataset.state = pinState[it.id] || 'new';
    pin.title = 'Comment ' + it.n + ': open to change or delete';
    pin.style.left = (r.left + win.scrollX + it.spot.fx * r.width) + 'px';
    pin.style.top = (r.top + win.scrollY + it.spot.fy * r.height) + 'px';
    doc.body.appendChild(pin);
  }
  // ---------- The conversation: page.js, shared with the other pages; the canvas adds verdicts and Decide ----------
  function el(tag, cls, text) { var x = document.createElement(tag); if (cls) x.className = cls; if (text != null) x.textContent = text; return x; }
  function time(at) { return (at || '').slice(11, 16); }
  // Show a comment where it was made: its screen size, its version, scrolled to its pin, which flashes.
  function reveal(e) {
    var sec = Array.prototype.filter.call(document.querySelectorAll('main > section'), function (x) {
      var f = x.querySelector('iframe'); return f && f.getAttribute('width') + 'x' + f.getAttribute('height') === e.screen;
    })[0];
    if (sec && sec.hidden) { var sb = document.querySelector('button[data-size="' + sec.dataset.size + '"]'); if (sb) sb.click(); }
    var i = labels.indexOf(e.version); if (i < 0) return;
    if (main.classList.contains('switch')) show(i);
    var frame = (sec || main).querySelector('iframe[data-i="' + i + '"]'); if (!frame) return;
    var doc; try { doc = frame.contentDocument; } catch (x) { return; }
    var pin = doc.querySelector('.db-pin[data-id="' + e.id + '"]'); if (!pin) return;
    pin.classList.remove('db-flash'); void pin.offsetWidth; pin.classList.add('db-flash');
    frame.contentWindow.scrollTo({ top: Math.max(0, parseFloat(pin.style.top) - frame.contentWindow.innerHeight / 3), behavior: 'smooth' });
    setTimeout(function () { pin.classList.remove('db-flash'); }, 2800);
  }
  var pinState = {}, STATE_WORD = { asked: 'waiting for you', replied: 'answered, back with the agent', followup: 'you replied, back with the agent', seen: 'seen', working: 'being worked on', done: 'done, waiting for you', accepted: 'accepted', reopened: 'reopened' };
  function syncPins() {
    document.querySelectorAll('iframe').forEach(function (f) {
      try { f.contentDocument.querySelectorAll('.db-pin').forEach(function (pin) {
        var st = pinState[pin.dataset.id] || 'new', it = byId(pin.dataset.id);
        pin.dataset.state = st;
        pin.title = 'Comment ' + (it ? it.n : '') + ': ' + (STATE_WORD[st] || 'new') + '. Click to open it.';
      }); } catch (e) {}
    });
  }
  function commentBody(e) {
    var body = el('p', 'body');
    if (e.verdict) body.append(el('span', 'verdict ' + e.verdict, e.verdict === 'up' ? 'Good' : 'Not good'));
    if (e.comment) body.append(e.comment);
    return body;
  }
  function decisionItem(c) {
    var e = c.e, li = el('li', 'msg me decision'), head = el('div', 'head');
    head.append(el('span', 'who', 'You decided'), el('span', 'when', time(e.at)));
    var d = el('p', 'body'); d.append(el('strong', '', e.label || e.option));
    if (e.carries && e.carries.length) d.append(el('span', 'with', ' with comments ' + e.carries.map(function (id) { var x = conv.log().filter(function (y) { return y.id === id; })[0]; return x && x.n ? x.n : '?'; }).join(', ')));
    li.append(head, d); if (e.note) li.append(el('p', 'body', e.note));
    return li;
  }
  function verdictItem(c) {
    var e = c.e, t = (e.verdict ? (e.verdict === 'up' ? 'Thumbs up for ' : 'Thumbs down for ') + e.version : 'You withdrew your verdict on ' + e.version);
    return el('li', 'sys', t + ', ' + time(e.at));
  }
  // New versions from the agent load on the same screen size, view and version.
  var KEY = 'canvas-view:' + location.pathname, deciding = false;
  var conv = pageConversation({
    served: served, name: 'canvas', unsent: 'Use Copy all to paste it in the chat.', apply: apply, byId: byId,
    reveal: reveal, edit: openEdit, remove: removeItem,
    showLabel: function (n) { return 'Show where comment ' + n + ' is'; },
    crumb: function (e) { return crumb(e.version, e.target || {}); }, commentBody: commentBody,
    kinds: { decide: decisionItem, verdict: verdictItem }, itemKinds: ['comment', 'note', 'decide'],
    sendMode: function () { return deciding ? sendDecision : null; },
    busy: function () { return !pop.hidden; },
    beforeReload: function () {
      var size = document.querySelector('button[data-size][aria-pressed="true"]');
      sessionStorage.setItem(KEY, JSON.stringify({ view: main.classList.contains('switch') ? 'switch' : 'side', current: current, size: size && size.dataset.size }));
    },
    rendered: function (state) { pinState = state; syncPins(); }
  });
  function send(method, params, what, done) { conv.send(method, params, what, done); }
  var say = conv.say, noteBox = conv.noteBox, noteBtn = conv.noteBtn;
  function asText() {
    var lines = [], log = conv.log();
    var dec = log.filter(function (x) { return x.action === 'decide'; }).pop();
    if (dec) lines.push('I decide: ' + (dec.label || dec.option) + (dec.carries && dec.carries.length ? ', with comments ' +
      dec.carries.map(function (id) { var x = byId(id); return x ? x.n : '?'; }).join(', ') : '') + '.' + (dec.note ? ' ' + dec.note : ''));
    labels.forEach(function (v) { if (verdicts[v]) lines.push(v + ': ' + (verdicts[v] === 'up' ? 'good' : 'not good') + '.'); });
    items.forEach(function (it) {
      var t = it.target || {};
      lines.push(it.n + '. ' + it.version + ', ' + (t.words || t.text ? '"' + (t.words || t.text).slice(0, 60) + '"' : t.selector) + ': ' +
                 (it.verdict ? (it.verdict === 'up' ? 'good' : 'not good') + (it.comment ? ', ' : '') : '') + (it.comment || ''));
    });
    log.forEach(function (e) { if (e.action === 'note') lines.push(e.note); });
    return lines.join('\n');
  }
  var copyBtn = document.querySelector('.notes .copy');
  copyBtn.hidden = served;
  copyBtn.addEventListener('click', function () {
    navigator.clipboard.writeText(asText()).then(function () { say('Copied. Paste it in the chat with the agent.'); },
      function () { say('Could not copy. Select the conversation and copy it by hand.', true); });
  });
  // Decide: one confirmed decision, sent with the open comments that come with it and the message as its note.
  // The Send button becomes Confirm while the decision panel is open, so the same place sends both.
  var decideBtn = document.querySelector('.decide-btn'), panel = document.querySelector('.decide');
  var beforeAfter = labels.length === 2 && labels[0].toLowerCase() === 'before' && labels[1].toLowerCase() === 'after';
  var OPTIONS = beforeAfter ? [['Ship After', 'After'], ['Keep Before', 'Before']]
    : labels.map(function (l) { return ['Build ' + l, l]; }).concat([['Combine versions (say how below)', 'combine']]);
  OPTIONS.push(['None of these (say why below)', 'none']);
  function openItems() {
    return items.filter(function (it) { return pinState[it.id] !== 'accepted' && pinState[it.id] !== 'done'; });
  }
  function setDeciding(on) {
    deciding = on; panel.hidden = !on; decideBtn.setAttribute('aria-expanded', String(on));
    decideBtn.textContent = on ? 'Cancel' : 'Decide…';
    noteBtn.textContent = on ? 'Confirm decision' : 'Send';
    if (!on) return;
    var box = panel.querySelector('.dopts'); box.replaceChildren();
    OPTIONS.forEach(function (o, k) {
      var lab = el('label', 'dopt'), r = el('input'); r.type = 'radio'; r.name = 'decision'; r.value = o[1]; if (!k) r.checked = true;
      lab.append(r, ' ' + o[0]); box.append(lab);
    });
    var open = openItems(), carry = panel.querySelector('.carry'); carry.replaceChildren();
    if (open.length) {
      carry.append(el('p', 'menu-h', 'Comes with your open comments'));
      open.forEach(function (it) { carry.append(el('p', 'carried', it.n + '. ' + (it.comment || (it.verdict === 'up' ? 'Good' : 'Not good')))); });
    }
    noteBox.focus();
  }
  decideBtn.addEventListener('click', function () { setDeciding(!deciding); });
  function sendDecision() {
    var pick = panel.querySelector('input[name="decision"]:checked'), note = noteBox.value.trim();
    if ((pick.value === 'combine' || pick.value === 'none') && !note) { say('Say how to combine them, or why none fits, in the message.', true); return noteBox.focus(); }
    var label = pick.parentElement.textContent.trim();
    send('decide', { id: 'd-' + Date.now().toString(36), option: pick.value, label: label,
                     carries: openItems().map(function (it) { return it.id; }), note: note || null },
         'Decision', function () { noteBox.value = ''; setDeciding(false); });
  }
  conv.start();
  if (served) {
    try {
      var kept = JSON.parse(sessionStorage.getItem(KEY) || 'null');
      sessionStorage.removeItem(KEY);
      if (kept) {
        var sb = kept.size && document.querySelector('button[data-size="' + kept.size + '"]'); if (sb) sb.click();
        if (kept.current < labels.length) current = kept.current;
        view(labels.length > 1 ? kept.view : 'side'); show(current);
      }
    } catch (e) {}
  }
})();
