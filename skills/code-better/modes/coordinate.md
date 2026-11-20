---
name: coordinate
description: Use when the work splits into several tasks that each need their own review, such as an epic of several tickets; you coordinate builders and verifiers instead of building.
---

# Mode: coordinate

You are the coordinator. Builders write the code, verifiers check it, and you keep the design, the spec and the task list correct. DO NOT build or verify parts yourself: an agent cannot approve its own work. This is also a design choice to save cost, because you are likely the most expensive model in the session.

IF you cannot start sub-agents, this mode cannot run: STOP before you build anything, and TELL the user WHY.

FOLLOW these steps in order. The general rules of SKILL.md apply throughout.

## 1. Write the spec, the design and the task list

READ [../templates/specs.md](../templates/specs.md). THEN WRITE the requirements of the whole change in `.code/<change>/specs.md`, in the template's format. IF the repo keeps specs in a spec tool, such as OpenSpec, Spec Kit or Kiro, UPDATE its files instead and WRITE no `specs.md`.

IF the change adds a module, a data model, a dependency or a migration, and no design covers it, WRITE `.code/<change>/design.md`: READ [../templates/design.md](../templates/design.md) and WRITE it in its format.

SPLIT the work into tasks by part, such as one module or one flow per task, never by role. EACH task fits in one context, and names its mode and its requirements. WRITE them in `.code/<change>/tasks.md`: READ [../templates/tasks.md](../templates/tasks.md) and WRITE the list in its format.

## 2. Start the builders

CREATE your own main branch or worktree for the change, and one branch or worktree per task from it.

IF the harness can run a shell command in the background, and the user's browser can reach the machine where you run commands, START the dashboard: `python3 scripts/dashboard.py watch <change folder>` from this skill's directory, with the full path of `.code/<change>/`. It opens the user's browser and prints its address. GIVE the user the address. IF the harness can only run commands in the foreground, DO NOT start it: TELL the user they can run it themselves. LEAVE it running until the user says they are done with it. The dashboard shows the agents at work from their logs, the tasks done from `tasks.md`, and a conversation with you in which your decisions and questions appear.

IF your harness tells you when a background command ends, ALSO RUN `python3 scripts/dashboard.py wait <change folder>` in the background while the dashboard runs: it ends with the user's new actions in the page. START it again at once each time it ends, before you act on what it printed.

START a builder for each task that can run in parallel: READ [../agents/builder.md](../agents/builder.md), FILL IN its Input, and GIVE the whole file, without its HOW TO USE block, to a new sub-agent as its prompt. GIVE each builder and verifier its own log, `.code/<change>/logs/<agent name>.md`, in its `log` input, with a name no other agent of the change uses. BEFORE you start each builder or verifier, WRITE `.code/<change>/logs/<agent name>.json`: `{"role": "builder", "task": "T3", "mode": "bug fix", "branch": "fix/t3-reads"}`, with `role` builder or verifier, `task` the task's # exactly as `tasks.md` writes it, `mode` one of feature, bug fix, refactor or tests, the one the agent works in, and `branch` the branch it works on. The dashboard reads what the agent works on from this file. IF the harness lets you choose a model, USE a cheaper model than yours for builders and the most capable model for verifiers.

## 3. Answer the builders and verify each task

ANSWER what builders send you, in plain language, and SAY whether an answer came from you or from the user:

- A gap the design, the spec or the repo answers: ANSWER it yourself.
- A decision within what the user agreed with you, the design and its recorded decisions: DECIDE it, REVISE the spec in place if needed, and RECORD it in `.code/<change>/decisions/`: READ [../templates/decision.md](../templates/decision.md) and WRITE it in its format.
- Anything that would change what the user agreed, or that only the user can answer: ASK the user, with everything the builder gave.
- A blocked task: GIVE what is missing, SPLIT the task, or ASK the user. DO NOT build the task yourself.

EACH time this mode says ASK the user, ALSO RECORD the question in `.code/<change>/decisions/` with the status `waiting`, so the dashboard shows it. ASK it in the chat too, because the user may not be watching the page. The user answers in either: APPLY the first answer, THEN SET the status to `answered` and COPY the answer into the file.

WHILE the dashboard runs, READ the user's open items with `python3 scripts/dashboard.py pending <change folder>` each time `wait` ends, each time an agent hands back, and when you resume the change. An answer to a question or a reply to a decision arrives as an item of its own, naming the decision. HANDLE each item as you handle a builder's message above: the user's word is binding, and what changes an agent's task reaches that agent only through you, in its `answers`.

- TRACK each item with `python3 scripts/dashboard.py status <change folder> seen|asked|done <id>...`: MARK it `seen` when it arrives, `asked` when you asked the user something about it and wait, and `done` once you answered it or made the change.
- REPLY in the page with `python3 scripts/dashboard.py reply <change folder> "<your answer, or what you changed>" --to <id>`, in one or two short sentences. WHILE the user works in the page, PUT your answers there, and DO NOT repeat page events in the chat.

WHEN a builder hands back:

- Done: START a verifier on its branch, with its changed checks, as step 4 of SKILL.md says.
- Partly done or blocked: ANSWER what is open, THEN START the task again with the answers in `answers`.
- KEEP its assumptions for your hand-back, and ASK the user about any costly one. ADD its proposed next steps to `.code/<change>/next-steps.md`, in the format of [../templates/next-steps.md](../templates/next-steps.md): ADMIT those that stay inside the design, and ASK the user about the rest.

WHEN a verifier fails a task, START the task again with its findings in `tried`. IF it fails the same task twice for the same finding, ASK the user. WHEN it passes with unconfirmed blocking findings or parts it could not review, ASK the user about them before you merge. UPDATE the task's status in `tasks.md`.

## 4. Merge and test the whole change

MERGE each task into your main branch only after its verifier passed it, or after the user decided its open findings.

AFTER the last merge, START a builder to run every check of the spec on your main branch, and FIX failures by starting the task again. THEN go on with step 4 of SKILL.md on the whole diff. MERGE into the user's branch only once you have handed back and the user allows it.
