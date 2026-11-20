# Live dashboard design example

Run `python3 skills/architect-better/scripts/architect.py serve skills/architect-better/scripts/example --no-browser` from the repository root. Open the printed address to inspect the reviewed design. Use a copy inside the repository for experiments, since the server writes conversation events to the served folder.

## Change folder

- `design.json` uses the container and flow format of `diagram.py`. Add `title`, `summary` and `scope` strings and an `accepted` list of section keys (`requirements`, `containers`, `flows`, `perspectives`, `decisions`, `spec`).
- `requirements.json` is a list of records with `id`, `kind`, `text` and `source`. Set the source to `{"guessed": true}` or name a `file` relative to the repository root. File sources may include a `symbol` and a one-based `line`. For `request.md`, include the exact `sentence` from the request. Confirmations and change requests appear in the conversation.
- `request.md` holds the user's original request.
- `perspectives.json` contains `perspectives`, a list of records with `id`, `name`, `applies`, `why`, `source` and `findings`. Each finding has an `id`, `finding` and `response`, optional `category`, and `parts`. Each inner list in `parts` names one logical part and all its diagram references. Use `box:<id>`, `edge:<id>`, or `step:<id>`. If multiple flows reuse a step ID, use `flow<N>:step:<id>` with a one-based flow number.
- `decisions.json` is a list with `id`, `title`, `drivers` (requirement IDs), `chosen`, `alternatives` (records with `option` and `why`), and `drawback`.
- `spec.json` is the structured summary of the code-better spec, with one record per origin and fields `origin`, `count`, `example` and `source`.
- `conversation.jsonl` is the shared conversation log. Omit it for a new design.

## Review handoff

Start with empty findings lists and omit `review` from `perspectives.json`. Approve and run the review sends an `approve` event with the IDs of the applicable perspectives. The architect receives it through `wait` and runs the corresponding reviews. Use `status` to mark the work and `reply --to` to report back in one or two short sentences.

When the review finishes, write the findings and add a `review` object. Its `changes` list describes changes since the completed review and its `rerun` list names the applicable perspective IDs that should review those changes. Review again sends these fields in another `approve` event. Update the review object and findings as the design and reviews progress.

Use `architect.py check CHANGE` to validate the folder. Mark an item working while you are changing it. Once an answer leads to a change, mark the item done and ask the next question as a new message.
