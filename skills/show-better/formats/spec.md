# Slides spec

The spec is one record, type `slides`. MAKE the unit with `create`, which takes the spec on stdin, and CHANGE it with `set`; the commands below are the ones you use on it.

```
python3 <skill dir>/scripts/better.pyz create .show/SLUG --by AGENT
python3 <skill dir>/scripts/better.pyz set .show/SLUG slides
python3 <skill dir>/scripts/better.pyz check .show/SLUG
python3 <skill dir>/scripts/better.pyz render .show/SLUG
python3 <skill dir>/scripts/better.pyz render .show/SLUG --format text
python3 <skill dir>/scripts/better.pyz render .show/SLUG --format md
python3 <skill dir>/scripts/better.pyz serve .show/SLUG --open
python3 <skill dir>/scripts/better.pyz wait .show/SLUG --timeout S
python3 <skill dir>/scripts/better.pyz reply .show/SLUG --to ID --read N
python3 <skill dir>/scripts/better.pyz status .show/SLUG seen|asked|working|done ID... --read N
python3 <skill dir>/scripts/better.pyz status .show/SLUG accepted ID... --text
python3 <skill dir>/scripts/better.pyz pending .show/SLUG
```

`create` and `set` take the spec on stdin, `reply` and `status --text` the words on stdin. `--read N` is the line of the last event you read: the `_i` of the last line `wait` or `serve` printed, or the number on the last line of `pending`. `check` names each wrong field as `panels[2].items[0].value: required`.

Text output takes `--width N` (default 72) and `--ascii` (ASCII characters only). `--format text --screen-reader` prints each slide as sentences and value lists, without box lines, bars, rules or symbols. In text output, an `svg` visual shows only its `alt`.

The page shows the opening slide, then one slide per panel. Slide N is panel N − 1.

## Top level

```json
{
  "type": "slides",
  "title": "<the answer to the reader's question, as a sentence>",
  "question": "<the reader's question, shown above the title>",
  "summary": "<one or two sentences that give the answer>",
  "source": "<where the content comes from; may contain [<text>](<https URL>) links>",
  "document": {"title": "<the document this introduces>", "address": "<its https URL>"},
  "lang": "<language code>",
  "style": {"background": "<colour>", "point": "<colour>", "serif": "<font stack>"},
  "panels": [ ... ]
}
```

A field that is optional may be `null`, which means the same as leaving it out. `type` is always `"slides"`.

`style` is optional: the project's look for the slides and their drawings. Its keys are `background`, `tint` (fills, detail boxes), `ink` (lines, text), `heading`, `muted`, `line` (rules), `point` (the highlight), `serif` (headlines) and `sans` (labels). Colours are CSS colours, such as `#1C1A17` or `rgb(28, 26, 23)`; fonts are font stacks, such as `"'Inter', sans-serif"`. The page around the slides keeps its own look.

`document.address` is optional. When it is set, the opening slide links to the document, and each slide's source links to the section it names. `document.sections`, a list of `{"id", "label", "gist"}`, is needed only by the `map` kind.

## Every panel

| Field | Required | Meaning |
|---|---|---|
| `template` | no | `visual` (default), `compare`, `statement` or `title` |
| `part` | no | The story part: a short question of two to five words, under 28 characters. Consecutive panels with the same part are grouped in the strip |
| `headline` | yes | A full sentence that answers the part's question. On a `title` panel, the title |
| `source` | yes | What the slide's claim rests on: `"<text>"`, or `{"text": "<text>", "section": "<section heading in the document>"}`. With `document.address`, the section becomes a link |
| `overview` | no | `true` on at most one `visual` panel of kind `flow`, `timeline`, `concept` or `groups` |
| `focus` | no | On a panel after the overview: the overview labels this slide covers, `["<label>"]`. The slide shows a small copy of the overview with them marked |

`note` and `read` are not used: put both in `source`.

### `visual`: one visual

```json
{"template": "visual", "part": "<part>", "headline": "<headline>", "kind": "<kind>", ...the kind's fields, "source": "<source>"}
```

### `compare`: two visuals in one frame

```json
{"template": "compare", "part": "<part>", "headline": "<headline>",
 "a": {"label": "<what side A shows>", "kind": "<kind>", ...the kind's fields},
 "b": {"label": "<what side B shows>", "kind": "<kind>", ...the kind's fields},
 "source": "<source>"}
```

Both sides of the same `bars`, `dots`, `slope`, `line` or `scatter` kind are drawn on one scale, at one height, with one key. Each side must be something the document reports.

### `statement`: one figure and its comparison

