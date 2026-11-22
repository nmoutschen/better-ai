---
name: audit
description: Use when reviewing an existing software design or checking how a system matches its design.
---

# Mode: audit

FOLLOW these steps in order. The general rules of SKILL.md apply throughout. KEEP the audit report-only. LEAVE the design, code and repo files as they are.

AFTER every write to a JSON or JSONL file in the change folder, RUN `python3 <skill dir>/scripts/schema.py check <file>` and FIX every error before your next step.

## 1. Establish what to review

NAME the goal and scenarios the design must serve, from the design, its recorded decisions and its requirements. WHEN checking the system against its design, READ the relevant callers, configuration and tests as well as the code.

CHECK the affected structure and responsibilities before inspecting individual parts. USE the existing diagrams or sketch the relevant parts in the report. WHEN deriving a view from code, CHECK its boxes, arrows and steps against the code. REPORT missing design evidence and the conclusions it prevents.

## 2. Run the review

PICK the perspectives that apply, from what the audit touches and the applicable repo standards. STATE why each perspective applies or does not apply.

| Perspective | Applies when the audited design or system has | Reviewer |
|---|---|---|
| Security | an entry point, a trust boundary, an identity or secret, a language model or agent, or a part tenants share | [../agents/security.md](../agents/security.md) |
| Data and privacy | data about people that it collects, derives, moves, keeps, logs or deletes | [../agents/data-and-privacy.md](../agents/data-and-privacy.md) |
| Failure handling | a call, message or write that crosses a process or network boundary | [../agents/failure-handling.md](../agents/failure-handling.md) |
| Observability | a flow, job or part that someone must operate | [../agents/observability.md](../agents/observability.md) |
| API standards | an interface others depend on: an API, a library, a CLI, an event or a file format | [../agents/api-standards.md](../agents/api-standards.md) |
| Each repo standard | what the standard covers | [../agents/repo-standards.md](../agents/repo-standards.md), one reviewer per standard |

START one fresh reviewer per applicable perspective: READ and FOLLOW the perspective's reviewer from the table, and FILL IN its inputs. WRITE its `scenarios` from the scenarios named in step 1 that reach what the perspective covers, up to five, the most harmful first. WHEN fewer than three do, WRITE scenarios up to three and MARK each "(added)". GIVE a reviewer in `standards` only the standards that have no reviewer of their own. WRITE its `context` with the facts the review needs that the design does not show, such as where the system runs or which data is personal, not your verdict or the problems you expect. WRITE its `decided` from the constraints and preferences the user stated, without your own judgement of them, not from the design's own decisions. WAIT for every report and HOLD the hand-back while reviewers run.

## 3. Confirm findings and report

USE `/review-better` if available to confirm and rank the reviewers’ findings against the evidence and the affected scenarios. OTHERWISE, CONFIRM each finding with evidence you can show, such as the code or the scenario that fails. MARK every finding not confirmed as unconfirmed.

ATTACH each finding to the affected box, arrow or flow step. NAME the scenario or standard, the evidence, the consequence and the proposed action.

ORDER confirmed findings by their effect on the goal and scenarios, and GROUP them by perspective with their diagram references, for the hand-back. NAME what should be kept, what could not be checked, the reviewers' checks once built, and which decisions the user needs to make.
