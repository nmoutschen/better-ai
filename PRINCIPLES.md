# Principles

The skills in this repository change how an AI agent works for its user. These principles are the author's preferences for what the skills do and how they are written. They are choices, not research findings. What research shows about agents and readers lives in `sources/` and in the Principles section of each skill. Use these principles to write a new skill or to change an existing one.

## 1. Base each rule on evidence

### 1.1. Research first, then write the skill

EACH skill starts from a research report in `sources/`, produced with `/research-better`. A rule enters a skill only if the report supports it, if this file asks for it, or if it is a stated design inference.

KEEP the evidence boundary in mind when writing a rule. A rule that rests on one study or on practitioner guidance gets softer wording, such as "TREAT this as a guide, not a rule".

### 1.2. Keep the reason with the rule

START each skill with a short Principles section that states the findings its rules depend on. ADD a short reason to a rule when the reason is not obvious, such as "because learners misjudge it".

DO NOT put citations or effect sizes in a skill. They belong in the source report.

### 1.3. Keep the model's training data out of the evidence

The user wants the agent's ability to read and reason, not what it remembers. A skill DOES NOT ask the agent to rely on facts from training data. Research questions and worker briefs DO NOT contain the expected answer.

## 2. Serve the user's GOAL, not the request's surface

### 2.1. Name what the user must be able to do afterwards

EVERY skill names the user's GOAL: what they must UNDERSTAND, LEARN, DO, or DECIDE after the work. The deliverable is only a means to that GOAL.

### 2.2. Being invoked is not a verdict

Invoking a skill tells the agent to apply its method, not what the result must be. `/ask-better` can end without a question. `/show-better` can end with prose. `/do-better` does not assume the user wants a shorter or longer answer. A skill SAYS this explicitly.

### 2.3. Follow the user's stated preferences over general rules

A user's stated preference overrides the skill's general rules. A skill DOES NOT adapt content to a guessed trait, such as a disclosed diagnosis, and DOES NOT treat silence as agreement. The way a user writes, such as their dialect, spelling or fluency, is not evidence of their ability.

DO NOT ask the user to disclose a condition.

WHEN a skill records preferences in memory, RECORD only preferences the user stated about the output, not inferred traits. SAY when a stored preference changes the output.

## 3. Spend the user's effort carefully

### 3.1. Ask only what only the user knows

LOOK UP what the context can answer. ASK the user only about what the context cannot answer.

### 3.2. Make assumptions visible

WHEN proceeding without asking, STATE the assumption next to the result it affects, so the user can correct it without investigating.

### 3.3. More is not better

DO NOT add length, polish, citations, formatting, or features to look thorough.

## 4. Be honest about the work

### 4.1. Report only what was done and checked

REPORT only checks the agent performed. DISTINGUISH meeting the requirements, passing checks, and the user accepting the result. DO NOT simulate a missing tool, such as describing a page that could not be opened.

### 4.2. Do not change the target to pass

DO NOT change requirements, tests, or checks so that the work passes. STOP and explain when a check looks wrong.

### 4.3. State the limits

STATE where evidence is weak, where sources disagree, and what could not be found. Missing evidence stays a gap; it does not become a conclusion.

## 5. Work in any harness

### 5.1. Name capabilities, not tools

A skill NAMES capabilities, such as web search, page fetch, asking the user, sub-agents, or writing files. It MAY give a tool name as an example ("such as `AskUserQuestion`"), but DOES NOT depend on it.

DO NOT depend on a skill, plugin, or feature that exists in only one harness.

### 5.2. Say what to do without each capability

FOR each capability a skill uses, SAY what to do when it is missing: ask in plain text, keep the board in working notes, run workers in batches. DO NOT block the user's harness or change its configuration without permission.

### 5.3. Use the cheapest agent that can do the step

WHEN a skill delegates, cheaper worker agents do the bulk of the work, and the more expensive agent checks and coordinates.

## 6. Write skills that agents follow

### 6.1. Use one instruction style

WRITE instructions as imperatives with the verb in capitals: CHECK, ASK, DO NOT. WRITE conditions as IF or WHEN at the start of the sentence. NUMBER sections so rules can be referenced, such as "section 3.2".

FOLLOW `/write-better` for the wording: plain words, one term per concept, literal statements.

### 6.2. Keep skills short and self-contained

KEEP each SKILL.md well under 500 lines. KEEP common mistakes and their fixes in SKILL.md, not in a reference file the agent may not open.

PUT copyable formats in `templates/`, with placeholders only. DO NOT include example content in templates.

### 6.3. Say how to invoke the skill

START each skill by saying what it does when invoked with an argument and without one.

### 6.4. Link skills instead of repeating them

WHEN a skill needs another skill's method, NAME it ("FOLLOW `/write-better` if available") and GIVE a short fallback for when it is missing.

## 7. Test a skill against not using it

COMPARE a run with the skill against a run without it on the same task. DAMAGE real outputs to check that each judged dimension notices the damage. TIGHTEN a skill when runs show a failure, and record the change and its reason.

TREAT judged scores as a check on the skill, not as evidence about readers.
