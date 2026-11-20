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

1. Models recovering architecture from code miss relationships. The recovered view needs a check against the code.
2. Models linking requirements to sources make false matches. Low-confidence links need a human check.
3. Highlighting changes in the diagram makes differences easier to find than showing two diagrams side by side. Evidence for keeping the layout stable is inconclusive.
4. STRIDE findings have modest precision. A one-off review can become a checklist exercise.
5. Tool vendors often make claims without supporting evidence.
6. Design documents commonly cover goals, non-goals, trade-offs, rejected alternatives, drawbacks and unresolved questions. Their shared structure is a convention.
7. Sharing a layout between Before and After, using a live page for debate, and reviewing by perspective on approval are design choices.

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

FOLLOW `/ask-better` if available. OTHERWISE, ASK only when the answer changes the design or resolves a material uncertainty in the audit. GIVE the concrete consequence of each option or a proposal the user can correct.

### Files

FOLLOW the repo's conventions for designs, decision records and specs. USE `.architect/<change>/` when there is no convention. KEEP the user's request word for word in the change folder as `request.md` when writing a design.

### Live page conversation

REPLY in the page, in one or two short sentences. KEEP `working` on the items you are changing now, usually one. WHEN the user's answer leads to a change, MARK the item `done` once the change is in the page, and PUT your next question in a new message.

### Diagram kinds

USE only kinds from the register exposed by `scripts/diagram.py`.

### Missing capabilities

IF a required capability is missing, KEEP the step's purpose and do what you can with the available tools. USE the chat when the page is unavailable, and a separate pass when a reviewer cannot start. IF code-better’s spec template is unavailable, KEEP one EARS rule per row with its ID, source and check. REPORT what was unavailable and what remains unchecked. LABEL a separate pass as your own review.
