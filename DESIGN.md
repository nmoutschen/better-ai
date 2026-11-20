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
| This document | `DESIGN.md`, `DESIGN.html` | The names here are the names in page.css. |

`tests/test_design.py` fails when a page uses a colour that is not in the colour table below, or when the table and page.css disagree.

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

| Name | Typeface | Size | Weight | Line height | Use |
|---|---|---|---|---|---|
| title | serif | 20px | 700 | 1.2 | the board's title in the header bar |
| stat | sans | 20px | 700 | 1.1 | a figure in the header; its "/ total" at 14px |
| card title | serif | 16–17px | 700 | 1.3 | a card or pop-up heading |
| body | sans | 15px | 400 | 1.55 | the board's body text and fields |
| message | sans | 14px | 400 | 1.45 | text in the conversation, pop-ups and cards |
| small | sans | 12–13px | 400 | 1.4 | times, metadata, the legend |
| label | sans | 11–12px | 700, uppercase, .08–.1em spacing | 1.2 | section labels, buttons, tags, progress words. Never under 11px |
| code | ui-monospace | .9em | 400 | 1.4 | code in messages |
| article title | serif | 2.75rem (2rem under 700px) | 700 | 1.15 | the title of an article page |
| lead | serif | 1.25rem | 400 | 1.55 | the paragraph under an article title |
| prose | serif | 17px | 400 | 1.75 | article text, at most 42rem wide (about 70 characters) |

- Use a size from this table. A new size is a change to this document.
- Uppercase only for labels of two or three words. Never for sentences.

## Spacing and layout

Spacing values, in px: 2, 4, 6, 8, 10, 12, 16, 20, 24, 32, 40. Use these only. They are not tokens yet.

| Layout | Rule |
|---|---|
| Board | Band (6px), header bar, then a grid: the board's own view, and the conversation column at `minmax(20rem, 24rem)` behind a 2px ink rule. Each part scrolls inside itself. Under 900px the column moves below and the page scrolls. |
| Board padding | 20px at the sides of the header, the view and the conversation. |
| Article page | Band (10px), a header, the title with a terracotta band under it, then the prose column, max 42rem. A figure or a side panel may sit beside the prose from 960px. |

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

- Labels are uppercase sans, 12px (11px small). Square corners. A button names its action.

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

- Site header: the site's name in sans, 1.5rem 700, with what the page is in muted. It does not have to be n14n.dev's header.
- Title: serif, with the terracotta band under it; a lead paragraph under the band.
- Figure: a sand-bordered box, its caption under a rule.

## Rules

- Use only the colours, sizes and components in this document, because one board that drifts makes the others look inconsistent. Correct: `color:var(--muted)`. Wrong: `color:#777`.
- Make a shared part shared: if two boards need the same rule, it goes in page.css, because copies drift. Correct: `.legend` in page.css. Wrong: the same `.key` rules in two boards.
- Square corners everywhere, except the round comment pins and numbered markers, because n14n never rounds boxes.
- One shadow (`--shadow`), on things that float over the page only.
- A thing that looks clickable is clickable, and the reverse: underline only links and button figures.
- Pair every colour that means a state with a word or a mark.
- Text colour and background follow the "Allowed on" column above.

## Known conflicts

Each of these breaks a rule above. They stay until the user decides.

- research-better's board writes "contested" claims in terracotta text (`.chip.bad`, 2.9:1 on cream). Alternative: `--terracotta-dark`, as architect-better's "1 comment".
- `--muted` text on linen is 4.0:1, under 4.5:1. page.css already switches times on linen to ink; other muted text on linen should do the same.
- The board type scale has more sizes than it needs (11, 12, 13, 14, 15px for small text). Merging them changes how boards look.
- Spacing values are not named in code.

## Changes and exceptions

- 2026-11-20: first version, drawn from the five boards. Added the names `--moss`, `--terracotta-dark`, `--white`, `--shadow`, `--surround-dark`, `--frame` and `--frame-dark` for values the boards already used. Moved the stats header, meter, section label, legend, pop-up, question box, decision item and the "not watching" notice into page.css. The research board's waiting figure is now a button that goes to the waiting decision, as on code-better's dashboard. architect-better's comment box now has the shared pop-up border, shadow and textarea, and its "architect is away" notice the shared `.unwatched` style it lacked.
- 2026-11-20: small buttons, tags, progress words and the canvas and slide labels went from 10px to 11px (the user's decision): text that carries meaning is never under 11px.
