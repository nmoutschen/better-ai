---
name: design
description: Use when designing a feature or a change to a software system.
---

# Mode: design

FOLLOW these steps in order. The general rules of SKILL.md and the rules of this mode apply throughout.

## Rules of this mode

### Change folder

KEEP the files the page reads in the change folder under the Files rule. READ and FOLLOW [../scripts/example/README.md](../scripts/example/README.md) for the fields of each file. RUN scripts from this skill's directory, with the full path of the change folder as `<folder>`. FROM step 2 on, AFTER each write to the change folder, RUN `python3 scripts/architect.py check <folder>` and FIX what it reports.

### Live page conversation

- RUN `python3 scripts/architect.py wait <folder>` to wait for new actions. WHEN it returns, START it again and HANDLE those actions.
- RUN `python3 scripts/architect.py pending <folder>` to read open items and their threads on each wake or resume.
- RUN `python3 scripts/architect.py reply <folder> "<text>" --to <id>` to reply under the item you answer.
- RUN `python3 scripts/architect.py status <folder> <state> <id>...` to set the state of items.

REPLY in the page, in one or two short sentences. MARK each item `seen` when it arrives and `asked` when you need an answer. KEEP `working` on the items you are changing now, usually one. WHEN an item needs only an answer, MARK it `done` once answered. WHEN the user's answer leads to a change, MARK the item `done` once the change is in the page, and PUT your next question in a new message. MARK it `accepted` when the user accepts it in words. TREAT a reply to a finished item as work to do.

### Box kinds

RUN `python3 scripts/diagram.py register --out <folder>/register.html` to see the available box kinds. USE only kinds from that register.

## 1. Read the request and the system

READ the user's request, the relevant repo instructions and docs, existing designs and decision records, and the code the change touches. WRITE the user's request word for word as `request.md` in the change folder.

## 2. Draw the system as it is

DRAW the current containers and flows in `design.json` in the change folder, from the code or existing design docs. CHECK each box, relationship and flow step against the code. MARK what you could not verify.

RUN `python3 scripts/diagram.py check <folder>/design.json` and `python3 scripts/diagram.py render <folder>/design.json --out <folder>/diagrams`.

RUN `python3 scripts/architect.py serve <folder>` to start the page and GIVE the user its address.

ASK the user to confirm or correct Before in the page. IF the change introduces a system or flow, SHOW its absence in Before. WAIT for the user's confirmation or correction and APPLY any corrections.

## 3. Agree the requirements

LIST functional requirements, quality attributes and constraints, and WRITE each as a record of `requirements.jsonl`. SET its source to where it comes from:

| Where it comes from | Source |
|---|---|
| A sentence of the request | `request`, with the sentence word for word |
| Code | `file`, with `<path from the repo root>` and the symbol |
| The user, in words or in the page | `user`, with the time |
| Nothing in the request, the code or the user's words | `guessed` |

DRAFT quality attributes from the request and current system as observable scenarios. NAME the trigger, conditions and observable response, with a measure where it matters. HAVE the user confirm or correct them in the page.

## 4. Design in attribute-driven iterations

USE Attribute-Driven Design (ADD 3.0). IN each iteration, PICK the requirements and constraints that drive the design of the part in scope. COMPARE options against those drivers. CHOOSE an approach for the draft, ASSIGN responsibilities and interfaces, and WALK the scenarios through it. USE gaps or trade-offs from that walk to choose the next iteration.

UPDATE `design.json` with the proposed containers, relationships and flows. USE the same boxes as flow participants. PRESERVE part identities across Before and After. SET `in` on every added or removed part. CHECK and render the updated JSON as in step 2.

READ and FOLLOW [../templates/design.md](../templates/design.md) for the conventional design document structure. WRITE `design.md` in the change folder, linking the JSON. RECORD each decision in `design.md` as an output of its iteration, with the recommendation, trade-offs, rejected alternatives and reasons. CHECK the evidence for vendor claims, because vendors often make claims without supporting evidence. FLAG options that rely on unsupported claims.

PICK the perspectives that apply, from what the change touches and the applicable repo standards:

| Perspective | What to check |
|---|---|
| Security | Use STRIDE, starting with the highest-risk assets, trust boundaries and flows. Check the impact and the proposed mitigation, because a one-off review can become a checklist exercise. |
| Observability | Check how operators detect and diagnose failures on the affected paths. |
| API standards | Check contracts, failure responses and compatibility against the applicable standards. |
| Data and privacy | Check what data moves, who can access it and what persists. |
| Repo standards | Check each applicable repo standard where the change touches it. |

WRITE every perspective of the table and every applicable repo standard as a record of `perspectives.jsonl`, with whether it applies and why. KEEP unresolved questions in the design and conversation.

## 5. Debate and iterate in the page

KEEP the page served. INVITE comments on boxes, arrows and flow steps. GIVE the options and your recommendation for each decision under discussion in the page conversation.

UPDATE the files and rendered views as the user corrects the design. WHEN the user accepts a section in words or in the page, ADD its key to `accepted` in `design.json`. WHEN the design is ready for review, ASK the user to choose Approve….

## 6. Review the approved design

WHEN the user chooses Approve…, READ and FOLLOW [../agents/perspective-reviewer.md](../agents/perspective-reviewer.md). FILL IN its inputs and START one fresh reviewer per applicable perspective on the approved design, with that perspective's checks from step 4.

WAIT for every report. HOLD changes and user replies about the reviewed design while the reviewers run. THEN RUN `python3 scripts/architect.py review <folder> --perspectives <name>...` with the perspectives run.

USE `/review-better` if available to confirm each finding. WRITE each finding as a record of `findings.jsonl`, with `confirmed` true when `/review-better` confirmed it and false otherwise. NAME each part it affects as `box:<id>`, `edge:<id>` or `step:<flow id>/<step id>`, where `<flow id>` is the flow's `id`, or `flow<N>` for the Nth flow. JOIN the views of one exchange with `+`, such as `edge:<id>+step:<flow id>/<step id>`. SET `handled_by` to the change or decision that addresses the finding, or `null` while it is open.

DEBATE findings in the page and UPDATE the design where needed. SET `handled_by` on findings the changes address. WHEN the user chooses Review again…, START fresh reviewers for the perspectives the page lists, and HANDLE their reports as above.

## 7. Record decisions and extract the spec

WHEN the approved design and its review are settled, WRITE each decision of `design.md` worth recording as a record of `decisions.jsonl`. READ and FOLLOW [../templates/decision.md](../templates/decision.md), and WRITE each of these decisions as `<id>.md` in the decision record location.

READ and FOLLOW [../templates/specs.md](../templates/specs.md) to extract the spec from the design and decisions. WRITE each requirement as a record of `spec.jsonl`, with its source. WRITE the same spec as `specs.md` in the spec location, or in the repo's spec format when it has one.

READ and FOLLOW [../agents/spec-checker.md](../agents/spec-checker.md). FILL IN its inputs and START a separate checker. WAIT for its report. HOLD spec edits and hand-back while it runs. FIX confirmed omissions and unsupported links, and have the checker verify the revised mapping. ASK the user to resolve low-confidence links, because models make false matches between requirements and sources. CARRY unresolved links into the hand-back.

## 8. Hand back for implementation

LINK the design doc and diagram JSON, the decision records and the spec. REPORT the remaining questions, findings and unchecked items. POINT the user to `/code-better` with the design and spec when they are ready to implement.
