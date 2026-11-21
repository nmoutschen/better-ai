'use strict';

const $ = (selector, root = document) => root.querySelector(selector);
const all = (selector, root = document) => [...root.querySelectorAll(selector)];
const byId = id => document.getElementById(id);
const text = value => String(value).replace(/[&<>"']/g, char => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[char]));
const inlineCode = value => value.split(/(`[^`]+`)/).map((part, index) =>
  index % 2 ? '<code>' + text(part.slice(1, -1)) + '</code>' : text(part)).join('');
const chip = (value, kind = '') => '<span class="chip ' + kind + '">' + text(value) + '</span>';

function table(headers, rows) {
  return '<table class="tbl"><thead><tr>' +
    headers.map(label => '<th scope="col">' + text(label) + '</th>').join('') +
    '</tr></thead><tbody>' + rows.join('') + '</tbody></table>';
}

function row(cells, attrs = '') {
  return '<tr ' + attrs + '>' + cells.map(cell => '<td>' + cell + '</td>').join('') + '</tr>';
}

function editor(label, value = '') {
  return '<form class="edit" hidden><textarea aria-label="' + text(label) + '">' + text(value) +
    '</textarea><button class="btn btn--sm" type="submit">Send to the architect</button></form>';
}

const changeButton = '<button class="btn btn--quiet btn--sm" type="button" data-edit>Change</button>';

function sourceLink(source) {
  if (source.type === 'guessed') return chip('guessed', 'guess');
  if (source.type === 'user') return 'You, on this page<br>' + text(source.at.slice(11, 16));
  const query = new URLSearchParams({file: source.type === 'request' ? 'request.md' : source.file});
  return '<a class="src" href="/source?' + text(query) + '" target="_blank" rel="noopener">' +
    (source.sentence ? text(source.sentence) : text(source.file) +
      (source.symbol ? '<br>' + text(source.symbol) : '')) + '</a>';
}

function requirementRows(requirements) {
  return requirements.map(req => row([
    '<strong>' + text(req.id) + '</strong>', text(req.kind), text(req.text) + editor('New wording for ' + req.id, req.text),
    '<span class="req-source">' + sourceLink(req.source) + '</span>',
    '<div class="row-actions">' + changeButton + (req.source.type === 'guessed' ?
      '<button class="btn btn--sm answer" type="button" data-confirm aria-label="Confirm the guess">✓</button>' : '') + '</div>'
  ], 'id="req-' + text(req.id) + '" data-record="' + text(req.id) + '"'));
}

function decisionRecords(decisions) {
  return decisions.map(decision => {
    const drivers = decision.drivers.map(id =>
      '<a class="chip req" href="#req-' + encodeURIComponent(id) + '" data-driver="' + text(id) + '">' + text(id) + '</a>'
    ).join(' ');
    const alternatives = decision.rejected.map(alt =>
      '<li><strong>' + text(alt.option) + '</strong><span class="muted">Not chosen: ' + text(alt.why) + '</span></li>'
    ).join('');
    return '<article class="dec" id="dec-' + text(decision.id) + '" data-record="' + text(decision.id) + '">' +
      '<div class="dh"><span>' + text(decision.id) + '</span><h3>' + text(decision.title) + '</h3>' + changeButton + '</div>' +
      editor('What should change in ' + decision.id) + '<p class="drv">Driven by ' + drivers + '</p>' +
      '<div class="chosen"><span class="lbl">Chosen</span><p>' + inlineCode(decision.chosen) + '</p></div>' +
      '<details class="rej"><summary>Rejected alternatives (' + decision.rejected.length +
      ')</summary><ul class="alts">' + alternatives + '</ul></details>' +
      '<p class="drawback"><span class="lbl">Main drawback</span> ' + inlineCode(decision.drawback) + '</p></article>';
  }).join('');
}

function controls(perspectives, review) {
  const segment = (label, attr, options) => '<div class="seg seg--light" role="group" aria-label="' + label + '">' +
    options.map(([key, name]) => '<button type="button" data-' + attr + '="' + text(key) +
      '" aria-pressed="false">' + text(name) + '</button>').join('') + '</div>';
  return '<div class="controls">' + segment('State', 'version', [['before', 'Before'], ['after', 'After']]) +
    (review ? segment('Findings', 'findings', [['', 'No findings'], ...perspectives.map(p => [p.name, p.name])]) : '') + '</div>';
}

function figures(versions) {
  return Object.entries(versions).map(([state, svg]) => '<div class="fig" data-state="' + state + '" hidden>' +
    (svg || '<p class="muted">This flow does not exist before the change.</p>') + '</div>').join('');
}

function perspectiveTables(perspectives, findings, parts, reviewed, removedLabels = {}) {
  const summary = table(['Perspective', 'Applicability', 'Why', 'From'], perspectives.map(p =>
    row(['<strong>' + text(p.name) + '</strong>', p.applies ? chip('Applies', 'ok') : chip('Does not apply'),
      text(p.why), '<span class="muted">' + text(p.from) + '</span>'])));
  if (!reviewed) return summary + '<p>' + chip('Review runs once you approve the design') + '</p>';
  return summary + perspectives.filter(p => p.applies).map(p => {
    const headers = ['ID', 'Part', 'Finding', 'Handled by'];
    const rows = findings.filter(f => f.perspective === p.name).map(f => {
      const links = f.parts.map(part => {
        const group = part.split('+');
        const refs = group.map(id => parts[id]);
        if (refs.some(ref => !ref)) {
          return text(group.map(id => parts[id]?.label ?? removedLabels[id]).join(' · '));
        }
        const first = refs[0];
        const icon = first.icon ? '<svg viewBox="-1 -1 16 16" width="13" height="13" aria-hidden="true">' +
          first.icon + '</svg>' : '<span aria-hidden="true">→</span>';
        const edge = refs.find(ref => ref.kind === 'edge');
        const step = refs.find(ref => ref.kind === 'step');
        const label = refs.length === 2 && edge && step ?
          edge.route + ': ' + step.description : refs.map(ref => ref.label).join(' · ');
        return '<a class="boxref ' + first.kind + '" href="#panel-' + first.view + '" data-parts="' +
          text(JSON.stringify(group)) + '" data-perspective="' + text(p.name) + '" data-badge="' + text(f.id) + '">' +
          icon + '<span>' + text(label) + '</span></a>';
      }).join('<br>');
      return row(['<strong>' + text(f.id) + '</strong>', links, text(f.text) +
        (f.confirmed ? '' : ' ' + chip('Unconfirmed', 'guess')), text(f.handled_by ?? 'Open')]);
    });
    return '<h3>' + text(p.name) + '</h3>' + (rows.length ? table(headers, rows) : '<p class="muted">No findings.</p>');
  }).join('');
}

function reviewSummary(changed, names, removed = []) {
  const rerun = names.join(', ') + (names.length === 1 ? ' runs' : ' run') + ' again';
  if (changed.length || removed.length) {
    return ((changed.length ? 'Changed since the review: ' + changed.join(', ') + '.' : '')
      + (removed.length ? ' Removed: ' + removed.join(', ') + '.' : '') + (names.length ? ' ' + rerun + '.' : '')).trim();
  }
  if (names.length) return rerun + ': not reviewed yet.';
  return 'Nothing changed since the review.';
}

function threadComment(log, id) {
  const event = log.findLast(event => (event.type === 'comment' && event.id === id) || (event.type === 'delete' && event.to === id));
  return event?.type === 'comment' && byId(event.on?.id) ? event : undefined;
}

function start(data) {
  const view = $('.view');
  const tabs = all('.tabs [role="tab"]');
  const panel = key => byId('panel-' + key);
  const pop = $('.pop');
  const reviewMenu = $('#review-menu');
  const reviewToggle = $('#review-toggle');
  const runReview = $('#run-review');
  const {perspectives} = data;
  const review = data.reviews.at(-1);
  const applicable = perspectives.filter(p => p.applies);
  const reviewNames = data.rerun;
  const items = ['comment', 'note', 'approve', 'confirm'];
  const waiting = (entry, states) => states[entry.e.id] === 'asked' ||
    (entry.kind === 'reply' && !entry.e.to && entry.e.id && !entry.replies.some(reply => reply.type === 'note'));
  const revKey = 'architecture-page';
  const saved = JSON.parse(sessionStorage.getItem(revKey) || '{}');
  sessionStorage.removeItem(revKey);
  let tab, version, findings;
  const requirementWording = new Map(data.requirements.map(req => [req.id, req.wording]));
  let commentsById = new Map();
  const partByElement = new Map();
  const openComments = byId('comment-count');
  const openQuestions = byId('question-count');

  function section(key, heading, content) {
    panel(key).innerHTML = '<h2>' + text(heading) + '</h2>' + content;
  }

  document.title = 'Design: ' + data.title;
  byId('title').textContent = document.title;
  byId('accepted-count').innerHTML = new Set(data.accepted).size + '<span class="of"> / ' + (tabs.length - 1) + '</span>';
  const sections = tabs.slice(1).map(button => {
    const key = button.id.slice(4);
    const accepted = data.accepted.includes(key);
    const name = button.textContent;
    if (accepted) button.insertAdjacentHTML('beforeend', '<span class="count ok" aria-label="Accepted">✓</span>');
    return row(['<a data-section="' + key + '" href="#panel-' + key + '">' + text(name) + '</a>',
      '<span data-section-status="' + key + '">' + (accepted ? chip('Accepted', 'ok') : chip('Draft')) + '</span>']);
  });
  section('overview', data.title, '<p class="lead">' + text(data.summary) + '</p><h3>Scope</h3><p>' +
    text(data.scope) + '</p><h3>Sections</h3>' + table(['Section', 'Status'], sections));
  section('requirements', 'Requirements', table(['ID', 'Kind', 'Requirement', 'Source', 'Actions'], requirementRows(data.requirements)));
  const diagramControls = controls(applicable, review);
  section('containers', 'Containers', diagramControls + figures(data.containers));
  section('flows', 'Flows', diagramControls + data.flows.map(flow =>
    '<h3 class="figtitle">' + text(flow.name) + (flow.new ? ' ' + chip('New', 'open') : '') + '</h3>' +
    figures(flow.versions)).join(''));
  section('perspectives', 'Perspectives', perspectiveTables(perspectives, data.findings, data.parts, review, data.removed_labels));
  section('decisions', 'Decision records', decisionRecords(data.decisions));
  section('spec', 'Spec', table(['ID', 'Requirement', 'Source', 'Checked by'], data.spec.map(rule =>
    row([text(rule.id), text(rule.requirement), text(rule.source), text(rule.checked_by)]))));

  for (const [key, part] of Object.entries(data.parts)) {
    if (key !== part.key) continue;
    for (const id of part.ids) {
      const target = byId(id);
      if (!target) continue;
      partByElement.set(target, {key: key, title: part.label});
      target.setAttribute('tabindex', '0');
      target.setAttribute('role', 'button');
      target.setAttribute('aria-label', 'Comment on ' + part.label);
    }
  }
  all('.fig svg').forEach(svg => svg.setAttribute('role', 'group'));

  function showTab(key) {
    if (!panel(key)) key = 'overview';
    if (key !== tab) view.scrollTop = 0;
    tab = key;
    tabs.forEach(button => {
      const selected = button.id === 'tab-' + key;
      button.setAttribute('aria-selected', String(selected));
      button.tabIndex = selected ? 0 : -1;
      byId(button.getAttribute('aria-controls')).hidden = !selected;
    });
    placePins();
  }

  function setVersion(state) {
    version = state === 'before' ? 'before' : 'after';
    all('[data-version]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.version === version)));
    all('.fig').forEach(fig => { fig.hidden = fig.dataset.state !== version; });
    placePins();
  }

  function setFindings(key) {
    findings = key || '';
    all('[data-findings]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.findings === findings)));
    all('.mark').forEach(mark => { mark.toggleAttribute('hidden', mark.dataset.p !== findings); });
  }

  function clearHighlight() {
    all('svg.focused, .highlighted').forEach(node => node.classList.remove('focused', 'highlighted'));
  }

  function revealFinding(link) {
    clearHighlight();
    const parts = JSON.parse(link.dataset.parts).map(key => data.parts[key]);
    showTab(parts.some(p => p.view === 'containers') ? 'containers' : 'flows');
    setVersion('after');
    setFindings(link.dataset.perspective);
    let first;
    for (const part of parts) {
      for (const id of part.ids) {
        const element = byId(id);
        if (!element || element.closest('.fig').hidden) continue;
        element.classList.add('highlighted');
        element.ownerSVGElement.classList.add('focused');
        if (!element.closest('[role="tabpanel"]').hidden) first ||= element;
      }
    }
    all('.mark').forEach(mark => {
      if (mark.dataset.p === findings && $('text', mark).textContent === link.dataset.badge) mark.classList.add('highlighted');
    });
    first?.scrollIntoView({block: 'center'});
  }

  function crumb(event) {
    const label = document.createElement('span');
    label.className = 'crumb';
    label.textContent = event.on?.title || '';
    return label;
  }

  function locate(event) {
    return byId(event.on?.id);
  }

  function reveal(event) {
    const element = locate(event);
    if (!element) return;
    showTab(element.closest('[role="tabpanel"]').id.slice(6));
    if (element.closest('.fig')) setVersion(element.closest('.fig').dataset.state);
    element.scrollIntoView({block: 'center'});
  }

  function placePins() {
    all('.fig .pin').forEach(pin => pin.remove());
    for (const event of commentsById.values()) {
      const target = locate(event);
      const fig = target?.closest('.fig');
      if (!fig || fig.hidden || fig.closest('[role="tabpanel"]').hidden) continue;
      const rect = target.getBoundingClientRect();
      const region = fig.getBoundingClientRect();
      const pin = commentLayer.placePin(fig, event);
      pin.style.left = (rect.right - region.left) + 'px';
      pin.style.top = (rect.top - region.top) + 'px';
    }
  }

  function editComment(event, opener) {
    const target = locate(event) || opener;
    const rect = target.getBoundingClientRect();
    commentLayer.open({on: event.on, item: event}, event, opener,
      popup => pageCommentPosition(rect.left, rect.bottom, popup));
  }

  function logItem(entry) {
    const li = document.createElement('li');
    li.className = 'msg me';
    const head = document.createElement('div');
    head.className = 'head';
    const who = document.createElement('span');
    who.className = 'who';
    who.textContent = 'You';
    const when = document.createElement('span');
    when.className = 'when';
    when.textContent = pageTime(entry.e.at);
    head.append(who, when);
    li.append(head, pageMarkdown(entry.e.text));
    return li;
  }

  const conversation = pageConversation({
    served: true, name: 'design page', agent: 'Architect', itemKinds: items, latestLast: true, waiting,
    kinds: {approve: logItem, confirm: logItem}, crumb, commentBody: event => pageMarkdown(event.text),
    byId: id => threadComment(conversation.log(), id),
    reveal, edit: editComment, remove: event => commentLayer.remove(event), showLabel: n => 'Show comment ' + n,
    busy: () => !pop.hidden || !reviewMenu.hidden || !!$('.edit:not([hidden])'),
    beforeReload: () => sessionStorage.setItem(revKey, JSON.stringify({tab, version, findings, scroll: view.scrollTop})),
    rendered: states => {
      const log = conversation.log();
      const model = pageThread(log, items, waiting, true);
      const open = model.open.filter(entry => entry.kind === 'comment');
      commentsById = new Map(model.entries.filter(entry => entry.kind === 'comment' && !entry.deleted)
        .map(entry => [entry.e.id, entry.e]));
      openComments.textContent = open.length;
      openQuestions.textContent = model.entries.filter(entry => !entry.deleted && waiting(entry, states)).length;
      const counts = new Map();
      for (const {e} of open) {
        const key = locate(e)?.closest('[role="tabpanel"]')?.id.slice(6);
        counts.set(key, (counts.get(key) || 0) + 1);
      }
      for (const button of tabs.slice(1)) {
        const key = button.id.slice(4);
        if (data.accepted.includes(key)) continue;
        const count = counts.get(key);
        $('.count', button)?.remove();
        if (count) button.insertAdjacentHTML('beforeend', '<span class="count">' + count + '</span>');
        const status = $('[data-section-status="' + key + '"]');
        status.innerHTML = count ? chip(count + (count === 1 ? ' comment' : ' comments'), 'open') : chip('Draft');
      }
      for (const event of log) {
        if (event.type !== 'confirm' || event.wording !== requirementWording.get(event.requirement)) continue;
        const record = byId('req-' + event.requirement);
        if (!record || !$('[data-confirm]', record)) continue;
        const link = document.createElement('a');
        link.className = 'src';
        link.href = '#thread';
        link.dataset.confirmation = event.id;
        link.append('You, on this page', document.createElement('br'), pageTime(event.at));
        $('.req-source', record).replaceChildren(link);
        $('[data-confirm]', record).remove();
      }
      commentLayer.state(states);
      placePins();
    }
  });
  const commentLayer = pageElementComments({
    pop, pinClass: 'pin', commenting: () => true, crumb,
    params: (draft, text) => ({on: draft.on, text}),
    nextNumber: () => 1 + Math.max(0, ...conversation.log().map(event => event.n || 0)),
    send: conversation.send, byId: id => commentsById.get(id), reopen: conversation.reopen
  });

  function commentOn(element, target, x, y) {
    const on = {...partByElement.get(element), id: element.id, selector: pageElementSelector(element)};
    commentLayer.open({on}, null, target, popup => pageCommentPosition(x, y, popup));
  }

  function showConversation(id) {
    $('[data-filter="all"]').click();
    const entry = all('.thread > li').find(li => li.dataset.id === id);
    if (entry) {
      entry.tabIndex = -1;
      entry.focus();
      entry.scrollIntoView({block: 'nearest'});
    }
  }

  view.addEventListener('click', event => {
    const button = event.target.closest('button');
    const link = event.target.closest('a');
    if (button?.matches('[role="tab"]')) showTab(button.id.slice(4));
    if (button?.matches('[data-version]')) setVersion(button.dataset.version);
    if (button?.matches('[data-findings]')) { clearHighlight(); setFindings(button.dataset.findings); }
    if (link?.matches('[data-parts]')) { event.preventDefault(); revealFinding(link); }
    if (link?.matches('[data-section]')) { event.preventDefault(); showTab(link.dataset.section); }
    if (link?.matches('[data-confirmation]')) { event.preventDefault(); showConversation(link.dataset.confirmation); }
    if (link?.matches('[data-driver]')) {
      event.preventDefault();
      showTab('requirements');
      const target = byId('req-' + link.dataset.driver);
      target.tabIndex = -1;
      target.focus({preventScroll: true});
      target.scrollIntoView({block: 'center'});
    }
    const record = button?.closest('[data-record]');
    if (button?.matches('[data-edit]')) {
      const form = $('.edit', record);
      form.hidden = !form.hidden;
      if (!form.hidden) $('textarea', form).focus();
    }
    if (button?.matches('[data-confirm]')) {
      const requirement = record.dataset.record;
      button.disabled = true;
      conversation.send('confirm', {id: 'confirm-' + Date.now().toString(36), requirement,
        wording: requirementWording.get(requirement), text: 'Confirmed requirement ' + requirement + '.'}, 'Confirmation', null, () => { button.disabled = false; });
    }
    const fig = event.target.closest('.fig');
    if (!fig) return;
    clearHighlight();
    const element = event.target.closest('g[data-id]');
    if (partByElement.has(element) || event.target.closest('.pin')) {
      commentLayer.click(event, () => commentOn(element, element, event.clientX, event.clientY), editComment);
    }
  });

  view.addEventListener('submit', event => {
    if (!event.target.matches('.edit')) return;
    event.preventDefault();
    const form = event.target;
    const input = $('textarea', form);
    const message = input.value.trim();
    if (!message) { input.focus(); return; }
    const record = form.closest('[data-record]');
    const button = $('button', form);
    button.disabled = true;
    conversation.send('comment', {id: 'change-' + Date.now().toString(36), text: message,
      on: {id: record.id, title: 'Change ' + record.dataset.record}}, 'Change request', () => {
      form.hidden = true;
      button.disabled = false;
      input.value = input.defaultValue;
    }, () => { button.disabled = false; });
  });

  view.addEventListener('keydown', event => {
    const element = event.target;
    if (element.matches('[role="tab"]')) {
      const i = tabs.indexOf(element);
      const next = {ArrowLeft: (i + tabs.length - 1) % tabs.length, ArrowRight: (i + 1) % tabs.length,
        Home: 0, End: tabs.length - 1}[event.key];
      if (next !== undefined) { event.preventDefault(); tabs[next].click(); tabs[next].focus(); }
    }
    if (partByElement.has(element) && ['Enter', ' '].includes(event.key)) {
      event.preventDefault();
      const rect = element.getBoundingClientRect();
      commentOn(element, element, rect.left, rect.bottom);
    }
  });
  pop.addEventListener('keydown', event => { if (event.key === 'Escape') commentLayer.close(); });
  window.addEventListener('resize', placePins);

  byId('questions').addEventListener('click', () => {
    const model = pageThread(conversation.log(), items, waiting, true);
    const entry = model.entries.find(c => !c.deleted && waiting(c, model.state));
    if (entry) showConversation(entry.e.id);
  });

  reviewToggle.textContent = review ? 'Review again…' : 'Approve…';
  $('.menu-h', reviewMenu).textContent = review ? 'Review the changes' : 'Approve the design';
  runReview.textContent = review ? 'Run the review again' : 'Approve and run the review';
  runReview.disabled = !!review && !reviewNames.length;
  function toggleReview(open) {
    reviewMenu.hidden = !open;
    reviewToggle.setAttribute('aria-expanded', String(open));
  }
  reviewToggle.addEventListener('click', () => {
    const scope = reviewNames.length ? 'Review: ' + reviewNames.join(', ') + '.' : 'No perspectives to review.';
    const stats = byId('accepted-count').textContent + ' sections accepted · ' + openComments.textContent + ' open comments. ';
    const removedKeys = data.removed || [];
    const changed = data.since.filter(key => !removedKeys.includes(key)).map(key => data.change_labels[key]);
    const removed = removedKeys.map(key => data.change_labels[key]);
    $('.review-summary').textContent = review ? reviewSummary(changed, reviewNames, removed) : stats + scope;
    toggleReview(reviewMenu.hidden);
  });
  runReview.addEventListener('click', () => {
    runReview.disabled = true;
    const label = review ? 'Review requested again' : 'Design approved';
    conversation.send('approve', {id: 'approval-' + Date.now().toString(36), again: !!review, perspectives: reviewNames,
      changes: data.since, text: label + (reviewNames.length ? ' · ' + reviewNames.join(', ') : '')},
    'Review request', () => { toggleReview(false); runReview.disabled = false; },
    () => { runReview.disabled = false; });
  });

  showTab(saved.tab || 'overview');
  setVersion(saved.version);
  setFindings(saved.findings);
  view.scrollTop = saved.scroll || 0;
  conversation.start();
}

async function loadDesign() {
  const message = $('.offline');
  let data;
  try {
    const response = await fetch('/design.json');
    if (!response.ok) throw new Error(await response.text());
    data = await response.json();
  } catch (error) {
    const original = message.textContent;
    message.textContent = 'Could not load the design. ' + error.message;
    message.hidden = false;
    setTimeout(() => {
      message.textContent = original;
      loadDesign();
    }, 2000);
    return;
  }
  message.hidden = true;
  start(data);
}

loadDesign();
