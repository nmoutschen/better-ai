---
name: refactor
description: Use for a change of structure, dependency or data format that keeps behaviour, such as a refactor, a dependency upgrade or a data migration.
---

# Mode: refactor or migration

FOLLOW these steps in order. The general rules of SKILL.md apply throughout.

## 1. Update the spec

WRITE the spec in `.code/<change>/specs.md`. READ [../templates/specs.md](../templates/specs.md) and WRITE it in its format. Its requirement is that observable behaviour stays the same: LIST the paths the change touches, and for a data migration, the data it moves. IF the repo keeps specs in a spec tool, such as OpenSpec, Spec Kit or Kiro, UPDATE its files instead and WRITE no `specs.md`.

IF the design says some behaviour changes, that part is not this change: LIST it as a proposed next step, or, under a coordinator, as its own task.

FOR a data migration, IF the design does not say what happens to records the old format allows and the new one does not, ASK the user.

WHEN the work spans several sessions, people or agents, ALSO WRITE `.code/<change>/tasks.md` now: READ [../templates/tasks.md](../templates/tasks.md) and WRITE it in its format, with every task todo.

## 2. Pin the current behaviour

PIN the behaviour of every path in the spec with checks: the existing tests, plus checks you add where a path has none. Each check compares the result with an expected value. FOR a data migration, ALSO PIN the record counts and a sample of records.

RUN the checks on the current code: they PASS, and you RECORD the results.

KEEP a copy of these checks: COMMIT them IF you work on a branch created for this change; OTHERWISE, COPY them to `.code/<change>/checks/`.

From now on, WHEN a check fails, CHANGE the code, not the check. DO NOT edit, skip or delete a check, or write code for its inputs. This mode allows no change to an existing check. IF a check looks wrong, STOP and ASK the user.

## 3. Refactor the code

CHANGE the structure, dependency or data format. FOLLOW the codebase's existing patterns, and SAY why where you depart from them. CHANGE no behaviour, and LIST anything else worth changing as a proposed next step. DO the work yourself; USE sub-agents only to read. REMOVE edits left over from approaches you abandoned.

## 4. Test the refactor

RUN, on the final code:

1. The checks of step 2. Any difference from the recorded results is a defect of the change.
2. FOR a data migration, the record counts, the same sample of records, and the records the old format allows and the new one does not.
3. A smoke check that the program starts and its main path works.
4. The static, type, lint and security checks the project uses.

COMPARE the checks with the copy of step 2. ASK the user about any difference.

FIX each failure in the code, THEN RUN the checks again. STOP and REPORT what fails, what you tried and the cause you suspect WHEN the same check fails twice for the same reason, WHEN three rounds have not made all checks pass, or WHEN a fix breaks a check that passed before.

DO NOT describe results you did not observe. Behaviour is kept only IF every check of step 2 gave its recorded result on the final code.

IF there is a task list, SET each task whose check you saw pass to done, in an edit of its own.
