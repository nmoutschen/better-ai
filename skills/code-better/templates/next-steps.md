# Proposed next steps: <short name of the change>

<HOW TO FILL THIS IN — delete this block when done.
- SAVE them in `.code/<change>/next-steps.jsonl`, one line per piece of work outside the change, in the format of `schemas/next-steps.schema.json`, which is the authority.
- Conventions: START each record with `type`, `at` (UTC, ending in Z) and `by` (your agent name). WRITE a missing value as `null`, a list as a JSON array, and a value that has a fixed set as one of its exact lowercase words. A field the schema does not name is an error. WRITE one record per line, as ASCII JSON, and the record a pointer names before the pointer. AFTER each write, RUN `python3 <skill dir>/scripts/schema.py check <the file>` and FIX what it reports.
- SET `priority` from `if_nobody` alone. DROP a step already in the tasks or an earlier hand-back.
- `origin` says where the step came up: a file, a requirement of the spec, an audit finding, or a task.
- IF a coordinator runs the change, it may admit a step that stays inside the design and asks the user about the rest. OTHERWISE, every step goes to the user in the hand-back.>

Conventions and fields: `schemas/*.schema.json` of this skill.

One line per kind of origin:

{"type": "step", "at": "<UTC time>", "by": "<agent>", "id": "N<n>", "step": "<one step>", "origin": {"type": "file", "path": "<file>"}, "if_nobody": "<what goes wrong, and for whom>", "done_when": "<the check or result that shows it is done>", "priority": "<high | medium | low>", "status": "<proposed | admitted | asked | dropped>"}
{"type": "step", "at": "<UTC time>", "by": "<agent>", "id": "N<n>", "step": "<step>", "origin": {"type": "spec", "spec": "S<n>"}, "if_nobody": "<what goes wrong>", "done_when": "<result>", "priority": "<priority>", "status": "<status>"}
{"type": "step", "at": "<UTC time>", "by": "<agent>", "id": "N<n>", "step": "<step>", "origin": {"type": "finding", "finding": "A<n>"}, "if_nobody": "<what goes wrong>", "done_when": "<result>", "priority": "<priority>", "status": "<status>"}
{"type": "step", "at": "<UTC time>", "by": "<agent>", "id": "N<n>", "step": "<step>", "origin": {"type": "task", "task": "T<n>"}, "if_nobody": "<what goes wrong>", "done_when": "<result>", "priority": "<priority>", "status": "<status>"}
