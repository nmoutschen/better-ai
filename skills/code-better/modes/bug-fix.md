---
name: bug-fix
description: Use for a defect in existing behaviour.
---

# Mode: bug fix

FOLLOW these steps in order. The general rules of SKILL.md apply throughout.

## 1. Update the spec

WRITE the behaviour the fix restores in `.code/<change>/specs.md`, usually one or two requirements. READ [../templates/specs.md](../templates/specs.md) and WRITE the spec in its format. IF the file exists from earlier work on this change, UPDATE it in place. IF the repo keeps specs in a spec tool, such as OpenSpec, Spec Kit or Kiro, UPDATE its files instead and WRITE no `specs.md`.

## 2. Reproduce the defect

WRITE a check that reproduces the defect with the input that triggers it, and compares the result with the expected value. IF the project would keep the check, ADD it as a test next to the existing tests, in their style. OTHERWISE, WRITE it as a command and RECORD it in the spec.

RUN it on the current code: it FAILS, and you RECORD the result. IF you cannot make it fail, STOP and REPORT what you tried: the defect is not understood yet.

KEEP a copy of this check and of the existing tests the fix could break: COMMIT them IF you work on a branch created for this change; OTHERWISE, COPY them to `.code/<change>/checks/`.

From now on, WHEN a check fails, CHANGE the code, not the check. DO NOT edit, skip or delete a check, or write code for its inputs. This mode allows no change to an existing check. IF an existing test asserts the defective behaviour, ASK the user about it with the defect: someone may rely on that behaviour.

## 3. Fix the cause

FIX the cause, not the symptom the check shows. FOLLOW the codebase's existing patterns, and SAY why where you depart from them. CHANGE only what the fix needs, and LIST anything else worth changing as a proposed next step. DO the fixing yourself; USE sub-agents only to read. REMOVE edits left over from approaches you abandoned.

## 4. Test the fix

RUN, on the final code:

1. The check of step 2.
2. The existing tests of the behaviour around the fix.
3. The check of every earlier spec in `.code/` that covers the code you changed.
4. A smoke check that the program starts and its main path works.
5. The static, type, lint and security checks the project uses.

COMPARE the checks with the copy of step 2. ASK the user about any difference.

FIX each failure in the code, THEN RUN the checks again. STOP and REPORT what fails, what you tried and the cause you suspect WHEN the same check fails twice for the same reason, WHEN three rounds have not made all checks pass, or WHEN a fix breaks a check that passed before.

IF you cannot run code, STOP with the fix marked **not finished: not verified**, WHY, and the checks still to run. DO NOT describe results you did not observe. The defect is fixed only IF the check of step 2 passed on the final code.
