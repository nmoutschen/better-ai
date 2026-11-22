# Task and progress records

ADD each with `python3 <skill dir>/scripts/better.pyz add <unit> <type> --by <your agent name>`, its fields as JSON on stdin, where `<unit>` is the change folder `.code/<change>` and `<type>` is `task`, `progress`, `problem` or `resolved`. CHANGE one with `python3 <skill dir>/scripts/better.pyz set <unit> <id>`. IF the command refuses a record, FIX the record and RUN it again.

- GIVE a missing value as `null`, a list as a JSON array, and a value that has a fixed set as one of its exact lowercase words. A field not shown below is an error. ADD the record a pointer names before the pointer.
- IF the repo's spec tool also keeps tasks, UPDATE its tasks from the records.
- ADD one `task` per part of the work, such as one module or one service, even when several are done in one session. ADD every task as `todo` when you create the list. `requirements` holds the requirement IDs of the spec, nothing else.
- Each task has its own check that tells done from not done: it FAILS before the task is done and PASSES after. A check that passes either way, such as running the whole suite, does not count.
- GIVE every task a check that is a command or test that names its part and runs as written, also for tasks someone else does later. RUN each check before its task starts, and KEEP it only if it fails then.
- RUN a task's check after its last edit. SET its status to `done` with `set` only once you have seen the check pass, in a command of its own: DO NOT set `done` in the same command that edits the code or runs the check. KEEP the list current. On a branch or worktree you created, also COMMIT after each task; in the user's checkout, only IF they allowed it.
- A `blocked` task holds `reason`: `task` with `waits_on`, `user`, or in coordinate mode `repair limit`. A task that is not blocked holds neither.
- ADD a `progress` record for what was done, found or is next, a `problem` record for an open problem, and a `resolved` record, pointing to the problem, when it is solved. In coordinate mode only the coordinator adds progress.
- BEGIN each session by reading the design, the spec and the tasks. At each checkpoint, RUN the spec's checks again and LOOK for growing duplication.
- WHEN you hand a task to another agent, give it the design, that task's requirements, and what you tried with what you found.

The tasks, type `task`: a task that is not blocked, then one blocked for each reason.

{"type": "task", "task": "<one task>", "mode": "<feature | bug fix | refactor | tests>", "requirements": ["S<n>"], "check": "<test or command specific to this task: fails before, passes after>", "status": "<todo | done; in coordinate mode a status from modes/coordinate.md>"}
{"type": "task", "task": "<task>", "mode": "<mode>", "requirements": ["S<n>"], "check": "<check>", "status": "blocked", "reason": "task", "waits_on": "T<n>"}
{"type": "task", "task": "<task>", "mode": "<mode>", "requirements": ["S<n>"], "check": "<check>", "status": "blocked", "reason": "user"}
{"type": "task", "task": "<task>", "mode": "<mode>", "requirements": ["S<n>"], "check": "<check>", "status": "blocked", "reason": "repair limit"}

The progress, types `progress`, `problem` and `resolved`:

{"type": "progress", "about": {"type": "change"}, "text": "<what was done, what was found, what to do next>"}
{"type": "problem", "about": {"type": "task", "task": "T<n>"}, "text": "<the problem: what was tried, what is known>"}
{"type": "resolved", "to": "P<n>", "text": "<how it was solved>"}
