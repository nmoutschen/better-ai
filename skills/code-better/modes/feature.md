---
name: feature
description: Use for a new or changed behaviour.
---

# Mode: feature

FOLLOW these steps in order. The general rules of SKILL.md apply throughout. AFTER every write to a JSON or JSONL file in `.code/`, or to the architect folder's `spec.jsonl`, RUN `python3 <skill dir>/scripts/schema.py check <file>` and FIX every error before your next step.

## 1. Update the spec

KEEP a spec for every change, however small: a one-line change needs one requirement. WRITE `.code/<change>/code.json`: the goal, the design and the mode. READ [../templates/spec.md](../templates/spec.md) and WRITE `.code/<change>/spec.jsonl` in the template's format, always: from the existing spec when one covers the change. WRITE the requirements of this change in the spec. IF the repo keeps specs in a spec tool, such as OpenSpec, Spec Kit or Kiro, UPDATE its files from it. WHEN `code.json` names an architect folder as the design, its `spec.jsonl` is the spec: UPDATE it there and WRITE no copy.

WHEN the work spans several sessions, people or agents, ALSO WRITE `.code/<change>/tasks.jsonl` now: READ [../templates/tasks.md](../templates/tasks.md) and WRITE it in its format, with every task `todo`.

## 2. Write the checks

WRITE one check per requirement. A check compares the result with an expected value: a check that only runs the code does not count. IF the project would keep the check, ADD it as a test next to the existing tests, in their style. OTHERWISE, WRITE it as a command and RECORD it as the `checked_by` of its requirement. DO NOT add test helpers or frameworks the project does not use.

RUN the checks on the current code and RECORD each result. A check for new or changed behaviour FAILS, for the reason its requirement gives. A check for behaviour that stays the same PASSES. IF a result differs, the check or your understanding is wrong: FIX that before step 3.

KEEP a copy of these checks and of the existing tests the change could break: COMMIT them IF you work on a branch created for this change; OTHERWISE, COPY them to `.code/<change>/checks/`.

From now on, WHEN a check fails, CHANGE the code, not the check. DO NOT edit, skip or delete a check, or write code for its inputs. This mode allows one change to an existing check: WHEN a requirement from the user's request or the design changes an expected value, UPDATE the check to it, and LIST it in the hand-back with the old and the new value. A requirement you assumed never justifies it. IF a check looks wrong for any other reason, STOP and ASK the user.

## 3. Write the code

WRITE the code that meets the spec. FOLLOW the codebase's existing patterns, and SAY why where you depart from them. CHANGE only what the spec needs, and LIST anything else worth changing as a proposed next step. DO the building yourself; USE sub-agents only to read, such as searching a large codebase. REMOVE edits left over from approaches you abandoned.

## 4. Test the change

RUN, on the final code:

1. The existing tests the change affects.
2. The check of every requirement in the spec, and of every earlier spec in `.code/` that covers the code you changed.
3. A smoke check that the program starts and its main path works.
4. The static, type, lint and security checks the project uses.

COMPARE the checks with the copy of step 2. ASK the user about any difference this mode does not allow.

FIX each failure in the code, THEN RUN the checks again. STOP and REPORT what fails, what you tried and the cause you suspect WHEN the same check fails twice for the same reason, WHEN three rounds have not made all checks pass, or WHEN a fix breaks a check that passed before.

DO NOT describe results you did not observe. A requirement is met only IF its check passed on the final code.

IF there is a task list, SET the `status` of each task whose check you saw pass to `done` in `tasks.jsonl`, in an edit of its own.
