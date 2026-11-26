// Both the canvas and its opaque local mocks use the same description for a comment anchor.
var canvasDescribe = (function () {
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
  function describe(el, cx, cy, description) {
    var doc = el.ownerDocument, win = doc.defaultView, r = el.getBoundingClientRect(), d = description(el, null, elementText(el), 120);
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
  return describe;
})();

// Runs only in a local Design mock's opaque sandbox. Only this packaged script can execute there.
// The port stays with this document if a link navigates the iframe to another document.
(function () {
  const script = document.currentScript;
  const key = script && script.dataset.key;
  if (!key || window.parent === window) return;
  const origin = new URL(script.src).origin;
  script.remove();
  const channel = new MessageChannel();
  const port = channel.port1;
  let commenting = true, quietUntil = 0;
  const pins = new Map();
  function selector(el) {
    const path = [];
    while (el && el !== document.body && el !== document.documentElement) {
      if (el.id && document.querySelectorAll('#' + CSS.escape(el.id)).length === 1) {
        path.unshift('#' + CSS.escape(el.id));
        return path.join(' > ');
      }
      let n = 1, sibling = el;
      while ((sibling = sibling.previousElementSibling)) if (sibling.localName === el.localName) n++;
      path.unshift(CSS.escape(el.localName) + ':nth-of-type(' + n + ')');
      el = el.parentElement;
    }
    return ['body'].concat(path).join(' > ');
  }
  function position(pin, target, spot) {
    const r = target.getBoundingClientRect();
    pin.style.left = (r.left + window.scrollX + spot.fx * r.width) + 'px';
    pin.style.top = (r.top + window.scrollY + spot.fy * r.height) + 'px';
  }
  function scrollRange() { return Math.max(0, document.documentElement.scrollHeight - window.innerHeight); }
  function render(list) {
    const kept = new Set();
    for (const item of list) {
      let target;
      try { target = document.querySelector(item.selector); } catch (e) { continue; }
      if (!target) continue;
      kept.add(item.id);
      const pin = pins.get(item.id) || document.createElement('span');
      if (!pins.has(item.id)) {
        pin.className = 'db-pin';
        pins.set(item.id, pin);
        document.body.append(pin);
      }
      pin.textContent = item.n;
      pin.dataset.state = item.state;
      pin.title = 'Comment ' + item.n;
      position(pin, target, item.spot);
    }
    for (const [id, pin] of pins) if (!kept.has(id)) { pin.remove(); pins.delete(id); }
  }
  document.addEventListener('DOMContentLoaded', () => {
    const style = document.createElement('style');
    document.head.append(style);
    port.onmessage = e => {
      const m = e.data;
      if (m.kind === 'view') {
        commenting = m.commenting;
        document.documentElement.classList.toggle('db-commenting', commenting);
        style.textContent = m.css;
        document.documentElement.style.setProperty('--db-s', String(m.inverseScale));
        render(m.pins);
      } else if (m.kind === 'scroll') {
        quietUntil = Date.now() + 150;
        window.scrollTo(0, m.fraction * scrollRange());
      } else if (m.kind === 'reveal') {
        const pin = pins.get(m.id);
        if (pin) {
          pin.classList.add('db-flash');
          window.scrollTo({top: Math.max(0, parseFloat(pin.style.top) - window.innerHeight / 3), behavior: 'smooth'});
          setTimeout(() => pin.classList.remove('db-flash'), 2800);
        }
      }
    };
    document.addEventListener('click', e => {
      if (!e.isTrusted || !(e.target instanceof Element)) return;
      const found = Array.from(pins).find(entry => entry[1].contains(e.target));
      if (!commenting && !found) return;
      e.preventDefault();
      e.stopPropagation();
      const el = e.target, r = el.getBoundingClientRect();
      const message = { kind: 'click', x: e.clientX, y: e.clientY };
      if (found) message.id = found[0];
      else {
        const target = canvasDescribe(el, e.clientX, e.clientY, (node, root, text, limit) => ({
          selector: selector(node), tag: node.localName, text: String(text).replace(/\s+/g, ' ').trim().slice(0, limit)
        }));
        Object.assign(message, target);
        message.fx = Math.min(1, Math.max(0, (e.clientX - r.left) / Math.max(1, r.width)));
        message.fy = Math.min(1, Math.max(0, (e.clientY - r.top) / Math.max(1, r.height)));
      }
      port.postMessage(message);
    }, true);
    document.addEventListener('keydown', e => {
      if (!e.isTrusted || e.defaultPrevented || e.ctrlKey || e.altKey || e.metaKey) return;
      if (e.key === 'Escape' || (e.key.toLowerCase() === 'c' && !e.target.closest('input,textarea,select,[contenteditable]')))
        port.postMessage({kind: 'key', key: e.key.toLowerCase()});
    });
    window.addEventListener('scroll', () => {
      if (Date.now() >= quietUntil) port.postMessage({kind: 'scroll', fraction: window.scrollY / Math.max(1, scrollRange())});
    }, {passive: true});
    window.parent.postMessage({kind: 'design-frame', key}, origin, [channel.port2]);
  });
})();