```json
{"template": "statement", "part": "<part>", "headline": "<headline>",
 "figure": "<short figure>", "sentence": "<one sentence on what it counts>", "compare": "<what it is compared to>",
 "source": "<source>"}
```

`check` warns when `compare` is missing.

### `title`: kicker, title, body and actions

A layout for the closing slide. The opening slide uses the same layout, drawn from the top-level `question`, `title`, `summary` and `source`.

```json
{"template": "title", "part": "<kicker>", "headline": "<the answer, restated>", "body": "<a short paragraph>",
 "actions": [{"text": "<what to do>", "panel": <number of the panel it points to>}],
 "source": "<source>"}
```

`part` is the kicker; without it, the kicker is the top-level `question`. Each action links to its panel's slide.

## Details

Any item that has a `label` may carry a detail. Clicking its label or mark opens the detail under the visual.

```json
{"label": "<item>", ..., "detail": {"text": "<what it is>", "source": "<where it comes from; may contain a link>", "evidence": "<strong|moderate|weak|stated>"}}
```

On kinds that draw one mark per item (`dots`, `effects`, `fork`, `lanes`), `evidence` sets the mark's fill: strong is filled ink, moderate half filled, weak hollow. When any item on the slide has evidence, the slide gets a key, and an item without it, or with `stated`, is drawn as a small dot, "no evidence given"; the point of the slide is ringed in terracotta. Every mark on the slide is in the key.

## Kinds

### `map`: the document's parts in order

```json
{"kind": "map", "highlight": ["<section-id>"]}
```

Draws `document.sections`, or its own `sections` list. `highlight` marks the parts to read first.

### `concept`: how ideas relate

```json
{"kind": "concept",
 "nodes": [{"id": "<node-a>", "label": "<idea>", "highlight": true}, {"id": "<node-b>", "label": "<idea>"}],
 "edges": [{"from": "<node-a>", "to": "<node-b>", "label": "<how they relate>"}]}
```

Every edge needs a `label` that says how the two relate, in a few words. Up to about 12 nodes.

### `flow`: a process or sequence

```json
{"kind": "flow", "arrow": "<what every arrow means>",
 "steps": [{"label": "<step>", "note": "<optional detail>"}, {"label": "<step>", "highlight": true}]}
```

Up to 7 steps.

### `lanes`: who does each step

```json
{"kind": "lanes", "actors": ["<actor>", "<actor>"],
 "steps": [{"label": "<step>", "actor": "<actor>"}, {"label": "<step>", "actor": "<actor>", "highlight": true}]}
```

Actors are rows; steps follow one shared order along them. A step in another actor's lane than the one before is a hand-off, drawn as an arrow between lanes. Up to 5 actors and 10 steps.

### `fork`: one input, two to four outcomes

```json
{"kind": "fork", "input": "<what comes in>", "decider": "<what decides the branch>",
 "branches": [{"label": "<branch>", "outcome": "<helps|hurts|never|neutral>", "note": "<optional detail>", "highlight": true}]}
```

Each outcome is shown by a glyph and a word: ▲ helps, ▼ hurts, ✕ never, = neutral.

### `groups`: categories and what belongs to each

```json
{"kind": "groups", "groups": [{"label": "<category>", "items": ["<item>", "<item>"], "highlight": true}]}
```

Up to 4 groups, about 15 items in total.

### `tree`: a whole broken into parts

```json
{"kind": "tree", "unit": "<unit>",
 "root": {"label": "<whole>", "children": [{"label": "<part>", "value": <number>}, {"label": "<part>", "value": <number>, "highlight": true}]}}
```

A node without `value` takes the sum of its children. Up to 4 levels.

### `sets`: overlapping categories

```json
{"kind": "sets", "sets": ["<set>", "<set>"],
 "regions": [{"label": "<item>", "in": ["<set>", "<set>"], "count": <number>, "highlight": true}]}
```

A set with no region is shown as "none found".

### `matrix`: which items have which property

```json
{"kind": "matrix", "columns": ["<property>", "<property>"],
 "rows": [{"label": "<item>", "group": "<group>", "cells": [null, "up"]}],
 "legend": {"same": "<word for this mark>"}, "blank": "<what a blank cell means>"}
```

Each cell is `yes`, `no`, `up`, `down`, `same`, or `null`. Up to 10 rows and 5 columns.

### `pairs`: items that help in one form and not in another

```json
{"kind": "pairs", "columns": ["<first form>", "<second form>"],
 "rows": [{"label": "<item>", "left": [{"label": "<form>", "effect": "up"}], "right": [{"label": "<form>", "effect": "down"}]}]}
```

