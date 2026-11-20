---
name: audit
description: Use when the user asks for a review of an interface or a design language, theirs or someone else's, or for what to improve, and wants findings rather than a change.
---

# Mode: audit

FOLLOW these steps in order. The general rules of SKILL.md apply throughout.

An audit reports; it does not change the work. DO NOT edit, create or delete any file outside `.design/`, even for a one-line fix: PROPOSE each fix instead. One exception: WHEN SKILL.md sent you here because you were invoked without argument on an interface the current conversation is building, CORRECT that work after the report (step 5). A fixed list of what to check, and findings tied to a step where a person is stopped, are design choices.

## 1. Check the brief's GOAL

WRITE the brief's GOAL and scenarios from what the AUDIENCE comes to do, not from the pages that exist. CHECK the GOAL of an existing brief or design document the same way: it can name the request instead.

## 2. Run the review

START a reviewer for every audit, however small. DO NOT review the interface yourself instead. READ [../agents/reviewer.md](../agents/reviewer.md), FILL IN its Input with the interface, the brief, the design language, every decision the user has made about them, and what to review, and GIVE the whole file, without its HOW TO USE block, to a new sub-agent as its prompt. WHEN the thing to review is a design language that has an interface built with it, ASK it to review both.

WAIT until the reviewer hands back its report. DO NOT write to the user while it runs.

## 3. Confirm and order the findings

REPRODUCE each finding in the rendered interface, or for a design language finding, FIND the value or component where the reviewer says it is. KEEP a finding only if it names the scenario and step, what was done, what happened, and why that stops or slows the person. MARK the others unconfirmed: most findings that only name a broken rule are not problems people have.

ORDER the findings: structure first, because a review of defects takes the pages as given, so a page that should merge or go comes ahead of any defect inside it; THEN the rest by their effect on the AUDIENCE completing a scenario.

## 4. Report

REPORT by SKILL.md step 6: the findings in order, each with its proposed fix; the unconfirmed ones in one line each; what works and must be kept; and, for a design language, your reading of whether it expresses what the user wants, separate from the findings.

IF the user then asks for changes, READ [design.md](design.md) or [language.md](language.md), whichever fits, and FOLLOW it.

## 5. Correct the work you are building

ONLY WHEN SKILL.md sent you here without argument for an interface the current conversation is building: CORRECT each confirmed finding in that work. FOR a fix inside one screen, FOLLOW SKILL.md's line for small changes; OTHERWISE, READ [design.md](design.md) and FOLLOW it from its step 2. THEN START a new reviewer as step 2 says, and REPORT what you changed and what remains open.
