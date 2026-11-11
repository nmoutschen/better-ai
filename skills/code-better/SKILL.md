---
name: code-better
description: Helps an AI agent write, check and review code so that it builds what the user needs, keeps the change small and correct, and leaves the user able to understand and maintain the result.
argument-hint: "[TASK]"
---

# Code Better

IF invoked with a task as argument, USE these instructions to do that task.
IF invoked without argument, USE these instructions on the coding work in the current conversation: CHECK the work done so far against sections 1, 5 and 6, THEN continue or correct it.
IF the code to check is someone else's, such as a diff or a pull request, USE section 6.

Being invoked does NOT mean you must write code now. These instructions can end with requirements and questions for the user, or with a report that the request works against the user's GOAL.

## Principles

1. Agents most often miss what the user wanted by filling a gap in the request with a plausible assumption and not saying so. Stating every requirement does not prevent it.
2. Passing tests does not show the result is what the user needs. Maintainers would reject many patches that pass their tests.
3. People judge whether a result is right more accurately from concrete scenarios, examples and tests than from prose or from the code itself.
4. Requirements, design and plan are different artifacts. Requirements align on intent and the user checks them. A design aligns on shared understanding and structure. A plan orders the work. They change each other: design work reveals missing requirements.
5. Agents edit more than the task needs, and agent code erodes in structure as it grows while still passing tests. A plain instruction to preserve existing code reduced over-editing. Requests for quality did not stop erosion.
6. Repair loops gain most in the first few rounds. Test results help more than compiler errors, and a weak critique can hurt more than a bare failure. Extra rounds can break code that was already correct, and repeated failure feedback leads agents to game tests.
7. Self-review without outside evidence finds few errors. A reviewer that sees only the result in a fresh context does better. LLM judgements of whether code meets its requirements are unreliable.
8. Delegating work to sub-agents usually costs more, and details of a plan get lost when it is handed to another agent. Teams of agents do not reliably beat a single agent.
9. Developers who let AI write code they do not engage with understand it less. Asking for explanations or conceptual answers preserved understanding.
10. The stopping rules for repair loops (section 5.2), the checks at checkpoints of long runs (section 8.3), and showing the design before building (section 2) are design choices.

This skill names capabilities, not tools: reading files, running commands and tests, asking the user, writing files, and sub-agents. FOR each capability you lack, FOLLOW the fallback the section gives.

## 1. Requirements: build the right thing

### 1.1. Name the GOAL and the need

NAME the user's GOAL: what they must be able to do, decide, or understand once the code works. DISTINGUISH it from the requested change.

IF the request states a solution, such as "add a cache" or "use a queue", NAME the need behind it. CHECK whether the solution serves that need. Agents follow a flawed proposed solution far more often than they serve the intended need. IF the solution works against the GOAL, SAY so once, with the evidence and one alternative, THEN FOLLOW the user's decision.

### 1.2. Read before deciding anything

READ the code the change touches, its callers and tests, the project's instruction and contribution files, and earlier conversation. Agents rarely look up a repository's rules unless reminded. DO NOT ask the user what these sources answer.

### 1.3. Sort each gap: requirement or design

LIST what the result depends on and is not stated. FOR each gap, DECIDE whether it is:

1. **A requirement gap**: behaviour the user can observe without reading the code, such as inputs, outputs, formats, errors, limits, permissions, or what happens to existing data.
2. **A design gap**: something only a person reading or changing the code would notice, such as module structure, internal names, or algorithms.

IF the user's request fixes part of the design, such as "use Postgres" or "add no dependency", TREAT it as a requirement: the user owns it.

DECIDE design gaps yourself from the codebase (section 2). CHECK requirement gaps with the user (section 1.5) or state them as assumptions.

### 1.4. Write the requirements as scenarios

IF the change is more than a small fix with one obvious reading, THEN WRITE the requirements with [templates/requirements.md](templates/requirements.md): the need, what changes for the user, scenarios with concrete inputs and expected results, constraints, what is out of scope, and assumptions.

WRITE each scenario in a structured form, such as Given/When/Then (Gherkin) or EARS ("When <trigger>, the <system> shall <response>"), with concrete data. WRITE it so the user can check it without reading code. INCLUDE the error and edge cases that the request leaves open, because that is where silent assumptions hide. KEEP the requirements short: a scenario earns its place only if a wrong guess on it would change what you build.

IF you cannot write files, PUT the requirements in your reply.

### 1.5. Check the requirements with the user

USE `/ask-better` if available. OTHERWISE, ASK only about requirement gaps that only the user can answer, that change what you build, and that are costly to get wrong. ASK all such questions at once, before building.

SHOW the scenarios the gap affects, with concrete inputs and outputs, and ASK the user to confirm or correct each one. DO NOT ask the user to review prose requirements or code instead.

FOR every other gap, CHOOSE the most plausible option, PROCEED, and STATE the assumption next to the result it affects.

KEEP the requirements as the reference for the whole task. ADD each later answer or correction to them. DO NOT treat your own proposals as requirements the user accepted.

## 2. Design: shared understanding and structure

IF the change adds or changes structure, such as a new module, data model, interface, dependency, or migration, THEN WRITE a design with [templates/design.md](templates/design.md). SHOW only the C4 levels the change touches and the main flows it adds or changes. OTHERWISE, KEEP the design to a few lines in your report.

FOLLOW the existing patterns, conventions and dependencies of the codebase. IF you must depart from them, SAY why.

NAME the design decisions that change behaviour, cost, risk, or how the code must be maintained, such as a new dependency, a schema change, or a trade-off between speed and simplicity. IF the user is a developer who will maintain the code, SHOW them these decisions before building. OTHERWISE, REPORT them with the result.

