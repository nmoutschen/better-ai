---
name: design
description: Use for a new interface, or a change to which screens exist, what they hold, their layout or their flow.
---

# Mode: design

FOLLOW these steps in order. The general rules of SKILL.md apply throughout.

You design; `/code-better` builds. Two loops run: `/code-better`'s inner loop builds the design and checks the code against its requirements, and this mode's outer loop accepts the result only once a reviewer has walked every scenario in the built interface. Showing directions before building, one review of the chosen direction instead of one per round, the design document, small visual batches, and the limits on the acceptance loop are design choices.

## 1. Show directions before anything is built

SKIP this step and step 4 WHEN the change keeps the existing structure and the brief leaves one reasonable direction: FOLLOW the existing interface's patterns instead.

IF the user already chose a direction, in the request or in the brief, RECORD it in the brief and GO to item 6 below, unless the brief records its review as settled: THEN GO ON at step 2 and SKIP step 4. A request to build the direction does not settle its review.

1. ASK whether the user has a direction or references in mind, and show none of yours yet: seeing examples first narrows what people consider. PREFER pictures and examples of interfaces they like and dislike over adjectives. WAIT for the answer, unless the request already gives it or says the user has none.
2. MAKE two or three rough directions that differ in a way the user can see: the structure, the order of content, or what is prominent. DO NOT vary only a colour or a font. USE the same real content in each. KEEP them rough: real structure and content, little styling, because polish changes how people rate a version and a rough one reveals largely the same problems.
3. SHOW them by the general rule [Show versions on one page](../SKILL.md#show-versions-on-one-page).
4. ASK which direction serves each scenario best and what is wrong with each one. DO NOT ask the user to design the fix: people find problems far more reliably than solutions. TREAT what the user picks about the look as their preference, not as evidence that the AUDIENCE can use it.
5. WAIT for the user's decision. RECORD the chosen direction in the brief.
6. START a reviewer on the chosen direction, because the user may choose a direction that people cannot use: READ [../agents/reviewer.md](../agents/reviewer.md), FILL IN its Input with the direction's files, the brief and the user's decisions, and START it as its HOW TO USE block says, in the background. DO NOT wait for it: GO ON with steps 2 and 3 while it runs. DO NOT start a reviewer on the directions of earlier rounds.

## 2. Decide the cases the design leaves out

WALK each scenario step by step in the chosen direction. AT each step, ASK what can go wrong or differ: no data yet, a lot of data, very long text, a slow or failed response, invalid input, no permission, the person going back or repeating the step, a small screen. THEN CHECK each screen against the states empty, loading, error, partial, full and success.

FOR each case, DECIDE what the interface shows. IF a case changes what happens to the person's data or work, ASK the user, as the general rule [Ask the user](../SKILL.md#ask-the-user) says, or STATE it as an assumption.

## 3. Write the design

READ [../templates/design.md](../templates/design.md). WRITE `.design/<slug>/design.md` in its format:

- The chosen direction, and the files that show it.
- Each screen, what it holds, and its states from step 2.
- The design language values and components to use. IF a screen needs one the design language lacks, PROPOSE it to the user, as [language.md](language.md) step 7 says.
- The requirements `/code-better` builds against: ONE per scenario, stated as the walk from its start to the end the person observes, with its concrete data; and the requirements from the [Design rules](../SKILL.md#design-rules) that only the code can meet, such as labels tied to their fields, native controls with names, keyboard order and visible focus, and the page's language.

## 4. Settle the review of the direction

WAIT for the reviewer of step 1.6. REPRODUCE each finding in the direction's files. IF no finding is confirmed and step 2 left no open question, GO ON without asking. SHOW the user each confirmed finding, with the scenario step where a person is stopped and the fix you propose, together with any open question of step 2, by [Show versions on one page](../SKILL.md#show-versions-on-one-page) WHEN the page is still served. The user decides which fixes to apply: the direction is theirs. WAIT for their answer before step 5, even when the request said to build, and DO NOT apply a fix they have not accepted. APPLY the fixes they accept to the design, and LIST the findings they accept as they are under its Assumptions.

IF the user's answer changes the structure or the flow of the direction, START a new reviewer on it as step 1.6 says, and SETTLE its report the same way. OTHERWISE, GO ON.

## 5. Build with /code-better

USE `/code-better` to build the design, GIVING it `.design/<slug>/design.md` as its design and requirements. IF it is not available, BUILD only what the design needs, REUSE the project's components and patterns, and RUN the project's existing checks.

WHEN the change alters how an existing interface looks, BUILD a few visual changes at a time, and SHOW each batch before and after by [Show versions on one page](../SKILL.md#show-versions-on-one-page): when many changes land at once, nobody can tell which one helped and which one did harm.

WAIT until the build is finished and its checks pass.

## 6. Accept: have a reviewer walk every scenario

The build and each fix are accepted only once a reviewer started after them walked every scenario. DO NOT walk the interface yourself instead, because you know what you meant it to do, and DO NOT hand back a change that no reviewer walked.

1. START a reviewer: READ [../agents/reviewer.md](../agents/reviewer.md), FILL IN its Input with the built interface, the brief and the user's decisions, and START it as its HOW TO USE block says.
2. WAIT until the reviewer hands back its report. DO NOT write to the user while it runs.
3. REPRODUCE each finding in the rendered interface. IF the reviewer walked every scenario with the pointer and the keyboard and no confirmed finding stops or slows a scenario, the build is accepted: LIST the other confirmed findings as open, and GO ON to SKILL.md step 6. IF the reviewer could not operate the interface, or left a walk undone for a reason other than a finding, FOLLOW the general rule [Missing capabilities](../SKILL.md#missing-capabilities) instead of starting another round.
4. FIX each confirmed finding that stops or slows a scenario, and each error an automated checker reported: USE `/code-better`, GIVING it the finding as a defect against the design's requirement; IF it is not available, FIX it in the code and RUN the project's checks.
5. GO BACK to 1. The new reviewer walks ALL scenarios again, not only the one that failed: fixing one problem in an interface often creates another.

STOP and REPORT the open findings WHEN:

1. The same finding comes back after two fixes.
2. Three rounds have not made every scenario pass.
3. A fix breaks a scenario that passed before.

WHEN a limit stops the loop, CHANGE nothing more: REPORT the findings still open instead of fixing them, because a fix that no reviewer walked is unchecked.

DO NOT change a scenario or drop a requirement so that the walk passes. IF a scenario looks wrong, STOP, EXPLAIN why, and ASK the user.