Up to 7 rows.

### `effects`: findings that raise or lower different outcomes

```json
{"kind": "effects", "rows": [{"group": "<group>", "label": "<finding>", "outcome": "<what it measured>", "effect": "<up|down|same>"}]}
```

Up to 12 rows.

### `quadrant`: options on two judged dimensions

```json
{"kind": "quadrant", "basis": "<where the positions come from>",
 "x": {"label": "<dimension>", "low": "<low end>", "high": "<high end>"}, "y": {"label": "<dimension>", "low": "<low end>", "high": "<high end>"},
 "quadrants": {"bottom_left": "<name>", "top_right": "<name>"},
 "items": [{"label": "<option>", "x": <0 to 1>, "y": <0 to 1>}]}
```

### `numbers`: one to three figures

```json
{"kind": "numbers", "figures": [{"value": "<formatted value>", "label": "<what it counts>"}]}
```

### `units`: a count out of a total

```json
{"kind": "units", "unit": "<what one square counts>", "parts": [{"label": "<part>", "count": <number>, "highlight": true}]}
```

Up to 3 parts and 100 units.

### `bars`: values compared across items

```json
{"kind": "bars", "unit": "<unit>", "sort": "desc", "items": [{"label": "<item>", "value": <number>}]}
```

Bars start at zero. `max` sets the scale's end.

### `slope`: change between two states

```json
{"kind": "slope", "from": "<first state>", "to": "<second state>", "unit": "<unit>",
 "items": [{"label": "<item>", "before": <number>, "after": <number>}]}
```

The scale starts at zero unless `"y_from_zero": false`, which requires a `y_note`.

### `dots`: the spread of values

```json
{"kind": "dots", "unit": "<unit>", "groups": [{"label": "<group>", "values": [<number>, <number>]}]}
```

### `scatter`: two measures across many items

```json
{"kind": "scatter", "x_label": "<measure (unit)>", "y_label": "<measure (unit)>",
 "points": [{"x": <number>, "y": <number>, "label": "<item>"}, {"x": <number>, "y": <number>}]}
```

### `line`: a trend over an ordered axis

```json
{"kind": "line", "unit": "<unit>", "x_label": "<axis label>",
 "series": [{"name": "<series>", "points": [["<x>", <number>], ["<x>", <number>]]}],
 "annotations": [{"series": "<series>", "x": "<x>", "text": "<what happened here>"}]}
```

### `timeline`: events in time

```json
{"kind": "timeline", "events": [{"date": "<date>", "label": "<event>"}]}
```

Events are evenly spaced. Up to 8 events.

### `table`: exact values

```json
{"kind": "table", "columns": [{"label": "<column>"}, {"label": "<column>", "unit": "<unit>"}],
 "rows": [["<item>", <number>]], "highlight_rows": [<row number>]}
```

### `text`: a point no visual makes clearer

```json
{"kind": "text", "body": ["<short paragraph>"]}
```

### `svg`: a relation no other kind fits

```json
{"kind": "svg", "alt": "<what the diagram shows, in words>", "svg": "<svg viewBox=\"0 0 800 <height>\">...</svg>"}
```

The SVG must have a `viewBox` and contain only static drawing elements: `g`, `defs`, `desc`, `symbol`, `use`, `path`, `rect`, `circle`, `ellipse`, `line`, `polyline`, `polygon`, `text`, `tspan`, `textPath`, `marker`, gradients, `stop`, `clipPath`, `mask` and `pattern`. Links and `url()` may only point to an `id` in the same SVG. No `title`, `style` element, comments, scripts, event handlers, images or animation. Use only the colours of the shared vocabulary, each for its one meaning. The page draws them with the slide's `style`, so a project's style restyles the diagram too:

| Colour | Hex | Means |
|---|---|---|
| Terracotta | `#E8725C` | The point of the slide: the highlighted item or path. Not for text |
| Ink | `#33302B` | Normal lines and text; strong evidence |
| Sand | `#C4B69C` | Dashed: indirect, or the deck's reading. Solid: secondary lines |
| Moss | `#6B7F5E` | Holds, helps |
| Umber | `#5C4033` | People and external actors |
| Linen | `#F2EDE5` | Neutral node fill, with ink text |
| Muted | `#78736B` | Ordinary marks and bars; annotations, on cream only |

A failure or a harm shows by glyph and word, such as ▼ or ✕, not by a colour.

Use `font-family="Space Grotesk, sans-serif"` and font sizes of 13 to 16 in an 800-wide `viewBox`.
