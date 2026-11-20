---
name: design
description: Use when designing a feature or a change to a software system.
---

# Mode: design

FOLLOW these steps in order. The general rules of SKILL.md apply throughout.

## 1. Read the request and the system

READ the user's request, the relevant repo instructions and docs, existing designs and decision records, and the code the change touches. SAVE the request as `request.md` under the Files rule.

## 2. Draw the system as it is

DRAW the current containers and flows in `design.json` in the design location, from the code or existing design docs. USE the design JSON accepted by `scripts/diagram.py`. CHECK each box, relationship and flow step against the code. MARK what you could not verify.

RUN these commands from this skill's directory. USE the full path of the change folder for `<folder>`.

RUN `python3 scripts/diagram.py check <folder>/design.json` and `python3 scripts/diagram.py render <folder>/design.json --out <folder>/diagrams`.

- RUN `python3 scripts/architect.py serve <folder>` to start the page and GIVE the user its address.
- RUN `python3 scripts/architect.py wait <folder>` to wait for new actions. WHEN it returns, START it again and HANDLE those actions.
- RUN `python3 scripts/architect.py pending <folder>` to read open items and their threads on each wake or resume.
- RUN `python3 scripts/architect.py reply <folder> "<text>" --to <id>` to reply under the item you answer.
- RUN `python3 scripts/architect.py status <folder> seen|asked|working|done|accepted <id>...` to track each item.

SHOW Before and ASK the user to confirm or correct it in the page. IF the change introduces a system or flow, SHOW its absence in Before. WAIT for the user’s confirmation or correction and APPLY any corrections.

MARK each item `seen` when it arrives, `asked` when you need an answer, and `done` when answered or applied. MARK it `accepted` when the user accepts it in words. TREAT a reply to a finished item as work to do.

## 3. Agree the requirements

LIST functional requirements, quality attributes and constraints. GIVE each an ID and a source. LINK to the request sentence or other originating material. WHEN using code as evidence, LINK the file and name the symbol on its own line.

DRAFT quality attributes from the request and current system as observable scenarios. NAME the trigger, conditions and observable response, with a measure where it matters. MARK guesses as guessed. HAVE the user confirm or correct them in the page. RECORD the user and time as the source of a confirmation. KEEP Change available on every requirement.

## 4. Design in attribute-driven iterations

USE Attribute-Driven Design (ADD 3.0). IN each iteration, PICK the requirements and constraints that drive the design of the part in scope. COMPARE options against those drivers. CHOOSE an approach for the draft, ASSIGN responsibilities and interfaces, and WALK the scenarios through it. USE gaps or trade-offs from that walk to choose the next iteration.

UPDATE `design.json` with the proposed containers, relationships and flows. USE the same boxes as flow participants. KEEP Before and After in the same layout and scale. PRESERVE part identities across Before and After, and link the same exchange across Containers and Flows. CHECK and render the updated JSON as in step 2. CHECK that the rendered views highlight additions and removals, because highlighting makes changes easier to find.

READ and FOLLOW [../templates/design.md](../templates/design.md) for the conventional design document structure. WRITE `design.md` in the design location, linking the JSON. RECORD decisions as outputs of each iteration. SHOW the recommendation, trade-offs, rejected alternatives and reasons. CHECK the evidence for vendor claims, because vendors often make claims without supporting evidence. FLAG options that rely on unsupported claims.

LIST each perspective and whether it applies, with a reason based on what the change touches and the applicable repo standards. KEEP unresolved questions in the design and conversation.

## 5. Debate and iterate in the page

KEEP the page served. SHOW Overview, Requirements, Containers, Flows, Perspectives, Decision records and Spec. OPEN each tab directly on its content. DO NOT add an agent-written line explaining what the section is. SHOW all flows together. USE the same Before or After setting in Containers and Flows. INVITE comments on boxes, arrows and flow steps. SHOW the options and recommendation for decisions under discussion.

UPDATE the files and rendered views as the user corrects the design. WHEN the design is ready for review, ASK the user to choose Approve….

## 6. Review the approved design

WHEN the user chooses Approve…, READ and FOLLOW [../agents/perspective-reviewer.md](../agents/perspective-reviewer.md). FILL IN its inputs and START one fresh reviewer per applicable perspective on the approved design.

| Perspective | What to check |
|---|---|
| Security | Use STRIDE, starting with the highest-risk assets, trust boundaries and flows. Check the impact and the proposed mitigation, because a one-off review can become a checklist exercise. |
| Observability | Check how operators detect and diagnose failures on the affected paths. |
| API standards | Check contracts, failure responses and compatibility against the applicable standards. |
| Data and privacy | Check what data moves, who can access it and what persists. |
| Repo standards | Check each applicable repo standard where the change touches it. |

WAIT for every report. HOLD changes and user replies about the reviewed design while the reviewers run. CHECK each finding against the cited evidence. ATTACH it to its box, arrow or flow step by part ID so the page can highlight the part. GROUP findings by perspective. SHOW the page-wide findings control once the review has run.

DEBATE findings in the page and UPDATE the design where needed. CLOSE findings the changes address. WHEN the user chooses Review again…, SHOW what changed since the review and START fresh reviewers only for the perspectives those changes touch. WAIT and handle their findings the same way. KEEP unresolved findings visible.

## 7. Record decisions and extract the spec

WHEN the approved design and its review are settled, READ and FOLLOW [../templates/decision.md](../templates/decision.md). WRITE one file per choice worth recording as `<id>.md` in the decision record location. LINK its drivers to requirement IDs. RECORD the chosen option, rejected alternatives with reasons and the main drawback. KEEP open questions in the design and conversation. SHOW the records with Change and fold the rejected alternatives in the page.

READ and FOLLOW code-better's `templates/specs.md`. WRITE `specs.md` in the spec location, or use the repo's spec format when it has one. EXTRACT every MUST and MUST NOT stated or implied by the design and decisions as one verifiable EARS statement per rule. LINK each rule to its source and name how it can be checked.

READ and FOLLOW [../agents/spec-checker.md](../agents/spec-checker.md). FILL IN its inputs and START a separate checker. WAIT for its report. HOLD spec edits and hand-back while it runs. FIX confirmed omissions and unsupported links, and have the checker verify the revised mapping. ASK the user to resolve low-confidence links, because models make false matches between requirements and sources. CARRY unresolved links into the hand-back.

## 8. Hand back for implementation

LINK the design doc and diagram JSON, the decision records and the spec. REPORT the remaining questions, findings and unchecked items. POINT the user to `/code-better` with the design and spec when they are ready to implement.
