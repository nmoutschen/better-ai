---
name: audit
description: Use when reviewing an existing software design or checking how a system matches its design.
---

# Mode: audit

FOLLOW these steps in order. The general rules of SKILL.md apply throughout. KEEP the audit report-only. LEAVE the design, code and repo files as they are.

After every write to a file in the change folder, run `python3 <skill dir>/scripts/schema.py check <file>` and fix every error before your next step.

## 1. Establish what to review

NAME the goal and scenarios the design must serve, from the design, its recorded decisions and its requirements. WHEN checking the system against its design, READ the relevant callers, configuration and tests as well as the code.

CHECK the affected structure and responsibilities before inspecting individual parts. USE the existing diagrams or sketch the relevant parts in the report. WHEN deriving a view from code, CHECK its boxes, arrows and steps against the code. REPORT missing design evidence and the conclusions it prevents.

## 2. Run the review

PICK the perspectives that apply, from what the audit touches and the applicable repo standards. STATE why each perspective applies or does not apply.

| Perspective | What to check |
|---|---|
| Security | Use STRIDE on the assets, trust boundaries and flows where harm would be greatest, not on every part. Check the impact and the proposed mitigation. |
| Observability | Check how operators detect and diagnose failures on the affected paths. |
| API standards | Check contracts, failure responses and compatibility against the applicable standards. |
| Data and privacy | Check what data moves, who can access it and what persists. |
| Repo standards | Check each applicable repo standard where the change touches it. |

READ and FOLLOW [../agents/perspective-reviewer.md](../agents/perspective-reviewer.md). FILL IN its inputs and START one fresh reviewer per applicable perspective. WRITE its `look_for` from that perspective's row of the table, the applicable standards and what the audit touches. WRITE its `decided` from the constraints the user or the design's recorded decisions set, without your own judgement of them. WAIT for every report and HOLD the hand-back while reviewers run.

## 3. Confirm findings and report

USE `/review-better` if available to confirm and rank the reviewers’ findings against the evidence and the affected scenarios. OTHERWISE, CONFIRM each finding with evidence you can show, such as the code or the scenario that fails. MARK every finding not confirmed as unconfirmed.

ATTACH each finding to the affected box, arrow or flow step. NAME the scenario or standard, the evidence, the consequence and the proposed action.

ORDER confirmed findings by their effect on the goal and scenarios, and GROUP them by perspective with their diagram references, for the hand-back. NAME what should be kept, what could not be checked and which decisions the user needs to make.
