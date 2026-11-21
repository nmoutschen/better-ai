# Tasks: <short name of the change>

<HOW TO FILL THIS IN — delete this block when done.
- SAVE the tasks in `.code/<change>/tasks.jsonl`; IF the repo's spec tool also keeps tasks, UPDATE its tasks from it. SAVE the progress in `.code/<change>/progress.jsonl`. `schemas/tasks.schema.json` and `schemas/progress.schema.json` are the authority.
- Conventions: START each record with `type`, `at` (UTC, ending in Z) and `by` (your agent name). WRITE a missing value as `null`, a list as a JSON array, and a value that has a fixed set as one of its exact lowercase words. A field the schema does not name is an error. WRITE one record per line, as ASCII JSON, and the record a pointer names before the pointer. AFTER each write, RUN `python3 <skill dir>/scripts/schema.py check <the file>` and FIX what it reports.
- One `task` per part of the work, such as one module or one service, even when several are done in one session. WRITE every task as `todo` when you create the list. `requirements` holds the requirement IDs of `spec.jsonl`, nothing else.
- Each task has its own check that tells done from not done: it FAILS before the task is done and PASSES after. A check that passes either way, such as running the whole suite, does not count.
- WRITE every task's check as a command or test that names its part and runs as written, also for tasks someone else does later. RUN each check before its task starts, and KEEP it only if it fails then.
- RUN a task's check after its last edit. SET its status to `done` only once you have seen the check pass, in an edit of its own: DO NOT write `done` in the same command that edits the code or runs the check. REWRITE the line in place, keeping `at` and `by`. KEEP the list current. On a branch or worktree you created, also COMMIT after each task; in the user's checkout, only IF they allowed it.
- A `blocked` task holds `reason`: `task` with `waits_on`, `user`, or in coordinate mode `repair limit`. A task that is not blocked holds neither.
- ADD a `progress` record for what was done, found or is next, a `problem` record for an open problem, and a `resolved` record, pointing to the problem, when it is solved. In coordinate mode only the coordinator writes progress.
- BEGIN each session by reading the design, the spec and the tasks. At each checkpoint, RUN the spec's checks again and LOOK for growing duplication.
- WHEN you hand a task to another agent, give it the design, that task's requirements, and what you tried with what you found.>

Conventions and fields: `schemas/*.schema.json` of this skill.

The tasks, `tasks.jsonl`: a task that is not blocked, then one blocked for each reason.

{"type": "task", "at": "<UTC time>", "by": "<agent>", "id": "T<n>", "task": "<one task>", "mode": "<feature | bug fix | refactor | tests>", "requirements": ["S<n>"], "check": "<test or command specific to this task: fails before, passes after>", "status": "<todo | done; in coordinate mode a status from modes/coordinate.md>"}
{"type": "task", "at": "<UTC time>", "by": "<agent>", "id": "T<n>", "task": "<task>", "mode": "<mode>", "requirements": ["S<n>"], "check": "<check>", "status": "blocked", "reason": "task", "waits_on": "T<n>"}
{"type": "task", "at": "<UTC time>", "by": "<agent>", "id": "T<n>", "task": "<task>", "mode": "<mode>", "requirements": ["S<n>"], "check": "<check>", "status": "blocked", "reason": "user"}
{"type": "task", "at": "<UTC time>", "by": "<agent>", "id": "T<n>", "task": "<task>", "mode": "<mode>", "requirements": ["S<n>"], "check": "<check>", "status": "blocked", "reason": "repair limit"}

The progress, `progress.jsonl`:

{"type": "progress", "at": "<UTC time>", "by": "<agent>", "about": {"type": "change"}, "text": "<what was done, what was found, what to do next>"}
{"type": "problem", "at": "<UTC time>", "by": "<agent>", "id": "P<n>", "about": {"type": "task", "task": "T<n>"}, "text": "<the problem: what was tried, what is known>"}
{"type": "resolved", "at": "<UTC time>", "by": "<agent>", "to": "P<n>", "text": "<how it was solved>"}
