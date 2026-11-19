---
name: bug-fix
description: Use for a defect in existing behaviour.
---

# Mode: bug fix

BEFORE you change the code, WRITE a check that reproduces the defect with the input that triggers it and FAILS on the current code. IF you cannot make it fail, STOP and REPORT what you tried: the defect is not understood yet.

KEEP the spec to the behaviour the fix restores, usually one or two requirements in the hand-back. IF the defect shows a requirement the design missed, SEND that gap up, and ADD it to a saved spec only once the user accepts it.

FIX the cause, not the symptom the check shows, and RUN the checks of the behaviour around it.

IF an existing test asserts the defective behaviour, DO NOT change it yourself: SEND it up with the defect, since someone may rely on that behaviour.
