# Design language: better-ai

better-ai's pages share one look: the live pages the skills serve (boards) and the better-ai website. It is the n14n "Journal" language, applied to two kinds of page:

- **Board**: a live page a skill serves while an agent works, such as research-better's board, code-better's dashboard, design-better's canvas, show-better's slides and architect-better's design page. One window, no page scroll, the conversation with the agent in a fixed right column.
- **Article page**: a page to read, such as a page of the website or a document a skill writes. Scrolls, with a column of prose.

[DESIGN.html](DESIGN.html) shows the colours, type and components rendered from the shared stylesheet.

## Where it lives

| What | File | Rule |
|---|---|---|
| Tokens and shared components | `src/better_ai/page/page.css` | The one copy. Every board's page loads it, and no board restyles what it defines. |
| The conversation column | `src/better_ai/page/page.js`, `shell.html` | The one copy, as page.css. |
| What only one board shows | `src/better_ai/*/` (`board.css`, `dashboard.css`, `canvas.css`, `show.css`, `page.css` in architect) | Uses only the tokens and components below. |
| This document | `DESIGN.md`, `DESIGN.html` | The names here are the names in page.css. DESIGN.html holds copies of page.css and page.js, so it works as a single file: after changing either, paste it again into DESIGN.html (the test says which). |

`tests/test_design.py` fails when a page uses a colour that is not in the colour table below, a raw px value for a space or a type size, a `font` shorthand that is not a `--font-*` token, or when this document and page.css disagree.

## What it must express

- Qualities: calm and readable; a journal, not a dashboard product. The agent's work and what waits for the user are found at a glance.
- Audience: the user of a skill, on a desktop browser with a pointer and a keyboard, while the agent works. Boards must still work at 800px wide. Website readers decide whether to use better-ai, on any device.
- Family: part of n14n.dev in colours, typefaces, the sayagata bands and the square, thin-lined forms. The website does not have to use n14n.dev's site header.

## Colour

Light only. Every colour a page uses is one of these. Write it as `var(--name)` in CSS; an SVG attribute or a slide that is exported on its own may write the value.

| Name | Value | Role | Allowed on |
|---|---|---|---|
| `--cream` | `#FFFCF7` | page background; text on dark fills | — |
| `--linen` | `#F2EDE5` | the agent's messages, code, a quiet panel | — |
| `--white` | `#FFFFFF` | inside fields; the user's own messages | — |
| `--umber` | `#5C4033` | the header bar, primary buttons, the band, "waiting for you" | as text: cream 9.2:1, linen 8.1:1, white 9.4:1 |
| `--ink` | `#33302B` | body text, borders that separate the conversation | cream 12.8:1, linen 11.3:1, white 13.1:1 |
| `--heading` | `#1C1A17` | headings, names | cream 17.0:1, linen 14.9:1; also on terracotta 5.8:1 and sand 8.7:1 |
| `--muted` | `#78736B` | times, metadata, hints | cream 4.6:1 and white 4.7:1 only. Not on linen (4.0:1) |
| `--terracotta` | `#E8725C` | edges and bands: the title band, the "working" bar, the selected tab, a selected outline | never as text (2.9:1 on cream). As a fill, heading text only |
| `--terracotta-dark` | `#AA5141` | terracotta as text: a link hover, "1 comment" | cream 5.2:1, linen 4.5:1 |
| `--moss-dark` | `#66795A` | done, accepted, a feature, a verifier | as text on cream 4.6:1 only; cream text on it 4.6:1 |
| `--moss` | `#6B7F5E` | fill only: a done mark on a map or a slide | not as text |
| `--sand` | `#C4B69C` | thin borders of boxes, "seen" bars, a quiet fill | not as text (2.0:1). As a fill, heading text only |
| `--line` | `#DDD6CA` | hairlines between rows and around panels | not as text |
| `--error` | `#9A3B2A` | failure, blocked, the page's server not answering | cream 6.8:1, linen 5.9:1; cream text on it 6.8:1 |
| `--surround` | `#F5F5F5` | behind the versions on the canvas and behind an exported slide | ink 12.1:1 |
| `--surround-dark` | `#1E1E1E` | the canvas's dark surround | cream text only |
| `--frame` | `#BDBDBD` | the outline of a version on the light surround | not as text |
| `--frame-dark` | `#5A5A5A` | the outline of a version on the dark surround | not as text |
| `--shadow` | `0 8px 24px rgba(28,26,23,.25)` | pop-ups and the toast, the only shadow | — |

