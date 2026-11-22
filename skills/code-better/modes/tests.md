---
name: tests
description: Use to add or improve tests for existing code, without changing the code under test.
---

# Mode: tests

FOLLOW these steps in order. The general rules of SKILL.md apply throughout.

## 1. Update the spec

KEEP a spec for every change, however small: a one-line change needs one requirement. MAKE the change folder with `python3 <skill dir>/scripts/better.pyz create .code/<change> --by <your agent name, such as builder>`, with the goal, the design and the mode as JSON on stdin. READ [../templates/spec.md](../templates/spec.md) and ADD each requirement to `spec.jsonl` in the template's format, always: from the existing spec when one covers the change. WRITE the behaviour the tests must cover in the spec. TAKE each expected value from the spec, the design or the documented behaviour, never from what the code does. IF the repo keeps specs in a spec tool, such as OpenSpec, Spec Kit or Kiro, UPDATE its files from it. WHEN the design is an architect folder, the change's spec is the copy of its `spec.jsonl` in the change folder: EDIT it there.

WHEN the work spans several sessions, people or agents, ALSO ADD the tasks to `.code/<change>/tasks.jsonl` now: READ [../templates/tasks.md](../templates/tasks.md) and WRITE them in its format, with every task `todo`.

## 2. Protect the existing tests

KEEP a copy of the existing tests: COMMIT them IF you work on a branch created for this change; OTHERWISE, COPY them to `.code/<change>/checks/`.

This mode allows a change to an existing test only to make it check more, such as a stronger assertion or a new case. DO NOT remove, skip or loosen one. LIST each change in the hand-back.

## 3. Write the tests

WRITE one test per requirement, next to the existing tests, in their style. EACH test ASSERTS an expected value. DO NOT add test helpers or frameworks the project does not use.

DO NOT change the code under test. LIST the changes it needs as proposed next steps.

## 4. Run the tests

RUN the new and the existing tests on the current code. A new test PASSES. IF one fails because the code disagrees with its expected value, DO NOT change the test to match the code: ASK the user about the disagreement as a possible defect.

COMPARE the existing tests with the copy of step 2. ASK the user about any change this mode does not allow.

FIX each test that fails for a reason of its own, THEN RUN the tests again. STOP and REPORT what fails, what you tried and the cause you suspect WHEN the same test fails twice for the same reason, or WHEN three rounds have not made the tests pass.

DO NOT describe results you did not observe.

IF there is a task list, SET the `status` of each task whose check you saw pass to `done` in `tasks.jsonl`, in an edit of its own.
