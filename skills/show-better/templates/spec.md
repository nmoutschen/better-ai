# Presentation spec

`scripts/show.py` renders a spec, a JSON file, as one HTML page or as plain text.

```
python3 scripts/show.py check SPEC                       # validate, print every value the page will show
python3 scripts/show.py render SPEC --out FILE [--open]  # check, then write the HTML page
python3 scripts/show.py render SPEC --format text        # print it as plain text for a terminal
python3 scripts/show.py render SPEC --format md          # print it as Markdown, diagrams in code blocks
python3 scripts/show.py example                          # print an example spec
```

Text output takes `--width N` (default 72) and `--ascii` (ASCII characters only). In text output, an `svg` panel shows only its `alt`.

`check` stops with an error when a panel cannot be drawn correctly, and prints a warning when a panel is likely hard to read. Both commands print a digest: every headline, value, label and note, in order, for comparison with the source.

## Top level

```json
{
  "title": "The overall conclusion, as a sentence or a short phrase",
  "summary": "One or two sentences that give the answer. A reader who stops here knows the result.",
  "kicker": "Optional small label above the title, such as the date or the topic",
  "source": "Optional line naming where the content comes from",
  "lang": "en",
  "document": {"title": "The document this introduces", "sections": [{"id": "§1", "label": "Goals", "gist": "Optional one line"}]},
  "panels": [ ... ]
}
```

`document` is optional: the parts of the document the presentation introduces, drawn by the `map` kind and marked by each panel's `part`.

## Every panel

| Field | Required | Meaning |
|---|---|---|
| `kind` | yes | One of the kinds below |
| `headline` | yes | A full sentence that states what the reader should conclude from this panel |
| `note` | no | Short text shown beside the visual: the source, a condition, a limit. A string or a list of paragraphs |
| `part` | no | The `document` section id, or list of ids, that this panel introduces |
| `read` | no | Where to read the detail in the document, such as "§3.2, the table of forms" |

Highlight only the one or two items that carry the headline's point.

## Kinds

### `map`: the document's parts in order

```json
{"kind": "map", "headline": "...", "highlight": ["§1", "§6"]}
```

Draws the top-level `document.sections`, or its own `sections` list. `highlight` marks the parts to read first.

### `concept`: how ideas relate

```json
{"kind": "concept", "headline": "...",
 "nodes": [{"id": "slow", "label": "Slow page loads", "highlight": true}, {"id": "tickets", "label": "Support tickets"}],
 "edges": [{"from": "slow", "to": "tickets", "label": "leads to"}]}
```

Every edge needs a `label` that says how the two relate. Up to about 12 nodes.

### `tree`: a whole broken into parts

```json
{"kind": "tree", "headline": "...", "unit": "days",
 "root": {"label": "Migration", "children": [{"label": "Content", "children": [{"label": "Reference", "value": 18}]}, {"label": "Launch", "value": 4, "highlight": true}]}}
```

A node without `value` takes the sum of its children. Children that sum to more than their parent's value are an error. Up to 4 levels.

### `sets`: overlapping categories

```json
{"kind": "sets", "headline": "...", "sets": ["Fast", "Offline", "No server"],
 "regions": [{"label": "Static pages", "in": ["Fast", "Offline", "No server"], "count": 1, "highlight": true}]}
```

Each region lists the sets it belongs to in `in`. A set with no region is shown as "none found", so it can show a gap.

### `quadrant`: options on two judged dimensions

```json
{"kind": "quadrant", "headline": "...", "basis": "The team's estimates, not measurements",
 "x": {"label": "Effort", "low": "small", "high": "large"}, "y": {"label": "Cost", "low": "low", "high": "high"},
 "quadrants": {"bottom_left": "Do now", "top_right": "Avoid"},
 "items": [{"label": "Static pages", "x": 0.3, "y": 0.15, "highlight": true}]}
```

`x` and `y` are between 0 and 1. `basis` is required: it says where the positions come from.

### `slope`: change between two states

```json
{"kind": "slope", "headline": "...", "from": "2024", "to": "2026", "unit": "ms",
 "items": [{"label": "Search", "before": 2300, "after": 850, "highlight": true}]}
```

The scale starts at zero unless `"y_from_zero": false`, which requires a `y_note`.

### `dots`: the spread of values

```json
{"kind": "dots", "headline": "...", "unit": "ms per load",
 "groups": [{"label": "Before", "values": [1200, 1500, 900]}, {"label": "After", "values": [800, 760, 820], "highlight": true}]}
```

The median is marked; `"marker": "none"` hides it.

### `scatter`: two measures across many items

```json
{"kind": "scatter", "headline": "...", "x_label": "Page size (kB)", "y_label": "Load time (ms)",
 "points": [{"x": 40, "y": 2300, "label": "Search", "highlight": true}, {"x": 20, "y": 600}]}
```

