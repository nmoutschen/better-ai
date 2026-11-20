---
name: audit
description: Use when reviewing an existing software design or checking how a system matches its design.
---

# Mode: audit

FOLLOW these steps in order. The general rules of SKILL.md apply throughout. KEEP the audit report-only. LEAVE the design, code and repo files as they are.

## 1. Establish what to review

READ the request, the design and recorded decisions, the requirements and the repo standards. NAME the goal and scenarios the design must serve. WHEN checking the system against its design, READ the relevant code, callers, configuration and tests.

CHECK the affected structure and responsibilities before inspecting individual parts. USE the existing diagrams or sketch the relevant parts in the report. WHEN deriving a view from code, CHECK its boxes, arrows and steps against the code. REPORT missing design evidence and the conclusions it prevents.

## 2. Run the review

PICK perspectives from what the audit touches. CHECK security with risk-first STRIDE, observability, API standards, data and privacy, and applicable repo standards. STATE why each perspective applies or does not apply.

FOLLOW `/review-better` if available for confirming and ranking findings. READ and FOLLOW [../agents/perspective-reviewer.md](../agents/perspective-reviewer.md). START one fresh reviewer per applicable perspective. GIVE each the design, requirements, decisions, relevant evidence and diagram references. KEEP your reasoning and verdict out of the brief. WAIT for every report and HOLD the hand-back while reviewers run.

## 3. Confirm findings and report

CHECK each finding against the design or the system, as the request requires. ATTACH it to the affected box, arrow or flow step. NAME the scenario or standard, the evidence, the consequence and the proposed action. MARK findings you could not confirm.

ORDER confirmed findings by their effect on the goal and scenarios. REPORT them by perspective with their diagram references. NAME what should be kept, what could not be checked and which decisions the user needs to make.
