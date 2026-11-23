---
name: design
description: Use when designing a feature or a change to a software system.
---

# Mode: design

FOLLOW these steps in order. The general rules of SKILL.md and the rules of this mode apply throughout.

## Rules of this mode

### Files

LOOK in `docs/` for the repo's design location, in `docs/adr/` or `docs/decisions/` for its decision record location, and in its existing specs location or spec tool for its spec location. KEEP the records of the change in the change folder `.architect/<change>/` at the repo root, and CALL it `<unit>` in the commands. KEEP `design.md`, in a folder of its own for the change, in the design location, and decision records and the spec in their respective locations. WHEN a location has no repo convention, USE `.architect/<change>/` for it, and `.architect/<change>/decisions/` for decision records.

READ and FOLLOW [../formats/records.md](../formats/records.md) before you first add a record: it gives one line of each kind of record, the fields of each, and the conventions for adding them. RUN `python3 <skill dir>/scripts/better.pyz check <unit>` before you start the page, and FIX what it reports.

### Live page conversation

- RUN `python3 <skill dir>/scripts/better.pyz wait <unit>` to wait for new actions. WHEN it returns, START it again and HANDLE those actions.
- RUN `python3 <skill dir>/scripts/better.pyz pending <unit>` to read open items and their threads on each wake or resume.
- RUN `python3 <skill dir>/scripts/better.pyz reply <unit> --to <id>`, with your words on stdin, to reply under the item you answer.
- RUN `python3 <skill dir>/scripts/better.pyz status <unit> <state> <id>...` to set the state of items.

REPLY in the page, in one or two short sentences. MARK each item `seen` when it arrives and `asked` when you need an answer. KEEP `working` on the items you are changing now, usually one. WHEN an item needs only an answer, MARK it `done` once answered. WHEN the user's answer leads to a change, MARK the item `done` once the change is in the page, and PUT your next question in a new message. MARK it `accepted` when the user accepts it in words. TREAT a reply to a finished item as work to do.

### Box kinds

RUN `python3 <skill dir>/scripts/better.pyz register <unit>`, then READ `register.html` in the unit for the available box kinds. USE only kinds from that register.

## 1. Save the request

RUN `python3 <skill dir>/scripts/better.pyz create .architect/<change> --by <your name>` with the head record on stdin: the user's request word for word as `request.text`, where it comes from as `request.from` (`{"type": "chat"}`, `{"type": "issue", "url": …}` or `{"type": "file", "path": …}`), a short `title`, an empty `summary` and `scope`, and `accepted` as `[]`.

## 2. Draw the system as it is

DRAW the current containers and flows as the `design` record, from the code or existing design docs. GIVE every flow an `id`, such as `order`: a part key names a flow by it. CHECK each box, relationship and flow step against the code. MARK what you could not verify.

RUN `python3 <skill dir>/scripts/better.pyz check <unit>` and `python3 <skill dir>/scripts/better.pyz render <unit>`.

RUN `python3 <skill dir>/scripts/better.pyz serve <unit>` to start the page and GIVE the user its address as it prints it, whole, with its `#t=` part.

ASK the user to confirm or correct Before in the page. IF the change introduces a system or flow, NAME it in your question as not existing yet, and DO NOT add it to the `design` record before step 4. WAIT for the user's confirmation or correction and APPLY any corrections. DO NOT start step 3 before the user confirms or corrects Before: HANDLE other actions and START `wait` again; IF `wait` times out before they answer, END your turn with the question, in the chat as well as the page.

## 3. Agree the requirements

LIST functional requirements, quality attributes and constraints, and ADD each with `python3 <skill dir>/scripts/better.pyz add <unit> requirement --by <your name>`. SET its source to where it comes from:

| Where it comes from | Source |
|---|---|
| A sentence of the request | `request`, with the sentence word for word |
| Code | `file`, with `<path from the repo root>` and the symbol |
| The user, in words or in the page | `user`, with the time |
| Nothing in the request, the code or the user's words | `guessed` |

