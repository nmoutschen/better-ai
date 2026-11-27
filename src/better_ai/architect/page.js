'use strict';

const $ = (selector, root = document) => root.querySelector(selector);
const all = (selector, root = document) => [...root.querySelectorAll(selector)];
const byId = id => document.getElementById(id);
const text = pageEscape;
const inlineCode = value => value.split(/(`[^`]+`)/).map((part, index) =>
  index % 2 ? '<code>' + text(part.slice(1, -1)) + '</code>' : text(part)).join('');
const invalid = record => record._errors && record._errors.length ?
  '<p class="invalid">' + chip('Not valid', 'error') + ' ' + text(record._errors[0]) + '</p>' : '';
const nameOf = (perspectives, id) => (perspectives.find(p => p.id === id) || {}).name || id;
// A perspective's origin as words: a sum type tagged by type, so no string mixes cases.
const fromWords = from => from.type === 'built_in' ? 'built in' + (from.method ? ' (' + from.method + ')' : '') :
  from.type === 'standard' ? from.file : 'not valid';
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
  if (source.type === 'guessed') return chip('guessed', 'plain');
  if (source.type === 'user') return 'You, on this page<br>' + text(String(source.at).slice(11, 16));
  if (source.type !== 'request' && source.type !== 'file') return chip('no valid source', 'error');
  return source.sentence ? text(source.sentence) : text(source.file) + (source.symbol ? '<br>' + text(source.symbol) : '');
}

function requirementRows(requirements) {
  return requirements.map(req => row([
    '<strong>' + text(req.id) + '</strong>', text(req.kind), text(req.text) + invalid(req) + editor('New wording for ' + req.id, req.text),
    '<span class="req-source">' + sourceLink(req.source) + '</span>',
    '<div class="row-actions">' + changeButton + (req.source.type === 'guessed' && !(req._errors || []).length ?
      '<button class="btn btn--sm answer" type="button" data-confirm aria-label="Confirm the guess">✓</button>' : '') + '</div>'
  ], 'id="req-' + text(req.id) + '" data-record="' + text(req.id) + '"'));
}

function decisionRecords(decisions) {
  return decisions.map(decision => {
    const drivers = decision.drivers.map(id =>
      '<a class="chip" href="#req-' + encodeURIComponent(id) + '" data-driver="' + text(id) + '">' + text(id) + '</a>'
    ).join(' ');
    const alternatives = decision.rejected.map(alt =>
      '<li><strong>' + text(alt.option) + '</strong><span class="muted">Not chosen: ' + text(alt.why) + '</span></li>'
    ).join('');
    return '<article class="dec" id="dec-' + text(decision.id) + '" data-record="' + text(decision.id) + '">' +
      '<div class="dh"><span>' + text(decision.id) + '</span><h3>' + text(decision.title) + '</h3>' + changeButton + '</div>' + invalid(decision) +
      editor('What should change in ' + decision.id) + '<p class="drv">Driven by ' + drivers + '</p>' +
      '<div class="chosen"><span class="lbl">Chosen</span><p>' + inlineCode(decision.chosen) + '</p></div>' +
      '<details class="rej"><summary>Rejected alternatives (' + decision.rejected.length +
      ')</summary><ul class="alts">' + alternatives + '</ul></details>' +
      '<p class="drawback"><span class="lbl">Main drawback</span> ' + inlineCode(decision.drawback) + '</p></article>';
  }).join('');
}

// The versions to switch between, Before and each version after the change, shown only when there is more than one.
function controls(perspectives, review, versions = []) {
  const segment = (label, attr, options) => '<div class="seg seg--light" role="group" aria-label="' + label + '">' +
    options.map(([key, name]) => '<button type="button" data-' + attr + '="' + text(key) +
      '" aria-pressed="false">' + text(name) + '</button>').join('') + '</div>';
  return '<div class="controls">' +
    (versions.length > 1 ? segment('Version', 'version', versions.map(v => [v.id, v.name])) : '') +
    (review ? segment('Findings', 'findings', [['', 'No findings'], ...perspectives.map(p => [p.id, p.name])]) : '') + '</div>';
}

// One drawing per version; a version that does not draw a flow says so, by the version's name.
function figures(drawings, versions = [], empty) {
  const nameOf = state => (versions.find(v => v.id === state) || {}).name || state;
  const missing = state => empty || (state === 'before' ? 'This flow does not exist before the change.' :
    state === 'after' ? 'This flow does not exist after the change.' : 'This flow is not part of ' + nameOf(state) + '.');
  return Object.entries(drawings).map(([state, svg]) => '<div class="fig" data-state="' + text(state) + '" hidden>' +
    (svg || '<p class="muted">' + text(missing(state)) + '</p>') + '</div>').join('');
}

// A flow's New or Removed mark, one per version that shows it so.
function flowMarks(status = {}) {
  return Object.entries(status).filter(([, how]) => how !== 'current').map(([state, how]) =>
    '<span class="chip by-version" data-state="' + text(state) + '" hidden>' + (how === 'new' ? 'New' : 'Removed') + '</span>').join('');
}

function bullets(items) {
  return items.length ? '<ul class="bullets">' + items.map(item => '<li>' + inlineCode(item) + '</li>').join('') + '</ul>' : '<p class="muted">None given.</p>';
}

// The alternatives side by side, each with its trade-offs; each row takes a change request.
function alternativeTable(alternatives) {
  if (!alternatives.length) return '';
  return '<h3>Alternatives</h3>' + table(['Alternative', 'Summary', 'Strengths', 'Drawbacks', 'Actions'], alternatives.map(alt => row([
    '<strong>' + text(alt.name) + '</strong>', inlineCode(alt.summary) + editor('What should change in ' + alt.name),
    bullets(alt.strengths), bullets(alt.drawbacks), '<div class="row-actions">' + changeButton + '</div>'
  ], 'id="alt-' + text(alt.id) + '" data-record="' + text(alt.id) + '" data-name="' + text(alt.name) + '"')));
}

// The trade-offs of the alternative a diagram shows, above the diagram, shown with its version.
function alternativeCards(alternatives) {
  return alternatives.map(alt => '<article class="dec by-version" data-state="' + text(alt.id) + '" hidden><div class="dh"><h3>' +
    text(alt.name) + '</h3></div><p>' + inlineCode(alt.summary) + '</p><span class="lbl">Strengths</span>' + bullets(alt.strengths) +
    '<span class="lbl">Drawbacks</span>' + bullets(alt.drawbacks) + '</article>').join('');
}

function specSource(source) {
  if (!source) return '';
  return source.type === 'design' ? 'design: ' + source.section : source.type === 'request' ? 'request: ' + source.sentence :
    source.type + ' ' + (source[source.type] ?? '');
}

function specTables(records) {
  const rules = records.filter(r => r.type === 'spec');
  const gaps = records.filter(r => r.type === 'gap');
  const unlinked = records.filter(r => r.type === 'unlinked');
  return table(['ID', 'Requirement', 'Source', 'Checked by'], rules.map(rule =>
    row([text(rule.id), text(rule.statement) + invalid(rule), text(specSource(rule.source)), text(rule.checked_by)]))) +
    (gaps.length ? '<h3>Gaps</h3>' + table(['ID', 'Gap', 'State', 'If wrong'], gaps.map(gap => row([text(gap.id), text(gap.text) + invalid(gap),
      text(gap.status === 'assumed' ? 'assumed: ' + (gap.choice ?? '') : (gap.status ?? '') + ' ' + (gap.decision ?? '')),
      text(gap.if_wrong ?? '')]))) : '') +
    (unlinked.length ? '<h3>Design items with no requirement</h3>' + table(['Item', 'Why'],
      unlinked.map(item => row([text(item.item ?? ''), text(item.why ?? '') + invalid(item)]))) : '');
}

function perspectiveTables(perspectives, findings, parts, reviewed, removedLabels = {}) {
  const summary = table(['Perspective', 'Applicability', 'Why', 'From'], perspectives.map(p =>
    row(['<strong>' + text(p.name) + '</strong>', p.applies ? chip('Applies', 'plain') : chip('Does not apply'),
      text(p.why) + invalid(p), '<span class="muted">' + text(fromWords(p.from)) + '</span>'])));
  if (!reviewed) return summary + '<p>' + chip('Review runs once you approve the design', 'wait') + '</p>';
  return summary + perspectives.filter(p => p.applies).map(p => {
    const headers = ['ID', 'Part', 'Finding', 'Handled by'];
    const rows = findings.filter(f => f.perspective === p.id).map(f => {
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
          text(JSON.stringify(group)) + '" data-perspective="' + text(p.id) + '" data-badge="' + text(f.id) + '">' +
          icon + '<span>' + text(label) + '</span></a>';
      }).join('<br>');
      return row(['<strong>' + text(f.id) + '</strong>', links, text(f.text) +
        (f.confirmed ? '' : ' ' + chip('Unconfirmed', 'plain')) + invalid(f), text(f.handled_by ?? 'Open')],
        'data-finding="' + text(f.id) + '" data-perspective="' + text(p.id) + '"');
    });
    return '<h3>' + text(p.name) + '</h3>' + (rows.length ? table(headers, rows) : '<p class="muted">No findings.</p>');
  }).join('');
}

// Past this many changes the panel gives counts instead of names, and folds the names behind a control.
const LISTED_CHANGES = 6;

function changeCounts(keys) {
  const plural = (n, one, many) => n + ' ' + (n === 1 ? one : many);
  const of = kind => keys.filter(key => key.startsWith(kind + ':'));
  const steps = of('step');
  const flows = new Set(steps.map(key => key.slice(5).split('/')[0])).size;
  return [
    of('box').length && plural(of('box').length, 'box', 'boxes'),
    of('edge').length && plural(of('edge').length, 'arrow', 'arrows'),
    steps.length && plural(steps.length, 'step', 'steps') + ' in ' + plural(flows, 'flow', 'flows'),
    of('requirement').length && plural(of('requirement').length, 'requirement', 'requirements'),
    of('section').length && plural(of('section').length, 'design section', 'design sections')
  ].filter(Boolean).join(', ');
}

// What changed since the last review, from the change keys, their labels and the removed keys, and who runs again.
function reviewSummary(since, labels, names, removed = []) {
  const rerun = names.join(', ') + (names.length === 1 ? ' runs' : ' run') + ' again';
  const ending = names.length ? ' ' + rerun + '.' : '';
  if (since.length > LISTED_CHANGES) {
    return since.length + ' parts changed since the review: ' + changeCounts(since) + '.' +
      (removed.length ? ' ' + removed.length + ' of them removed.' : '') + ending;
  }
  const changed = since.filter(key => !removed.includes(key)).map(key => labels[key]);
  if (since.length) {
    return ((changed.length ? 'Changed since the review: ' + changed.join(', ') + '.' : '')
      + (removed.length ? ' Removed: ' + removed.map(key => labels[key]).join(', ') + '.' : '') + ending).trim();
  }
  if (names.length) return rerun + ': not reviewed yet.';
  return 'Nothing changed since the review.';
}

// The full list of changes, folded, when the summary gives only counts.
function changeList(since, labels, removed = []) {
  if (since.length <= LISTED_CHANGES) return '';
  const items = since.map(key => '<li>' + text(labels[key]) + (removed.includes(key) ? ' <span class="muted">(removed)</span>' : '') + '</li>');
  return '<details class="rej"><summary>All ' + since.length + ' changes</summary><ul>' + items.join('') + '</ul></details>';
}

function threadComment(log, id) {
  const event = log.findLast(event => (event.type === 'comment' && event.id === id) || (event.type === 'delete' && event.to === id));
  return event?.type === 'comment' && byId(event.on?.id) ? event : undefined;
}

function start(data) {
  const view = $('.view');
  const readOnly = !!data.static;  // a copy written by `render`: nothing can be sent
  byId('status').innerHTML = '<span class="stat"><b id="accepted-count"></b>sections accepted</span>' +
    '<span class="stat"><b id="comment-count">0</b>open comments</span>' +
    '<button type="button" class="stat" id="questions"><b id="question-count">0</b>open questions</button>';
  const versions = data.versions || [];
  const alternatives = data.alternatives || [];
  const before = versions.length < 2;  // the design draws only the system as it is: nothing to approve yet
  const tabs = all('.tabs [role="tab"]');
  const panel = key => byId('panel-' + key);
  const pop = $('.pop');
  if (readOnly) $('.composer').hidden = true;
  let approval = null;
  const {perspectives} = data;
  const review = data.reviews.at(-1);
  const applicable = perspectives.filter(p => p.applies);
  const reviewIds = data.rerun;
  const reviewNames = reviewIds.map(id => nameOf(perspectives, id));
  const items = ['comment', 'note', 'approve', 'confirm'];
  const waiting = (entry, states) => (entry.items || []).some(id => states[id] === 'asked') ||
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

  pageShowErrors(byId('errors'), data.errors);
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
    text(data.scope) + '</p>' + alternativeTable(alternatives) + '<h3>Sections</h3>' + table(['Section', 'Status'], sections));
  section('requirements', 'Requirements', table(['ID', 'Kind', 'Requirement', 'Source', 'Actions'], requirementRows(data.requirements)));
  const diagramControls = controls(applicable, review, versions) + alternativeCards(alternatives);
  section('containers', 'Containers', diagramControls + figures(data.containers, versions, 'The containers are not drawn: see the errors above.'));
  section('flows', 'Flows', diagramControls + data.flows.map(flow =>
    '<h3 class="figtitle">' + text(flow.name) + ' ' + flowMarks(flow.status) + '</h3>' +
    figures(flow.versions, versions)).join(''));
  section('perspectives', 'Perspectives', perspectiveTables(perspectives, data.findings, data.parts, review, data.removed_labels));
  section('decisions', 'Decision records', decisionRecords(data.decisions));
  section('spec', 'Spec', specTables(data.spec));

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
  all('.fig .mark').forEach(mark => {
    mark.setAttribute('tabindex', '0');
    mark.setAttribute('role', 'button');
    mark.setAttribute('aria-label', 'Show finding ' + $('text', mark).textContent + ' under Perspectives');
  });

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

  // Shows one version; by default the first after the change, or Before when there is none.
  function setVersion(state) {
    const known = versions.map(v => v.id);
    version = known.includes(state) ? state : known[1] || 'before';
    all('[data-version]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.version === version)));
    all('.fig, .by-version').forEach(node => { node.hidden = node.dataset.state !== version; });
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

  // A finding's mark on a diagram opens its row under Perspectives, as the row's part link opens the diagram.
  function showFinding(mark) {
    clearHighlight();
    showTab('perspectives');
    const id = $('text', mark).textContent;
    const target = all('[data-finding]').find(r => r.dataset.finding === id && r.dataset.perspective === mark.dataset.p);
    if (!target) return;
    target.classList.add('highlighted');
    target.tabIndex = -1;
    target.focus({preventScroll: true});
    target.scrollIntoView({block: 'center'});
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
    served: !readOnly, readOnly, itemKinds: items, latestLast: true, waiting,
    kinds: {approve: entry => pageApprovalItem(entry, conversation.log()), confirm: logItem}, crumb, commentBody: event => pageMarkdown(event.text),
    byId: id => threadComment(conversation.log(), id),
    reveal, edit: editComment, remove: event => commentLayer.remove(event), showLabel: n => 'Show comment ' + n,
    busy: () => !pop.hidden || !!approval?.open() || !!$('.edit:not([hidden])'),
    sendMode: () => approval?.sendMode() || null,
    beforeReload: () => sessionStorage.setItem(revKey, JSON.stringify({tab, version, findings, scroll: view.scrollTop})),
    rendered: states => {
      const log = conversation.log();
      const model = pageThread(log, items, waiting, true);
      const open = model.open.filter(entry => entry.kind === 'comment');
      commentsById = new Map(model.entries.filter(entry => entry.kind === 'comment' && !entry.deleted)
        .map(entry => [entry.e.id, entry.e]));
      openComments.textContent = open.length;
      openQuestions.textContent = pageOpenDecisions([], log, items, waiting).length;
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
        status.innerHTML = count ? chip(count + (count === 1 ? ' comment' : ' comments')) : chip('Draft');
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
    pop, pinClass: 'pin', commenting: () => !readOnly, crumb,
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
    const mark = event.target.closest('.mark');
    if (mark) { showFinding(mark); return; }
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
      on: {id: record.id, title: 'Change ' + (record.dataset.name || record.dataset.record)}}, 'Change request', () => {
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
    if (element.matches('.mark') && ['Enter', ' '].includes(event.key)) {
      event.preventDefault();
      showFinding(element);
    }
    if (!readOnly && partByElement.has(element) && ['Enter', ' '].includes(event.key)) {
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

  // Approve…: page.js's panel, as on design-better's canvas. Before a review: one option per alternative, or Ship After
  // and Keep Before; after one, Review again… while a perspective has changes to review.
  function approvalOptions() {
    if (review) return [{label: 'Review the changes again', value: 'again'}];
    const options = alternatives.length ?
      [...alternatives.map(alt => ({label: 'Build ' + alt.name, value: alt.id})),
        {label: 'Combine alternatives (say how below)', value: 'combine', note: true}] :
      [{label: 'Ship After', value: 'after'}, {label: 'Keep Before', value: 'before'}];
    return [...options, {label: 'None of these (say why below)', value: 'none', note: true}];
  }
  function approvalIntro(box) {
    const removed = data.removed || [];
    const scope = reviewNames.length ? 'Review: ' + reviewNames.join(', ') + '.' : 'No perspectives to review.';
    const summary = document.createElement('p');
    summary.className = 'review-summary';
    summary.textContent = review ? reviewSummary(data.since, data.change_labels, reviewNames, removed) : scope;
    const changes = document.createElement('div');
    changes.className = 'review-changes';
    changes.innerHTML = review ? changeList(data.since, data.change_labels, removed) : '';
    box.append(summary, changes);
  }
  const openItems = () => pageThread(conversation.log(), items, waiting, true).open
    .filter(entry => entry.kind === 'comment' && !entry.deleted).map(entry => ({id: entry.e.id, n: entry.e.n, text: entry.e.text}));
  if (!readOnly && !before && !(review && !reviewNames.length)) {
    approval = pageApprovalPanel({conversation, options: approvalOptions, openItems, intro: approvalIntro,
      button: review ? 'Review again…' : 'Approve…', params: () => ({again: !!review, perspectives: reviewIds, changes: data.since}),
      needs: 'Say how to combine them, or why none fits, in the message.'});
  }

  showTab(saved.tab || 'overview');
  setVersion(saved.version);
  setFindings(saved.findings);
  view.scrollTop = saved.scroll || 0;
  if (readOnly) conversation.setLog(data.events || []);
  conversation.start();
}

// The page's data: embedded in a copy written by `render`, else served at /data.
function embeddedData() {
  const node = byId('page-data');
  try { return node ? JSON.parse(node.textContent) : null; } catch (error) { return null; }
}

async function loadDesign() {
  const status = byId('status');
  let data = embeddedData();
  if (!data) {
    try {
      const response = await pageFetch('/data');
      if (!response.ok) throw new Error(await response.text());
      data = await response.json();
    } catch (error) {
      if (error && error.stale) return;  // the shared strip says the page is out of date; asking again cannot help
      status.textContent = 'Could not load the design. ' + error.message;
      setTimeout(loadDesign, 2000);
      return;
    }
  }
  start(data);
}

loadDesign();
