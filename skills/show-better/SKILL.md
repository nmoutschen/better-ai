---
name: show-better
description: Helps an AI agent introduce a dense document, such as a research paper, a strategy or a design doc, with a short sequence of visual slides the reader goes through before reading it. Each slide shows a relation the reader would otherwise have to work out from the prose, in a form chosen from a wide range (concept maps, actor lanes, forks, set diagrams, slope charts, distributions, hierarchies, quadrants and more). The slides are served as a live page where the reader comments and the agent answers, exported as a presentation, or rendered as plain text for a terminal, and every value is checked against the source.
argument-hint: "[DOCUMENT OR CONTENT]"
---

# Show Better

IF invoked without argument, USE these instructions on your previous output.
IF invoked with a document, a path or content as argument, USE these instructions to introduce it.

Being invoked means: find the structure and the relations in the content that a visual shows better than prose, and show them as a short story of slides. It does NOT mean every point becomes a visual. A point that one sentence states well stays a sentence.

## Principles

1. Graphics help comprehension only modestly, and only graphics that organize information help. Pictures that merely illustrate add nothing significant. A visual is better than prose when it lets the reader see a relation that the text would make them work out.
2. Organizers given with a text improved comprehension of that text, and signals of a text's structure helped learning. The slides are an organizer for the document: they introduce the document and do not replace it.
3. Plain diagrams supported transfer to new cases better than rich, detailed ones. Readers who already know a topic need less guidance, and guidance can get in their way.
4. Readers learn more deeply from content in segments they move through at their own pace. Keeping one structure from slide to slide helped memory, and most professional visual stories move from general to specific.
5. Readers recall a slide's message from its headline, and take the most prominent feature of a visual as its point.
6. Generated slides fail mostly through missing content, then wrong values. Language models read text diagrams far more reliably than they draw them, so every diagram is laid out by code.
7. Placing a visual introduction before a full research paper or business document is a design choice, and so are the rules marked as design choices and the six rules in section 3.1.

## 1. Know the goal and the reader

IDENTIFY what the reader must UNDERSTAND, LEARN, DO or DECIDE after reading the document. The slides prepare the reader for that GOAL. IF the context does not show the GOAL, CHOOSE the most plausible one and STATE it (section 7).

IDENTIFY what the reader already knows about the topic. FOR an expert reader, SHOW less: fewer slides and fewer labels.

## 2. Read the document and extract its structure

READ the whole document before planning. WRITE an extract, and WORK from it, not from memory of the document:

1. **The question and the answer.** What question does the reader bring, and what does the document conclude or propose? FOR a business document, WRITE the situation, the complication, the question it raises, and the answer.
2. **The parts.** The document's sections in order, each with its heading and a few words on what it covers.
3. **The relations.** What causes, depends on, contains, overlaps, hands off to or competes with what. These are the candidates for visuals.
4. **The evidence.** Every value and every claim you might show, with the section it comes from and how strong the document says its support is.
5. **The case.** A concrete case the document follows, if it has one.
6. **The terms.** The words the reader must know to read the document.

## 3. Plan the story

### 3.1. Follow the six rules

1. **TELL one story.** The opening slide asks the reader's question (`question`) and answers it (`title`). Each `part` is the next question that follows, in two to five words; each headline answers its part's question, so the headlines read in order make the argument. CARRY the document's case through every slide. WHEN the document has no case, MAKE one early panel the `overview` and SET `focus` on later slides, so each shows where it sits in the whole.
2. **EVERY slide earns its place.** CUT a slide that answers no question in the story, and any element that carries no information.
3. **SHOW ideas, not text.** CHOOSE each visual for the mechanism, the comparison ("compared to what?") or several variables at once, with the evidence on the picture. A reader must see what it means at a glance. DO NOT set a list of sentences in boxes: that is text in a frame, so WRITE it as a sentence or cut it.
4. **USE one vocabulary.** DRAW only with the shared marks, lines and colours (section 4.2), and NEVER give one a new meaning on one slide. WHEN nothing fits, SAY so in your hand-over (section 7) instead of inventing a mark.
5. **PICK the template by what the slide shows** (section 3.2).
6. **CHECK values and shapes.** Every value, alignment, link, hand-off and curve has a place in the document, and each slide's `source` names it.

KEEP the deck to about 5 to 12 panels. This range is a design choice. IF the document needs more, INTRODUCE only the parts the GOAL needs. REFER to parts of the document by their headings, in headlines and sources. DO NOT use section numbers or § signs.

### 3.2. Pick the template