IF design work reveals a requirement gap, such as what happens when a step fails halfway, RETURN to section 1.3 for that gap. DO NOT decide it silently in the design.

## 3. Plan: only for long or shared work

IF the work spans several sessions, several agents, or more steps than fit in one context, THEN WRITE a plan with [templates/plan.md](templates/plan.md). A plan orders the work and records progress. It does not replace the requirements or the design.

KEEP one task per step, each with a check that shows it is done. MARK a task done only after its check passes.

## 4. Write the code

### 4.1. Change only what the task needs

PRESERVE existing code that the task does not require you to change. DO NOT add features, options, refactors, or defensive code the requirements do not ask for. IF you see something else worth changing, LIST it in your report instead of changing it.

KEEP each change to one purpose. Maintainers ask for small, focused changes, and large mixed changes are rejected more often.

BEFORE finishing, REMOVE edits left over from approaches you tried and abandoned.

### 4.2. Decide error handling on purpose

HANDLE invalid input and failures as the requirements' scenarios say. IF they do not say, TREAT it as a requirement gap (section 1.3). Differences in input validation and error handling explained why agent code was harder to build on. TREAT this as a guide, not a rule.

## 5. Verify

### 5.1. Choose checks that test the requirements

RUN, in this order:

1. The existing tests that the change affects. FIND them from the code you changed, not by running a generic test-first procedure.
2. A check for each scenario in the requirements. IF the project would keep the test, THEN ADD it next to the existing tests, in their style. OTHERWISE, RUN a command or the program and record the result. DO NOT add test helpers, fixtures or frameworks the project does not already use.
3. A smoke check that the program starts and its main path works.
4. Static analysis, type checks and security checks that the project already uses.

PREFER narrow checks tied to the requirements over broad generic end-to-end suites, which often reject working code.

IF you cannot run code, SAY so. DO NOT describe results you did not observe. LIST the checks the user should run.

### 5.2. Bound the repair loop

FIX failures with the evidence from the latest run of the current code. DO NOT act on output from an earlier version of the code.

STOP repairing and REPORT when:

1. The same check fails for the same reason twice in a row.
2. About three rounds of fixes have not made all checks pass.
3. A fix would break a check that passed before.

IN the report, STATE what fails, what you tried, and what you think the cause is.

### 5.3. Never weaken the checks

DO NOT edit, skip, or delete tests or checks to make them pass. DO NOT special-case test inputs. IF a check looks wrong, or the task cannot be done as stated, STOP, EXPLAIN why, and ASK the user.

### 5.4. Check the result against the requirements

COMPARE the finished behaviour with each scenario in the requirements, using the results of section 5.1. A scenario counts as met only if a check you ran shows it. DO NOT rely on your own reading of the code as proof that it meets the requirements.

## 6. Review

### 6.1. Review in a fresh context

IF you can start a sub-agent, GIVE a fresh reviewer only the diff, the requirements, and access to the code. DO NOT give it your reasoning or your conversation with the user. A cheaper model can review, but it must not share your context.

OTHERWISE, REVIEW in a separate pass after verification: RE-READ the requirements first, THEN read the diff as if someone else wrote it.

### 6.2. Look for defects that matter

LOOK first for wrong behaviour against the requirements, broken callers, security problems, data loss, and missing error handling. LOOK for style only where the project's rules require it. AI reviewers comment on style far more than human reviewers do, and on correctness and security far less.

READ beyond the diff: callers, configuration, and tests. Most missed defects need context the diff does not show.

### 6.3. Confirm each finding with evidence

FOR each finding, FIND evidence: a failing test, a reproduction, or the exact lines and input that cause it. DROP a finding only when you can show it is wrong. DO NOT drop a finding only because you could not confirm it: REPORT it as unconfirmed.

### 6.4. Report few, specific findings

REPORT each finding with its location, the input or situation that triggers it, the effect, and a suggested fix as code. ORDER findings by effect on the user. DO NOT pad the report with minor style comments.

## 7. Hand back

### 7.1. Report what was done and checked

USE `/write-better` if available. OTHERWISE, lead with the result, THEN report:

1. What changed and why, in terms of the requirements.
2. The design decisions from section 2 and the assumptions from section 1.5.
3. Each check you ran and its result, and each requirement scenario you could not check.
4. Anything you listed instead of changing (section 4.1).

DISTINGUISH meeting the requirements, passing the checks, and the user accepting the result. DO NOT claim one from another.

### 7.2. Leave the user able to maintain the code

OFFER a short explanation of how the change works and why it is built this way. IF the user wants to understand the code, THEN USE `/write-better` for the explanation if available. OTHERWISE, ASK a question about the change that the user can attempt first, THEN EXPLAIN the reasoning.

IF the user has stated how much explanation they want, FOLLOW that instead of this section.

IF the user rejects the result, USE `/do-better` if available.

## 8. Sub-agents and long runs

### 8.1. Default to one agent

DO the building yourself. USE sub-agents for independent reading, such as searching a large codebase, and for review (section 6.1). DO NOT split building across agents by role, such as planner, coder and tester, unless the work does not fit in one context.

### 8.2. Hand over the full requirements

WHEN you hand work to another agent or session, GIVE it the requirements, the design, and your raw notes on what you tried and found. DO NOT give only a summary: details get lost at handoffs.

### 8.3. Keep long runs on track

FOR work that spans several sessions, KEEP the plan file current, COMMIT a working state after each task, and BEGIN each session by reading the requirements, the design, and the plan.

AT each checkpoint, RE-CHECK the result against the requirements' scenarios and REVIEW the structure for growing duplication or complexity. Agent code erodes over long runs while its tests keep passing.
