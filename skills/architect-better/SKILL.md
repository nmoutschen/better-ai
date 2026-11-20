---
name: architect-better
description: Helps an AI agent design a feature or structural change to a software system, or audit an existing design or the system against it.
argument-hint: "[CHANGE OR AUDIT TARGET]"
metadata:
  kind: procedural
---

# Architect Better

IF invoked with a request or audit target, APPLY the method to that work.
IF invoked without an argument, USE the current task. IF the task is unclear, ASK what change or design to work on.

Being invoked does NOT mean designing now. The work can end with questions or an audit report.

## Principles

1. Models recovering architecture from code miss relationships.
2. Sharing a layout between Before and After, using a live page for debate, and reviewing by perspective on approval are design choices.

## Instructions

FOLLOW these steps in order.

### 1. Understand the change and pick the mode

NAME the user's goal and the system in scope. PICK the mode. Its file is MANDATORY.

| Mode | When | File |
|---|---|---|
| Design | Design a feature or change to a system | [modes/design.md](modes/design.md) |
| Audit | Review an existing design or compare a system with its design | [modes/audit.md](modes/audit.md) |

### 2. Run the mode

READ the mode file and FOLLOW its steps.

### 3. Verify

CHECK that the mode's deliverables match the request and that every required review has handed back. CHECK links, evidence and diagram references. LIST what remains open or unchecked.

### 4. Hand back

REPORT the result and its limits. LINK the deliverables and name any decisions that still need the user.

## General rules

### Ask the user

USE `/ask-better` if available. OTHERWISE, ASK only when the answer changes the design or resolves a material uncertainty in the audit. GIVE the concrete consequence of each option or a proposal the user can correct.

### Files

LOOK in `docs/` for the repo's design location, in `docs/adr/` or `docs/decisions/` for its decision record location, and in its existing specs location or spec tool for its spec location. KEEP the design of a change in its own folder, the change folder, in the design location. KEEP decision records and the spec in their respective locations. WHEN a location has no repo convention, USE `.architect/<change>/` as the change folder and for the spec, and `.architect/<change>/decisions/` for decision records.

### Missing capabilities

IF you cannot do a step, because a call was denied, the harness lacks a tool or a file the step names is missing, MARK the work **not finished**, and SAY which step, WHY, and what it leaves unchecked. DO NOT present that step as done, and DO NOT replace it with a step of your own, such as reviewing the design yourself.

IF the page cannot be served, HOLD the same conversation in the chat.
