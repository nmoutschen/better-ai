---
name: show-better
description: Helps an AI agent introduce a dense document, such as a research paper, a strategy or a design doc, with a short sequence of visual panels the reader goes through before reading it. Each panel shows a relation the reader would otherwise have to work out from the prose, in a form chosen from a wide range (concept maps, set diagrams, slope charts, distributions, hierarchies, quadrants and more). The presentation is rendered as an HTML page or as plain text for a terminal, and every value is checked against the source.
argument-hint: "[DOCUMENT OR CONTENT]"
---

# Show Better

IF invoked without argument, USE these instructions on your previous output.
IF invoked with a document, a path or content as argument, USE these instructions to introduce it.

Being invoked means: find the structure and the relations in the content that a visual shows better than prose, and show them. It does NOT mean every point becomes a visual. A point that one sentence states well stays a sentence.

## Principles

1. Graphics help comprehension only modestly, and only graphics that organize information help. Pictures that merely illustrate add nothing significant. A visual is better than prose when it lets the reader see a relation that the text would make them work out.
2. Organizers given with a text improved comprehension of that text, and signals of a text's structure helped learning. The presentation is an organizer for the document: it introduces the document and does not replace it.
3. Plain diagrams supported transfer to new cases better than rich, detailed ones. Readers who already know a topic need less guidance, and guidance can get in their way.
4. Readers learn more deeply from content in segments they move through at their own pace. Keeping one structure from panel to panel helped memory, and most professional visual stories move from general to specific.
5. Readers recall a panel's message from its headline, and take the most prominent feature of a visual as its point.
6. Reach, preference and engagement do not show understanding. Readers prefer formats they do not learn more from, and polish does not show that a visual is understood.
7. Generated slides fail mostly through missing content, then wrong values. Language models read text diagrams far more reliably than they draw them, so every diagram is laid out by code.
8. Placing a visual introduction before a full research paper or business document is a design choice, and so are the rules marked as design choices.

## 1. Know the goal, the reader and the medium

### 1.1. Name the GOAL

IDENTIFY what the reader must UNDERSTAND, LEARN, DO or DECIDE after reading the document. The presentation prepares the reader for that GOAL. IF the context does not show the GOAL, CHOOSE the most plausible one and STATE it when you hand the presentation over (section 7).

IDENTIFY what the reader already knows about the topic. FOR an expert reader, SHOW less: fewer panels and fewer labels.

### 1.2. Choose the medium

The renderer draws the same presentation in three formats. CHOOSE the first one the user can read:

1. **A page.** IF you can run Python 3, and you can either publish a page for the user or the user's browser can open files on the machine where you run commands, RENDER HTML (section 5). IF you can publish it, PUBLISH it and GIVE the link. OTHERWISE, OPEN it with `--open` and GIVE its path.
2. **A terminal or a chat.** IF the user reads in a terminal, RENDER `--format text`. IF they read Markdown, RENDER `--format md`. USE `--ascii` when the output must survive copying into plain-text files or commit messages. IF the user says they read with a screen reader, or says the diagrams are hard to follow, RENDER `--format text --screen-reader`: sentences and value lists instead of drawn diagrams.
3. **No renderer.** IF you cannot run Python, PRESENT the panels in Markdown (section 6).

DO NOT draw a text diagram by hand when the renderer is available.

DO NOT describe a page you have not rendered.

## 2. Read the document and extract its structure

READ the whole document before planning. WRITE an extract, and WORK from it, not from memory of the document:

1. **The question and the answer.** What problem does the document address, and what does it conclude or propose? FOR a business document, WRITE the situation, the complication, the question it raises, and the answer.
2. **The parts.** The document's sections in order, each with its title and a few words on what it covers.
3. **The relations.** What causes, depends on, contains, overlaps or competes with what. These are the candidates for visuals.
4. **The evidence.** Every value you might show, with the place in the document it comes from.
5. **The terms.** The words the reader must know to read the document.

## 3. Plan the panels

### 3.1. Order them as an introduction

PUT the question and the answer on the cover: the title states the answer, and the summary gives it in one or two sentences.

THEN, in this order:

1. An overview panel that shows how the document's main ideas relate, usually a `concept` or `groups` panel. This is the organizer: it shows the ideas, not the list of sections.
2. One panel or a few panels per important part, in the document's order, moving from the general to the specific. SET each panel's `part` to the section it introduces, and its `read` to where the reader finds the detail.
3. A closing panel on the point the GOAL needs most.

DO NOT add a panel that only lists the document's sections: the strip above each panel already shows where the reader is. USE a `map` only when the reader must find their way in a long document.

REFER to parts of the document by their titles, in headlines, notes and `read`. DO NOT use section numbers or § signs: the reader has not seen them yet.

KEEP the presentation to about 5 to 12 panels. This range is a design choice. IF the document needs more, INTRODUCE only the parts the GOAL needs.

### 3.2. Give each panel a relation to show

WRITE each panel's point as a sentence that states a conclusion, not a topic. THEN ASK: does a visual let the reader see something that this sentence does not already say?

- IF yes, the panel shows a relation among several items: a structure, an overlap, a change, a spread, a ranking, a dependency. CHOOSE the kind in section 3.3.
- IF the headline already says everything, such as a single number, USE a `text` panel, or fold the point into another panel. DO NOT draw a chart of one or two numbers just to have a visual.

### 3.3. Choose the kind by the relation

