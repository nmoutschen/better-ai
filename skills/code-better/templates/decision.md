# Decisions: <short name of the change>

<HOW TO FILL THIS IN — delete this block when done.
- ADD them to `.code/<change>/decisions.jsonl`, one line per decision or question. In coordinate mode only the coordinator writes it; otherwise you write it.
- Conventions: WRITE a missing value as `null`, a list as a JSON array, and a value that has a fixed set as one of its exact lowercase words. A field not shown below is an error. WRITE the record a pointer names before the pointer.
- WRITE one for each decision you take within what the user agreed, with status `decided` and `decision`, and one for each question you ask the user, with status `waiting`, `default` (what happens if the user does not answer, or `null` while the work waits for the answer) and `deadline` (`+<minutes>m`, or `null`). `raised_by` is the agent that raised it, or coordinator.
- WHEN the user answers a question, EDIT it with `set`: status `answered` and `answer` set. IF the deadline passed without an answer, SET status `defaulted`. IF the user answered on the page, `answer` points to the answer event in `conversation.jsonl`; IF in the chat, it holds their words.
- WHEN the user replies to a decision and that changes it, REVISE `decision` with `set`.>

{"type": "decision", "raised_by": "<agent, or coordinator>", "about": {"type": "task", "task": "T<n>"}, "asked": "<what came up, in one short sentence>", "status": "decided", "decision": "<what you decided, in one short sentence>"}
{"type": "decision", "raised_by": "<agent>", "about": {"type": "change"}, "asked": "<the question to the user>", "status": "waiting", "default": "<what happens without an answer, or null>", "deadline": "<+<minutes>m, or null>"}
{"type": "decision", "raised_by": "<agent>", "about": {"type": "change"}, "asked": "<the question>", "status": "answered", "default": "<as in the waiting line>", "deadline": "<as in the waiting line>", "answer": {"type": "page", "event": "<id of the answer event in conversation.jsonl>"}}
{"type": "decision", "raised_by": "<agent>", "about": {"type": "change"}, "asked": "<the question>", "status": "answered", "default": "<as in the waiting line>", "deadline": "<as in the waiting line>", "answer": {"type": "chat", "text": "<the user's words>"}}
{"type": "decision", "raised_by": "<agent>", "about": {"type": "change"}, "asked": "<the question>", "status": "defaulted", "default": "<what was applied>", "deadline": "<as in the waiting line>"}