| Template | Use it when the slide shows |
|---|---|
| `title` | A layout of kicker, title, body and actions. USE it for the closing slide: the answer restated and what to do, each action linked to the slide that supports it |
| `visual` | One relation, drawn with one kind (section 3.3). The default |
| `compare` | Two things the document reports side by side, such as documented and observed, on one scale. Not a case the document rules out |
| `statement` | One measured figure with what it is compared to, such as "40%, against 89% before". Not a figure without its comparison |

The opening slide uses the same `title` layout, drawn from the top-level `question` (kicker), `title`, `summary` and `source`; it is not a panel.

### 3.3. Choose the kind by the relation

WRITE each slide's point as a sentence that states a conclusion, not a topic. THEN ASK: does a visual let the reader see something this sentence does not already say? IF not, USE a `statement` for a figure, fold the point into another slide, or cut it.

| What the reader must see | Kind |
|---|---|
| How ideas relate: causes, dependencies, parts of an argument | `concept` |
| A process or a sequence of steps | `flow` |
| Who does each step, and where work passes between actors | `lanes` |
| One input that leads to different outcomes depending on one factor | `fork` |
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
| The parts of a long document the reader must find their way in | `map` |
| One to three numbers the reader must remember | `numbers` |
| Exact values or wording to look up | `table` |
| A point no visual makes clearer | `text` |
| A relation no other kind fits | `svg` |

PREFER a kind that shows the relation through position, length, count or shape over one that sets words in rows or boxes. USE a `matrix` only when every row is measured on the same columns. USE `table` and `text` only when the reader needs the exact words or values. FOLLOW the conventions of the reader's field when they differ.

### 3.4. Order the slides

- MOVE from general to specific: the overview before its parts, the main result before its conditions.
- PUT the question before its answer. IN a business document, the complication comes before the proposal.
- KEEP one structure across slides: the same kind for the same kind of point, and the same order of items.
- STATE limits in the `source` or the `detail` of the claim they qualify. A limit that changes the slide's point goes in the headline or the `source`, not only in the `detail`.

## 4. Design each slide

### 4.1. Make the point clear

WRITE the headline as a full sentence that states what the reader should conclude. The headline MUST match what the visual shows.

MAKE the headline's point the most prominent part of the visual. MARK with `highlight` the one or two items that carry the point, and leave the rest neutral. HIGHLIGHT only items the headline names. IF the point is a small feature of the data, CHANGE the visual so that feature stands out, such as by sorting, filtering or showing the difference itself.

KEEP the first view light: PUT what an item is, its source and the strength of its evidence in the item's `detail`, which the reader opens by clicking it. Most readers never open a `detail`, so WRITE each slide so its point can be read without one, and PUT in `detail` only what a reader may want to check. GIVE `evidence` on items of `dots`, `effects`, `fork` and `lanes`, so their marks show it.

### 4.2. Keep to the vocabulary

The renderer draws the marks; KEEP their meanings in custom `svg` visuals and in your words:

- Terracotta is the point of the slide: the highlighted item or path. Risk and failure show by glyph and word (▼ hurts, ✕ never), not by colour alone.
- Fill shows evidence strength: filled strong, half moderate, hollow weak; a small dot means no evidence given. The renderer adds the key.
- Nodes are small marks with their labels on the drawing, joined by thin lines; only data is filled.
- Solid lines are stated in the document; dashed sand lines are indirect or the deck's own reading.

DO NOT add images, icons or effects that carry no information.

WHEN the user or the project has a style, such as brand colours and fonts, SET the spec's `style` to them: the slides and their drawings take those colours and fonts, and the page around the slides keeps its look. MAP each colour to the role it plays in the vocabulary, such as the brand's accent to `point`. OTHERWISE, LEAVE `style` out: the slides use n14n's Journal style.

### 4.3. Write the source line

GIVE every slide one `source`: what its claim rests on, and the `section` where the reader finds it. SET `document.address` when the document has a URL, so each section becomes a link. LINK each cited work as `[<author> (<year>)](<url>)`. FOR judged positions, such as in a `quadrant`, STATE in `basis` where they come from.

### 4.4. Check the wording

CHECK the wording of the title, the question, the summary, every part, headline, label, detail and source. FOLLOW `/write-better` for this if available, THEN CONTINUE with section 5. With or without it, KEEP words the reader already knows: EXPLAIN or REPLACE research terms and metaphors. USE one term for one idea across slides. KEEP labels and relations to a few words. DO NOT leave a headline vaguer than its visual, such as "depends on several factors".

### 4.5. Custom diagrams

USE the `svg` kind only when no other kind fits. KEEP one direction of flow, under about 15 nodes, short labels, and the colours in [templates/spec.md](templates/spec.md). WRITE an `alt` text that describes the essential information. In text output, an `svg` visual shows only its `alt`.

