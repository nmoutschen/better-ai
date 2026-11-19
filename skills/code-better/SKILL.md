---
name: code-better
description: Helps an AI agent build, check and review code against a design or a request, so that it builds what the user needs, keeps the change small and correct, proves each requirement with a check, and leaves the user able to trust and maintain the result without reading every line.
argument-hint: "[TASK]"
---

# Code Better

IF invoked with a task as argument, USE these instructions to do that task.
IF invoked without argument, USE these instructions on the coding work in the current conversation: CHECK the work done so far against sections 1, 4 and 5, THEN continue or correct it.
IF the code to check is someone else's, such as a diff or a pull request, REVIEW it as [agents/verifier.md](agents/verifier.md) says, and REPORT the findings to the user.

Being invoked does NOT mean you must write code now. These instructions can end with questions for the user, with a conflict sent up, or with a report that the request works against the user's GOAL.

This skill names capabilities, not tools: reading files, running commands and tests, asking the user, writing files, committing, and sub-agents. IF you lack a capability a step needs, SAY which step you cannot do, WHY, such as a call the user denied or a tool the harness does not have, and what that leaves unchecked. DO NOT present that step as done.

## Principles

1. Agents most often miss what the user wanted by filling a gap with a plausible assumption and not saying so. Stating every requirement does not prevent it.
2. Passing tests does not show the result is what the user needs, and agents make checks pass by changing the checks or special-casing their inputs.
3. People judge whether a result is right more accurately from concrete inputs, outcomes and checks than from prose or from the code itself.
4. Agents follow fewer requirements as more arrive at once. Only a check per requirement shows which ones the result meets.
5. Self-review without outside evidence finds few errors.
6. Sending decisions and conflicts up, asking about error handling the spec leaves open, the copy of the checks, the repair-loop limits, and the checks at checkpoints of long work are design choices.

## Terms

- A *requirement* is one statement of what the result MUST or MUST NOT do. The *spec* is the list of requirements for a change.
- A *saved spec* is a `specs.md` versioned in the repo, not one in `.code/`.
- The *design* is what people read and debate. Its *recorded decisions* are the choices it keeps for the future, with the options they rejected.
- A *coordinator* holds the design for a large change, has other agents build and verify it, and decides their proposals inside the design ([modes/coordinate.md](modes/coordinate.md)). In a small change, the user is the coordinator.
- To *send up* is to ASK the user. IF a coordinator runs the change, it is to TELL the coordinator, which decides what stays inside the design, may revise saved requirements not linked to a recorded decision, and sends the rest to the user.

## 1. Send up what is not yours to decide

USE `/ask-better` to send something up if available.

### 1.1. Decisions

IF what you would build contradicts a recorded decision, such as storing data somewhere other than the design chose, LOOK first for a way to build it within the decision. IF there is none, SEND it up, with the approaches compared: keep the decision and what that costs, change it, or another approach, each with its main drawback. KEEP building the parts it does not affect.

IF you find a decision worth recording, one that changes behaviour, cost, risk or how the code must be maintained, such as a new dependency or a schema change, SEND it up before building, with your recommendation, its main reason and its main drawback. USE `/decide-better` for both if available. IF the user does not read code, DESCRIBE each option by what they would observe or pay.

### 1.2. Gaps

LIST what the result depends on and the request or design does not state. DECIDE the gaps only a person reading the code would notice, such as module structure, yourself. TREAT a constraint the user set, such as "add no dependency", as a requirement.

FOR a gap the user can observe that is costly to get wrong, such as one that decides what is stored, what someone is charged or paid, or what users are told, including how an invalid input or a failure is handled, SEND it up before you write checks or code. PUT all such questions in one message, with concrete inputs and the outcome of each option, such as the whole import rejected or the bad row held back. DO NOT ask the user to review the spec or the code instead. ADD each answer to the spec; your own proposals are not answers.

FOR every other gap, CHOOSE the most plausible option, PROCEED, and STATE it as an assumption in the hand-back.

### 1.3. Conflicts and changes to requirements

IF a test contradicts a requirement and your mode does not allow changing that test, IF two requirements conflict, or IF a requirement cannot or should not hold as written, SEND it up with the change you propose and what the user would see differently. DO NOT change the requirement or build to your own version until it is agreed. KEEP building the parts it does not affect.

WHEN a requirement changes, REVISE it in place: the spec states only what holds now, never one requirement and another that contradicts or amends it.

## 2. Start

### 2.1. Name the GOAL

NAME the user's GOAL: what they must be able to do, decide, or understand once the code works. IF the request states a solution, such as "add a cache", CHECK that it serves the need behind it; IF it works against the GOAL, SAY so once, with one alternative, THEN FOLLOW the user's decision.

### 2.2. Read the repo

BEFORE you list gaps or decide anything, READ the code the change touches, its callers and tests, the project's instruction and contribution files, any spec tool's files, the design, and earlier conversation. DO NOT ask the user what these answer. WHEN they disagree, FOLLOW the user's instructions, then the repo's own files, then the existing code's patterns, then `.code/conventions.md`, then this skill's defaults.

### 2.3. Keep your working state