- Meaning: four colours carry a state, each with a word or a shape: moss-dark for done ("Done", ✓), terracotta for working (a pulsing bar, "Working"), umber for waiting for the user ("Waiting for you"), error for blocked or reopened ("Blocked", ⊘). The progress bars in page.js always show the word.
- The `rgba(232,114,92,…)` in show.css is terracotta with transparency, for the pulse around a new pin.

## Type

Two typefaces, loaded from Google Fonts: **Libre Baskerville** (`--serif`) for titles and prose to read, **Space Grotesk** (`--sans`) for the interface.

A type style is one token that sets weight, size, line height and typeface together. Write `font:var(--font-message)`. Override only what a box needs, such as `line-height:24px` to centre a pin's number. Labels add their spacing and case: `letter-spacing:.08em; text-transform:uppercase`.

| Token | Value | Use |
|---|---|---|
| `--font-label` | `700 var(--text-label)/1.3 var(--sans)` | buttons, tags, progress words, table heads, in uppercase |
| `--font-small` | `400 var(--text-small)/1.4 var(--sans)` | times, metadata, the legend |
| `--font-small-strong` | `700 var(--text-small)/1.3 var(--sans)` | section labels (uppercase), names in the conversation |
| `--font-message` | `400 var(--text-message)/1.45 var(--sans)` | the conversation, pop-ups, cards, tables |
| `--font-message-strong` | `700 var(--text-message)/1.4 var(--sans)` | tabs, a name or number that leads a row |
| `--font-body` | `400 var(--text-body)/1.55 var(--sans)` | the board's body text and fields |
| `--font-body-strong` | `700 var(--text-body)/1.3 var(--sans)` | a version's label, a strong line in a pop-up |
| `--font-subtitle` | `400 var(--text-body)/1.4 var(--serif)` | the goal or question under the board's title |
| `--font-heading` | `700 var(--text-heading)/1.3 var(--serif)` | a card, pop-up or section heading |
| `--font-title` | `700 var(--text-title)/1.2 var(--serif)` | the board's title |
| `--font-figure` | `700 var(--text-title)/1.1 var(--sans)` | a figure in the stats header; its "/ total" in `--text-message` |
| `--font-code` | `400 .9em/1.4 ui-monospace, SFMono-Regular, Menlo, monospace` | code in messages |

The styles are built from these sizes:

| Token | Size |
|---|---|
| `--text-label` | 11px |
| `--text-small` | 12px |
| `--text-message` | 14px |
| `--text-body` | 15px |
| `--text-heading` | 17px |
| `--text-title` | 20px |

Slides and drawings, such as the research map and architect-better's diagrams, keep their own type: they are documents and pictures that scale with their frame.

An article page, such as the website or a document a skill writes, uses these, as n14n.dev:

| Token | Value | Use |
|---|---|---|
| `--font-site` | `700 var(--text-site)/1.2 var(--sans)` | the site's name in the site header |
| `--font-article-title` | `700 var(--text-article-title)/1.15 var(--serif)` | the title of an article page |
| `--font-lead` | `400 var(--text-lead)/1.55 var(--serif)` | the paragraph under an article title |
| `--font-prose` | `400 var(--text-prose)/1.75 var(--serif)` | article text, at most 42rem wide (about 70 characters) |
| `--text-site` | 1.5rem | |
| `--text-article-title` | 2.75rem | 2rem under 700px, set in page.css |
| `--text-lead` | 1.25rem | |
| `--text-prose` | 17px | |

- Use a style from these tables. A new style or size is a change to this document.
- Uppercase only for labels of two or three words. Never for sentences.

## Spacing and layout

Boards use these tokens for every padding, margin and gap, named by what the space does. Write `padding:var(--space-item)`, and `calc(-1 * var(--space-item))` for a negative margin. 1px is a hairline, such as a tag's top padding, not a space.

