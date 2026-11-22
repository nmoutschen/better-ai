# Live dashboard design example

From the repository root, copy the example to a folder outside `skills/` and open the address printed by the server. Keep the copy inside the repository so its file sources resolve.

```sh
mkdir -p .design
cp -R skills/architect-better/scripts/example .design/architect-dashboard
python3 skills/architect-better/scripts/architect.py serve .design/architect-dashboard --no-browser
```

## Change folder

A new folder can start with `architect.json` and `design.json`. Write one JSON object per line in each `.jsonl` file. Missing record files are read as empty. Every record has `type`, `at` (UTC, with Z, the time it was first written) and `by`, then its own fields; the schemas in `schemas/` list them, and no other field is allowed. After every write, run `python3 scripts/schema.py check <file>`, and `python3 scripts/architect.py check <folder>` for the whole folder: each prints one line per error, `<file>:<line>: <field>: <reason>`, and exits 1 if there is one. The page lists the same errors in a band above the work and keeps showing every other record.

- `architect.json` holds `request` (the user's words in `text`, and where they come from in `from`: `{"type": "chat"}`, `{"type": "issue", "url": ...}` or `{"type": "file", "path": ...}`), `title`, `summary`, `scope` and `accepted` (the section keys the user accepted: `requirements`, `containers`, `flows`, `perspectives`, `decisions` and `spec`).
- `design.json` holds the diagrams in `containers` and `flows`, and nothing else. Every flow has an `id`.
- `requirements.jsonl` has `id` (such as `F1`), `kind` (`functional`, `quality` or `constraint`), `text` and `source`. The source is one of `{"type":"request","sentence":"<exact sentence of the request>"}`, `{"type":"file","file":"<repo-relative path>","symbol":"<symbol>"}`, `{"type":"guessed"}` or `{"type":"user","at":"<time>"}`.
- `perspectives.jsonl` has `id` (such as `security`), `name`, `applies` (boolean), `why` and `from`: `{"type":"built_in"}` (with `method`, such as `STRIDE`, if it has one) or `{"type":"standard","file":"<repo-relative path>"}`.
- `findings.jsonl` has `id` (`V<n>`), `perspective` (a perspective `id`), `parts` (a list of part keys), `text`, `confirmed` (boolean) and `status`: `open`, or `handled` with `handled_by` (what addresses it). A finding with `confirmed: false` displays an Unconfirmed chip.
- `reviews.jsonl` has one record per run with `perspectives` (the ids reviewed), `changed` (part keys added, edited or removed since the preceding run), `hashes` (part keys mapped to SHA-256 digests) and `labels` (part keys mapped to their labels at review time). The first run records every part in `changed`.
- `decisions.jsonl` has `id` (`D<n>`), `title`, `drivers` (requirement ids), `chosen`, `rejected` (a list of objects with `option` and `why`) and `drawback`.
- `spec.jsonl` is the spec format of code-better too: `spec` records with `id` (`S<n>`), `statement` (an EARS statement), `source` (`{"type":"design","section":...}`, `{"type":"request","sentence":...}`, `{"type":"decision","decision":"D2"}` or `{"type":"requirement","requirement":"F1"}`) and `checked_by`; `gap` and `unlinked` records. `python3 scripts/architect.py specs <folder> --out <spec location>/specs.md` writes a `specs.md` from it, marked as generated, for a repo with no spec format or tool.
- `conversation.jsonl` is the shared conversation log, written by the page and its commands. Every event has `type`, `at` and `by`. Comments have `id`, `text`, an optional pin number `n` and `on` (target element `id`, `title` and, when available, a part `key` and CSS `selector`). Notes have `id`, `text` and `to`. Replies have `id`, `text` and `to`. Status events have `to` and `status`, accept events have `to`, and delete events have `to`, the comment they take back. Approval events have `id`, `again`, `perspectives` (ids), `changes` and `text`. Confirmations have `id`, `requirement`, `wording` (a fingerprint of the confirmed text) and `text`.
- `.server` holds the live address while the server runs. `.conversation-seen` tracks how far the agent has read. Both are generated.

### Diagrams and part keys

`containers` contains three lists.

| List | Fields |
| --- | --- |
| `nodes` | `id`, `label`, `kind` (from the diagram kind register), optional `detail` and `in` |
| `edges` | `id`, `from` and `to` (node IDs), optional `label` and `in` |
| `groups` | `id`, `label`, `members` (node IDs), optional `in` |

Each entry in `flows` has `id`, `name`, optional `in`, and two lists.

| List | Fields |
| --- | --- |
| `participants` | `id`, `box` (the container node ID) |
| `steps` | `id`, `from` and `to` (participant IDs), optional `label`, `kind` (`request`, `response` or `async`, defaults to `request`) and `in` |

Omit `in` for a part in both versions. Use `["before"]` for a removed part and `["after"]` for a new part.

Refer to a node with `box:<id>`, a container edge with `edge:<id>`, or a flow step with `step:<flow id>/<step id>`. A key that names no part of `design.json`, and none a review once recorded, is an error. Join the two views of an exchange with `+`, for example `edge:e3+step:ask/s6`.

## What checks what

- `python3 scripts/schema.py check <file or folder>` checks every record against its schema: shapes, allowed values, the fields a status requires, pointers by id between the files, part keys, the references inside `design.json`, box kinds and the files `file` sources name. For a folder it also reports a file the others need and that is missing: `architect.json` and `design.json` are required by every file of the change folder except `spec.jsonl`.
- `python3 scripts/architect.py check <folder>` runs the same checks, then reads the folder as the page does, so it prints the same errors the page shows in its band.
- `python3 scripts/diagram.py check <design.json>` checks the shape of one design with the schema and what stops it from being drawn; `render` draws it. Any other failure of either is one line on stderr and exit 1.
- `spec.schema.json` is shared with code-better, so it cannot require architect files: a folder that holds only `spec.jsonl` passes `schema.py check` and fails `architect.py check`, which wants `architect.json` and `design.json`.

## Review handoff

**Approve…** sends an `approve` event with the applicable perspectives. Read the event with `wait`, use `status` to mark progress and use `reply --to` to report back in the thread.

When the review finishes, save the findings and use the CLI to record the diagram fingerprints. Pass the ids of the perspectives that ran.

```sh
python3 skills/architect-better/scripts/architect.py review .design/architect-dashboard --perspectives security observability
python3 skills/architect-better/scripts/architect.py check .design/architect-dashboard
```

The first run enables the Findings control. **Review again…** lists changes since the last run, including removals and any older changes that still require a review. An applicable perspective runs if it has never been reviewed or if, since its last review, a part changed that either has a finding from that perspective or has no findings. The request sends the listed part keys and perspective ids. Set `status` to `handled`, with `handled_by`, as findings are addressed.
