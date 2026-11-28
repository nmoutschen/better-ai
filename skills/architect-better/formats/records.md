# Architect records

ADD each with `python3 <skill dir>/scripts/better.pyz add <unit> <type> --by <your name>`, its fields as JSON on stdin, where `<unit>` is the change folder `.architect/<change>` and `<type>` is `design`, `requirement`, `perspective`, `finding`, `decision` or `agent`. The head record is the one you gave `create`. CHANGE a record with `python3 <skill dir>/scripts/better.pyz set <unit> <id>`, or `set <unit> design` for the design. Leave out `at`, `by` and `id`: the command adds them. IF the command refuses a record, FIX the record and RUN it again.

- GIVE a missing value as `null`, a list as a JSON array, and a value that has a fixed set as one of its exact lowercase words. A field the record does not name is an error. ADD the record a pointer names before the pointer: a perspective before its findings, a requirement before the decision it drives. An optional field may be `null`, which means it is absent; a field a status drives, such as `handled_by`, exists only in that status.
- `kind` of a requirement is `functional`, `quality` or `constraint`. ADD one record per requirement, with the source it comes from.
- Name a perspective with `--id <perspective id>` on the command.

The head, type `architect`, one record given to `create`: the request word for word, and where it comes from. Once `design.md` exists, `document` gives its path from the repo root.

{"type": "architect", "request": {"text": "<the request, verbatim>", "from": {"type": "chat"}}, "title": "<title>", "summary": "<summary, or an empty string>", "scope": "<scope, or an empty string>", "accepted": []}
{"type": "architect", "request": {"text": "<the request, verbatim>", "from": {"type": "issue", "url": "<issue url>"}}, "title": "<title>", "summary": "<summary>", "scope": "<scope>", "accepted": ["requirements"]}
{"type": "architect", "request": {"text": "<the request, verbatim>", "from": {"type": "file", "path": "<path of the file>"}}, "title": "<title>", "summary": "<summary>", "scope": "<scope>", "accepted": []}
{"type": "architect", "request": {"text": "<the request, verbatim>", "from": {"type": "chat"}}, "title": "<title>", "summary": "<summary>", "scope": "<scope>", "accepted": ["requirements", "containers"], "document": {"file": "<path of design.md from the repo root>"}}

The design, type `design`, one record: the containers and the flows, each flow with an `id`.

{"type": "design", "containers": {"nodes": [{"id": "<box id>", "label": "<label>", "kind": "<kind from the register>", "detail": "<detail, or leave out>", "in": ["<before | after>"]}], "edges": [{"id": "<edge id>", "from": "<box id>", "to": "<box id>", "label": "<what travels>", "in": ["<before | after>"]}], "groups": [{"id": "<group id>", "label": "<label>", "members": ["<box id>"], "in": ["<before | after>"]}]}, "flows": [{"id": "<flow id>", "name": "<name>", "in": ["<before | after>"], "participants": [{"id": "<participant id>", "box": "<box id>"}], "steps": [{"id": "<step id>", "from": "<participant id>", "to": "<participant id>", "label": "<what is sent>", "kind": "<request | response | async>", "in": ["<before | after>"]}]}]}

Leave `in` out for a part in both versions; use `["before"]` for a part the change removes and `["after"]` for a part it adds, and leave `kind` of a step out for `request`. A part key, used in `parts` of a finding and in `changed` of a review, is `box:<box id>`, `edge:<edge id>` or `step:<flow id>/<step id>`; join the two views of one exchange with `+`, such as `edge:<edge id>+step:<flow id>/<step id>`.

A design that also groups its boxes by trust and by where they run, with a logic flow: a process with a decision, a loop back and two exits.

{"type": "design", "containers": {"nodes": [{"id": "<box id>", "label": "<label>", "kind": "<kind>"}], "edges": [], "groups": [{"id": "<group id>", "label": "<label>", "members": ["<box id>"]}, {"id": "<group id>", "kind": "trust", "label": "<trust zone>", "members": ["<box id>"]}, {"id": "<group id>", "kind": "runs", "label": "<region, zone or host>", "members": []}, {"id": "<group id>", "kind": "runs", "label": "<host>", "within": "<group id of the region>", "members": ["<box id>"]}]}, "flows": [{"id": "<flow id>", "name": "<name>", "kind": "logic", "nodes": [{"id": "<node id>", "type": "start"}, {"id": "<node id>", "type": "step", "label": "<what is done>", "by": "<box id>"}, {"id": "<node id>", "type": "decision", "label": "<question>"}, {"id": "<node id>", "type": "exit", "label": "<how it ends>", "outcome": "<positive | negative>"}, {"id": "<node id>", "type": "exit", "label": "<how it ends>", "outcome": "<positive | negative>"}], "edges": [{"id": "<edge id>", "from": "<node id>", "to": "<node id>", "label": "<outcome or trigger>"}]}]}