| Token | Value | Use |
|---|---|---|
| `--space-tight` | 4px | inside small things: a badge, a tag; between a mark and its word, between lines of a list |
| `--space-control` | 8px | between controls: buttons, tags, the parts of a pop-up |
| `--space-item` | 12px | inside an item or a card, between cards, above the view |
| `--space-section` | 16px | between sections of a column, between tabs |
| `--space-edge` | 20px | the sides of the header, the view and the side column |
| `--space-group` | 24px | between groups of cards, around a slide |
| `--space-wide` | 40px | between the header's title and its figures, the end of a scrolling view |

When no role fits, pick the token whose role is closest, and do not add a value.

Slides keep their own spacing, as their type.

| Layout | Rule |
|---|---|
| Board | See Board layout below. |
| Article page | Band (10px), a header, the title with a terracotta band under it, then the prose column, max 42rem. A figure or a side panel may sit beside the prose from 960px. |

## Board layout

A board fills the window and never scrolls as a page: each area scrolls inside itself, so the header and the message box stay in view. [DESIGN.html](DESIGN.html) draws each layout below.

### Areas

From top to bottom, then left to right. Every board has all of them, in this order.

| Area | Markup | Holds | Scrolls |
|---|---|---|---|
| Band | `div.band` | the sayagata band, 6px | no |
| Header | `header` | the title, and the figures or the controls (see Headers) | no |
| Offline notice | `p.offline` | only when the server stops answering | no |
| Work | `div.work` | a grid: the view, then the side column at `minmax(20rem, 24rem)` behind a 2px ink rule | no |
| View | `main` | what the agent is working on; one of the view patterns below | inside itself |
| Side column | `aside.notes` | the conversation, and what else the agent says (see Side column) | the thread only |
| Toast, pop-ups | `div.toast`, `.qpop`, `.pop` | over everything, outside `.work` | no |

Padding is `--space-edge` at the sides of the header, the view and the side column, and `--space-item` above the view's first row (tabs bring their own `--space-section`).

### Headers

| Header | Markup | Use when | Board |
|---|---|---|---|
| Stats header | `header.bar--stats`: the title (and a goal line under it) on the left, `.stats` on the right | the agent works on its own, and the user comes back to see how far it is and what waits for them | research, code, architect |
| Question header | `header`: `.ttl` with the title and `p.question` under it on the left, `.controls` on the right | the page asks the user one question, and the user works the page with modes and views | canvas, show |

- In the stats header the title wraps to two lines at most, then cuts off with an ellipsis. The question header wraps its controls under the title on a narrow window.
- In the question header, keep to the controls used on every visit. Put settings changed rarely in a menu, as the canvas's Display menu.
- A board never has both: figures go in the stats header, a question goes in the question header.
- The one exception is page.js's "N your turn" figure, on every page that talks to the agent. A page with a stats header places it among its own figures (`.yourturn` slot) and has no other figure for what waits for you; a page with a question header places it among its controls, one line at their size.

### View patterns

| Pattern | Layout of the view | Board |
|---|---|---|
| Tool row and canvas | `.tools`: the legend on the left, the view's buttons on the right; then one drawing that takes the rest of the height and pans and zooms inside its frame | research |
| Cards and fixed list | the agents at work as cards: a section label and legend, then cards in a grid that scroll; under them a list fixed at the bottom of the view, five rows high, scrolling on its own | code |
| Tabs and sections | `.tabs` fixed at the top of the view, then one section at a time; the view scrolls under the tabs | architect |
| Versions side by side | a label row per version (its name, Full size, and thumbs up and down from three versions), then the versions in equal columns on the neutral surround, each scrolling inside its frame | canvas |
| Strip and stage | `nav.route`: Previous, the strip of slides, the count, Next; then one slide centred on the surround | show |

- A new board uses one of these patterns. A new pattern is a change to this document.
- Put what the user acts on most at the top of the view, and what they read for detail below it or in a pop-up.
- A drawing, a version or a slide sits on `--surround` or in a 1px `--line` frame. Panels of text sit on cream.

### Side column

From top to bottom:

The side column holds the conversation, and above it a list of the agents at work when they are not what the view shows.

1. Optional: the agents at work, with a section label, at most 30% of the height, scrolling on its own (research). Put them here when a run can have many agents, up to about twenty, and the view shows something else, such as the map. Put them in the view, as cards, when the agents are what the user watches (code).
2. `.notes-top`: the label "Conversation", and the All / Open filter when the board has items the user accepts.
3. `p.empty` until the first message; it says what the user can click to comment, and that they can write below.
4. `ol.thread`: the items in time order. What waits for the user comes last, next to the message box.
5. `.composer`: a panel for a decision when one is open (`.decide`), the `.unwatched` notice, the label "Message to …" naming the agent, the box, then `.send`: Send first, then the quiet buttons (Decide…, Copy all, Review again…), then the status line.

