# Principles

Use these principles to write a new skill or to change an existing one. The skills in this repository make AI elevate the user and work better with them.

These principles are the author's preferences for what the skills do and how they are written. They are choices, not research findings. What research shows about agents and readers lives in the research reports (see section 1) and in the Principles section of each skill.

## 1. Base each rule on evidence

EACH skill starts from a Markdown research report, produced with `/research-better`. The reports and their research boards are kept outside this repository, in the author's research archive; articles written from them are published at https://w.n14n.dev/. A rule enters a skill only if the report supports it, if this file asks for it, or if the skill states it as a design choice. A rule that rests on one study or on practitioner guidance gets softer wording, such as "TREAT this as a guide, not a rule".

START each skill with a short Principles section that states the findings two or more of its rules depend on. ADD a short reason to a rule when the reason is not obvious, such as "because learners misjudge it". A finding that only one rule depends on goes there, as that rule's reason, not in the Principles section. STATE each finding once. DO NOT describe the research in a skill: no citations, effect sizes, references to studies, or statements about where the evidence comes from, how strong it is, or what it does not cover. They belong in the source report.

A skill DOES NOT ask the agent to rely on facts from its training data. The user wants the agent's ability to read and reason, not what it remembers.

## 2. Serve the user's GOAL, not the request's surface

### 2.1. Name what the user must be able to do afterwards

EVERY skill names the user's GOAL: what they must UNDERSTAND, LEARN, DO, or DECIDE after the work. The deliverable is only a means to that GOAL.

### 2.2. Put the user's stated preferences above the skill's rules

A skill LETS a user's stated preference override its general rules. It DOES NOT adapt content to a guessed trait, DOES NOT treat silence as agreement, and DOES NOT treat the way a user writes, such as their dialect, spelling or fluency, as evidence of their ability. It NEVER asks the user to disclose a condition.

WHEN a skill records preferences in memory, it RECORDS only preferences the user stated about the output, and SAYS when a stored preference changes the output.

## 3. Spend the user's effort carefully

### 3.1. Ask only what only the user knows

A skill TELLS the agent to look up what the context can answer and to ask the user only about the rest. WHEN it lets the agent proceed without asking, it TELLS the agent to state the assumption next to the result it affects.

### 3.2. More is not better

A skill DOES NOT ask for length, polish, citations, formatting, or features that only make the work look thorough.

## 4. Be honest about the work

### 4.1. Report only what was done and checked

A skill TELLS the agent to report only checks it performed, and to distinguish meeting the requirements, passing checks, and the user accepting the result. It FORBIDS simulating a missing tool, such as describing a page that could not be opened.

A skill FORBIDS changing requirements, tests, or checks so that the work passes. It TELLS the agent to stop and explain when a check looks wrong.

### 4.2. State the limits

A skill TELLS the agent to state where evidence is weak, where sources disagree, and what could not be found. Missing evidence stays a gap; it does not become a conclusion.

## 5. Work in any harness

### 5.1. Name capabilities, and what to do without them

A skill NAMES capabilities, such as web search, page fetch, asking the user, sub-agents, or writing files. It MAY give a tool name as an example ("such as `AskUserQuestion`"), but DOES NOT depend on it. A skill also DOES NOT depend on a skill, plugin, or feature that exists in only one harness.

FOR each capability a skill uses, SAY what to do when it is missing: ask in plain text, keep the board in working notes, run workers in batches. A skill DOES NOT tell the agent to block the user's harness or change its configuration without permission.

### 5.2. Use the cheapest agent that can do the step

WHEN a skill delegates, cheaper worker agents do the bulk of the work, and the more expensive agent checks and coordinates.

## 6. Write skills that agents follow

### 6.1. Use one instruction style

WRITE instructions as imperatives with the verb in capitals: CHECK, ASK, DO NOT. WRITE conditions as IF or WHEN at the start of the sentence. NUMBER sections so rules can be referenced, such as "section 3.2".

FOLLOW `/write-better` for the wording: plain words, one term per concept, literal statements.

### 6.2. Keep skills short and self-contained

KEEP each skill self-contained: SKILL.md, its templates and its scripts DO NOT link to or depend on files outside the skill's directory, such as research reports. KEEP each SKILL.md well under 500 lines. KEEP common mistakes and their fixes in SKILL.md, not in a reference file the agent may not open.

BEFORE adding a rule or a Principles bullet to a SKILL.md, LOOK in that SKILL.md for one that covers the same case, and MERGE the new content into it instead. STATE each rule once in a SKILL.md. A template that an agent reads without SKILL.md, such as a worker brief, MAY restate it.

PUT copyable formats in `templates/`, with placeholders only. DO NOT include example content in templates.

### 6.3. Say what invoking the skill means

START each skill by saying what it does when invoked with an argument and without one.

Invoking a skill tells the agent to apply its method, not what the result must be. `/ask-better` can end without a question, and `/show-better` can end with prose. A skill SAYS this explicitly.

### 6.4. Link skills instead of repeating them

WHEN a skill needs another skill's method, NAME it ("FOLLOW `/write-better` if available") and GIVE a short fallback that makes the step work without it, because naming a skill does not make the agent load it. No harness offers a portable way for one skill to declare or call another, so the name in the text is the link.

REFER to what the other skill does, not to its internals, such as its section numbers, wording or output format. A skill that relies on another skill's internals breaks when that skill changes.

PREFER linking another skill at the end of a workflow, and PUT the steps the result depends on before the link. In some harnesses the agent stops when the other skill returns, and the remaining steps never run. TREAT this as a guide, not a rule.

### 6.5. Use a script only for consistent output

ADD a script only when a step must produce the same form whatever the content, such as rendering a page. The agent supplies the content and the script supplies the form, so the agent never sees or reproduces the style. For example, `/show-better` writes a spec and `show.py` renders it. DO NOT add a script for a step the agent can do from instructions.

WRITE scripts with the Python standard library only, so they run with `python3` and need no installs or network access.

### 6.6. Keep each skill's purpose distinct

KEEP each skill's purpose distinct from the other skills', and WRITE a description that says when to use it. Agents confuse skills whose purposes overlap or whose descriptions are vague.

WHEN two skills cover the same kind of work, such as `/write-better` and a user's `write-for-<name>`, SAY in both how they relate: which one applies the general method, and which one adjusts it.
