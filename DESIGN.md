# Design language: better-ai

better-ai's pages share one look: the live pages the skills serve (boards) and the better-ai website. It is the n14n "Journal" language, applied to two kinds of page:

- **Board**: a live page a skill serves while an agent works, such as research-better's board, code-better's dashboard, design-better's canvas, show-better's slides and architect-better's design page. One window, no page scroll, the conversation with the agent in a fixed right column.
- **Article page**: a page to read, such as a page of the website or a document a skill writes. Scrolls, with a column of prose.

[DESIGN.html](DESIGN.html) shows the colours, type and components rendered from the shared stylesheet.

## Where it lives

| What | File | Rule |
|---|---|---|
| Tokens and shared components | `skills/*/scripts/page.css` | Identical in every skill that serves a board. Change it in one skill, then copy it to the others: the Scripts workflow fails if the copies differ. |
| The conversation column | `skills/*/scripts/page.js`, `page.py` | Identical copies, as page.css. |
| What only one board shows | `board.html`, `dashboard.html`, `canvas.css`, `show.css`, `architect.css` | Uses only the tokens and components below. |
| This document | `DESIGN.md`, `DESIGN.html` | The names here are the names in page.css. DESIGN.html holds copies of page.css and page.js, so it works as a single file: after changing either, paste it again into DESIGN.html (the test says which). |

`tests/test_design.py` fails when a page uses a colour that is not in the colour table below, a raw px value for a space or a type size, or when this document and page.css disagree.

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

Boards use these tokens for every type size. Write `font-size:var(--text-small)` or `font:700 var(--text-label) var(--sans)`.

| Token | Size | Typeface and weight | Use |
|---|---|---|---|
| `--text-label` | 11px | sans 700, uppercase, .08–.1em spacing | buttons, tags, progress words, table heads. Nothing under it |
| `--text-small` | 12px | sans 400 or 700 | times, metadata, the legend, section labels (uppercase) |
| `--text-message` | 14px | sans 400 | the conversation, pop-ups, cards, tables, secondary lines |
| `--text-body` | 15px | sans 400 | the board's body text and fields |
| `--text-heading` | 17px | serif 700 | a card, pop-up or section heading |
| `--text-title` | 20px | serif 700, or sans 700 for a header figure | the board's title; a figure in the stats header, its "/ total" in `--text-message` |

Code in messages is `ui-monospace` at .9em. Slides and drawings, such as the research map and architect-better's diagrams, keep their own sizes: they are documents and pictures that scale with their frame.

An article page, such as the website or a document a skill writes, uses these tokens, as n14n.dev:

| Token | Size | Typeface and weight | Use |
|---|---|---|---|
| `--text-site` | 1.5rem | sans 700 | the site's name in the site header |
| `--text-article-title` | 2.75rem | serif 700, line height 1.15 | the title of an article page; 2rem under 700px, set in page.css |
| `--text-lead` | 1.25rem | serif 400, line height 1.55 | the paragraph under an article title |
| `--text-prose` | 17px | serif 400, line height 1.75 | article text, at most 42rem wide (about 70 characters) |

- Use a token from this table. A new size is a change to this document.
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

- The stats header never wraps: the title cuts off. The question header wraps its controls under the title on a narrow window.
- In the question header, keep to the controls used on every visit. Put settings changed rarely in a menu, as the canvas's Display menu.
- A board never has both: figures go in the stats header, a question goes in the question header.

### View patterns

| Pattern | Layout of the view | Board |
|---|---|---|
| Tool row and canvas | the agents at work in one row; `.tools`: the legend on the left, the view's buttons on the right; then one drawing that takes the rest of the height and pans and zooms inside its frame | research |
| Cards and fixed list | the agents at work: a section label and legend, then cards in a grid that scroll; under them a list fixed at the bottom of the view, five rows high, scrolling on its own | code |
| Tabs and sections | `.tabs` fixed at the top of the view, then one section at a time; the view scrolls under the tabs | architect |
| Versions side by side | a label row per version (its name, Full size, and thumbs up and down from three versions), then the versions in equal columns on the neutral surround, each scrolling inside its frame | canvas |
| Strip and stage | `nav.route`: Previous, the strip of slides, the count, Next; then one slide centred on the surround | show |

- A new board uses one of these patterns. A new pattern is a change to this document.
- Put what the user acts on most at the top of the view, and what they read for detail below it or in a pop-up.
- A drawing, a version or a slide sits on `--surround` or in a 1px `--line` frame. Panels of text sit on cream.

### Side column

From top to bottom:

The side column holds the conversation only. The agents at work belong to the view, at its top, because they are part of what the agent is doing.

