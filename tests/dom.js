// A small stand-in DOM for the tests of the Conversation panel and of the pages that use it: elements keep their
// children, attributes, listeners and focus, parse the simple HTML the pages write, and answer the simple selectors the
// pages use (tag, .class, #id, [attr], [attr="v"], and one space between parts). The shell's parts the panel uses are
// in shellDocument; panelOn runs pageConversation on it. A page's own code runs with mixedDocument: the stand-in for
// what the shell has, and harness.js's stand-ins for the rest. Used by tests/*.test.js.
const { stand, loadPage } = require('./harness');

const ENTITY = { amp: '&', lt: '<', gt: '>', quot: '"', '#39': "'", nbsp: ' ', hellip: '…' };
const decode = t => t.replace(/&(amp|lt|gt|quot|#39|nbsp|hellip);/g, (_, e) => ENTITY[e]);
const VOID = new Set(['br', 'hr', 'img', 'input', 'meta', 'link', 'wbr', 'source', 'col']);
// HTML as stand-in nodes: elements with their attributes, text with its entities read.
function parseHTML(doc, html) {
  const top = { kids: [] }, stack = [top];
  const re = /<!--[\s\S]*?-->|<(\/?)([a-zA-Z][\w-]*)((?:[^>"']|"[^"]*"|'[^']*')*?)(\/?)>|[^<]+|</g;
  let m;
  while ((m = re.exec(html))) {
    const here = stack[stack.length - 1];
    if (m[0].startsWith('<!--')) continue;
    if (!m[2]) { here.kids.push({ node: doc.createTextNode(decode(m[0])) }); continue; }
    const tag = m[2].toLowerCase();
    if (m[1]) { for (let i = stack.length - 1; i > 0; i--) if (stack[i].tag === tag) { stack.length = i; break; } continue; }
    const x = doc.createElement(tag), attrs = /([^\s=/]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g;
    let a;
    while ((a = attrs.exec(m[3]))) {
      const v = decode(a[2] ?? a[3] ?? a[4] ?? '');
      if (a[1] === 'class') x.className = v; else if (a[1] === 'hidden') x.hidden = true; else x.setAttribute(a[1], v);
    }
    const entry = { node: x, tag, kids: [] };
    here.kids.push(entry);
    if (!m[4] && !VOID.has(tag)) stack.push(entry);
  }
  // Each element gets the nodes collected under it.
  const build = list => list.map(k => { if (k.kids && k.kids.length) k.node.append(...build(k.kids)); return k.node; });
  return build(top.kids);
}

class El {
  constructor(doc, tag) {
    Object.assign(this, { ownerDocument: doc, tagName: tag.toUpperCase(), nodeType: 1, children: [], parentNode: null, attributes: {},
      dataset: {}, className: '', hidden: false, value: '', listeners: {}, style: {}, scrollTop: 0, scrollHeight: 0, clientHeight: 0,
      disabled: false });
  }
  get childNodes() { return this.children; }
  get firstChild() { return this.children[0] || null; }
  get classList() {
    const n = this, list = () => n.className.split(/\s+/).filter(Boolean);
    return { contains: c => list().includes(c), add: c => { if (!list().includes(c)) n.className = list().concat(c).join(' '); },
      remove: c => { n.className = list().filter(x => x !== c).join(' '); },
      toggle: (c, on) => { if (on === undefined ? !list().includes(c) : on) n.classList.add(c); else n.classList.remove(c); } };
  }
  get textContent() { return this.children.map(c => c.textContent).join(''); }
  set textContent(v) { this.children.forEach(c => { c.parentNode = null; }); this.children = []; this._html = ''; if (String(v)) this.append(String(v)); }
  set innerHTML(v) { this.textContent = ''; this._html = String(v); this.append(...parseHTML(this.ownerDocument, String(v))); }
  insertAdjacentHTML(where, html) {
    const nodes = parseHTML(this.ownerDocument, html);
    if (where === 'beforeend') this.append(...nodes);
    else if (where === 'afterbegin') this.prepend(...nodes);
    else if (where === 'beforebegin') nodes.forEach(n => this.parentNode.insertBefore(n, this));
    else nodes.reverse().forEach(n => this.after(n));
  }
  hasAttribute(k) { return this.getAttribute(k) !== null; }
  get outerHTML() { const t = this.tagName.toLowerCase(); return '<' + t + '>' + this.textContent + '</' + t + '>'; }
  get innerHTML() { return this._html || ''; }
  get id() { return this.attributes.id || ''; }
  set id(v) { this.attributes.id = v; }
  set htmlFor(v) { this.attributes.for = v; }
  get htmlFor() { return this.attributes.for; }
  set type(v) { this.attributes.type = v; }
  get type() { return this.attributes.type; }
  setAttribute(k, v) { if (k.startsWith('data-')) this.dataset[k.slice(5).replace(/-(\w)/g, (_, c) => c.toUpperCase())] = String(v); else this.attributes[k] = String(v); }
  getAttribute(k) {
    if (k === 'class') return this.className;
    if (k.startsWith('data-')) { const v = this.dataset[k.slice(5).replace(/-(\w)/g, (_, c) => c.toUpperCase())]; return v === undefined ? null : v; }
    return k in this.attributes ? this.attributes[k] : null;
  }
  removeAttribute(k) { delete this.attributes[k]; }
  adopt(n) {
    if (typeof n === 'string' || typeof n === 'number') n = this.ownerDocument.createTextNode(String(n));
    if (n.parentNode) n.remove();
    n.parentNode = this;
    return n;
  }
  append(...nodes) { nodes.forEach(n => { const k = this.adopt(n); this.children.push(k); }); }
  appendChild(n) { this.append(n); return n; }
  prepend(...nodes) { nodes.reverse().forEach(n => { const k = this.adopt(n); this.children.unshift(k); }); }
  insertBefore(n, ref) { const k = this.adopt(n), i = this.children.indexOf(ref); this.children.splice(i < 0 ? this.children.length : i, 0, k); return n; }
  before(n) { this.parentNode.insertBefore(n, this); }
  after(n) { const p = this.parentNode, i = p.children.indexOf(this); p.insertBefore(n, p.children[i + 1] || null); }
  remove() { if (this.parentNode) { const p = this.parentNode; p.children.splice(p.children.indexOf(this), 1); this.parentNode = null; } }
  replaceChildren(...nodes) { this.children.slice().forEach(c => c.remove && c.remove()); this._html = ''; this.append(...nodes); }
  contains(n) { for (; n; n = n.parentNode) if (n === this) return true; return false; }
  addEventListener(type, fn) { (this.listeners[type] = this.listeners[type] || []).push(fn); }
  dispatch(type, extra = {}) {
    const ev = Object.assign({ type, target: this, defaultPrevented: false, preventDefault() { ev.defaultPrevented = true; }, stopPropagation() {} }, extra);
    for (let n = this; n; n = n.parentNode) (n.listeners && n.listeners[type] || []).forEach(f => f(ev));
    return ev;
  }
  click() { if (!this.disabled) this.dispatch('click'); }
  key(key, extra = {}) { return this.dispatch('keydown', Object.assign({ key }, extra)); }
  input(value) { this.value = value; this.selectionStart = this.selectionEnd = value.length; this.dispatch('input'); }
  focus() { this.ownerDocument.activeElement = this; }
  blur() { if (this.ownerDocument.activeElement === this) this.ownerDocument.activeElement = this.ownerDocument.body; }
  setSelectionRange(a, b) { this.selectionStart = a; this.selectionEnd = b; }
  scrollIntoView() {}
  scrollTo(o) { this.scrolledTo = o; this.scrollTop = o.top; }
  getBoundingClientRect() { return this.rect || { top: 0, bottom: 0, height: 0 }; }
  matches(sel) { return matchesSelector(this, sel); }
  closest(sel) { for (let n = this; n && n.nodeType === 1; n = n.parentNode) if (n.matches(sel)) return n; return null; }
  descendants() { return this.children.filter(c => c.nodeType === 1).flatMap(c => [c].concat(c.descendants())); }
  querySelectorAll(sel) { return this.descendants().filter(n => sel.split(',').some(s => n.matches(s.trim()))); }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
}
function matchesOne(n, part) {
  const re = /([.#]?[\w-]+)|\[([\w-]+)(?:="([^"]*)")?\]/g;
  let m;
  while ((m = re.exec(part))) {
    if (m[1]) {
      const s = m[1];
      if (s[0] === '.' && !n.classList.contains(s.slice(1))) return false;
      if (s[0] === '#' && n.id !== s.slice(1)) return false;
      if (/^\w/.test(s) && n.tagName !== s.toUpperCase()) return false;
    } else {
      const v = n.getAttribute(m[2]);
      if (v === null || (m[3] !== undefined && v !== m[3])) return false;
    }
  }
  return true;
}
function matchesSelector(n, sel) {
  const parts = sel.trim().split(/\s+/);
  if (!matchesOne(n, parts.pop())) return false;
  for (let p = n.parentNode; parts.length && p && p.nodeType === 1; p = p.parentNode) if (matchesOne(p, parts[parts.length - 1])) parts.pop();
  return !parts.length;
}
function makeDocument() {
  const doc = { activeElement: null };
  doc.createElement = tag => new El(doc, tag);
  doc.createTextNode = text => ({ nodeType: 3, textContent: text, parentNode: null, remove() { const p = this.parentNode; if (p) { p.children.splice(p.children.indexOf(this), 1); this.parentNode = null; } } });
  doc.body = doc.createElement('body');
  doc.activeElement = doc.body;
  doc.contains = n => doc.body.contains(n);
  doc.querySelectorAll = sel => doc.body.querySelectorAll(sel);
  doc.querySelector = sel => doc.body.querySelector(sel);
  doc.getElementById = id => doc.body.querySelector('#' + id);
  return doc;
}
// The shell's parts the panel uses, as shell.html has them.
function shellDocument() {
  const doc = makeDocument(), make = (tag, attrs = {}, kids = []) => {
    const x = doc.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => (k === 'class' ? (x.className = v) : k === 'text' ? (x.textContent = v) : x.setAttribute(k, v)));
    x.append(...kids);
    return x;
  };
  doc.body.append(
    make('header', { class: 'bar--stats' }, [make('div', { class: 'stats', id: 'status', text: 'Loading…' })]),
    make('p', { class: 'offline', id: 'offline' }),
    make('aside', { class: 'notes' }, [
      make('div', { class: 'notes-top' }, [make('div', { class: 'seg' }, [
        make('button', { type: 'button', 'data-filter': 'all', 'aria-pressed': 'false', text: 'All' }),
        make('button', { type: 'button', 'data-filter': 'open', 'aria-pressed': 'true', text: 'Open' })])]),
      make('p', { class: 'empty', id: 'empty', text: 'Nothing yet.' }),
      make('ol', { class: 'thread', id: 'thread' }),
      make('form', { class: 'composer', id: 'noteform' }, [
        make('p', { class: 'unwatched', id: 'unwatched' }),
        make('textarea', { id: 'note' }),
        make('div', { class: 'send' }, [make('button', { type: 'submit', class: 'btn', text: 'Send' }), make('p', { class: 'status' })])])]),
    make('div', { class: 'toast', id: 'toast' }));
  doc.querySelector('.offline').hidden = true;
  return doc;
}



// What a page's own code sees as its document: the stand-in shell's elements where it has them, and a stand-in that
// takes anything for the rest, so a page runs whole without its main view.
// ABSENT names the ids the page must find missing: page-data on a served page, and the pop-up until one opens.
function mixedDocument(doc, absent = ['page-data', 'pop']) {
  return new Proxy(stand(), {
    get: (t, k) => {
      if (k === 'createElement' || k === 'createTextNode') return doc[k];
      if (k === 'getElementById') return id => doc.getElementById(id) || (absent.includes(id) ? null : stand());
      if (k === 'querySelector') return sel => doc.querySelector(sel) || stand();
      if (k === 'querySelectorAll') return sel => doc.querySelectorAll(sel);
      if (k === 'activeElement' || k === 'body') return doc[k];
      if (k === 'contains') return n => doc.contains(n);
      return t[k];
    },
  });
}

// pageConversation on the stand-in shell, run by the shared page.js in its own context. LOG, if given, is fed with
// setLog; EXTRA is the panel's options, or a function of the document that gives them (null: no panel, only the
// context); SETUP(context, conv) runs before the log is fed. Returns the panel and helpers to find its rows, move its
// clock and read what it sent.
function panelOn(log, extra = {}, { config = { agent: 'coordinator' }, setup, document: given, globals } = {}) {
  const document = given || shellDocument(), timers = [];
  let clock = 0;
  const pageConfigEl = { textContent: JSON.stringify(config) };
  const getById = document.getElementById;
  document.getElementById = id => (id === 'page-config' ? pageConfigEl : getById(id));
  const context = loadPage(Object.assign({
    document, Date, JSON, Object, Math, String, Array, isNaN, Number, Promise,
    setTimeout: (f, ms) => { timers.push({ f, at: clock + (ms || 0) }); return timers.length; },
    clearTimeout: id => { if (timers[id - 1]) timers[id - 1].f = null; },
    requestAnimationFrame: f => f(), CSS: { escape: s => s }, location: { hash: '' },
    sessionStorage: { getItem() { return null; }, setItem() {}, removeItem() {} }, history: { replaceState() {} },
    fetch: () => new Promise(() => {}),
  }, globals));
  const conv = extra === null ? null
    : context.pageConversation(Object.assign({ served: false }, typeof extra === 'function' ? extra(document) : extra));
  if (setup) setup(context, conv);
  if (log && conv) conv.setLog(log);
  const $ = sel => document.querySelector(sel), $$ = sel => document.querySelectorAll(sel);
  const rows = () => $$('li.trow');
  const rowOf = id => rows().find(li => li.dataset.id === id);
  const tick = ms => {
    clock += ms;
    for (let due; (due = timers.find(t => t.f && t.at <= clock));) { const f = due.f; due.f = null; f(); }
  };
  const filter = name => $(`[data-filter="${name}"]`).click();
  const label = n => n.getAttribute('aria-label');
  const sent = () => conv.log().slice((log || []).length);
  return { document, context, conv, $, $$, rows, rowOf, tick, filter, label, sent };
}

const text = n => n.textContent.replace(/\s+/g, ' ').trim();
const actions = li => li.querySelectorAll('.tacts button');

module.exports = { El, parseHTML, makeDocument, shellDocument, mixedDocument, panelOn, text, actions };
