const test = require('node:test');
const assert = require('node:assert/strict');
const { read, between } = require('./harness');

function create(version, driven) {
  let frame;
  const node = (tag, cls, text, attrs) => {
    const result = { attrs: { ...attrs }, append() {}, setAttribute(k, v) { this.attrs[k] = v; } };
    if (tag === 'iframe') frame = result;
    return result;
  };
  const funcs = between(read('design', 'canvas.js'), '  // One version at one screen size, with its label and buttons. Full size shows it alone, so it needs another button.', '  // The controls that depend');
  new Function('node', 'pageDriven', 'location', 'version', funcs + '; figure(0, version, {w:800,h:600}, false, false);')(
    node, driven, { origin: 'http://127.0.0.1:31337' }, version);
  return frame;
}

test('a driven local mock gets an opaque sandbox and a fixed bridge before the supplied markup', () => {
  const html = '<p>First version</p>';
  const frame = create({ label: 'First', srcdoc: html }, true);
  assert.equal(frame.attrs.sandbox, 'allow-scripts');
  const prefix = frame.srcdoc.split(html)[0];
  assert.match(prefix, /Content-Security-Policy/i);
  assert.match(prefix, /script-src http:\/\/127\.0\.0\.1:31337\/mock-frame\.js/);
  assert.match(prefix, /src="http:\/\/127\.0\.0\.1:31337\/mock-frame\.js"/);
});

test('a remote driven mock has no script or origin permission', () => {
  const frame = create({ label: 'Site', src: 'https://example.org/' }, true);
  assert.equal(frame.attrs.sandbox, '');
  assert.equal(frame.attrs.src, 'https://example.org/');
});

test('fallback and rendered pages retain their ordinary mock document', () => {
  const html = '<p>Local</p>';
  const frame = create({ label: 'First', srcdoc: html }, false);
  assert.equal(frame.attrs.sandbox, undefined);
  assert.equal(frame.srcdoc, html);
});

test('only a registered opaque local frame can bind its document port once', () => {
  const source = read('design', 'canvas.js');
  const handler = between(source, "  if (typeof pageDriven !== 'undefined' && pageDriven) window.addEventListener", '  function openPop');
  const frame = { contentWindow: {}, dataset: {bridge: 'one-shot'} };
  let listen, views = 0, messages = 0;
  new Function('listen', 'main', 'ports', 'offsets', 'sendView', 'fromMock', 'listen' + handler)(
    (type, fn) => { listen = fn; }, {querySelectorAll: () => [frame]}, new WeakMap(), new WeakMap(),
    () => views++, () => messages++);
  const event = {origin: 'null', source: frame.contentWindow, data: {kind: 'design-frame', key: 'one-shot'}, ports: [{}]};
  for (const changes of [{origin: 'http://elsewhere'}, {source: {}}, {data: {kind: 'design-frame', key: 'x'}}, {ports: []}]) listen({...event, ...changes});
  assert.equal(views, 0);
  listen(event);
  listen({...event, ports: [{}]});
  assert.equal(views, 1);
  event.ports[0].onmessage({data: {}});
  assert.equal(messages, 1);
});

test('only bounded local click details open a draft and parent supplies the version', () => {
  const fn = new Function('openPop', 'byId', 'pop', 'menu', 'labels', 'commenting', between(read('design', 'canvas.js'), '  function fraction', '  if (typeof pageDriven') .replace(/^\(n\)/, 'function fraction(n)') + ';return fromMock');
  const calls = [], item = {id: 'x', version: 'A'}, frame = {dataset: {i: '0'}, clientWidth: 320, clientHeight: 800};
  const handle = fn((...args) => calls.push(args), id => id === 'x' && item, {hidden: true}, {hidden: true}, ['A'], true);
  const click = {kind: 'click', x: 13, y: 17, selector: '#lead', text: 'Lead', tag: 'p', fx: 0, fy: 1};
  for (const changes of [{kind:'rpc'}, {kind:'approve'}, {x: Infinity}, {x: 321}, {fy: '1'}, {id: 'absent'}, {text: {}}]) handle(frame, {...click, ...changes});
  assert.equal(calls.length, 0);
  handle(frame, {...click, version: 'B', method: 'approve'});
  assert.deepEqual(calls[0], [frame, null, {fx:0, fy:1}, 13, 17, null, {selector:'#lead', tag:'p', text:'Lead'}]);
  handle(frame, {...click, id:'x'});
  assert.equal(calls[1][5], item);
});

test('the packaged bridge uses its port for clicks, pin editing, shortcuts and scroll', () => {
  const vm = require('node:vm');
  const handlers = {}, messages = [], added = [], updates = [], sent = [];
  const style = {setProperty() {}};
  class Element {
    constructor(name) { this.localName = name; this.tagName = name.toUpperCase(); this.dataset = {}; this.style = {}; this.textContent = ''; this.classList = {add() {}, remove() {}}; }
    getAttribute() { return ''; }
    closest() { return null; }
    getBoundingClientRect() { return {left:0, top:0, width:100, height:100}; }
    contains(el) { return this === el; }
    remove() { this.removed = true; }
  }
  const element = new Element('p'), body = new Element('body');
  element.parentElement = body;
  body.append = pin => added.push(pin);
  const channel = {port1: {postMessage: m => messages.push(m)}, port2: {}};
  const parent = {postMessage: (...args) => sent.push(args)};
  const doc = {
    currentScript: {src: 'http://127.0.0.1:3200/mock-frame.js', dataset: {key: 'abc'}, remove() {}},
    head: {append() {}}, body, documentElement: {style, classList: {toggle() {}}, scrollHeight: 1000},
    createElement: tag => new Element(tag), querySelector: () => element, querySelectorAll: () => [],
    addEventListener: (name, fn) => {handlers[name] = fn;},
  };
  const win = {parent, innerHeight:500, scrollY:250, scrollX:0, addEventListener: doc.addEventListener, scrollTo: (...args) => updates.push(args)};
  element.ownerDocument = doc; doc.defaultView = win; win.getComputedStyle = () => ({backgroundImage:'none'});
  vm.runInNewContext(read('design', 'mock-frame.js'), {window:win, document:doc, URL, Element, CSS:{escape: x => x}, MessageChannel: function () {return channel;}});
  handlers.DOMContentLoaded();
  assert.equal(sent[0][0].kind, 'design-frame');
  assert.equal(sent[0][1], 'http://127.0.0.1:3200');
  assert.equal(sent[0][2][0], channel.port2);
  const event = {target:element, clientX:10, clientY:30, preventDefault() {}, stopPropagation() {}};
  handlers.click(event);
  assert.equal(messages.length, 0);
  handlers.click({...event, isTrusted:true});
  assert.equal(messages[0].selector, 'body > p:nth-of-type(1)');
  assert.equal(messages[0].fy, .3);
  channel.port1.onmessage({data: {kind:'view', commenting:false, css:'', inverseScale:1, pins:[{id:'c1', n:1, selector:'p', spot:{fx:.1, fy:.3}, state:'working'}]}});
  assert.equal(added[0].dataset.state, 'working');
  assert.equal(added[0].style.top, '280px');
  handlers.click({...event, isTrusted:true, target:added[0]});
  assert.equal(messages.at(-1).id, 'c1');
  handlers.keydown({...event, isTrusted:true, key:'c'});
  assert.equal(messages.at(-1).key, 'c');
  handlers.scroll();
  assert.equal(messages.at(-1).fraction, .5);
  channel.port1.onmessage({data:{kind:'scroll', fraction:.2}});
  assert.deepEqual(updates, [[0,100]]);
});
