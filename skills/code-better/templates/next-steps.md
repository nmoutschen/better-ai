# Proposed next steps: <short name of the change>

<HOW TO FILL THIS IN — delete this block when done.
- ADD them to `.code/<change>/next-steps.jsonl`, one line per piece of work outside the change.
- Conventions: WRITE a missing value as `null`, a list as a JSON array, and a value that has a fixed set as one of its exact lowercase words. A field not shown below is an error. WRITE the record a pointer names before the pointer.
- SET `priority` from `if_nobody` alone. DROP a step already in the tasks or an earlier hand-back.
- `origin` says where the step came up: a file, a requirement of the spec, an audit finding, or a task.
- IF a coordinator runs the change, it may admit a step that stays inside the design and asks the user about the rest. OTHERWISE, every step goes to the user in the hand-back.>

One line per kind of origin:

{"type": "next_step", "step": "<one step>", "origin": {"type": "file", "path": "<file>"}, "if_nobody": "<what goes wrong, and for whom>", "done_when": "<the check or result that shows it is done>", "priority": "<high | medium | low>", "status": "<proposed | admitted | asked | dropped>"}
{"type": "next_step", "step": "<step>", "origin": {"type": "spec", "spec": "S<n>"}, "if_nobody": "<what goes wrong>", "done_when": "<result>", "priority": "<priority>", "status": "<status>"}
{"type": "next_step", "step": "<step>", "origin": {"type": "finding", "finding": "A<n>"}, "if_nobody": "<what goes wrong>", "done_when": "<result>", "priority": "<priority>", "status": "<status>"}
{"type": "next_step", "step": "<step>", "origin": {"type": "task", "task": "T<n>"}, "if_nobody": "<what goes wrong>", "done_when": "<result>", "priority": "<priority>", "status": "<status>"}