DRAFT quality attributes from the request and current system as observable scenarios. NAME the trigger, conditions and observable response, with a measure where it matters. HAVE the user confirm or correct them in the page.

## 4. Design in attribute-driven iterations

USE Attribute-Driven Design (ADD 3.0). IN each iteration, PICK the requirements and constraints that drive the design of the part in scope. LIST the options before choosing one, including at least one that is not the familiar choice, and COMPARE them against those drivers. CHOOSE an approach for the draft, ASSIGN responsibilities and interfaces, and WALK the scenarios through it. USE gaps or trade-offs from that walk to choose the next iteration.

UPDATE the `design` record with `set`, using the proposed containers, relationships and flows. USE the same boxes as flow participants. PRESERVE part identities across Before and After. SET `in` on every added or removed part. CHECK and render the updated JSON as in step 2.

READ and FOLLOW [../templates/design.md](../templates/design.md) for the conventional design document structure. WRITE `design.md` in the design location, linking the unit, and SET `document` in the `architect` record to its path from the repo root, with `set`. RECORD each decision in `design.md` as an output of its iteration, with the recommendation, its drivers, each rejected alternative with its reason, and the main drawback of the chosen option. A reason to reject an alternative is not a drawback. TREAT a choice that changes behaviour, cost, risk or how the system is maintained as a decision, and COMPARE its options. LIST other choices in the hand-back as assumptions you made. CHECK the evidence for vendor claims, because vendors often make claims without supporting evidence. FLAG options that rely on unsupported claims.

PICK the perspectives that apply, from what the change touches and the applicable repo standards:

| Perspective (`id`) | Applies when the change | Reviewer |
|---|---|---|
| Security (`security`, method STRIDE) | adds or changes an entry point, a trust boundary, an identity or secret, a language model or agent, or a part tenants share | [../agents/security.md](../agents/security.md) |
| Data and privacy (`data-and-privacy`, method LINDDUN) | collects, derives, moves, keeps, logs or deletes data about people | [../agents/data-and-privacy.md](../agents/data-and-privacy.md) |
| Failure handling (`failure-handling`) | adds or changes a call, message or write that crosses a process or network boundary | [../agents/failure-handling.md](../agents/failure-handling.md) |
| Observability (`observability`) | adds or changes a flow, job or part that someone must operate | [../agents/observability.md](../agents/observability.md) |
| Agent experience (`agent-experience`) | adds or changes something an agent calls, a call to an agent, or a workspace agents share with people | [../agents/agent-experience.md](../agents/agent-experience.md) |
| API standards (`api-standards`) | adds or changes an interface others depend on: an API, a library, a CLI, an event or a file format | [../agents/api-standards.md](../agents/api-standards.md) |
| Each repo standard (its own `id`) | touches what the standard covers | [../agents/repo-standards.md](../agents/repo-standards.md), one reviewer per standard |

ADD every perspective of the table and every applicable repo standard with `python3 <skill dir>/scripts/better.pyz add <unit> perspective --by <your name> --id <perspective id>`, giving whether it applies and why, and where it comes from: `built_in` (with its `method`, such as STRIDE, if it has one), or `standard` with the standard's `file`. KEEP unresolved questions in the design and conversation.

## 5. Debate and iterate in the page

KEEP the page served. INVITE comments on boxes, arrows and flow steps. GIVE the options and your recommendation for each decision under discussion in the page conversation.

UPDATE the files and rendered views as the user corrects the design. WHEN the user accepts a section in words or in the page, ADD its key to `accepted` in the `architect` record, with `set`. WHEN the design is ready for review, ASK the user to choose Approve….

## 6. Review the approved design

