---
name: design
description: Use when designing a feature or a change to a software system.
---

# Mode: design

FOLLOW these steps in order. The general rules of SKILL.md and the rules of this mode apply throughout.

## Rules of this mode

### Change folder

KEEP the files the page reads in the change folder under the Files rule. WRITE each `.jsonl` file with one JSON record per line. RUN scripts from this skill's directory, with the full path of the change folder as `<folder>`. AFTER each write to the change folder, RUN `python3 scripts/architect.py check <folder>` and FIX what it reports.

### Live page conversation

- RUN `python3 scripts/architect.py wait <folder>` to wait for new actions. WHEN it returns, START it again and HANDLE those actions.
- RUN `python3 scripts/architect.py pending <folder>` to read open items and their threads on each wake or resume.
- RUN `python3 scripts/architect.py reply <folder> "<text>" --to <id>` to reply under the item you answer.
- RUN `python3 scripts/architect.py status <folder> <state> <id>...` to set the state of items.

REPLY in the page, in one or two short sentences. MARK each item `seen` when it arrives and `asked` when you need an answer. KEEP `working` on the items you are changing now, usually one. WHEN an item needs only an answer, MARK it `done` once answered. WHEN the user's answer leads to a change, MARK the item `done` once the change is in the page, and PUT your next question in a new message. MARK it `accepted` when the user accepts it in words. TREAT a reply to a finished item as work to do.

### Diagram kinds

RUN `python3 scripts/diagram.py register --out <file>.html` to see the available diagram kinds. USE only kinds from that register.

## 1. Read the request and the system

READ the user's request, the relevant repo instructions and docs, existing designs and decision records, and the code the change touches. WRITE the user's request word for word as `request.md` in the change folder.

## 2. Draw the system as it is

DRAW the current containers and flows in `design.json` in the change folder, from the code or existing design docs. USE the design JSON accepted by `scripts/diagram.py`. CHECK each box, relationship and flow step against the code. MARK what you could not verify.

RUN `python3 scripts/diagram.py check <folder>/design.json` and `python3 scripts/diagram.py render <folder>/design.json --out <folder>/diagrams`.

RUN `python3 scripts/architect.py serve <folder>` to start the page and GIVE the user its address.

SHOW Before and ASK the user to confirm or correct it in the page. IF the change introduces a system or flow, SHOW its absence in Before. WAIT for the user’s confirmation or correction and APPLY any corrections.

## 3. Agree the requirements

LIST functional requirements, quality attributes and constraints. WRITE each as one line of `requirements.jsonl` with `id`, `kind` (`functional`, `quality` or `constraint`), `text` and `source`. SET `source` to where it comes from:

| Source | `source` |
|---|---|
| A sentence of the request | `{"type": "request", "sentence": "<the sentence, word for word>"}` |
| Code | `{"type": "file", "file": "<path>", "symbol": "<symbol>"}` |
| Your guess | `{"type": "guessed"}` |
| The user's confirmation | `{"type": "user", "at": "<time>"}` |

DRAFT quality attributes from the request and current system as observable scenarios. NAME the trigger, conditions and observable response, with a measure where it matters. HAVE the user confirm or correct them in the page. KEEP Change available on every requirement.

## 4. Design in attribute-driven iterations

USE Attribute-Driven Design (ADD 3.0). IN each iteration, PICK the requirements and constraints that drive the design of the part in scope. COMPARE options against those drivers. CHOOSE an approach for the draft, ASSIGN responsibilities and interfaces, and WALK the scenarios through it. USE gaps or trade-offs from that walk to choose the next iteration.

UPDATE `design.json` with the proposed containers, relationships and flows. USE the same boxes as flow participants. KEEP Before and After in the same layout and scale. PRESERVE part identities across Before and After, and link the same exchange across Containers and Flows. CHECK and render the updated JSON as in step 2. CHECK that the rendered views highlight additions and removals, because highlighting makes changes easier to find.

READ and FOLLOW [../templates/design.md](../templates/design.md) for the conventional design document structure. WRITE `design.md` in the change folder, linking the JSON. RECORD each decision in `design.md` as an output of its iteration, with the recommendation, trade-offs, rejected alternatives and reasons. CHECK the evidence for vendor claims, because vendors often make claims without supporting evidence. FLAG options that rely on unsupported claims.

