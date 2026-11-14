# Review

USE this file WHEN the task is to review an interface or a design language, yours or someone else's.

IF the interface has no brief, WRITE one first (SKILL.md section 1.3). WRITE the GOAL and the scenarios from what the AUDIENCE comes to do, not from the pages that exist. CHECK the GOAL of an existing brief or design document the same way: it can name the request instead.

CHECK the structure (SKILL.md section 1.3) before looking for defects inside pages, because a review of defects takes the pages as given. A page or part that should merge or go is a finding ahead of any defect inside it. Your own check of the structure finds candidates. It does not show that readers find what they look for: a model finds items in a structure that people struggle with.

## R1. Run the review

FOLLOW `/review-better` if available to run the review, confirm findings and hand them back, with this file and SKILL.md sections 2 and 3 as what to look for. GIVE the reviewer [../templates/review-brief.md](../templates/review-brief.md) as its brief, with every decision the user has made about the interface or its design language.

OTHERWISE, IF you can start a sub-agent, GIVE a fresh reviewer only the interface, the brief, and those decisions, with the same template. DO NOT give it your reasoning or your conversation with the user. IF you cannot, REVIEW in a separate pass after you built: RE-READ the brief and the user's decisions first, THEN check the interface by SKILL.md sections 2 and 3 as if someone else built it.

## R2. Findings about an interface

KEEP a finding only if it names the scenario and step, what the reviewer did, what happened, and why that stops or slows the person. REPRODUCE it in the rendered interface before fixing it. A finding that only names a broken rule, with no step where a person is stopped, is unconfirmed: most such findings are not problems people have.

A finding about structure names the page or part, the scenarios checked, and why none needs it or which page it repeats.

ORDER findings by their effect on the AUDIENCE completing a scenario.

## R3. Review a design language

WHEN the thing to review is a design language, CHECK items 1 to 4 below in this order. WHEN it is an interface that has a design language, WALK its scenarios first (SKILL.md section 3.1), THEN CHECK items 2 and 3.

1. The rules of SKILL.md section 2 that a design language fixes: each allowed pair of text and background colour, text sizes, and meaning carried by colour alone.
2. What was built against what is written: LIST the colours, type sizes, spacing values and components the interface uses, and COMPARE them with the document. LOOK at screens side by side, because reviews of single elements miss problems that span a page.
3. What the scenarios need and the document lacks, such as a component or a state.
4. Whether it expresses what the user wants it to express. REPORT this as your reading, separate from the findings: it is a matter of preference.

WORK through this list instead of reviewing freely: a fixed list of criteria makes a review more useful to the person who receives it. REPORT each finding in the format of section R2, with the builder or the member of the AUDIENCE who is stopped. NAME what works and must be kept, specifically, so that fixes do not remove it.

## R4. Hand back

HAND BACK by SKILL.md section 4. IF the review is of someone else's work, DO NOT change the work unless the user asks.

IF the user then asks for changes, READ [build.md](build.md) and START at SKILL.md section 1.4.
