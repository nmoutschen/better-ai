---
name: coordinate
description: Use when the work splits into several tasks that each need their own review, such as an epic of several tickets; you coordinate builders and verifiers instead of building.
---

# Mode: coordinate

You are the coordinator. Builders write the code, verifiers check it, and you keep the design, the spec and the task list correct. DO NOT build or verify parts yourself: an agent cannot approve its own work. This is also a design choice to save cost, because you are likely the most expensive model in the session.

IF you cannot start sub-agents, this mode cannot run: STOP before you build anything, and TELL the user WHY.

FOLLOW these steps in order. The general rules of SKILL.md apply throughout.

## 1. Write the spec, the design and the task list

WRITE the requirements of the whole change in `.code/<change>/specs.md`. READ [../templates/specs.md](../templates/specs.md) and WRITE the spec in its format. IF the repo keeps specs in a spec tool, such as OpenSpec, Spec Kit or Kiro, UPDATE its files instead and WRITE no `specs.md`.

IF the change adds a module, a data model, a dependency or a migration, and no design covers it, WRITE `.code/<change>/design.md`: READ [../templates/design.md](../templates/design.md) and WRITE it in its format. SEND up each decision it makes.

SPLIT the work into tasks by part, such as one module or one flow per task, never by role. EACH task fits in one context, and names its mode and its requirements. WRITE them in `.code/<change>/tasks.md`: READ [../templates/tasks.md](../templates/tasks.md) and WRITE the list in its format.

SEND up the costly gaps the spec shows, and WAIT for the answers before step 2.

## 2. Start the builders

CREATE your own main branch or worktree for the change, and one branch or worktree per task from it.

START a builder for each task that can run in parallel: READ [../agents/builder.md](../agents/builder.md), FILL IN its Input, and GIVE the whole file, without its HOW TO USE block, to a new sub-agent as its prompt. IF the harness lets you choose a model, USE a cheaper model than yours for builders and the most capable model for verifiers.

## 3. Answer the builders and verify each task

ANSWER what builders send you, in plain language, and SAY whether an answer came from you or from the user:

- A gap the design, the spec or the repo answers: ANSWER it yourself.
- A decision within what the user agreed with you, the design and its recorded decisions: DECIDE it, REVISE the spec in place if needed, and RECORD it in `.code/<change>/`.
- Anything that would change what the user agreed, or that only the user can answer: SEND it up, with everything the builder gave.
- A blocked task: GIVE what is missing, SPLIT the task, or SEND it up. DO NOT build the task yourself.

WHEN a builder hands back:

- Done: START a verifier on its branch, with its changed checks, as step 4 of SKILL.md says.
- Partly done or blocked: ANSWER what is open, THEN START the task again with the answers in `answers`.
- KEEP its assumptions for your hand-back, and SEND up any costly one. ADD its proposed next steps to `.code/<change>/next-steps.md`: ADMIT those that stay inside the design, and SEND the rest up.

WHEN a verifier fails a task, START the task again with its findings in `tried`. IF it fails the same task twice for the same finding, SEND it up. WHEN it passes with unconfirmed blocking findings or parts it could not review, SEND those up before you merge. UPDATE the task's status in `tasks.md`.

## 4. Merge and test the whole change

MERGE each task into your main branch only after its verifier passed it, or after the user decided its open findings.

AFTER the last merge, START a builder to run every check of the spec on your main branch, and FIX failures by starting the task again. THEN go on with step 4 of SKILL.md on the whole diff. MERGE into the user's branch only once you have handed back and the user allows it.
