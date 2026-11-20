---
name: design
description: Use for a new interface, or a change to which screens exist, what they hold, their layout or their flow.
---

# Mode: design

FOLLOW these steps in order. The general rules of SKILL.md apply throughout.

You design; `/code-better` builds. Two loops run: `/code-better`'s inner loop builds the design and checks the code against its requirements, and this mode's outer loop accepts the result only once a reviewer has walked every scenario in the built interface. Showing directions before building, the design document, small visual batches, and the limits on the acceptance loop are design choices.

## 1. Show directions before anything is built

SKIP this step WHEN the change keeps the existing structure and the brief leaves one reasonable direction: FOLLOW the existing interface's patterns instead.

1. ASK whether the user has a direction or references in mind, and show none of yours yet: seeing examples first narrows what people consider. PREFER pictures and examples of interfaces they like and dislike over adjectives. WAIT for the answer, unless the request already gives it or says the user has none.
2. MAKE two or three rough directions that differ in a way the user can see: the structure, the order of content, or what is prominent. DO NOT vary only a colour or a font. USE the same real content in each. KEEP them rough: real structure and content, little styling, because polish changes how people rate a version and a rough one reveals largely the same problems.
3. SHOW them by the general rule [Show versions on one page](../SKILL.md#show-versions-on-one-page).
4. ASK which direction serves each scenario best and what is wrong with each one. DO NOT ask the user to design the fix: people find problems far more reliably than solutions. TREAT what the user picks about the look as their preference, not as evidence that the AUDIENCE can use it.
5. WAIT for the user's decision. RECORD the chosen direction in the brief.

## 2. Decide the cases the design leaves out

WALK each scenario step by step in the chosen direction. AT each step, ASK what can go wrong or differ: no data yet, a lot of data, very long text, a slow or failed response, invalid input, no permission, the person going back or repeating the step, a small screen. THEN CHECK each screen against the states empty, loading, error, partial, full and success.

FOR each case, DECIDE what the interface shows. IF a case changes what happens to the person's data or work, ASK the user, as the general rule [Ask the user](../SKILL.md#ask-the-user) says, or STATE it as an assumption.

## 3. Write the design

READ [../templates/design.md](../templates/design.md). WRITE `.design/<slug>/design.md` in its format:

- The chosen direction, and the files that show it.
- Each screen, what it holds, and its states from step 2.
- The design language values and components to use. IF a screen needs one the design language lacks, PROPOSE it to the user, as [language.md](language.md) step 7 says.
- The requirements `/code-better` builds against: ONE per scenario, stated as the walk from its start to the end the person observes, with its concrete data; and the requirements from the [Design rules](../SKILL.md#design-rules) that only the code can meet, such as labels tied to their fields, native controls with names, keyboard order and visible focus, and the page's language.

## 4. Build with /code-better

USE `/code-better` to build the design, GIVING it `.design/<slug>/design.md` as its design and requirements. IF it is not available, BUILD only what the design needs, REUSE the project's components and patterns, and RUN the project's existing checks.

WHEN the change alters how an existing interface looks, BUILD a few visual changes at a time, and SHOW each batch before and after by [Show versions on one page](../SKILL.md#show-versions-on-one-page): when many changes land at once, nobody can tell which one helped and which one did harm.

WAIT until the build is finished and its checks pass.

## 5. Accept: have a reviewer walk every scenario

START a reviewer for every build, however small. DO NOT walk the interface yourself instead, because you know what you meant it to do. READ [../agents/reviewer.md](../agents/reviewer.md), FILL IN its Input with the built interface, the brief and the user's decisions, and GIVE the whole file, without its HOW TO USE block, to a new sub-agent as its prompt.

WAIT until the reviewer hands back its report. DO NOT write to the user while it runs.

REPRODUCE each finding in the rendered interface. FOR each confirmed finding that stops or slows a scenario, USE `/code-better` to fix it, GIVING it the finding as a defect against the design's requirement; IF it is not available, FIX it in the code and RUN the project's checks. THEN START a new reviewer, which walks ALL scenarios again, not only the one that failed: fixing one problem in an interface often creates another. A fix is accepted only once a reviewer started after it reports no finding against it: DO NOT hand back fixes that no new reviewer walked, unless a limit below stops the loop.

STOP and REPORT the open findings WHEN:

1. The same finding comes back after two fixes.
2. Three rounds have not made every scenario pass.
3. A fix breaks a scenario that passed before.

DO NOT change a scenario or drop a requirement so that the walk passes. IF a scenario looks wrong, STOP, EXPLAIN why, and ASK the user.
