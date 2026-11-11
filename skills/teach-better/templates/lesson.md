# Lesson folder

`scripts/lesson.py` shows a lesson folder as a local page and writes the learner's answers back to it. It also builds a static reference page from a folder, for readers who come back to it.

```
python3 scripts/lesson.py check LESSON               # validate lesson.json, print every text and value the page shows
python3 scripts/lesson.py serve LESSON [--port N]    # serve the page; exits once lesson.json has "status": "ended"
python3 scripts/lesson.py wait LESSON [--timeout S]  # block until an answer has no feedback, print it, exit 0 (2 on timeout)
python3 scripts/lesson.py build LESSON [--out DIR]   # write DIR/index.html (default LESSON/site): a static reference, no server
```

```
.teach/<slug>/
  lesson.json            written by the agent: goal, chunks, cards, progress
  answers/<id>.<n>.json  written by the page: attempt n at practice card <id>
  feedback/<id>.<n>.json written by the agent: the reply to that attempt, same file name
```

The page re-reads the folder every two seconds. Edit `lesson.json` to add cards or move the learner on; the page updates by itself.

## lesson.json

```json
{
  "title": "<topic>",
  "goal": "<what the learner can do without AI after the lesson, as a task>",
  "status": "active",
  "chunks": [
    {"id": "<chunk-id>", "title": "<one idea or step>", "status": "planned | current | done | skipped", "quiz": false,
     "cards": [ ... ]}
  ]
}
```

- One chunk at most is `current`. The page opens on it.
- List every planned chunk from the start, with `"cards": []`, so the learner sees the plan. Add cards when you teach it.
- A chunk with `"quiz": true` holds only `practice` cards. While it is `current`, the page hides every other chunk. Set it to `done` to show them again. `wait` reports quiz answers only once every question in the quiz has an answer. Each quiz question takes one answer: its form does not reopen after feedback.
- Set the top-level `status` to `ended` when the lesson ends; `serve` then exits.

## Cards

Each card is one screen. The learner moves through them with Back and Next.

USE a `terms` card only where section 2.2 of SKILL.md allows it: the named parts of a system, or terms the user must use with other people. OTHERWISE, GIVE a term in the `text` or `example` card that first needs it.

| `kind` | Shows | Fields |
|---|---|---|
| `terms` | Key terms and what each refers to | `title`, `terms`: `[{"term": "<term>", "means": "<what it refers to>"}]`, optional `blocks` |
| `text` | An explanation | `title`, `blocks` |
| `example` | A worked example, each step with its reason | `title`, `blocks` |
| `practice` | A problem and the answer form | `id`, `title`, `blocks` |

A practice card's answer form has one required box for the answer and how the learner got it, then an optional confidence rating (low, medium or high). IF the question asks several things, GIVE one field per thing with `fields`. Every field is required.

| `type` | Shows | Fields |
|---|---|---|
| `text` (default) | A multi-line box | `id`, `label`, optional `prefill`. A box left as its prefill counts as empty |
| `short` | A one-line box, for a number, a word or an option number | `id`, `label`, optional `prefill` |
| `choice` | One option to pick, or several with `"multiple": true` | `id`, `label`, `options`: 2 to 8 strings, optional `multiple` |
| `rank` | The options in a list the learner reorders, best first | `id`, `label`, `options`: 3 to 8 strings |

`options` show in the order you list them, and a `rank` field starts in that order. LIST them in an order that does not hint at the answer.

ASK for the reasoning in a `text` field next to a `choice` or `rank` field: a choice alone does not show how the learner got it.

## Static fields

A static page is a reference: one chunk per page, no quiz chunks and no `practice` cards. An `example` card becomes an example to try when it has a `solution`: the page shows the problem, then the hints and the solution on a click. `build` refuses quiz chunks and practice cards.

| Field | Shows | Format |
|---|---|---|
| `hints` | Up to 3 hints, each behind its own click, in order | list of strings, with the same inline marks as `p` |
| `solution` | The worked solution, behind a click | list of blocks |
| `wrong` | Common wrong answers, under the solution | `[{"answer": "<wrong answer>", "why": "<the idea it misapplies>"}]` |

Add a top-level `"audience"`: who the page is for and what they must know before it. The page shows it under the goal. On a static page every chunk is open and `status` is ignored.

## Blocks

| `type` | Fields |
|---|---|
| `p` | `text`. Inline `` `code` ``, `**bold**`, and links to a card as `[<text>](#<chunk-id>/<card number>)`, and links to a source as `[<text>](https://<url>)` only |
| `list` | `items`: list of strings, optional `numbered`: true. NUMBER the questions on a practice card, so feedback can refer to them |
| `code` | `text`. Use it for formulas, one operation per line |
| `table` | `columns`, `rows` (lists of cells), optional `highlight`: row indexes |
| `steps` | `items`: `[{"label": "<step>", "note": "<optional detail>"}]`, at most 7 |
| `timeline` | `start`, `end`, optional `unit`, `ticks`, `bands`, `events`, `legend` (below) |

Every block takes an optional `caption`.

A `timeline` draws events on a number line, with optional shaded spans:

```json
{"type": "timeline", "start": 0, "end": 0, "unit": "<unit>",
 "bands": [{"from": 0, "to": 0, "label": "<span name>", "highlight": false}],
 "events": [{"at": 0, "mark": "allow | reject | neutral", "label": "<optional>"}],
 "legend": {"allow": "<word>", "reject": "<word>", "neutral": "<word>"}}
```

Each mark has its own symbol and colour: ● `allow`, ✕ `reject`, ○ `neutral`. `legend` names what each mark means in this lesson.

## answers/<id>.<n>.json

Written by the page. Read it; do not edit it.

```json
{"id": "<card id>", "attempt": 0, "quiz": false, "answer": "<every field as readable text>", "fields": [{"id": "<field id>", "label": "<label>", "type": "<field type>", "value": "<text>"}], "confidence": "low | medium | high | null", "at": "<time>"}
```

A `choice` field also has `"selected"`: the chosen options. A `rank` field also has `"order"`: every option, best first.

## feedback/<id>.<n>.json

```json
{"verdict": "right | partly | wrong | hint | noted", "text": "<reply>", "blocks": []}
```

`blocks` is optional and takes the block types above. `text` takes the same inline marks as `p`, including links to a card. After a `right` verdict the form closes. `noted` also closes it, without judging the answer. After any other verdict the learner can try again, and each box starts with their previous answer.
