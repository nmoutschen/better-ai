# Tasks: <short name of the change>

<HOW TO FILL THIS IN — delete this block when done.
- Write this before the first step when the work spans several sessions, people or agents, or more than fits in one context.
- Save it in .code/<change>/tasks.md, unless the repo's spec tool keeps tasks elsewhere.
- One task per step, each with its own check that tells done from not done: it FAILS before the task is done and PASSES after. A check that passes either way, such as running the whole suite, does not count.
- RUN a task's check after its last edit. SET its status to done in a separate edit, only after the check passes. Keep the list current. On a branch or worktree you created, also commit after each task; in the user's checkout, only IF they allowed it.
- Begin each session by reading the design, the spec and this list. At each checkpoint, re-run the spec's checks and look for growing duplication.
- WHEN you hand a task to another agent, give it the design, that task's requirements, and what you tried with what you found.>

Design: <path or link>
Spec: <path or link>

| # | Task | Mode | Requirements | Check that tells done from not done | Status |
|---|---|---|---|---|---|
| <n> | <one task> | <feature / bug fix / refactor / tests> | <requirement IDs> | <test or command specific to this task: fails before, passes after> | <todo / done / blocked> |

## Progress notes

- <date or session>: <what was done, what was found, what to do next>

## Open problems

- <Problem>: <what was tried, what is known>
