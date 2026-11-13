# Build an interface

USE this file WHEN the task is to design, build or change an interface. FOLLOW SKILL.md sections 1 and 2 with it. Showing directions before building, reusing the project's components, shipping visual changes in small batches, and the stopping rules of section B4 are design choices.

## B1. Direction: show before building

USE this section WHEN the interface is new, or the change alters its layout or flow, and the brief leaves more than one reasonable direction. FOR a small change inside an existing interface, FOLLOW its patterns and SKIP this section.

### B1.1. Ask for the user's own direction first

ASK whether the user has a direction or references in mind BEFORE you show yours, because seeing examples first narrows what people consider. TREAT this order as a guide, not a rule. IF no design language exists, ASK for interfaces they like and dislike. PREFER pictures and examples over adjectives: people rarely have the words for a look they would recognise.

### B1.2. Show two or three rough directions

MAKE the directions differ in a way the user can see, such as the structure, the order of content, or what is prominent. DO NOT vary only a colour or a font. USE the same real content in each.

KEEP them rough: real structure and content, little styling. A rough version reveals largely the same problems as a finished one, and polish changes how people rate it. SHOW them by SKILL.md section 1.4. TREAT two or three as a guide, not a rule.

### B1.3. Ask what is wrong, not how to fix it

ASK which direction serves each scenario best and what is wrong with each one. DO NOT ask the user to design the fix: people identify problems far more reliably than solutions. RECORD the chosen direction in the brief.

TREAT what the user picks about the look as this user's preference. It is not evidence that the interface works for the AUDIENCE.

## B2. Change only what the task needs

PRESERVE the parts of an existing interface that the task does not require you to change. REUSE the project's components, tokens and patterns. IF none exist, DEFINE a small set of colours, type sizes and spacing values once, and USE only those.

BUILD by the rules of SKILL.md section 2.

WHEN you change how the interface looks, CHANGE a few things at a time and SHOW each batch before and after, so that the user can tell which change caused their reaction: when many changes land at once, nobody can tell which one helped and which one did harm. DO NOT ship many visual changes together.

## B3. Decide the cases the design leaves out

WALK each scenario step by step. AT each step, ASK what can go wrong or differ: no data yet, a lot of data, very long text, a slow or failed response, invalid input, no permission, the person going back or repeating the step, a small screen.

THEN CHECK each screen against a short list of states: empty, loading, error, partial, full and success. Each method finds cases the other misses. TREAT this section as a guide, not a rule.

FOR each case, DECIDE what the interface shows, and BUILD it. IF a case changes what happens to the person's data or work, TREAT it as a question for the user (SKILL.md section 1.4) or state it as an assumption.

## B4. Verify, and bound the fix loop

CHECK the interface by SKILL.md section 3.

AFTER each round of fixes, WALK all scenarios again, not only the one that failed, because fixing one problem in an interface often creates another.

STOP fixing and REPORT when:

1. The same problem remains after two attempts.
2. About three rounds of fixes have not made every scenario pass.
3. A fix breaks a scenario that passed before.

DO NOT change a scenario or drop a check so that the walk passes. IF a scenario looks wrong, STOP, EXPLAIN why, and ASK the user.

## B5. Review, then hand back

REVIEW the result with [review.md](review.md), THEN hand back by SKILL.md section 4.
