# Live dashboard design example

From the repository root, copy the example to a folder outside `skills/` and open the address printed by the server. Keep the copy inside the repository so its file sources resolve.

```sh
mkdir -p .design
cp -R skills/architect-better/scripts/example .design/architect-dashboard
python3 skills/architect-better/scripts/architect.py serve .design/architect-dashboard --no-browser
```

## Change folder

A new folder can start with `request.md` and `design.json`. Write one JSON object per line in each `.jsonl` file. Missing record files are read as empty.

- `request.md` holds the user's original request verbatim.
- `design.json` holds the diagrams in `containers` and `flows`. Optional page fields are `title` (defaults to the request's first line or the folder name), `summary` and `scope` (both default to empty strings), and `accepted` (defaults to an empty list). Accepted section keys are `requirements`, `containers`, `flows`, `perspectives`, `decisions` and `spec`.
- `requirements.jsonl` has `id`, `kind` (`functional`, `quality` or `constraint`), `text` and `source`. The source is one of `{"type":"request","sentence":"<exact sentence>"}`, `{"type":"file","file":"<repo-relative path>","symbol":"<symbol>"}`, `{"type":"guessed"}` or `{"type":"user","at":"<timestamp>"}`.
- `perspectives.jsonl` has `name`, `applies` (boolean), `why` and `from` (built in or the path to a repository standard).
- `findings.jsonl` has `id`, `perspective` (a perspective name), `parts` (a list of part keys), `text`, `handled_by` (a string or null while open) and `confirmed` (boolean). A finding with `confirmed: false` displays an Unconfirmed chip.
- `reviews.jsonl` has one record per run with `at` (timestamp), `perspectives` (names reviewed), `changed` (current parts new or changed since the preceding run) and `hashes` (part keys mapped to SHA-256 digests of each node, edge or step's own JSON serialized with sorted keys). The first run records every part in `changed`.
- `decisions.jsonl` has `id`, `title`, `drivers` (requirement IDs), `chosen`, `rejected` (a list of objects with `option` and `why`) and `drawback`.
- `spec.jsonl` has `id`, `requirement` (an EARS statement), `source` and `checked_by`.
- `conversation.jsonl` is the shared conversation log, written by the page and its commands. It records `at` and `action` on each event. Comments have `id`, `comment`, an optional pin number `n` and `on` (target element `id`, `title` and, when available, a part `key` and CSS `selector`). Messages have `id` and `note` or `text`. Replies can add `to` (item ID). Status events have `to` and `status`, accept events have `to`, and delete events have the comment `id`. Approval events have `id`, `again`, `perspectives`, `changes` and `text`. Confirmations have `id`, `requirement`, `wording` (a fingerprint of the confirmed text) and `text`. Agent events may carry `by`.
- `.server` holds the live address while the server runs. `.conversation-seen` tracks how far the agent has read. Both are generated.

### Diagrams and part keys

`containers` contains three lists.

| List | Fields |
| --- | --- |
| `nodes` | `id`, `label`, `kind` (from the diagram kind register), optional `detail` and `in` |
| `edges` | `id`, `from` and `to` (node IDs), optional `label` and `in` |
| `groups` | `id`, `label`, `members` (node IDs), optional `in` |

Each entry in `flows` has `name`, optional `id` and `in`, and two lists.

| List | Fields |
| --- | --- |
| `participants` | `id`, `box` (the container node ID) |
| `steps` | `id`, `from` and `to` (participant IDs), optional `label`, `kind` (`request`, `response` or `async`, defaults to `request`) and `in` |

Omit `in` for a part in both versions. Use `["before"]` for a removed part and `["after"]` for a new part.

Refer to a node with `box:<id>`, a container edge with `edge:<id>`, or a flow step with `step:<flow id>/<step id>`. Use either the flow's explicit `id` or its one-based position as `flow<N>`. Review fingerprints use the explicit ID when present. Join the two views of an exchange with `+`, for example `edge:e3+step:flow1/s6`.

## Review handoff

**Approve…** sends an `approve` event with the applicable perspectives. Read the event with `wait`, use `status` to mark progress and use `reply --to` to report back in the thread.

When the review finishes, save the findings and use the CLI to record the diagram fingerprints. Pass the names of the perspectives that ran.

```sh
python3 skills/architect-better/scripts/architect.py review .design/architect-dashboard --perspectives Security Observability
python3 skills/architect-better/scripts/architect.py check .design/architect-dashboard
```

The first run enables the Findings control. **Review again…** shows the current parts whose fingerprints differ from the last run. It sends those part keys and the applicable perspectives that have a finding on a changed part or were absent from the last run. Update `handled_by` as findings are addressed.
