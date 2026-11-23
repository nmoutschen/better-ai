# Audit records

MAKE the audit folder with `python3 <skill dir>/scripts/better.pyz create .code/audit/<YYYY-MM-DD> --by <your agent name>`, with the `audit` record below on stdin. ADD each fact and each finding with `python3 <skill dir>/scripts/better.pyz add <unit> <type> --by <your agent name>`, its fields as JSON on stdin, where `<unit>` is `.code/audit/<YYYY-MM-DD>` and `<type>` is `history`, `check`, `rule` or `finding`. CHANGE one with `python3 <skill dir>/scripts/better.pyz set <unit> <id>`. IF the command refuses a record, FIX the record and RUN it again.

- GIVE a missing value as `null`, a list as a JSON array, and a value that has a fixed set as one of its exact lowercase words. A field not shown below is an error. ADD the record a pointer names before the pointer. ADD each fact before the finding whose `evidence_ids` names it.
- The `audit` record holds the GOAL, the commit, and in `not_read` the history, checks or areas left out, and why, or `null`. GIVE `create` `not_read` as `null`, and SET it with `python3 <skill dir>/scripts/better.pyz set <unit> audit` at the end.
- ADD each fact of step 2 as one record, with the command that produced it.
- ADD every finding, however small, in the order of the ranking. `where` lists a file and its lines for each place. `change_frequency` is the commits touching it in the last twelve months and the files it changes with, or `null` when there is no history. `evidence` says what shows it: a test, a reproduction, history entries or exact lines.
- A confirmed finding holds no `settle`. An unconfirmed one holds `settle`: what would settle it. `task` holds the code-better mode and the requirement in one sentence.

The header, type `audit`, given to `create` on stdin:

{"type": "audit", "goal": "<what the user will do with this code next>", "commit": "<hash>", "not_read": "<what was left out, and why, or null>"}

The facts, types `history`, `check` and `rule`:

{"type": "history", "fact": "<what the Git history shows>", "command": "<command that produced it>"}
{"type": "check", "fact": "<what the test or static check shows>", "command": "<command>"}
{"type": "rule", "fact": "<the rule the repository states>", "command": "<command or file that shows it>"}

The findings, type `finding`:

{"type": "finding", "where": [{"file": "<file>", "lines": "<lines>"}], "problem": "<the problem, and the input or situation that shows it>", "cost": "<its effect on the GOAL now, or when the code changes>", "change_frequency": "<commits and files that change with it, or null>", "evidence": "<what shows it>", "evidence_ids": ["E<n>"], "status": "confirmed", "task": {"mode": "<feature | bug fix | refactor | tests>", "requirement": "<the requirement in one sentence>"}}
{"type": "finding", "where": [{"file": "<file>", "lines": "<lines>"}], "problem": "<problem>", "cost": "<cost>", "change_frequency": null, "evidence": "<what shows it>", "evidence_ids": [], "status": "unconfirmed", "settle": "<what would settle it>", "task": {"mode": "<mode>", "requirement": "<requirement>"}}
