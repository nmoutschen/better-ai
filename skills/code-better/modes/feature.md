---
name: feature
description: Use for a new or changed behaviour.
---

# Mode: feature

WRITE the checks for the requirements before the code. A check for new or changed behaviour FAILS on the current code, for the reason its requirement gives, and passes after the change. A check for behaviour that must stay the same passes both times.

WHEN a requirement whose source is the user's request or the design changes an expected value, such as a new rounding rule, UPDATE the existing check to the requirement, and LIST it in the hand-back with the old and the new value. This is the only change to an existing check this mode allows. A requirement you assumed never justifies it: SEND the conflict up instead.
