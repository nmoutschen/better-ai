# `/show-better`

Introduces a dense document, such as a research paper, a strategy or a design doc, with a short sequence of visual panels you go through before you read it. Each panel shows one relation you would otherwise work out from the prose, and every value is checked against the document.

## When to use it

- Before reading a long, dense document, to see its question, its answer and how its main ideas relate.
- After an agent wrote a long report, to add a visual introduction to it.

It does not turn every point into a visual. A point one sentence states well stays a sentence. The panels introduce the document; they do not replace it.

Use something else nearby:

- For the wording of a text, use [`/write-better`](write-better.md). `/write-better` sends long, dense documents here.
- To design or build an interface, use [`/design-better`](design-better.md).

## How to run it

```
/show-better <document, path or content>
```

Example: `/show-better reports/pricing-strategy.md`.

Without an argument, it introduces the agent's previous output.

## What happens

1. **It names the goal.** It works out what you must understand, learn, do or decide after reading, and what you already know. For an expert reader it shows less. If it guesses the goal, it says so when it hands over.
2. **It reads the whole document** and writes an extract: the question and the answer, the parts, the relations between ideas, every value it might show with where it comes from, and the terms you need.
3. **It plans 5 to 12 panels:**
   - a cover whose title states the answer
   - an overview of how the main ideas relate
   - a panel or a few per important part, in the document's order, each saying where to read the detail
   - a closing panel on what your goal needs most
4. **It picks each panel's kind from the relation it shows.** There are more than twenty kinds, including concept maps, flows, set diagrams, matrices, slope charts, dot plots, scatter plots, timelines, quadrants and counts like "7 of 15". Code lays out every diagram.
5. **It checks the panels.** A checker prints every headline, value, label and note. The agent compares each against the extract and the document, and checks that each headline matches its visual. It looks at the rendered page for overlaps, cut-off labels and missing highlights.
6. **It hands over** the link or path once, with the document's answer in one or two sentences in the chat.

If your style guide conflicts with the renderer's fixed style, it tells you and asks whether to keep the renderer's style.

## What you get

- An HTML page at `.show/<slug>/index.html`, opened in your browser or published as a link. It is not committed unless you ask.
- The spec it was drawn from, `.show/<slug>/spec.json`.
- Or, for a terminal or chat, the same panels as plain text or Markdown.
- The document's answer, stated in the chat, and any assumption it made about the goal or the reader.

Text output has three options:

- `--ascii` keeps the text intact when pasted into plain-text files or commit messages.
- `--screen-reader` gives sentences and value lists instead of drawn diagrams. The agent uses it if you say you read with a screen reader or find the diagrams hard to follow.
- `--format md` gives Markdown.

## Works with

- [`/write-better`](write-better.md) checks the wording of the title, summary, headlines, labels and notes.
- [`/write-better`](write-better.md) calls `/show-better` to introduce a long, dense document.

## What it needs

| Capability | Without it |
|---|---|
| Python 3, and a browser that can open files on the machine or a way to publish a page | It renders text or Markdown for the terminal or chat instead. |
| Python 3 at all | It writes the panels in Markdown by hand: tables for comparisons, lists for structure, and plain-text diagrams only for flows of four short steps or fewer. It checks every value against the document by hand. |
| Viewing the page or a screenshot | It says it could not look at the result. |