## 5. Build, check and show

1. **Extract.** WRITE the extract in section 2.
2. **Write the spec.** WRITE a JSON spec in the format in [templates/spec.md](templates/spec.md). SAVE it as `.show/<slug>/spec.json` in the working directory. DO NOT commit it unless the user asks.
3. **Check the spec.** RUN `python3 scripts/show.py check <spec>` from this skill's directory. FIX every error. TREAT each warning as a reason to split or simplify the slide, unless you can say why it does not apply.
4. **Compare the digest with the document.** The check prints every headline, value, label, detail and source. CHECK each against the extract and the document, and CHECK that each headline matches its visual and that nothing the GOAL needs is missing.
5. **Render and show.** CHOOSE the first route the user can read:
   1. IF the user's browser can reach this machine, SERVE the page: RUN `python3 scripts/show.py render <spec> --out .show/<slug>/index.html --serve --open` in the background, GIVE the address it prints, and FOLLOW section 6.
   2. IF the user asks to share the slides, or their browser cannot reach this machine and you can publish a page, RENDER without `--serve` and PUBLISH that file: opened as a file, it shows the slides without the conversation. GIVE the link.
   3. IF the user reads in a terminal, RENDER `--format text`, or `--format md` for Markdown. USE `--ascii` when the output must survive plain-text files. IF the user reads with a screen reader or finds the diagrams hard to follow, RENDER `--format text --screen-reader`.
   4. IF you cannot run Python, WRITE the slides in Markdown: the question and answer first, then each slide as a bold headline, its content as a table or list, and its source. USE a plain-text diagram only for a flow of at most four short steps, and CHECK each value against the document by hand.
6. **Look at the result.** IF you can view the page or a screenshot, CHECK each slide: the headline matches the most prominent feature, labels do not overlap or get cut off, and highlights are visible. FOR text output, READ it as printed. DO NOT describe a page you have not rendered.

The page also offers Export, which downloads the slides alone as a presentation. TELL the user about it WHEN they want to present the slides.

REPORT only the checks you performed. IF you could not look at the result, SAY so.

## 6. Work with the user in the page

On the served page, the user reads the slides, switches to Comment and clicks any part of a slide to comment on it, or writes a message in the column on the right. Each action is printed as one JSON line and appended to `answers.jsonl` next to the page. A comment names the slide, its part and headline, the clicked text, the nearest drawn item and where the click fell: WORK OUT what the user pointed at from all of these.

1. RECEIVE the actions by the first route your harness offers:
   1. IF your harness can stream a background command's output to you as it arrives, STREAM the serve command's output. A stream that expires stops only the watch: START it again.
   2. OTHERWISE, IF you can run a command in the background and be told when it ends, RUN `python3 scripts/show.py wait .show/<slug>` that way. It ends with the actions you have not seen: START it again at once, before you act on them, and KEEP it running while the page is served. WHILE no `wait` runs, the page tells the user that you are not watching.
   3. OTHERWISE, ASK the user to say "sent" in the chat, THEN READ the new lines of `answers.jsonl`.
2. TREAT each action as the user's reply. WHILE the user works in the page, PUT everything for them in the page, and DO NOT answer each page action in the chat.
   - TRACK each comment and message with `python3 scripts/show.py status .show/<slug> seen|asked|working|done|accepted <id>...`: MARK it `seen` when it arrives, `asked` when you asked the user something and wait for the answer, `working` only while you are changing it now, and `done` once the answer or the change is in the page. READ a note the user adds under an item as part of that item's thread, in the order of the `at` times. ONCE an answer leads to a change, MARK the item `done` and ASK the next question as a new message. TREAT an item as finished only when the user accepts it, in the page or in words (then MARK it `accepted`).
   - REPLY in the page with `python3 scripts/show.py reply .show/<slug> "<text>" --to <id>`, in one or two short sentences: what you changed, or the one thing you need.
   - TO change slides, EDIT the spec, CHECK it, and RUN the same `render` command without `--serve` and `--open`: the open page loads the new slides by itself once the user is not typing.
   - RUN `python3 scripts/show.py pending .show/<slug>` after each batch of changes, before you wait again, and after an interruption: FINISH or ANSWER what it lists.
3. STOP the server only when the user says so.

## 7. Hand it over

GIVE the user the page's address, link or path once, or the text output. STATE the document's answer in one or two sentences in the chat, so a reader who does not open the page still has it. STATE any assumption you made about the GOAL or the reader, and any gap in the vocabulary (section 3.1, rule 4), next to the result it affects. DO NOT repeat the slides in the chat.
