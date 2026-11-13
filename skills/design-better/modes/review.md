# Review

USE this file WHEN the task is to review an interface or a design language, yours or someone else's. Review in a fresh context is a design choice.

IF the interface has no brief, WRITE its scenarios first (SKILL.md section 1.3).

## R1. Review in a fresh context

IF you can start a sub-agent, GIVE a fresh reviewer only the interface and the brief, with [../templates/review-brief.md](../templates/review-brief.md). DO NOT give it your reasoning or your conversation with the user. A cheaper model can review, but it must not share your context.

OTHERWISE, REVIEW in a separate pass after you built: RE-READ the brief first, THEN check the interface by SKILL.md section 3 as if someone else built it.

IF the interface is important enough for more than one review, RUN the same review again independently. DO NOT give reviewers different characters or temperaments instead: repeated independent reviews find most of what such roles find. TREAT this as a guide, not a rule.

## R2. Treat findings as candidates

KEEP a finding only if it names the scenario and step, what the reviewer did, what happened, and why that stops or slows the person. REPRODUCE it in the rendered interface before fixing it.

A finding that only names a broken rule, with no step where a person is stopped, is unconfirmed. Most such findings are not problems people have. DROP it only when you can show it is wrong. OTHERWISE, REPORT it as unconfirmed.

ORDER findings by their effect on the AUDIENCE completing a scenario.

## R3. Review a design language

WHEN the thing to review is a design language, or an interface against its design language, CHECK in this order:

1. The rules of SKILL.md section 2 that a design language fixes: each allowed pair of text and background colour, text sizes, and meaning carried by colour alone.
2. What was built against what is written: LIST the colours, type sizes, spacing values and components the interface uses, and COMPARE them with the document. LOOK at screens side by side, because reviews of single elements miss problems that span a page.
3. What the scenarios need and the document lacks, such as a component or a state.
4. Whether it expresses what the user wants it to express. REPORT this as your reading, separate from the findings: it is a matter of preference.

WORK through this list instead of reviewing freely: a fixed list of criteria makes a review more useful to the person who receives it. REPORT each finding in the format of section R2, with the builder or the member of the AUDIENCE who is stopped. NAME what works and must be kept, specifically, so that fixes do not remove it.

## R4. Hand back

HAND BACK by SKILL.md section 4. IF the review is of someone else's work, REPORT the findings and DO NOT change the work unless the user asks.
