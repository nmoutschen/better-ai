// A small stand-in for a browser document, enough to run the shared page.js for real: elements with children, classes,
// attributes, listeners and the selectors page.js uses (tag, .class, #id, [attr], [attr="value"], compounds, a space and
// ">"), and a click that goes through the capture listeners on the document, the target and its parents, as a browser does.
// Used by tests/page_agents_panel.test.js. No real browser is opened.

class El {
  constructor(tag, doc) {
    this.tag = tag; this.doc = doc; this.attrs = {}; this.children = []; this.parent = null; this.listeners = {};
    this.dataset = {}; this.style = {}; this.hidden = false; this.disabled = false; this.className = ''; this._html = null;
  }
  get id() { return this.attrs.id || ''; }
  set id(v) { this.attrs.id = v; }
  get type() { return this.attrs.type; }
  set type(v) { this.attrs.type = v; }
  get textContent() { return this.children.map(c => (typeof c === 'string' ? c : c.textContent)).join(''); }
  set textContent(v) { this.children.forEach(c => { if (typeof c !== 'string') c.parent = null; }); this.children = v === '' ? [] : [String(v)]; this._html = null; }
  get innerHTML() { return this._html !== null ? this._html : this.children.map(c => (typeof c === 'string' ? c : c.outer)).join(''); }
  set innerHTML(v) { this.children = []; this._html = String(v); }
  get outer() { return '<' + this.tag + '>' + this.innerHTML + '</' + this.tag + '>'; }
  get classList() {
    const n = this, list = () => n.className.split(/\s+/).filter(Boolean);
    return {
      add: (...c) => { n.className = Array.from(new Set(list().concat(c))).join(' '); },
      remove: (...c) => { n.className = list().filter(x => c.indexOf(x) < 0).join(' '); },
      toggle: (c, on) => { const has = list().indexOf(c) >= 0, want = on === undefined ? !has : !!on; if (want && !has) n.classList.add(c); if (!want && has) n.classList.remove(c); },
      contains: c => list().indexOf(c) >= 0,
    };
  }
  _adopt(n) { if (typeof n !== 'string') { if (n.parent) n.parent.children.splice(n.parent.children.indexOf(n), 1); n.parent = this; } return n; }
  append(...nodes) { this._html = null; nodes.forEach(n => this.children.push(this._adopt(n))); }
  appendChild(n) { this.append(n); return n; }
  insertBefore(n, ref) {
    this._html = null; this._adopt(n);
    const i = ref ? this.children.indexOf(ref) : -1;
    if (i < 0) this.children.push(n); else this.children.splice(i, 0, n);
    return n;
  }
  replaceChildren(...nodes) { this.children.forEach(c => { if (typeof c !== 'string') c.parent = null; }); this.children = []; this._html = null; this.append(...nodes); }
  remove() { if (this.parent) { this.parent.children.splice(this.parent.children.indexOf(this), 1); this.parent = null; } }
  setAttribute(k, v) { this.attrs[k] = String(v); if (k === 'class') this.className = String(v); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  hasAttribute(k) { return k in this.attrs; }
  removeAttribute(k) { delete this.attrs[k]; }
  addEventListener(type, fn, capture) { (this.listeners[type] = this.listeners[type] || []).push({ fn, capture: !!(capture === true || (capture && capture.capture)) }); }
  focus() { this.doc.activeElement = this; this.focused = (this.focused || 0) + 1; }
  scrollIntoView() {}
  get firstChild() { return this.children[0] || null; }
  contains(n) { for (let x = n; x; x = x.parent) if (x === this) return true; return false; }
  get elements() { return this.children.filter(c => typeof c !== 'string'); }
  closest(sel) { for (let x = this; x && x.tag; x = x.parent) if (matchesAny(x, sel)) return x; return null; }
  querySelector(sel) { return queryAll(this, sel)[0] || null; }
  querySelectorAll(sel) { return queryAll(this, sel); }
  get isConnected() { return this.doc.body.contains(this); }
}

function parseCompound(text) {
  const out = { tag: null, classes: [], id: null, attrs: [] };
  const re = /([.#]?)([\w-]+)|\[([\w-]+)(?:="([^"]*)")?\]/g;
  let m;
  while ((m = re.exec(text))) {
    if (m[3]) out.attrs.push([m[3], m[4]]);
    else if (m[1] === '.') out.classes.push(m[2]);
    else if (m[1] === '#') out.id = m[2];
    else out.tag = m[2];
  }
  return out;
}
function matchCompound(el, c) {
  if (c.tag && el.tag !== c.tag) return false;
  if (c.id && el.id !== c.id) return false;
  const have = el.className.split(/\s+/);
  if (c.classes.some(k => have.indexOf(k) < 0)) return false;
  return c.attrs.every(([k, v]) => {
    const own = k.startsWith('data-') ? el.dataset[k.slice(5).replace(/-(\w)/g, (_, x) => x.toUpperCase())] : undefined;
    const value = own !== undefined ? own : el.attrs[k];
    return v === undefined ? value !== undefined : String(value) === v;
  });
}
function parseSelector(sel) {
  const tokens = sel.trim().replace(/\s*>\s*/g, ' > ').split(/\s+/), parts = [];
  let combinator = ' ';
  tokens.forEach(t => { if (t === '>') combinator = '>'; else { parts.push({ c: parseCompound(t), combinator }); combinator = ' '; } });
  return parts;
}
function matchesChain(el, parts, i) {
  if (!matchCompound(el, parts[i].c)) return false;
  if (i === 0) return true;
  if (parts[i].combinator === '>') return !!el.parent && el.parent.tag !== undefined && matchesChain(el.parent, parts, i - 1);
  for (let p = el.parent; p && p.tag; p = p.parent) if (matchesChain(p, parts, i - 1)) return true;
  return false;
}
function matchesAny(el, sel) { return sel.split(',').some(s => matchesChain(el, parseSelector(s), parseSelector(s).length - 1)); }
function queryAll(root, sel) {
  const out = [];
  (function walk(n) {
    n.elements.forEach(c => { if (matchesAny(c, sel)) out.push(c); walk(c); });
  })(root);
  return out;
}

function makeDocument() {
  const doc = { listeners: {}, title: '', activeElement: null };
  doc.createElement = tag => new El(tag, doc);
  doc.createTextNode = text => String(text);
  doc.body = new El('body', doc);
  doc.documentElement = new El('html', doc);
  doc.getElementById = id => queryAll(doc.body, '#' + id)[0] || null;
  doc.querySelector = sel => doc.body.querySelector(sel);
  doc.querySelectorAll = sel => doc.body.querySelectorAll(sel);
  doc.contains = n => !!n && doc.body.contains(n);
  doc.addEventListener = (type, fn, capture) => { (doc.listeners[type] = doc.listeners[type] || []).push({ fn, capture: !!(capture === true || (capture && capture.capture)) }); };
  return doc;
}

// A browser's event path for TYPE on TARGET: capture listeners on the document, then the target and its parents, then the
// document's own. EVENT's fields are added; stopPropagation ends the path.
function fire(doc, target, type, extra) {
  const event = Object.assign({ type, target, stopped: false, defaultPrevented: false, key: '', shiftKey: false,
    preventDefault() { this.defaultPrevented = true; }, stopPropagation() { this.stopped = true; } }, extra);
  const run = (list, capture) => (list || []).filter(l => l.capture === capture).forEach(l => { if (!event.stopped) l.fn(event); });
  run(doc.listeners[type], true);
  for (let n = target; n && n.tag && !event.stopped; n = n.parent) run(n.listeners[type], false);
  run(doc.listeners[type], false);
  return event;
}
// A press reaches only a control that is on the page and not disabled.
const click = (doc, target, extra) => (target.disabled || !target.isConnected ? null : fire(doc, target, 'click', extra));

// Builds an element tree: h(doc, 'div.work#id', {attr: 'v'}, child, child...).
function h(doc, spec, attrs, ...kids) {
  const m = /^(\w+)((?:[.#][\w-]+)*)$/.exec(spec), el = doc.createElement(m[1]);
  (m[2].match(/[.#][\w-]+/g) || []).forEach(p => { if (p[0] === '.') el.className = (el.className + ' ' + p.slice(1)).trim(); else el.id = p.slice(1); });
  Object.keys(attrs || {}).forEach(k => { if (k === 'hidden') el.hidden = !!attrs[k]; else el.setAttribute(k, attrs[k]); });
  kids.forEach(k => { if (k !== null && k !== undefined) el.append(k); });
  return el;
}
// Every element below ROOT, in order.
const all = root => queryAll(root, '*');

module.exports = { El, makeDocument, fire, click, h, all, queryAll, matchesAny };