| What the reader must see | Kind |
|---|---|
| The parts of a long document the reader must find their way in | `map` |
| How ideas relate: causes, dependencies, parts of an argument | `concept` |
| A process or a sequence of steps | `flow` |
| Categories and what belongs to each | `groups` |
| A whole broken into parts, over several levels | `tree` |
| Which items belong to several overlapping categories | `sets` |
| Which items have which properties | `matrix` |
| Items that help in one form and not in another | `pairs` |
| Findings that raise or lower different outcomes | `effects` |
| Options placed on two judged dimensions | `quadrant` |
| A count out of a total, such as 7 of 15 | `units` |
| Values compared across items | `bars` |
| The change of several items between two states | `slope` |
| The spread of values, not only their average | `dots` |
| The relation between two measures across many items | `scatter` |
| A trend over many points | `line` |
| Events in time | `timeline` |
| One or two numbers the reader must remember | `numbers` |
| Exact values or wording to look up | `table` |
| A point no visual makes clearer | `text` |
| A relation no other kind fits | `svg` |

PREFER a kind that shows the relation through position, length, count or shape over one that sets words in rows or boxes. USE a `matrix` only when every row is measured on the same columns. A list of findings, each with its own condition or outcome, is not a grid: USE `pairs` or `effects`. USE `table` and `text` only when the reader needs the exact words or values.

FOLLOW the conventions of the reader's field when they differ.

### 3.4. Make the sequence a story the reader can follow

- KEEP one structure across panels: the same kind for the same kind of point, and the same order of items.
- MOVE from general to specific: the whole before its parts, the main result before its conditions.
- WHERE the document has one, USE a concrete case to introduce an abstract point. This is a design choice: plain, abstract diagrams supported transfer better than rich, concrete ones, so KEEP the case itself plain.
- PUT the question before its answer. IN a business document, the complication comes before the proposal.
- STATE limits in the note of the panel whose claim they qualify.

## 4. Design each panel

### 4.1. Make the point clear

WRITE the headline as a full sentence that states what the reader should conclude from this panel. Readers remember the headline, so it MUST match what the visual shows.

MAKE the headline's point the most prominent part of the visual. MARK with `highlight` the one or two items that carry the point, and leave the rest neutral. HIGHLIGHT only items the headline names, so the reader can see why they stand out. IF the headline names none, highlight nothing. IF the point is a small feature of the data, CHANGE the visual so that feature stands out, such as by sorting, filtering or showing the difference itself.

### 4.2. Keep it plain

DO NOT add images, icons or effects that carry no information. SHOW each panel whole, not revealed step by step. TREAT this as a guide, not a rule.

The renderer's style is fixed. IF the user or project has a style guide that conflicts with it, SAY so and ASK whether to keep the renderer's style.

### 4.3. Keep text short and next to the visual

PUT the source, conditions and limits of a panel in its `note`. KEEP each note to a few sentences. LINK each source the note cites to the page in the document's references, as `[Koh (2026)](https://...)`.

SHOW only what the reader needs to understand the point. Details about how the research was done, such as which sources were read in full, go in the note, not in the visual. FOR judged positions, such as in a `quadrant`, STATE in `basis` where they come from.

### 4.4. Check the wording

CHECK the wording of the title, the summary, every headline, label and note. FOLLOW `/write-better` for this if available, THEN CONTINUE with section 5. With or without it, KEEP words the reader already knows: EXPLAIN or REPLACE research terms, such as "voice" or "ingratiation", and metaphors, such as "lever". USE one term for one idea across panels. KEEP labels, relations and section descriptions to a few words, and PUT conditions in the note. A headline names what the reader should conclude, so DO NOT leave it vaguer than its visual, such as "depends on several factors".

### 4.5. Custom diagrams

USE the `svg` kind only when no other kind fits. GIVE each line style one meaning and state it. KEEP one direction of flow, under about 15 nodes, short labels, and the colours in [templates/spec.md](templates/spec.md). DO NOT use colour as the only signal. WRITE an `alt` text that describes the essential information. In text output, an `svg` panel shows only its `alt`.

## 5. Build and check

1. **Extract.** WRITE the extract in section 2.
2. **Write the spec.** WRITE a JSON spec in the format in [templates/spec.md](templates/spec.md), with a top-level `document` for the map. SAVE it as `.show/<slug>/spec.json` in the working directory. DO NOT commit it unless the user asks.
3. **Check the spec.** RUN `python3 scripts/show.py check <spec>` from this skill's directory. FIX every error. TREAT each warning as a reason to split or simplify the panel, unless you can say why it does not apply.
4. **Compare the digest with the document.** The check prints every headline, value, label, relation and note. CHECK each against the extract and the document. CHECK that each headline matches its visual. CHECK that nothing the GOAL needs is missing.
5. **Render.** FOR a page: `python3 scripts/show.py render <spec> --out .show/<slug>/index.html --open`. FOR a terminal: `python3 scripts/show.py render <spec> --format text`, or `--format md` for Markdown.
6. **Look at the result.** IF you can view the page or a screenshot, CHECK each panel: the headline matches the most prominent feature, labels do not overlap or get cut off, and highlights are visible. FOR text output, READ it as printed.

REPORT only the checks you performed. IF you could not look at the result, SAY so.

## 6. Without the renderer

PRESENT the same plan in Markdown:

- START with the question and the answer, as the cover.
- LIST the document's parts as a numbered list, as the map.
- GIVE each panel as a bold sentence headline, then its content, then its note and where to read it in the document.
- USE Markdown tables for comparisons and lists for structure. USE a plain-text diagram only for a flow of at most four short steps, and CHECK its alignment character by character.

APPLY section 5's extract and digest checks by hand: CHECK each value against the document before showing it.

## 7. Hand it over

GIVE the user the page's link or path once, or the text output. STATE the document's answer in one or two sentences in the chat, so a reader who does not open the page still has it. STATE any assumption you made about the GOAL or the reader next to the result it affects. DO NOT repeat the whole presentation in the chat.
