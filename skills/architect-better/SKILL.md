---
name: architect-better
description: Helps an AI agent design a feature or a structural change to a software system, or audit an existing design or a system against its design, so that the user agrees the structure before it is built, sees each decision with the options it rejected, and hands code-better a spec it can check the code against.
argument-hint: "[CHANGE OR AUDIT TARGET]"
metadata:
  kind: procedural
---

# Architect Better

IF invoked with a change or an audit target as argument, FOLLOW the instructions below for it.
IF invoked without argument, CHECK the design work in the current conversation against the instructions below, THEN continue or correct it. IF there is none, ASK the user what change or design to work on.

Being invoked does NOT mean you must design now. The work can end with questions for the user, with an audit report, or with a report that the change adds no structure and needs no design.

## Principles

1. Models that draw an architecture from code or from requirements find its parts more reliably than the relations between them: they miss relations, invent others, and draw views at the level of code instead of the system's parts. A design with the right structure can still miss requirements or not trace back to them.
2. A quality goal stated as a wish, such as "fast" or "secure", cannot be checked against a design. A scenario with a trigger and an observable response can.
3. Designers who have a workable solution in mind often stop looking for alternatives, prefer familiar solutions, and stick to their first idea.
4. A diagram does not keep why a decision was made or what it rejected, and decision records often leave out their drivers and alternatives.
5. Links that a model draws between requirements and other documents often include false ones, more so on some kinds of document than others.
6. Threat modelling with STRIDE reports many threats that are not real. Starting from the risks finds more of the threats that matter than applying STRIDE to each element in turn.
7. Reviewers who walk the project's most important scenarios through a design find more of its critical faults than reviewers who work through a generic checklist. Reviewers who look for some kinds of problem can miss others.
8. The live page for debating the design, one layout shared by Before and After, the register of box kinds, Attribute-Driven Design iterations, STRIDE for security, LINDDUN for privacy, one reviewer per applicable perspective once the user approves the design, each with its own ranked rules, and the spec in EARS are design choices.

## Instructions

FOLLOW these steps in order, for every change and every audit. DO NOT skip a step because the change looks small.

### 1. Understand the work

NAME the user's GOAL: what they must be able to build, decide or understand once the design or the audit exists. IF the request states a solution, CHECK that it serves the need behind it. IF it works against the GOAL, SAY so once, with one alternative, THEN FOLLOW the user's decision.

READ the repository's documentation: README.md, docs/, CONTRIBUTING.md, AGENTS.md, and its existing designs, decision records, specs and standards. READ the code the change or audit touches, and the earlier conversation.

WHEN sources disagree, FOLLOW the user's instructions, THEN the repo's own files, THEN the existing code, THEN this skill.

LIST what the design depends on that the request and these sources do not state. ASK the user about the gaps that need it, as the general rule [Ask the user](#ask-the-user) says, before you go on.

### 2. Pick the mode

PICK the one mode that fits the work. READ its file: it is MANDATORY, and the next step cannot run without it. LIST any part of the work that needs the other mode as a proposed next step.

| Mode | When | File |
|---|---|---|
| Design | you design a feature or a change to a system | [modes/design.md](modes/design.md) |
| Audit | you review an existing design, yours or someone else's, or compare a system with its design | [modes/audit.md](modes/audit.md) |

### 3. Run the mode

FOLLOW every step of the mode's file, in order. The mode ends once every review it starts has handed back and its findings are handled or listed as open, or once you stop as its limits say.

### 4. Hand back

LEAD with the result, THEN report, USING `/write-better` for the wording if available:

1. The deliverables, each linked: the design doc, the diagram JSON, the decision records and the spec; or, for an audit, the findings by perspective with their diagram references.
2. Each requirement and scenario, and the part of the design that meets it, or that nothing does.
3. The assumptions you made, the requirements still marked guessed, and the decisions and conflicts you asked the user about.
4. Each review's result, as its report states it: the confirmed findings and whether each is handled, the unconfirmed findings, the checks it leaves to the built system, and what it could not check.
5. Proposed next steps, such as `/code-better` with the design and the spec. LIST each with what goes wrong if nobody does it. IF there are none, SAY so.

DISTINGUISH the design meeting its requirements, the reviews leaving no open finding, and the user approving the design. DO NOT claim one from another.

IF the user rejects the result, USE `/do-better` if available. OTHERWISE, CORRECT what their feedback and the requirements show it misses.

## General rules

FOLLOW these rules in every step and every mode.

### Ask the user

ASK the user, USING `/ask-better` if available, in these cases:

- **Gaps.** DECIDE yourself a gap only someone building the change would notice. ASK about a gap that changes what the system stores, who can reach what, what it costs to run, what users see when it fails, or what is hard to undo, such as a data format, a public interface or a dependency. PUT all of them in one message, each with the outcome of each option. FOR every other gap, CHOOSE the most plausible option, MARK it as guessed, and STATE it as an assumption in the hand-back. A fact about someone else that you cannot check, such as whether a team agreed to an interface, is not a gap to assume: REPORT it as unknown.
- **Decisions.** ASK about each decision that changes behaviour, cost, risk or how the system is maintained, with the options, your recommendation, its main reason and its main drawback. USE `/decide-better` if available. IF the user does not read code, DESCRIBE each option by what they would observe or pay.
- **Conflicts.** ASK about two requirements that conflict, a requirement that contradicts a recorded decision or a repo standard, and a requirement that cannot or should not hold as written, with the change you propose. DO NOT design to your own version until it is agreed. ONCE agreed, REVISE the requirement in place.

TREAT a constraint the user set as a requirement. KEEP working on the parts your questions do not affect, EXCEPT where a step says to wait for the user.

### Write the records

WRITE each record of the unit with `python3 <skill dir>/scripts/better.pyz add <unit> <type> --by <your name>`, or `set`. IF it refuses the record, FIX the record and RUN it again. IF it reports busy, RUN it again. DO NOT write the record by hand to get past a refusal.

### Missing capabilities

IF you cannot do a step, because a call was denied, the harness lacks a tool or a file the step names is missing, MARK the work **not finished**, and SAY which step, WHY, and what it leaves unchecked. DO NOT present that step as done, and DO NOT replace it with a step of your own, such as reviewing the design yourself. IF you cannot run commands, MARK the work **not finished** and NAME the records not written.

IF the design page cannot be served, HOLD its conversation in the chat instead, TREAT the user's approval in words as Approve…, and SAY in the hand-back that the page was not used.