Label only the points the headline is about. Axes start at zero unless `"x_from_zero": false` or `"y_from_zero": false`.

### `numbers`: one to three figures

```json
{"kind": "numbers", "headline": "...", "figures": [{"value": "10 of 10", "label": "tests supported segmenting", "highlight": true}]}
```

`value` is shown as written, so format it yourself.

### `units`: a count out of a total

```json
{"kind": "units", "headline": "...", "unit": "questions",
 "parts": [{"label": "significantly better", "count": 7, "highlight": true}, {"label": "no significant difference", "count": 6}, {"label": "significantly worse", "count": 2}]}
```

One square per counted thing. Up to 3 parts and 100 units. `unit` names what one square counts.

### `matrix`: which items have which property

```json
{"kind": "matrix", "headline": "...",
 "columns": ["Trust", "Recall", "Accuracy"],
 "rows": [{"label": "Embellished charts", "group": "Bateman et al. 2010", "cells": [null, "up", {"mark": "same", "highlight": true}]}],
 "legend": {"same": "no difference"}, "blank": "not measured"}
```

Each cell is a mark: `yes` (✓), `no` (✗), `up` (▲, higher), `down` (▼, lower), `same` (=, no difference), or `null` for a blank cell. `legend` replaces the word shown for a mark; `blank` names what a blank cell means. Rows with the same `group` are shown under one label. A row or a cell can be highlighted. Up to 10 rows and 5 columns. Use a `table` instead when the cells must hold words or exact values.

### `bars`: compare values across items

```json
{"kind": "bars", "headline": "...", "unit": "% correct", "sort": "desc",
 "items": [{"label": "Sentence headlines", "value": 79, "highlight": true}, {"label": "Phrase headlines", "value": 69}]}
```

Bars start at zero. Values must be zero or positive. `sort` is `desc`, `asc`, or omitted to keep the given order. `max` sets the scale's end when panels must share a scale.

### `line`: a trend over an ordered axis

```json
{"kind": "line", "headline": "...", "unit": "ms", "x_label": "Release",
 "series": [{"name": "p95 latency", "points": [["v1", 120], ["v2", 95], ["v3", 80]], "highlight": true}],
 "annotations": [{"series": "p95 latency", "x": "v2", "text": "Cache added"}]}
```

`x` values are all numbers (drawn to scale) or all labels (drawn in order). The y axis starts at zero unless `"y_from_zero": false`, which requires a `y_note` that states where it starts and why.

### `table`: exact values, or items compared on several aspects

```json
{"kind": "table", "headline": "...",
 "columns": [{"label": "Option"}, {"label": "Cost", "unit": "€/month"}, {"label": "Setup"}],
 "rows": [["A", 40, "1 day"], ["B", 25, "1 week"]], "highlight_rows": [2]}
```

Give numeric columns a `unit`, or `"align": "right"`. `highlight_rows` counts from 1.

### `flow`: a process or sequence

```json
{"kind": "flow", "headline": "...", "arrow": "then",
 "steps": [{"label": "Extract", "note": "a table of values"}, {"label": "Check", "highlight": true}]}
```

`arrow` states what every arrow means; all arrows have this one meaning. Up to 7 steps.

### `groups`: categories, membership or structure

```json
{"kind": "groups", "headline": "...",
 "groups": [{"label": "Raised", "items": ["Trust", "Recall"], "highlight": true}, {"label": "Unchanged", "items": ["Accuracy"]}]}
```

Up to 4 groups, about 15 items in total.

### `timeline`: events in time

```json
{"kind": "timeline", "headline": "...", "events": [{"date": "2022", "label": "First version"}, {"date": "2026", "label": "Rewrite", "highlight": true}]}
```

Events are evenly spaced, so the spacing does not show the time between them. Up to 8 events.

### `text`: a point that a visual would not help

```json
{"kind": "text", "headline": "...", "body": ["Short paragraph.", "Another short paragraph."]}
```

### `svg`: a relation no other kind fits

```json
{"kind": "svg", "headline": "...", "alt": "What the diagram shows, in words", "svg": "<svg viewBox=\"0 0 800 300\" ...>...</svg>"}
```

The SVG must have a `viewBox`, and must contain no scripts, event handlers, `foreignObject` or external links. `alt` is required. Use only these colours:

| Colour | Hex | Use |
|---|---|---|
| Moss | `#6B7F5E` | Systems, components, ordinary nodes |
| Terracotta | `#E8725C` | The highlighted node or path that carries the point |
| Umber | `#5C4033` | People, teams, external actors |
| Linen | `#F2EDE5` | Neutral node fill, with ink text |
| Ink | `#33302B` | Lines and text |
| Sand | `#C4B69C` | Secondary or dashed lines, group borders |
| Muted | `#78736B` | Annotations |

Use `font-family="Space Grotesk, sans-serif"` and font sizes of 13 to 16 in an 800-wide `viewBox`.
