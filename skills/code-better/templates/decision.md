# Decisions: <short name of the change>

<HOW TO FILL THIS IN — delete this block when done.
- Save them in `.code/<change>/decisions.jsonl`, one line per decision or question, in the format of `schemas/decisions.schema.json`, which is the authority. Only the coordinator writes it.
- Conventions: START each record with `type`, `at` (UTC, ending in Z) and `by` (your agent name). WRITE a missing value as `null`, a list as a JSON array, and a value that has a fixed set as one of its exact lowercase words. A field the schema does not name is an error. WRITE one record per line, as ASCII JSON, and the record a pointer names before the pointer. AFTER each write, RUN `python3 <skill dir>/scripts/schema.py check <the file>` and FIX what it reports.
- WRITE one for each decision you take within what the user agreed, with status `decided` and `decision`, and one for each question you ask the user, with status `waiting`. `id` is D<n>, counting up; `raised_by` is the agent that raised it, or coordinator.
- WHEN the user answers a question, REWRITE the line in place: status `answered`, `decision` removed, and `answer` set. IF the user answered on the page, `answer` points to the answer event in `conversation.jsonl`; IF in the chat, it holds their words.
- WHEN the user replies to a decision and that changes it, REVISE `decision` in place.>

Conventions and fields: `schemas/*.schema.json` of this skill.

{"type": "decision", "at": "<UTC time>", "by": "<agent>", "id": "D<n>", "raised_by": "<agent, or coordinator>", "about": {"type": "task", "task": "T<n>"}, "asked": "<what came up, in one short sentence>", "status": "decided", "decision": "<what you decided, in one short sentence>"}
{"type": "decision", "at": "<UTC time>", "by": "<agent>", "id": "D<n>", "raised_by": "<agent>", "about": {"type": "change"}, "asked": "<the question to the user>", "status": "waiting"}
{"type": "decision", "at": "<UTC time>", "by": "<agent>", "id": "D<n>", "raised_by": "<agent>", "about": {"type": "change"}, "asked": "<the question>", "status": "answered", "answer": {"type": "page", "event": "<id of the answer event in conversation.jsonl>"}}
{"type": "decision", "at": "<UTC time>", "by": "<agent>", "id": "D<n>", "raised_by": "<agent>", "about": {"type": "change"}, "asked": "<the question>", "status": "answered", "answer": {"type": "chat", "text": "<the user's words>"}}