WHEN the user chooses Approve…, START one fresh reviewer per applicable perspective on the approved design: READ and FOLLOW the perspective's reviewer from the table in step 4, and FILL IN its inputs. GIVE its `scenarios` from the scenarios of the `requirement` records that reach what the perspective covers, up to five, the most harmful first. WHEN fewer than three do, GIVE scenarios up to three and MARK each "(added)". GIVE a reviewer in `standards` only the standards that have no reviewer of their own. GIVE its `context` with the facts the review needs that the design does not show, such as where the system runs or which data is personal, not your verdict on the design or the problems you expect. GIVE its `decided` from the constraints and preferences the user stated, such as the `requirement` records with source `user`, not from the design's own decisions.

WAIT for every report. HOLD changes and user replies about the reviewed design while the reviewers run. THEN RUN `python3 <skill dir>/scripts/better.pyz review <unit> --perspectives <id>...` with the ids of the perspectives run.

USE `/review-better` if available to confirm each finding. OTHERWISE, CONFIRM each finding with evidence you can show, such as the code or the scenario that fails, and KEEP a finding you cannot confirm as unconfirmed. ADD each finding with `python3 <skill dir>/scripts/better.pyz add <unit> finding --by <your name>`, with the `id` of its perspective, `confirmed` true when it is confirmed and false otherwise, and `status` `open`. NAME each part it affects as `box:<id>`, `edge:<id>` or `step:<flow id>/<step id>`, where `<flow id>` is the flow's `id`. JOIN the views of one exchange with `+`, such as `edge:<id>+step:<flow id>/<step id>`. WHEN a change or decision addresses the finding, SET `status` to `handled` and `handled_by` to it; `handled_by` exists only then.

DEBATE findings in the page and UPDATE the design where needed. WHEN the user disputes a finding, FOLLOW `/review-better` for a disputed finding if available. OTHERWISE, CHANGE the finding only when the user's argument adds evidence or shows that the finding misread the design. SET `status` and `handled_by` on findings the changes address. WHEN the user chooses Review again…, START fresh reviewers for the perspectives the page lists, with `scope` set to the `changes` listed on the approval item, or to the whole design WHEN those changes name a `requirement:` or `section:`, and HANDLE their reports as above.

## 7. Record decisions and extract the spec

WHEN the approved design and its review are settled, ADD each decision of `design.md` worth recording with `python3 <skill dir>/scripts/better.pyz add <unit> decision --by <your name>`. ALSO write each of these decisions as a document in the decision record location, in the repo's decision record format when it has one: NAME the file as the repo names its records, KEEP its sections and PUT the drivers, rejected alternatives and main drawback within them. OTHERWISE, READ and FOLLOW [../templates/decision.md](../templates/decision.md) and NAME the file `<id>.md`.

READ and FOLLOW [../formats/specs.md](../formats/specs.md) to extract the spec from the design and decisions. INCLUDE each check the reviewers listed under "Checks once built" for behaviour the design states, with that design `section` as its source. ADD each requirement with `python3 <skill dir>/scripts/better.pyz add <unit> spec --by <your name>`, with its `statement` and its source: the `section` of the design, a request `sentence`, a `decision` id or a `requirement` id. WHEN the repo keeps its specs in a spec format or tool, write the spec there too, in its format. OTHERWISE RUN `python3 <skill dir>/scripts/better.pyz specs <unit>` and WRITE its output to `<spec location>/specs.md`, ONLY IF that file is missing or its first line is the generated marker the output starts with. IF it exists and its first line is not that marker, DO NOT overwrite it. NEVER edit a generated `specs.md` by hand; CHANGE the `spec` records with `set` and run the command again.

READ and FOLLOW [../agents/spec-checker.md](../agents/spec-checker.md). FILL IN its inputs and START a separate checker. WAIT for its report. HOLD spec edits and hand-back while it runs. FIX each confirmed blocking finding, THEN START a new checker on the revised spec. DO this at most twice. STOP and CARRY the open findings into the hand-back WHEN the same finding comes back. ASK the user to settle each link the checker lists as unconfirmed. CARRY unresolved links into the hand-back.
