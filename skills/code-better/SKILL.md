---
name: code-better
description: Helps an AI agent build, check and review code against a design or a request, so that it builds what the user needs, keeps the change small and correct, proves each requirement with a check, and leaves the user able to trust and maintain the result without reading every line.
argument-hint: "[TASK]"
---

# Code Better

IF invoked with a task as argument, FOLLOW the instructions below for that task.
IF invoked without argument, CHECK the coding work in the current conversation against the instructions below, THEN continue or correct it.
IF asked to review code you did not write, READ [agents/verifier.md](agents/verifier.md), REVIEW the code as it says, and REPORT the findings to the user.

Being invoked does NOT mean you must write code now. The work can end with questions for the user, or with a report that the request works against the user's GOAL.

## Principles

1. Agents most often miss what the user wanted by filling a gap with a plausible assumption and not saying so. Stating every requirement does not prevent it.
2. Passing tests does not show the result is what the user needs, and agents make checks pass by changing the checks or special-casing their inputs.
3. People judge whether a result is right more accurately from concrete inputs, outcomes and checks than from prose or from the code itself.
4. Agents follow fewer requirements as more arrive at once. Only a check per requirement shows which ones the result meets.
5. Self-review without outside evidence finds few errors.
6. Sending decisions and conflicts up, asking about error handling the spec leaves open, the copy of the checks, the limits on repair loops, and the review by a verifier for every change are design choices.

## Instructions

FOLLOW these steps in order, for every change. DO NOT skip a step because the change looks small.

### 1. Understand the work

NAME the user's GOAL: what they must be able to do, decide, or understand once the code works. IF the request states a solution, CHECK that it serves the need behind it. IF it works against the GOAL, SAY so once, with one alternative, THEN FOLLOW the user's decision.

READ the code the change touches, its callers and tests, the project's instruction and contribution files, the design if there is one, and the earlier conversation. DO NOT ask the user what these sources answer. WHEN they disagree, FOLLOW the user's instructions, then the repo's own files, then the existing code's patterns, then `.code/conventions.md`, then this skill.

LIST what the result depends on that the request and these sources do not state. ASK the user about the gaps that need it, as the general rule [Ask the user](#ask-the-user) says, before you go on.

### 2. Pick the mode

PICK the one mode that fits the work. READ its file: it is MANDATORY, and the next step cannot run without it. LIST any part of the work that needs another mode as a proposed next step.

| Mode | When | File |
|---|---|---|
| Feature | the change adds or changes behaviour | [modes/feature.md](modes/feature.md) |
| Bug fix | existing behaviour is defective | [modes/bug-fix.md](modes/bug-fix.md) |
| Refactor | the structure, a dependency or the data format changes and behaviour stays the same | [modes/refactor.md](modes/refactor.md) |
| Tests | you add or improve tests for existing code, without changing the code under test | [modes/tests.md](modes/tests.md) |
| Coordinate | the work splits into several tasks that each need their own review | [modes/coordinate.md](modes/coordinate.md) |

### 3. Run the mode

FOLLOW every step of the mode's file, in order. The mode ends once its checks pass on the final code, or once you stop as its limits say.

### 4. Verify with a verifier agent and fix

START a verifier for every change: READ [agents/verifier.md](agents/verifier.md), FILL IN its Input, and GIVE the whole file, without its HOW TO USE block, to a new sub-agent as its prompt.

WAIT until the verifier hands back its report. DO NOT write to the user while it runs.

FIX each confirmed blocking finding, RUN the checks of the mode's last step again, THEN START a new verifier on the fixed change. DO this at most twice. STOP and REPORT the open findings WHEN the same finding comes back, or WHEN the second fix does not clear them. LIST the unconfirmed findings as unchecked.

### 5. Hand back

LEAD with the result, THEN report, USING `/write-better` for the wording if available:

1. What changed and why.
2. Each requirement, the check that shows it and its result, or why it was not checked.
3. The assumptions you made, the decisions and conflicts you asked the user about, and each check you changed with what in your mode allows it.
4. The verifier's result, as its report states it: pass, or its open findings.
5. Proposed next steps: work outside the change worth doing. READ [templates/next-steps.md](templates/next-steps.md) and WRITE them in its format. IF there are none, SAY so.

DISTINGUISH meeting the spec, passing the checks, and the user accepting the result. DO NOT claim one from another.

OFFER a short explanation of how the change works. IF the user wants to understand the code, ASK a question they can attempt first, THEN EXPLAIN. IF the user rejects the result, USE `/do-better` if available; OTHERWISE, CORRECT what their feedback and the spec show it misses.

## General rules

FOLLOW these rules in every step and every mode.

### Ask the user

ASK the user, USING `/ask-better` if available, in these cases:

- **Gaps.** DECIDE yourself a gap only someone reading the code would notice. ASK about a gap the user would notice that is costly to get wrong: what is stored, what someone is charged or paid, what users are told, and how an invalid input or a failure is handled. PUT all of them in one message, each with concrete inputs and the outcome of each option. FOR every other gap, CHOOSE the most plausible option and STATE it as an assumption in the hand-back.
- **Decisions.** ASK about a decision that changes behaviour, cost, risk or how the code is maintained, and anything that contradicts a decision the design records, with your recommendation, its main reason and its main drawback. USE `/decide-better` if available. IF the user does not read code, DESCRIBE each option by what they would observe or pay.
- **Conflicts.** ASK about a test that contradicts a requirement, two requirements that conflict, and a requirement that cannot or should not hold as written, with the change you propose and what the user would see differently. DO NOT build to your own version until it is agreed. ONCE agreed, REVISE the requirement in place.

TREAT a constraint the user set as a requirement. ADD each answer to the spec; your own proposals are not answers. KEEP building the parts your questions do not affect.

### Working notes

KEEP your working files in `.code/<change>/`, and ADD `.code/` to `.git/info/exclude`. KEEP `.code/conventions.md` as a short list of facts about the repo, each with its source. WHEN the work spans several sessions, people or agents, WRITE a task list in `.code/<change>/tasks.md`: READ [templates/tasks.md](templates/tasks.md), WRITE it in its format, and KEEP it current. IN a session the harness may compact, WRITE each constraint the user gives to `.code/<change>/notes.md`, and READ it again after each compaction.

### Missing capabilities

IF you cannot do a step, because a call was denied or the harness lacks a tool, MARK the change **not finished**, and SAY which step, WHY, and what it leaves unchecked. DO NOT present that step as done, and DO NOT replace it with a step of your own.
