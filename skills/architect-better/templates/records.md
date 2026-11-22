# The files of a change folder

<HOW TO FILL THIS IN — you write the records of the change folder, in the formats of `schemas/`, which are the authority for the fields. Delete this block when done.
- Conventions: START each record with `type`, `at` (UTC, ending in Z) and `by` (your agent name). WRITE a missing value as `null`, a list as a JSON array, and a value that has a fixed set as one of its exact lowercase words. A field the schema does not name is an error. WRITE one record per line in a `.jsonl` file, as ASCII JSON, and the record a pointer names before the pointer: a perspective before its findings, a requirement before the decision it drives. An optional field may be `null`, which means it is absent; a field a status drives, such as `handled_by`, exists only in that status.
- AFTER each write, RUN `python3 <skill dir>/scripts/schema.py check <the file>` and FIX what it reports.
- `kind` of a requirement is `functional`, `quality` or `constraint`. Write one line per requirement, with the source it comes from.>

`architect.json`, one record: the request word for word, and where it comes from.

{"type": "architect", "at": "<UTC time>", "by": "architect", "request": {"text": "<the request, verbatim>", "from": {"type": "chat"}}, "title": "<title>", "summary": "<summary, or an empty string>", "scope": "<scope, or an empty string>", "accepted": []}
{"type": "architect", "at": "<UTC time>", "by": "architect", "request": {"text": "<the request, verbatim>", "from": {"type": "issue", "url": "<issue url>"}}, "title": "<title>", "summary": "<summary>", "scope": "<scope>", "accepted": ["requirements"]}
{"type": "architect", "at": "<UTC time>", "by": "architect", "request": {"text": "<the request, verbatim>", "from": {"type": "file", "path": "<path of the file>"}}, "title": "<title>", "summary": "<summary>", "scope": "<scope>", "accepted": []}

`design.json`, one record: the containers and the flows, each flow with an `id`.

{"type": "design", "at": "<UTC time>", "by": "architect", "containers": {"nodes": [{"id": "<box id>", "label": "<label>", "kind": "<kind from the register>"}], "edges": [{"id": "<edge id>", "from": "<box id>", "to": "<box id>", "label": "<what travels>"}], "groups": []}, "flows": [{"id": "<flow id>", "name": "<name>", "participants": [{"id": "<participant id>", "box": "<box id>"}], "steps": [{"id": "<step id>", "from": "<participant id>", "to": "<participant id>", "label": "<what is sent>", "kind": "request"}]}]}

`requirements.jsonl`: one line per source.

{"type": "requirement", "at": "<UTC time>", "by": "architect", "id": "F<n>", "kind": "functional", "text": "<requirement>", "source": {"type": "request", "sentence": "<a sentence of the request, word for word>"}}
{"type": "requirement", "at": "<UTC time>", "by": "architect", "id": "Q<n>", "kind": "quality", "text": "<scenario with a trigger and an observable response>", "source": {"type": "file", "file": "<path from the repo root>", "symbol": "<symbol>"}}
{"type": "requirement", "at": "<UTC time>", "by": "architect", "id": "C<n>", "kind": "constraint", "text": "<constraint>", "source": {"type": "user", "at": "<UTC time>"}}
{"type": "requirement", "at": "<UTC time>", "by": "architect", "id": "F<n>", "kind": "functional", "text": "<requirement>", "source": {"type": "guessed"}}

`perspectives.jsonl`: one line per perspective, built in or from a repo standard.

{"type": "perspective", "at": "<UTC time>", "by": "architect", "id": "<perspective id>", "name": "<name>", "applies": true, "why": "<why it applies, from what the change touches>", "from": {"type": "built_in", "method": "<method, such as STRIDE, or null>"}}
{"type": "perspective", "at": "<UTC time>", "by": "architect", "id": "<perspective id>", "name": "<name>", "applies": false, "why": "<why it does not apply>", "from": {"type": "standard", "file": "<path of the repo standard>"}}

`findings.jsonl`: one line per finding, open or handled.

{"type": "finding", "at": "<UTC time>", "by": "architect", "id": "V<n>", "perspective": "<perspective id>", "parts": ["edge:<edge id>+step:<flow id>/<step id>"], "text": "<what is wrong and its effect>", "confirmed": true, "status": "open"}
{"type": "finding", "at": "<UTC time>", "by": "architect", "id": "V<n>", "perspective": "<perspective id>", "parts": ["box:<box id>"], "text": "<what is wrong and its effect>", "confirmed": false, "status": "handled", "handled_by": "<the change or decision that addresses it>"}

`decisions.jsonl`: one line per decision.

{"type": "decision", "at": "<UTC time>", "by": "architect", "id": "D<n>", "title": "<title>", "drivers": ["<requirement id>"], "chosen": "<what was chosen>", "rejected": [{"option": "<option>", "why": "<why not>"}], "drawback": "<main drawback of the chosen option>"}

`reviews.jsonl`, written by `python3 <skill dir>/scripts/architect.py review <folder> --perspectives <id>...`, never by hand:

{"type": "review", "at": "<UTC time>", "by": "architect", "perspectives": ["<perspective id>"], "changed": ["box:<box id>"], "hashes": {"box:<box id>": "<SHA-256 of the part's JSON>"}, "labels": {"box:<box id>": "<label>"}}
