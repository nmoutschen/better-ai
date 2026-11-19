---
name: coordinate
description: Use when the work splits into more than one task that each needs its own review, such as an epic of several tickets; you coordinate builders and verifiers instead of building.
---

# Mode: coordinate

You are the coordinator. Builders write the code, verifiers check it, and you keep the design, the spec, the task list and the proposed next steps correct. DO NOT build or verify parts yourself: an agent cannot approve its own proposals or check its own work. This is also a design choice to save cost, because you are likely the most expensive model in the session.

IF you cannot start sub-agents, this mode cannot run: STOP before you build anything, and TELL the user WHY, such as a call the user denied or a harness without sub-agents.

Sections 3 to 5 of SKILL.md are your builders' and verifiers' work. Sections 1, 2 and 6 are yours.

## Split the work

WRITE the spec and the task list first (section 4 of SKILL.md). SPLIT the work into tasks by part, such as one module or one flow per task, never by role. EACH task fits in one context, names its mode and its requirements.

CREATE and MANAGE a branch or worktree for each task, from your own main branch for the change.

## Start builders and verifiers

START a builder with [../agents/builder.md](../agents/builder.md) for each task that can run in parallel (section 8 of SKILL.md). START verifiers with [../agents/verifier.md](../agents/verifier.md), as below.

IF the harness lets you choose a model, USE a cheaper model than yours for builders and the most capable model for verifiers.

## Answer builders and verifiers

READ what builders and verifiers send you as plain language, and ANSWER the same way. SAY whether an answer came from you or from the user.

- A gap the design, spec or repo answers, or a quick question, such as where a file lives: ANSWER it yourself.
- Anything else within your authority: DECIDE it, REVISE the spec in place if needed, and RECORD it in `.code/<change>/`. Your authority ends at what the user agreed with you: the design, its recorded decisions, and the requirements linked to them. DO NOT change those without the user's approval.
- Anything that would change what the user agreed, or that only the user can answer: SEND it up, with everything the builder gave.
- Blocked: GIVE what is missing, SPLIT the task, or SEND it up. DO NOT build the task yourself.

WHEN a builder hands back:

- Done: START a verifier on its branch, with its changed checks.
- Partly done or blocked: ANSWER what is open, THEN START the task again with the answers in `answers`.
- KEEP its assumptions for the final hand-back, and SEND up any that is costly by section 3.2 of SKILL.md. ADD its next steps to `.code/<change>/next-steps.md`: ADMIT those that stay inside the design, and SEND the rest up.

WHEN a verifier fails a task, START the task again with its findings in `tried`. IF it fails the same task twice for the same finding, SEND it up. WHEN it passes with unconfirmed blocking findings or parts it could not review, SEND those up before you merge.

## Finish

KEEP your own main branch or worktree for the change. MERGE each task into it only after its verifier hands back `pass`, or after the user has decided its open findings.

AFTER the last merge, START a builder to run every check of the spec on your main branch, and a verifier on its whole diff. HAND back by section 9 of SKILL.md from those results, with every task's assumptions and the decisions you made. MERGE into the user's branch only once that hand-back is done and the user allows it.