PICK the perspectives that apply, from what the change touches and the applicable repo standards:

| Perspective | What to check |
|---|---|
| Security | Use STRIDE, starting with the highest-risk assets, trust boundaries and flows. Check the impact and the proposed mitigation, because a one-off review can become a checklist exercise. |
| Observability | Check how operators detect and diagnose failures on the affected paths. |
| API standards | Check contracts, failure responses and compatibility against the applicable standards. |
| Data and privacy | Check what data moves, who can access it and what persists. |
| Repo standards | Check each applicable repo standard where the change touches it. |

WRITE each perspective as one line of `perspectives.jsonl` with `name`, `applies` (`true` or `false`), `why` and `from` (`built in` for a perspective of the table, or the path of the repo standard). KEEP unresolved questions in the design and conversation.

## 5. Debate and iterate in the page

KEEP the page served. SHOW Overview, Requirements, Containers, Flows, Perspectives, Decision records and Spec. OPEN each tab directly on its content. DO NOT add an agent-written line explaining what the section is. SHOW all flows together. USE the same Before or After setting in Containers and Flows. INVITE comments on boxes, arrows and flow steps. SHOW the options and recommendation for decisions under discussion.

UPDATE the files and rendered views as the user corrects the design. WHEN the design is ready for review, ASK the user to choose Approve….

## 6. Review the approved design

WHEN the user chooses Approve…, READ and FOLLOW [../agents/perspective-reviewer.md](../agents/perspective-reviewer.md). FILL IN its inputs and START one fresh reviewer per applicable perspective on the approved design, with that perspective's checks from step 4.

WAIT for every report. HOLD changes and user replies about the reviewed design while the reviewers run. USE `/review-better` if available to confirm each finding. OTHERWISE, MARK each finding unconfirmed. WRITE each finding as one line of `findings.jsonl` with `id`, `perspective`, `parts`, `text` and `handled_by`. NAME each part in `parts` as `box:<id>`, `edge:<id>` or `step:<flow>/<id>`, and JOIN the views of one exchange with `+`, such as `edge:<id>+step:<flow>/<id>`. SET `handled_by` to the change or decision that addresses the finding, or `null` while it is open. WRITE one line of `reviews.jsonl` for the run, with `at` (the time), `perspectives` (those run) and `changed` (the parts changed since the previous run, empty for the first).

DEBATE findings in the page and UPDATE the design where needed. SET `handled_by` on findings the changes address. WHEN the user chooses Review again…, SHOW what changed since the review and START fresh reviewers only for the perspectives those changes touch. WAIT and handle their findings and run record the same way. KEEP unresolved findings visible.

## 7. Record decisions and extract the spec

WHEN the approved design and its review are settled, WRITE each decision of `design.md` worth recording as one line of `decisions.jsonl` with `id`, `title`, `drivers` (requirement IDs), `chosen`, `rejected` (a list of `{"option": ..., "why": ...}`) and `drawback` (the main drawback). READ and FOLLOW [../templates/decision.md](../templates/decision.md), and WRITE each of these decisions as `<id>.md` in the decision record location.

READ and FOLLOW code-better's spec template, [../../code-better/templates/specs.md](../../code-better/templates/specs.md) (`skills/code-better/templates/specs.md` in this repo). EXTRACT every MUST and MUST NOT stated or implied by the design and decisions as one verifiable EARS statement per rule. WRITE each as one line of `spec.jsonl` with `id`, `requirement` (the EARS statement), `source` (the design section, decision ID or request sentence it comes from) and `checked_by` (how it can be checked). WRITE the same spec as `specs.md` in the spec location, or in the repo's spec format when it has one.

READ and FOLLOW [../agents/spec-checker.md](../agents/spec-checker.md). FILL IN its inputs and START a separate checker. WAIT for its report. HOLD spec edits and hand-back while it runs. FIX confirmed omissions and unsupported links, and have the checker verify the revised mapping. ASK the user to resolve low-confidence links, because models make false matches between requirements and sources. CARRY unresolved links into the hand-back.

## 8. Hand back for implementation

LINK the design doc and diagram JSON, the decision records and the spec. REPORT the remaining questions, findings and unchecked items. POINT the user to `/code-better` with the design and spec when they are ready to implement.