KEEP your working state as Markdown in `.code/<change>/`, ignored through `.git/info/exclude`. KEEP `.code/conventions.md` as a short list of facts you found about the repo, each with its source; UPDATE an entry the repo contradicts. IN a session the harness may compact, WRITE each constraint the user gives to `.code/<change>/notes.md`, and RE-READ it after each compaction.

### 2.4. Pick the mode

PICK one mode, and READ its file: [feature](modes/feature.md), [bug fix](modes/bug-fix.md), [refactor](modes/refactor.md) (behaviour stays the same, such as a migration), [tests](modes/tests.md), or [coordinate](modes/coordinate.md) WHEN the work splits into more than one task that each needs its own review, such as an epic of several tickets. LIST work of another kind as a proposed next step.

### 2.5. Write the spec and what the work needs

WHEN you write one of these, READ its template first. IF the repo uses a spec tool, such as OpenSpec, Spec Kit or Kiro, USE its files instead, and WRITE none of your own beside them.

| Write | When | Template |
|---|---|---|
| The spec | the change is more than a small fix with one obvious reading. FOR a small fix, REVISE the committed spec in place instead, IF one covers the code | [templates/specs.md](templates/specs.md) |
| A design | there is none and the change adds structure, such as a module, data model, dependency or migration | [templates/design.md](templates/design.md) |
| A task list | the work spans several sessions, people or agents | [templates/tasks.md](templates/tasks.md) |
| Proposed next steps | at hand-back | [templates/next-steps.md](templates/next-steps.md) |

## 3. Write the code

BEFORE you write code, PROTECT the checks by section 5. FOLLOW the codebase's existing patterns; SAY why where you depart from them. CHANGE only what the change needs: DO NOT add features, options, refactors or defensive code the spec does not ask for, and LIST anything else worth changing as a proposed next step. BEFORE finishing, REMOVE edits left over from approaches you abandoned.

DO the building yourself. USE sub-agents only for independent reading, such as searching a large codebase, and for review. DO NOT split building across agents by role.

## 4. Verify

RUN, in this order:

1. The existing tests the change affects.
2. One check per requirement that compares the result with the expected value; a check that only runs the code does not count. ADD it next to the existing tests, in their style, IF the project would keep it; OTHERWISE, RUN a command and RECORD the result. DO NOT add test helpers or frameworks the project does not use.
3. A smoke check that the program starts and its main path works.
4. The static, type and security checks the project already uses.

PREFER narrow checks tied to the spec over broad end-to-end suites. IF you cannot run code, HAND back with the change marked **not finished: not verified**, WHY you could not run it, and the checks still to run. DO NOT call it done, and DO NOT describe results you did not observe.

FIX failures from the latest run of the current code. STOP and REPORT what fails, what you tried and the cause you suspect WHEN the same check fails for the same reason twice in a row, WHEN about three rounds have not made all checks pass, or WHEN a fix would break a check that passed before.

WHEN a requirement changes, or the change touches code a saved spec covers, RE-RUN the checks of every requirement in that spec. IF one fails, UNDO the change that broke it, THEN do it another way or SEND the conflict up.

A requirement counts as met only IF a check you ran on the final code shows it.

## 5. Protect the checks

WHEN a check fails, CHANGE the code, not the check: DO NOT edit, skip or delete a check to make it pass, or write code for the test inputs. IF a check looks wrong, STOP, EXPLAIN why, and SEND it up.

BEFORE you write code, KEEP a copy of the checks that decide the change: one per requirement, and the existing tests the change could break. COMMIT them IF you work on a branch the user, the harness, or you with the user's permission created for this change; OTHERWISE, COPY them to `.code/<change>/checks/`. DO NOT change harness settings without the user's permission.

BEFORE you hand back, COMPARE the checks with that copy. SEND up any difference your mode does not allow, such as a removed or skipped test, a loosened assertion, or a special-cased input.

## 6. Hand back

HAVE a verifier, a sub-agent that did not build the change, review it with [agents/verifier.md](agents/verifier.md). FIX the confirmed blocking findings, THEN have a new verifier review the change again. REPEAT within the limits of section 4: STOP and REPORT WHEN the same finding comes back twice, WHEN about three rounds have not cleared the blocking findings, or WHEN a fix breaks a check that passed before. LIST the unconfirmed findings as unchecked. IF you cannot start a sub-agent, HAND back with the change marked **not finished: needs a verifier**, WHY you could not start one, and everything else the report holds. DO NOT call it done, and DO NOT review it yourself instead.

LEAD with the result, THEN report, USING `/write-better` for the wording if available:

1. What changed and why.
2. Each check you ran with its result, and each requirement with how it was checked and the result, or why it was not.
3. The decisions and assumptions of section 1, the checks you changed as your mode allows, and any conflict sent up.
4. Proposed next steps.

DISTINGUISH meeting the spec, passing the checks, and the user accepting the result. DO NOT claim one from another.

OFFER a short explanation of how the change works. IF the user wants to understand the code, ASK a question they can attempt first, THEN EXPLAIN, USING `/write-better` if available, unless they stated how much explanation they want. IF the user rejects the result, USE `/do-better` if available; OTHERWISE, CORRECT what their feedback and the spec show it misses.