`kind` of a group is `trust` or `runs`; leave it out for a system boundary. A box is in at most one group of each kind, and `within` puts a group inside another of the same kind. A logic flow has one `start`; a lifecycle uses nodes of type `state`. Give each outcome of a decision a `label`, and each edge out of a state its trigger, such as a timeout. Do not mark the edges that go back: the drawing finds them. A part key names a node or an edge of a logic flow as `step:<flow id>/<node or edge id>`.

A design with alternatives, still to choose from: `in` names an alternative by its `id`, one word of lowercase letters and digits, and `after` stands for every alternative.

{"type": "design", "alternatives": [{"id": "<alternative id>", "name": "<name>", "summary": "<what it does differently>", "strengths": ["<strength>"], "drawbacks": ["<drawback>"]}, {"id": "<other alternative id>", "name": "<name>", "summary": "<summary>", "strengths": [], "drawbacks": ["<drawback>"]}], "containers": {"nodes": [{"id": "<box id>", "label": "<label>", "kind": "<kind>", "in": ["<alternative id>"]}, {"id": "<box id>", "label": "<label>", "kind": "<kind>", "in": ["before", "<other alternative id>"]}]}, "flows": []}

The requirements, type `requirement`: one record per source.

{"type": "requirement", "kind": "functional", "text": "<requirement>", "source": {"type": "request", "sentence": "<a sentence of the request, word for word>"}}
{"type": "requirement", "kind": "quality", "text": "<scenario with a trigger and an observable response>", "source": {"type": "file", "file": "<path from the repo root>", "symbol": "<symbol>"}}
{"type": "requirement", "kind": "constraint", "text": "<constraint>", "source": {"type": "user", "at": "<UTC time>"}}
{"type": "requirement", "kind": "functional", "text": "<requirement>", "source": {"type": "guessed"}}

The perspectives, type `perspective`: one per perspective, built in or from a repo standard.

{"type": "perspective", "name": "<name>", "applies": true, "why": "<why it applies, from what the change touches>", "from": {"type": "built_in", "method": "<method, such as STRIDE, or null>"}}
{"type": "perspective", "name": "<name>", "applies": false, "why": "<why it does not apply>", "from": {"type": "standard", "file": "<path of the repo standard>"}}

The findings, type `finding`: one per finding, open or handled.

{"type": "finding", "perspective": "<perspective id>", "parts": ["edge:<edge id>+step:<flow id>/<step id>"], "text": "<what is wrong and its effect>", "confirmed": true, "status": "open"}
{"type": "finding", "perspective": "<perspective id>", "parts": ["box:<box id>"], "text": "<what is wrong and its effect>", "confirmed": false, "status": "handled", "handled_by": "<the change or decision that addresses it>"}

The decisions, type `decision`: one per decision.

{"type": "decision", "title": "<title>", "drivers": ["<requirement id>"], "chosen": "<what was chosen>", "rejected": [{"option": "<option>", "why": "<why not>"}], "drawback": "<main drawback of the chosen option>"}

The agents you start, type `agent`: one per agent, added `running` when it starts; its `at` is when it started. `task` is `review`, `proof of concept` or `spec check`, and `what` says in a few words what it works on, such as the perspective's name or the question a proof of concept answers. SET `status` to `done` when it hands back, or `stopped` when it ends without a hand-back.

{"type": "agent", "name": "<the agent's name>", "task": "review", "what": "<perspective name>", "status": "running"}
{"type": "agent", "name": "<the agent's name>", "task": "proof of concept", "what": "<the question it answers, in a few words>", "status": "done"}
{"type": "agent", "name": "<the agent's name>", "task": "spec check", "what": "<what it checks>", "status": "stopped"}

The reviews, type `review`: the `review` command adds them, never `add`:

{"type": "review", "perspectives": ["<perspective id>"], "changed": ["box:<box id>"], "hashes": {"box:<box id>": "<SHA-256 of the part's JSON>"}, "labels": {"box:<box id>": "<label>"}, "texts": {"requirement:<requirement id>": "<SHA-256 of the requirement>", "section:<heading>": "<SHA-256 of the section of design.md>"}}
