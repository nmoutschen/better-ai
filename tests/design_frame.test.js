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
