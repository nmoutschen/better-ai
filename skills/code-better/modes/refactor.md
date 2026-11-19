---
name: refactor
description: Use for a change of structure or platform that keeps behaviour, such as a refactor, a dependency upgrade or a data migration.
---

# Mode: refactor or migration

The requirement is that observable behaviour stays the same. BEFORE you change the code, PIN the current behaviour with checks on the paths the change touches, from the existing tests plus checks you add where those paths have none. RUN them on the current code: they PASS, and you RECORD the results. This mode allows no change to an existing check.

AFTER the change, RUN the same checks. Any difference is a defect of the change. IF the design says that behaviour changes, that part is not this change: LIST it as a proposed next step, or, under a coordinator, its own task.

FOR a data migration, ALSO CHECK the data: counts, a sample of records before and after, and what happens to records the old format allowed and the new one does not. SEND the last up as a gap if the design does not say (section 1.2 of SKILL.md).
