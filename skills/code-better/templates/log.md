# Agent card and log: <agent name>

<HOW TO FILL THIS IN — delete this block when done.
- The coordinator writes the card, `.code/<change>/logs/<agent name>.card.json`, before it starts the agent, with `python3 <skill dir>/scripts/dashboard.py card <change folder> <agent name> --role <role> --task T<n> --branch <branch>`. The agent adds one line for each event at the end of `.code/<change>/logs/<agent name>.jsonl` with `python3 <skill dir>/scripts/dashboard.py log <change folder> <agent name> <type> "<text>" [--result <result>]`. NEVER write either by hand or type a time: the commands stamp `at` and `by`, and refuse a record that does not check. The lines below show what they write. `schemas/card.schema.json` and `schemas/log.schema.json` are the authority. A verifier writes no `asked` or `blocked` line.
- Conventions: START each record with `type`, `at` (UTC, ending in Z) and `by` (your agent name). WRITE a missing value as `null`, a list as a JSON array, and a value that has a fixed set as one of its exact lowercase words. A field the schema does not name is an error. WRITE one record per line, as ASCII JSON, and the record a pointer names before the pointer: the task of a card is in `tasks.jsonl` first. AFTER each write, RUN `python3 <skill dir>/scripts/schema.py check <the file>` and FIX what it reports.
- KEEP `text` to one short sentence.>

Conventions and fields: `schemas/*.schema.json` of this skill.

The card:

{"type": "card", "at": "<UTC time>", "by": "<agent>", "role": "<builder | verifier>", "task": "T<n>", "branch": "<branch>"}

The log:

{"type": "start", "at": "<UTC time>", "by": "<agent>", "text": "<what you begin with>"}
{"type": "step", "at": "<UTC time>", "by": "<agent>", "text": "<what you just did or found>"}
{"type": "asked", "at": "<UTC time>", "by": "<agent>", "text": "<what you sent the coordinator, in a few words>"}
{"type": "blocked", "at": "<UTC time>", "by": "<agent>", "text": "<what you need>"}
{"type": "handed_back", "at": "<UTC time>", "by": "<agent>", "result": "<builder: done | partly done | blocked; verifier: passes | fails>", "text": "<one short reason>"}