- What waits for the user comes last in the thread. On a board with a stats header, a button figure there also counts it and goes to it.
- A page opened as a file, with no agent, hides the side column and the view takes the whole width (show-better).

### Narrow windows

- Under 900px, the work stops being a grid: the view comes first at 85% of the window height, the side column under it behind a 2px ink rule, and the page scrolls.
- The stats header keeps one row and cuts the title. The question header puts its controls under the title.
- Boards are made for a desktop window. Phones are not tested.

## Components

All of these are in page.css. A board that needs one uses it; it does not restyle it.

### Band

- Use for: the top edge of every page. Umber with the sayagata pattern (`.band`, `--saya`). On an article page, a terracotta band with the pattern sits under the title.
- Name and role: decorative, no role.

### Stats header

- Use for: the board's title and the few figures that tell the user where the work stands.
- Markup: `<header class="bar--stats"><div><h1>…</h1></div><div class="stats">` with a `.stat` per figure: `<b>` the figure, then its words. A total is `<span class="of"> / n</span>` inside `<b>`. A progress meter under a figure is `<span class="meter"><i style="width:…%"></i></span>`.
- A figure that takes the user somewhere, such as to what waits for them, is a `<button class="stat">` and is underlined. A plain figure is a `<span>` and is not.
- States: default; hover and focus thicken the underline of a button figure.
- The title wraps to two lines at most, then cuts off with an ellipsis.
- Correct: "2 open questions" as a button that scrolls to the first one. Wrong: an underlined figure that does nothing when clicked.

### Section label

- Use for: naming a part of the board, such as Agents, Tasks, Conversation (`.section-h`, or any `h2` in `.notes`).
- Name and role: a real `h2`.

### Legend

