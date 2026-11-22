# The files of a change folder

<HOW TO FILL THIS IN — you write the records of the change folder with the commands of SKILL.md, each line below as the JSON on the command's standard input, and you leave out `at`, `by` and `id`. Delete this block when done.
- Conventions: WRITE a missing value as `null`, a list as a JSON array, and a value that has a fixed set as one of its exact lowercase words. A field the record does not name is an error. WRITE the record a pointer names before the pointer: a perspective before its findings, a requirement before the decision it drives. An optional field may be `null`, which means it is absent; a field a status drives, such as `handled_by`, exists only in that status.
- `kind` of a requirement is `functional`, `quality` or `constraint`. Write one line per requirement, with the source it comes from.
- A perspective is named with `--id <perspective id>` on the command.>

`architect.json`, one record: the request word for word, and where it comes from.

{"type": "architect", "request": {"text": "<the request, verbatim>", "from": {"type": "chat"}}, "title": "<title>", "summary": "<summary, or an empty string>", "scope": "<scope, or an empty string>", "accepted": []}
{"type": "architect", "request": {"text": "<the request, verbatim>", "from": {"type": "issue", "url": "<issue url>"}}, "title": "<title>", "summary": "<summary>", "scope": "<scope>", "accepted": ["requirements"]}
{"type": "architect", "request": {"text": "<the request, verbatim>", "from": {"type": "file", "path": "<path of the file>"}}, "title": "<title>", "summary": "<summary>", "scope": "<scope>", "accepted": []}

`design.json`, one record: the containers and the flows, each flow with an `id`.

{"type": "design", "containers": {"nodes": [{"id": "<box id>", "label": "<label>", "kind": "<kind from the register>", "detail": "<detail, or leave out>", "in": ["<before | after>"]}], "edges": [{"id": "<edge id>", "from": "<box id>", "to": "<box id>", "label": "<what travels>", "in": ["<before | after>"]}], "groups": [{"id": "<group id>", "label": "<label>", "members": ["<box id>"], "in": ["<before | after>"]}]}, "flows": [{"id": "<flow id>", "name": "<name>", "in": ["<before | after>"], "participants": [{"id": "<participant id>", "box": "<box id>"}], "steps": [{"id": "<step id>", "from": "<participant id>", "to": "<participant id>", "label": "<what is sent>", "kind": "<request | response | async>", "in": ["<before | after>"]}]}]}

Leave `in` out for a part in both versions; use `["before"]` for a part the change removes and `["after"]` for a part it adds, and leave `kind` of a step out for `request`. A part key, used in `parts` of a finding and in `changed` of a review, is `box:<box id>`, `edge:<edge id>` or `step:<flow id>/<step id>`; join the two views of one exchange with `+`, such as `edge:<edge id>+step:<flow id>/<step id>`.

`requirements.jsonl`: one line per source.

{"type": "requirement", "kind": "functional", "text": "<requirement>", "source": {"type": "request", "sentence": "<a sentence of the request, word for word>"}}
{"type": "requirement", "kind": "quality", "text": "<scenario with a trigger and an observable response>", "source": {"type": "file", "file": "<path from the repo root>", "symbol": "<symbol>"}}
{"type": "requirement", "kind": "constraint", "text": "<constraint>", "source": {"type": "user", "at": "<UTC time>"}}
{"type": "requirement", "kind": "functional", "text": "<requirement>", "source": {"type": "guessed"}}

`perspectives.jsonl`: one line per perspective, built in or from a repo standard.

{"type": "perspective", "name": "<name>", "applies": true, "why": "<why it applies, from what the change touches>", "from": {"type": "built_in", "method": "<method, such as STRIDE, or null>"}}
{"type": "perspective", "name": "<name>", "applies": false, "why": "<why it does not apply>", "from": {"type": "standard", "file": "<path of the repo standard>"}}

`findings.jsonl`: one line per finding, open or handled.

{"type": "finding", "perspective": "<perspective id>", "parts": ["edge:<edge id>+step:<flow id>/<step id>"], "text": "<what is wrong and its effect>", "confirmed": true, "status": "open"}
{"type": "finding", "perspective": "<perspective id>", "parts": ["box:<box id>"], "text": "<what is wrong and its effect>", "confirmed": false, "status": "handled", "handled_by": "<the change or decision that addresses it>"}

`decisions.jsonl`: one line per decision.

{"type": "decision", "title": "<title>", "drivers": ["<requirement id>"], "chosen": "<what was chosen>", "rejected": [{"option": "<option>", "why": "<why not>"}], "drawback": "<main drawback of the chosen option>"}

`reviews.jsonl`, written by the `review` command, never by `add`:

{"type": "review", "perspectives": ["<perspective id>"], "changed": ["box:<box id>"], "hashes": {"box:<box id>": "<SHA-256 of the part's JSON>"}, "labels": {"box:<box id>": "<label>"}}
