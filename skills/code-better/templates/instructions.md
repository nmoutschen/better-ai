# Instructions: <short name of the change>

<HOW TO FILL THIS IN — delete this block when done.
- SAVE them in `.code/<change>/instructions.jsonl`, one line per instruction, in the format of `schemas/instructions.schema.json`, which is the authority.
- WRITE only an instruction on how to work, such as never touch a folder or run a check before each commit, with the user's words in `said`. A constraint on what the code does goes into the spec.
- Conventions: START each record with `type`, `at` (UTC, ending in Z) and `by` (your agent name). WRITE a missing value as `null`, a list as a JSON array. A field the schema does not name is an error. WRITE one record per line, as ASCII JSON. AFTER each write, RUN `python3 <skill dir>/scripts/schema.py check <the file>` and FIX what it reports.
- In coordinate mode only the coordinator writes it.>

Conventions and fields: `schemas/*.schema.json` of this skill.

{"type": "instruction", "at": "<UTC time>", "by": "<agent>", "instruction": "<the instruction, in one sentence>", "said": "<the user's words>"}