1. `.notes-top`: the label "Conversation", and the All / Open filter when the board has items the user accepts.
2. `p.empty` until the first message; it says what the user can click to comment, and that they can write below.
3. `ol.thread`: the items in time order. What waits for the user comes last, next to the message box.
4. `.composer`: a panel for a decision when one is open (`.decide`), the `.unwatched` notice, the label "Message to …" naming the agent, the box, then `.send`: Send first, then the quiet buttons (Decide…, Copy all, Review again…), then the status line.

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
- The header never wraps: the title cuts off with an ellipsis.
- Correct: "2 open questions" as a button that scrolls to the first one. Wrong: an underlined figure that does nothing when clicked.

### Section label

- Use for: naming a part of the board, such as Agents, Tasks, Conversation (`.section-h`, or any `h2` in `.notes`).
- Name and role: a real `h2`.

### Legend

- Use for: saying what each mark on the board means (`<ul class="legend">`; only a `ul`, because show-better's slides have their own `p.legend`, one `li` per mark with its word).
- Correct: a mark and "blocked". Wrong: a mark without a word.

### Tabs and segmented controls

- Tabs (`.tabs`, `role="tab"`): switch between sections of one page; the selected tab has a terracotta underline; a count badge in umber, or moss-dark when done.
- Segmented control (`.seg`, `.seg--light` on cream): one of a few options, the chosen one filled, `aria-pressed`.

### Buttons

| Class | Use |
|---|---|
| `.btn` | the main action of a place: Send, Answer |
| `.btn--quiet` | the other actions: Reply, Decide…, Copy all |
| `.btn--sm` | an action inside a conversation item |
| `.mini` | a small square action, such as a thumbs up |

- Labels are uppercase sans, `--text-small` (`--text-label` on a small button). Square corners. A button names its action.

### Conversation

- The right column of every board (`.notes`), built by page.js: the thread of items, each with its replies, its progress and its actions, then the message box.
- Item states and their left edge: seen sand, asked umber, working terracotta, done and accepted moss-dark, reopened error. The progress row says the state in words.
- Accept is a small umber button with ✓; Reply and Answer are quiet buttons.
- Do not rebuild any part of it. A page that needs the conversation embeds page.js.

### Pop-up

- Use for: details of a question or an agent (`.qpop`, 34rem wide), or a comment box (`.pop`, 22rem, with `.target`, a textarea and a `.row2` of buttons). Cream, a 2px ink border, `--shadow`, square corners.
- Name and role: `role="dialog"` with a name (its heading, or `aria-label`); Escape closes it; the close button is `.x`.

### Decision in the conversation

- An agent's decision or question is a `li.msg.decision`, with an umber edge and the agent's name and time in umber.

### Notices

| Class | Use |
|---|---|
| `.unwatched` | above the message box when no agent is watching, so the user knows a message waits |
| `.offline` | under the header when the page's server stops answering |
| `.toast` | a short confirmation at the bottom; moss-dark for done, error for failure |

### Diagram boxes

- Nodes are cream boxes with a 1px sand border and square corners, ink text. A dashed border for a group or a boundary. Linen to shade related boxes. Terracotta only as the outline of the selected box. No coloured fills, no rounded corners, no heavy ink strokes.

### Article page parts

- Site header: the site's name in sans 700 at `--text-site`, with what the page is in muted. It does not have to be n14n.dev's header.
- Title: serif, with the terracotta band under it; a lead paragraph under the band.
- Figure: a sand-bordered box, its caption under a rule.

## Rules

- Use only the colours, type sizes, spaces and components in this document, by their token, because one board that drifts makes the others look inconsistent. Correct: `color:var(--muted); padding:var(--space-control)`. Wrong: `color:#777; padding:9px`.
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
- 2026-11-20: the agents at work moved from the side column to the top of the view on research-better's board, as on code-better's dashboard; the side column holds the conversation only. architect-better's view has 20px at the sides, as the other boards; the `--pad` token is gone.
- 2026-11-20: spacing and type sizes became tokens (`--space-*`, `--text-*`) in every board. Off-scale values moved to the nearest step: 3px to 4, 5 to 6, 7 to 8, 14 to 16, 18 to 20, 28 to 24, 48 to 40. Type sizes merged: 13px into 14 (`--text-message`), 16 and 18 into 17 (`--text-heading`), 22 into 20 (`--text-title`). On linen, muted text and the progress words use ink, and research-better's "contested" uses `--terracotta-dark`.
- 2026-11-20: spacing tokens named by role, in seven steps instead of eleven (the user's choice): 2px became 4, 6 became 8, 10 became 12, and 32 became 40.
