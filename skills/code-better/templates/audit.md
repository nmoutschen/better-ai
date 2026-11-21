# Audit: <scope>

<HOW TO FILL THIS IN — delete this block when done.
- Save three files in `.code/audit/<YYYY-MM-DD>/`: `audit.json`, one record; `evidence.jsonl`, one line per fact; and `findings.jsonl`, one line per finding, in the order of the ranking. `schemas/audit.schema.json`, `schemas/evidence.schema.json` and `schemas/findings.schema.json` are the authority.
- Conventions: START each record with `type`, `at` (UTC, ending in Z) and `by` (your agent name). WRITE a missing value as `null`, a list as a JSON array, and a value that has a fixed set as one of its exact lowercase words. A field the schema does not name is an error. WRITE one record per line, as ASCII JSON, and the record a pointer names before the pointer: each fact in `evidence.jsonl` before the finding whose `evidence_ids` names it. AFTER each write, RUN `python3 <skill dir>/scripts/schema.py check <the file>` and FIX what it reports.
- `audit.json` holds the GOAL, the commit, and in `not_read` the history, checks or areas left out, and why, or `null`.
- WRITE each fact of step 2 as one evidence record, with the command that produced it.
- WRITE every finding, however small. `where` lists a file and its lines for each place. `change_frequency` is the commits touching it in the last twelve months and the files it changes with, or `null` when there is no history. `evidence` says what shows it: a test, a reproduction, history entries or exact lines.
- A confirmed finding holds no `settle`. An unconfirmed one holds `settle`: what would settle it. `task` holds the code-better mode and the requirement in one sentence.>

Conventions and fields: `schemas/*.schema.json` of this skill.

The header, `audit.json`:

{"type": "audit", "at": "<UTC time>", "by": "<agent>", "goal": "<what the user will do with this code next>", "commit": "<hash>", "not_read": "<what was left out, and why, or null>"}

The facts, `evidence.jsonl`:

{"type": "history", "at": "<UTC time>", "by": "<agent>", "id": "E<n>", "fact": "<what the Git history shows>", "command": "<command that produced it>"}
{"type": "check", "at": "<UTC time>", "by": "<agent>", "id": "E<n>", "fact": "<what the test or static check shows>", "command": "<command>"}
{"type": "rule", "at": "<UTC time>", "by": "<agent>", "id": "E<n>", "fact": "<the rule the repository states>", "command": "<command or file that shows it>"}

The findings, `findings.jsonl`:

{"type": "finding", "at": "<UTC time>", "by": "<agent>", "id": "A<n>", "where": [{"file": "<file>", "lines": "<lines>"}], "problem": "<the problem, and the input or situation that shows it>", "cost": "<its effect on the GOAL now, or when the code changes>", "change_frequency": "<commits and files that change with it, or null>", "evidence": "<what shows it>", "evidence_ids": ["E<n>"], "status": "confirmed", "task": {"mode": "<feature | bug fix | refactor | tests>", "requirement": "<the requirement in one sentence>"}}
{"type": "finding", "at": "<UTC time>", "by": "<agent>", "id": "A<n>", "where": [{"file": "<file>", "lines": "<lines>"}], "problem": "<problem>", "cost": "<cost>", "change_frequency": null, "evidence": "<what shows it>", "evidence_ids": [], "status": "unconfirmed", "settle": "<what would settle it>", "task": {"mode": "<mode>", "requirement": "<requirement>"}}
