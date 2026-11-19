---
name: tests
description: Use to add or improve tests for existing code, without changing the code under test.
---

# Mode: tests

FOLLOW these steps in order. The general rules of SKILL.md apply throughout.

## 1. Update the spec

WRITE the behaviour the tests must cover in `.code/<change>/specs.md`. READ [../templates/specs.md](../templates/specs.md) and WRITE it in its format. TAKE each expected value from the spec, the design or the documented behaviour, never from what the code does. IF the repo keeps specs in a spec tool, such as OpenSpec, Spec Kit or Kiro, UPDATE its files instead and WRITE no `specs.md`.

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

IF you cannot run code, STOP with the tests marked **not finished: not verified**, WHY, and the tests still to run. DO NOT describe results you did not observe.
