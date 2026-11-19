---
name: tests
description: Use to add or improve tests for existing code, without changing the code under test.
---

# Mode: tests

TAKE the expected values from the spec, the design, or the documented behaviour. IF the code disagrees with them, DO NOT write the test to match the code: SEND the disagreement up as a possible defect.

DO NOT change the code under test in this mode. LIST the changes it needs as proposed next steps.

EACH test ASSERTS an expected value. A new test PASSES on the current code, unless it shows a possible defect, which you SEND up.

KEEP a copy of the existing tests before you change them (section 5 of SKILL.md). This mode allows a change to an existing test only to make it check more, such as a stronger assertion or a new case; LIST each one in the hand-back. Removing, skipping or loosening one is never allowed.