- Use for: saying what each mark on the board means (`<ul class="legend">`; only a `ul`, because show-better's slides have their own `p.legend`, one `li` per mark with its word).
- Correct: a mark and "blocked". Wrong: a mark without a word.

### Tabs and segmented controls

- Tabs (`.tabs`, `role="tab"`): switch between sections of one page; the selected tab has a terracotta underline; a count badge in umber, or moss-dark when done. `.tabs--wrap` on the row lets a page with many tabs wrap them onto more lines instead of scrolling the row.
- Segmented control (`.seg`, `.seg--light` on cream): one of a few options, the chosen one filled, `aria-pressed`.

### Buttons

| Class | Use |
|---|---|
| `.btn` | the main action of a place: Send, Answer |
| `.btn--quiet` | the other actions: Reply, Decide…, Copy all |
| `.btn--sm` | an action inside a conversation item |
| `.mini` | a small square action, such as a thumbs up |

- Labels are uppercase `--font-small-strong` (`--font-label` on a small button). Square corners. A button names its action.

### Chip

- Use for: a short state word on an item, in a table or a header, such as "Supported" or "Waiting for you" (`.chip`).
- Markup: `<span class="chip ok">Supported</span>`. The modifier carries the meaning, and the word always says it too:

| Class | Meaning | Look |
|---|---|---|
| `.ok` | done, confirmed | moss-dark border and word |
| `.error` | blocked, contradicted | error border and word; page.css puts ⊘ before the word |
| `.working` | being worked on | terracotta border, terracotta-dark word, a pulsing bar |
| `.wait` | waiting for the user | umber border and word |
| `.plain` (or none) | anything else | sand border, ink on linen |

- The word is in the label style, uppercase, one or two words. Do not recolour a chip or add a modifier for a new meaning: use the nearest one and change the word.
- Name and role: text only, no role. A chip that is a link is an `a.chip`.

### Table

- Use for: records with the same fields, one per row (`table.tbl`, on a `table` element only); its heads are in the label style and muted, its rows are separated by hairlines.
- Markup: `<table class="tbl"><thead><tr><th>…` with `th` heads and `td` cells.
- Name and role: a real `table` with `th` heads. A page-specific highlight, such as an outline on a row, belongs to that page's file.

### Decision panel

- Use for: a decision the user is asked to make on the page body, next to the figure or table it is about (`.decide`): a cream box with a sand border, a short paragraph, then the options.
- Markup: `<div class="decide"><p>…</p>` and its buttons.
- Name and role: a `div` in the page's flow; its buttons name their options. The conversation's own decisions use "Decision in the conversation".

### Section intro

- Use for: one line under a section's title that says what the section is for (`.intro`), in `--font-message`, up to 72 characters wide. One sentence, not a paragraph.
- Markup: `<p class="intro">…</p>`.
- Name and role: a plain paragraph.

### Inline record form

- Use for: adding, changing or removing one record in place (`.rec`): a cream box with a sand border, a label above each field, and one button under the last.
- Markup: `<form class="rec">` with a `label` and its `input`, `textarea` or `select` for each field, a `fieldset` with a `legend` for a group of radio buttons or checkboxes, and one `.btn`.
- Name and role: a `form` with a name (its heading, or `aria-label`); every field has its `label`.

### Agents at work

- Use for: the agents working now, one row each: who, what on, and how long (`.agentsec`, built by `pageAgents` in page.js). Put it at the top of the side column when a run can have many agents and the view shows something else (see Side column).
- Markup: `<section class="agentsec" aria-labelledby="agents-h"><h2 class="section-h" id="agents-h">Agents</h2><ul class="agents" id="agents"></ul></section>`, then `pageAgents(rows, {now, empty})` gives the `li` rows. A row is who, what, since (when its work began), and last (when the agent last wrote a record). Nothing else is read: the board says what each agent does, and the list reads no log.
- A row with since shows `.chip.working` with the age, "Checking, 12 min". From 30 minutes after its last record (the server's `quiet_after`, the same for every page) the row reads "No word from analyst-2 for 40 min" in the error colour. A second try reads "second try". A row that opens something is a `button`; an agent that checks what others wrote (`.verifier`) has a moss edge, the others a terracotta one.
- The section scrolls on its own, at most 30% of the height.
- Name and role: a section named by its heading, a plain list; a row that is a button is named by its text.

### Conversation

- The right column of every board (`.notes`), built by page.js: one row per thread, then the message box.
- A row holds, left to right: the state chip, the agent's progress, "You:" or "Agent:" and the first sentence of the thread, a drawn equilateral triangle (▼ opens the thread, ▲ folds it; no outline), where the head of the row opens and folds the thread, the message count, and the buttons for the state. An open thread's messages run flat across the row, with no box inside the row.
- Thread states and their left edge: Your turn umber, Agent's turn sand (Not seen, Seen) or terracotta (Working), Done moss-dark. The progress says the state in words.
- Progress is three bars with a green Done step: Not seen shows none, Seen one, Working two, Done all three in moss-dark.
- Buttons by state: Answer is the one filled (umber) button on a row, with ✓ beside it; ✓, Reply and Reopen are outlined; a thread done by the agent offers ✓ (Confirm done) and Reopen; one you closed offers Reopen. Buttons differ by more than their text.
- ✓ closes a thread. The row stays in place as Closed with its own Undo for 6 seconds, then leaves Open and shows Done in All.
- A page's own kind, such as a decision, an approval or a worker's report, keeps its body and controls inside the row; a done thread of any kind still offers ✓ (Confirm done) and Reopen. A user's action that needs no reply, such as a verdict or a confirmation, starts closed: it shows in All, never in Open.
- Do not rebuild any part of it. A page that needs the conversation embeds page.js.

### Pop-up

- Use for: details of a question or an agent (`.qpop`, 34rem wide), or a comment box (`.pop`, 22rem, with `.target`, a textarea and a `.row2` of buttons). Cream under the n14n band (umber with the saya pattern, 6px), no outline, `--shadow`, square corners.
- A details pop-up has a header (`.hd`): what it is and its state as a phrase (`.kind`), the title, and the full question (`.full`) when there is one. A hairline separates it from the body (`.bd`): the answer or summary, then sections (`.sec`), each under a section label, the last one the conversation with its message box. Tags keep their own colours in the header, such as a task's mode.
- The comment box's `.target`, where the comment points, is its header, above a hairline.
- Name and role: `role="dialog"` with a name (its heading, or `aria-label`); Escape closes it; the close button is `.x`.

### Decision in the conversation

- An agent's decision or question is a `li.msg.decision`, with an umber edge and the agent's name and time in umber.
- An open question's footer is its state, a filled Answer and an outlined ✓ (use the default), on one row (`.foot.question`). Each control's accessible name includes the question. After ✓ the focus goes to the next open question, then to what waits next.
- The top bar counts the threads that wait for the user as the figure "N your turn".
- A page whose defaults never apply on a timer sets `pageDecision({suggested: true})`: the default reads "Suggested default" and no deadline shows.

### Notices

| Class | Use |
|---|---|
| `.unwatched` | above the message box when no agent is watching, so the user knows a message waits |
| `.offline` | under the header when the page's server stops answering |
| `.toast` | a short confirmation at the bottom; moss-dark for done, error for failure |

### Diagram boxes

- Nodes are cream boxes with a 1px sand border and square corners, ink text. A dashed border for a group or a boundary. Linen to shade related boxes. Terracotta only as the outline of the selected box. No coloured fills, no rounded corners, no heavy ink strokes.

### Article page parts

- Site header: the site's name in `--font-site`, with what the page is in muted. It does not have to be n14n.dev's header.
- Title: serif, with the terracotta band under it; a lead paragraph under the band.
- Figure: a sand-bordered box, its caption under a rule.

## Rules

- Use only the colours, type sizes, spaces and components in this document, by their token, because one board that drifts makes the others look inconsistent. Correct: `color:var(--muted); padding:var(--space-control); font:var(--font-message)`. Wrong: `color:#777; padding:9px; font:400 14px/1.4 var(--sans)`.
- Make a shared part shared: if two boards need the same rule, it goes in page.css, because copies drift. Correct: `.legend` in page.css. Wrong: the same `.key` rules in two boards.
- Square corners everywhere, except the round comment pins and numbered markers, because n14n never rounds boxes.
- One shadow (`--shadow`), on things that float over the page only.
- A thing that looks clickable is clickable, and the reverse: underline only links and button figures.
- Pair every colour that means a state with a word or a mark.
- Text colour and background follow the "Allowed on" column above.

## Known conflicts

None. A conflict between a rule above and a page is listed here until the user decides it.

## Changes and exceptions

- 2026-11-20: first version, drawn from the five boards. Added the names `--moss`, `--terracotta-dark`, `--white`, `--shadow`, `--surround-dark`, `--frame` and `--frame-dark` for values the boards already used. Moved the stats header, meter, section label, legend, pop-up, question box, decision item and the "not watching" notice into page.css. The research board's waiting figure is now a button that goes to the waiting decision, as on code-better's dashboard. architect-better's comment box now has the shared pop-up border, shadow and textarea, and its "architect is away" notice the shared `.unwatched` style it lacked.
- 2026-11-20: small buttons, tags, progress words and the canvas and slide labels went from 10px to 11px (the user's decision): text that carries meaning is never under 11px.
- 2026-11-20: architect-better's view has 20px at the sides, as the other boards; the `--pad` token is gone. The agents at work stay in the side column on research-better's board (a run can have twenty) and in the view on code-better's dashboard (they are the work): the side column rule says when to use which.
- 2026-11-20: spacing and type sizes became tokens (`--space-*`, `--text-*`) in every board. Off-scale values moved to the nearest step: 3px to 4, 5 to 6, 7 to 8, 14 to 16, 18 to 20, 28 to 24, 48 to 40. Type sizes merged: 13px into 14 (`--text-message`), 16 and 18 into 17 (`--text-heading`), 22 into 20 (`--text-title`). On linen, muted text and the progress words use ink, and research-better's "contested" uses `--terracotta-dark`.
- 2026-11-20: spacing tokens named by role, in seven steps instead of eleven (the user's choice): 2px became 4, 6 became 8, 10 became 12, and 32 became 40.
- 2026-11-20: type styles became tokens (`--font-*`): each sets weight, size, line height and typeface, and replaces the full shorthand written in each rule. Line heights of the same style were made equal (1.4, 1.45 and 1.5 became the style's one value), and weight 600, which the page never loaded, became 700.
- 2026-11-21: pop-ups lost the 2px ink border for the n14n band (the user's decision): the outline read heavy against the Journal style. Details pop-ups now open with a header (what, title, full question) and labelled sections; the research board shows a question's claims open, not folded, and states its status as a phrase instead of a dot-joined line.
