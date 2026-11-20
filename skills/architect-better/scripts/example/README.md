# Live dashboard design example

Run the server from the repository root and open the printed address to inspect the reviewed design.

```sh
python3 skills/architect-better/scripts/architect.py serve skills/architect-better/scripts/example --no-browser
```

Use a copy inside the repository for experiments so that file sources still resolve and conversation events go to the copy.

## Change folder

Write one JSON object per line in each `.jsonl` file. Use empty files for sections with no records yet. You can omit `reviews.jsonl` before the first run.

- `request.md` holds the user's original request verbatim.
- `design.json` uses the container and flow format of `diagram.py` with `title`, `summary` and `scope` strings and an `accepted` list of section keys (`requirements`, `containers`, `flows`, `perspectives`, `decisions`, `spec`).
- `requirements.jsonl` has `id`, `kind` (`functional`, `quality` or `constraint`), `text` and `source`. Use `{"type":"request","sentence":"<exact sentence>"}`, `{"type":"file","file":"<repo-relative path>","symbol":"<symbol>"}`, `{"type":"guessed"}` or `{"type":"user","at":"<time>"}`.
- `perspectives.jsonl` has `name`, `applies` (a boolean), `why` and `from` (built in or the path to a repo standard).
- `findings.jsonl` has `id`, `perspective` (the perspective name), `parts`, `text` and `handled_by` (a string or null while open). Each entry in `parts` is a string such as `box:server`, `edge:e3` or `step:flow1/s6`. Use a flow's ID if present or its one-based position as `flow<N>`. Join two views of the same exchange with `+`, as in `edge:e3+step:flow1/s6`.
- `reviews.jsonl` has one record per run with `at`, `perspectives` (a list of perspective names) and `changed` (a list of part references, empty for the first run).
- `decisions.jsonl` has `id`, `title`, `drivers` (requirement IDs), `chosen`, `rejected` (a list of objects with `option` and `why`) and `drawback`.
- `spec.jsonl` has `id`, `requirement` (an EARS statement), `source` and `checked_by`.
- `conversation.jsonl` is the shared conversation log. Omit it for a new design.

## Review handoff

Approve and run the review sends an `approve` event with the names of the applicable perspectives. The architect receives it through `wait` and runs the corresponding reviews. Use `status` to mark the work and `reply --to` to report back in the thread.

When the review finishes, write the findings and append a review record. This enables the Findings control and changes Approve… to Review again…. The Review again panel shows the changed parts and perspectives from the latest record. Running the review again sends those values in another `approve` event. Keep open findings visible and update `handled_by` as they are addressed.

Run `architect.py check CHANGE` after changing the folder.
