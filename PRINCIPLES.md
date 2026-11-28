# Principles

Use these principles to write a new skill or to change an existing one. The skills in this repository make AI elevate the user and work better with them.

These principles are the author's preferences for what the skills do and how they are written. They are choices, not research findings. What research shows about agents and readers lives in the research reports (see section 1) and in the Principles section of each skill.

## 1. Base each rule on evidence

EACH skill starts from a Markdown research report, produced with `/research-better`. The reports and their research boards are kept outside this repository, in the author's research archive; articles written from them are published at https://w.n14n.dev/. A rule enters a skill only if the report supports it, if this file asks for it, or if the skill states it as a design choice. A rule that rests on one study or on practitioner guidance gets softer wording, such as "TREAT this as a guide, not a rule".

START each skill with a short Principles section that states the findings two or more of its rules depend on. ADD a short reason to a rule when the agent must apply it to cases the rule does not name, such as "because learners misjudge it". A reason does not make a rule more likely to be followed. A finding that only one rule depends on goes there, as that rule's reason, not in the Principles section. STATE each finding once. DO NOT describe the research in a skill: no citations, effect sizes, references to studies, or statements about where the evidence comes from, how strong it is, or what it does not cover. They belong in the source report.

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

FOR each capability a skill uses, SAY what to do when it is missing: ask in plain text, keep the board in working notes, run workers in batches. A fallback FAILS CLOSED: it DOES NOT quietly put something weaker in place of a step, such as putting the spec in replies when files cannot be written. IF a step cannot run without the capability, the skill SAYS which step, why it cannot run, such as a denied call or a harness without the feature, and what that leaves unchecked, and the agent STOPS there instead of handing back the work. A skill DOES NOT tell the agent to block the user's harness or change its configuration without permission.

### 5.2. Use the cheapest agent that can do the step

WHEN a skill delegates, cheaper worker agents do the bulk of the work, and the more expensive agent checks and coordinates.

## 6. Write skills that agents follow

### 6.1. Use one instruction style

WRITE instructions as imperatives with the verb in capitals: CHECK, ASK, DO NOT. WRITE conditions as IF or WHEN at the start of the sentence. NUMBER steps and sections so rules can be referenced, such as "step 3" or "section 3.2"; NAME each general rule by its heading (section 6.8).

FOLLOW `/write-better` for the wording: plain words, one term per concept, literal statements.

WHEN a rule can say what to do instead of what not to do, WRITE it that way. WHEN a DO NOT stays, because the behaviour has no positive form, SAY what to do instead in the same rule.

STATE the scope of each rule: when it applies, and to what. Agents read rules literally and do not extend a rule from one named case to others.

### 6.2. Keep skills short and self-contained

KEEP each skill self-contained: SKILL.md, its templates, formats and scripts DO NOT link to or depend on files outside the skill's directory, such as research reports. KEEP each SKILL.md well under 500 lines. KEEP common mistakes and their fixes in SKILL.md, not in a reference file the agent may not open.

KEEP the number of rules low: agents follow fewer of them as rules are added, and keep earlier rules better. PUT the rules that matter most first in each section. BEFORE adding a rule or a Principles bullet to a SKILL.md, LOOK in that SKILL.md for one that covers the same case, and MERGE the new content into it instead. STATE each rule once in a SKILL.md. A template that an agent reads without SKILL.md, such as a worker brief, MAY restate it.

PUT each document an agent writes in `templates/` and the shape of each record type in `formats/`, with placeholders only. DO NOT include example content in either. A format opens with the command that adds the record, never with a fill-in block or a heading that holds placeholders.

### 6.3. Say what invoking the skill means

START each skill by saying what it does when invoked with an argument and without one.

Invoking a skill tells the agent to apply its method, not what the result must be. `/ask-better` can end without a question, and `/show-better` can end with prose. A skill SAYS this explicitly.

### 6.4. Link and layer skills instead of repeating them

WHEN a skill needs another skill's method, NAME it ("FOLLOW `/write-better` if available") and GIVE a short fallback that makes the step work without it, because naming a skill does not make the agent load it. No harness offers a portable way for one skill to declare or call another, so the name in the text is the link.

WHEN several skills share a method, such as reviewing, LAYER them. One general skill holds the method, such as `/review-better`. Each skill for a kind of work holds only what that kind of work adds, such as what to look for in code, and NAMES the general skill for the method. The general skill NAMES each of them for what they add. DO NOT copy the method into each skill: a fallback that makes the step work is enough.

REFER to what the other skill does, not to its internals, such as its section numbers, wording or output format. A skill that relies on another skill's internals breaks when that skill changes.

PREFER linking another skill at the end of a workflow, and PUT the steps the result depends on before the link. In some harnesses the agent stops when the other skill returns, and the remaining steps never run. TREAT this as a guide, not a rule.

### 6.5. Use a script only for consistent output

ADD a script only when a step must produce the same form whatever the content, such as rendering a page. The agent supplies the content and the script supplies the form, so the agent never sees or reproduces the style. For example, `/show-better` writes a spec and `better.pyz render` renders it. DO NOT add a script for a step the agent can do from instructions.

A script MAY also check what agents get wrong when they write by hand. `better.pyz check` checks every file an agent writes against its schema (section 6.10), so the rules live in one place and a skill's instructions only say when to run it, with `add`, `set` and `check`.

A script MAY write records for the agent: it stamps the fields an agent would get wrong by hand, such as `at` and `by`, and assigns each `id`, so agents never type them.

WRITE scripts with the Python standard library only, so they run with `python3` and need no installs or network access.

SUPPORT Python 3.10 and newer. KEEP the source in `src/` passing `ruff check` and `ruff format --check` with the settings in `pyproject.toml`: the Scripts workflow runs them, and runs each built `better.pyz` with `--help` on the oldest and newest supported Python. Ruff is a development tool only: DO NOT make a script import it or anything else outside the standard library.

PUT a page's HTML, CSS and JavaScript in files in `src/better_ai/`, next to the module that renders it, not in strings inside the module. The module reads them and fills in the content. DO NOT build markup in Python beyond the parts that depend on the content. KEEP those files passing stylelint and html-validate with the repo's `.stylelintrc.json` and `.htmlvalidate.json`, and the JavaScript passing `node --check`: the workflow runs them over `src/`.

GIVE each script subcommands for its separate tasks, such as `check`, `serve` and `wait`, not flags that change what the script does.

### 6.6. Keep each skill's purpose distinct

KEEP each skill's purpose distinct from the other skills', and WRITE a description that says when to use it. Agents confuse skills whose purposes overlap or whose descriptions are vague.

WHEN two skills cover the same kind of work, such as `/write-better` and a user's `write-for-<name>`, SAY in both how they relate: which one applies the general method, and which one adjusts it.

### 6.7. Give pages that talk to the agent one conversation

WHEN a skill serves a page where the user writes to the agent, such as design-better's canvas and research-better's board, MAKE its conversation work like the others', so the user learns it once:

- EACH thing the user sends, a comment on an element or a message, is an item with a state the agent sets: seen, waiting for you (the agent asked something), working, done. SHOW the state on the item with one design language, the progress bars and a short word, adapted to each page's use: a page shows only the steps its use has, such as no working step where the agent answers at once, and names them for that use, such as Answered for a question.
- The agent's replies NEST under the item they answer. An answer from the user to a question from the agent ENDS the wait and shows as "You answered"; it is part of the item, not a new one.
- EVERY message OFFERS Reply; a reply under a finished item puts it back with the agent. WHEN the user reviews the agent's work on the page, as in design-better, a done item also OFFERS Accept, a brown check next to Reply, and a done or accepted item CANNOT be edited. WHEN the page only shows work the user does not approve, as research-better's board, a done item is finished.
- WHERE the user approves items, Open SHOWS the items not yet accepted and All shows everything. WHERE an answer finishes an item, the page SHOWS one list in time order, without a filter, so an answer does not vanish as it arrives. Items that wait for the user, such as a decision with a deadline, COME LAST in the same list, next to the message box, until the user answers.
- The conversation SITS in a right-hand column of the same width, `minmax(20rem, 24rem)`, with the message box at its foot.
- Live updates NEVER take what the user is typing: a box with text keeps its text and cursor through a redraw, and a new page version loads by itself only while the user is not typing.
- The script GIVES the agent the same subcommands to read and answer: `wait`, `reply --to`, `status`, `pending`.
- The pages SHARE one stylesheet, `page.css`, for the bar, the side column, the conversation, the buttons and the toast. They SHARE the conversation's code too: the `page` module for the log, the server's conversation endpoints and the agent's subcommands, `page.js` for the conversation on the page, the "not watching" and "closed" strips, the approve pattern and the decision-question renderer, and `conversation.schema.json` for the shape of a conversation line; `tests/` tests them. The `schema` module, the validator that checks those lines and every other agent file, and `base.schema.json`, the fields every record starts with, are shared the same way. SHARED code and assets live once in `src/better_ai/` and ship inside each skill's `better.pyz`; the Scripts workflow rebuilds each one and fails if it differs from the committed file. A page's own files add only what that page alone shows, such as a feature only one page has, through the hooks the shared files offer.

The skill TELLS the agent the same rules for its side, in the same words: reply in the page, in one or two short sentences; mark `working` only what it is changing now; and once an answer leads to a change, mark the item done and ask the next question as a new message.

### 6.8. Structure a skill by its kind

A skill is one of two kinds, and its kind sets its structure and how it is evaluated (see `evals/PRINCIPLES.md`):

- A **procedural** skill is a workflow the agent runs as the task itself, such as building code, running research or reviewing work. It fails when the agent skips a step, a file or a sub-agent.
- A **behavioural** skill sets qualities the agent keeps in work it is already doing, such as writing text, correcting earlier work, asking a question or supporting a decision. It fails when the agent does not apply a rule, or applies it where it does harm, such as rewriting text that was already clear.

TELL them apart by how a run fails: IF a run can fail by skipping a step, the skill is procedural. DECLARE the kind in the SKILL.md frontmatter as `metadata.kind: procedural` or `metadata.kind: behavioural`.

Agents skip what a skill leaves vague, what it says only in passing, and what it buries among rules that do not apply to the work.

#### Procedural skills

STRUCTURE a procedural skill so its order and scope are explicit:

- **SKILL.md** HAS, in this order: the lines that say what invoking it means (section 6.3), `## Principles`, `## Instructions`, then `## General rules`.
- **Instructions** OPEN with "FOLLOW these steps in order", and HOLD one numbered `###` heading per step. The heading NAMES the step's action. The order lives in the step numbers: DO NOT write order as "before X, do Y" or "do Y after X" inside rules.
- **General rules** HOLD what applies in every step and every mode, such as when to ask the user, under one `###` heading each. STATE each general rule there only, and DO NOT repeat it in a step or a mode, even as a reminder: a second wording invites agents to treat the two as different rules.
- **A rule that applies to only some modes** GOES in those modes' files, not in SKILL.md. Each mode file HOLDS its own numbered steps, complete enough to follow alone. A mode MAY repeat another mode's wording where both need it, because each is read alone.
- **Every file the agent must read** is NAMED in the step that needs it, with READ and FOLLOW. WHEN the choice of file depends on the work, such as a mode, a template or an agent, GIVE a table with what it is, when it applies, and its file. SAY that a mandatory file is mandatory.
- **Every document the agent writes** is NAMED in the step that writes it, with when to write it, its path, and its template. READ a template only for a document you write.
- **A step that starts a sub-agent** SAYS to wait for its report and what not to do meanwhile, such as writing to the user. Starting is not finishing: agents hand back while the sub-agent still runs.
- **One fallback for a missing capability**, in the general rules, not one per step. A fallback in a step reads as permission to skip that step.

Each point comes from evals of `/code-better`, where agents skipped mode files and the verifier until the steps were numbered and the files named as mandatory, and handed back before the verifier finished until the step said to wait.

#### Behavioural skills

STRUCTURE a behavioural skill so each rule can be checked against the result:

- **SKILL.md** HAS, in this order: the lines that say what invoking it means (section 6.3), `## Principles`, then numbered `##` sections that group the rules by concern, with one numbered `###` heading per rule.
- **Sections** FOLLOW the order in which their rules come up in the work, but each rule applies whenever its condition holds. DO NOT write "FOLLOW these steps in order": a behavioural skill has no step that must run on every use.
- **Each rule** STATES a quality of the result or of the agent's conduct, and when it applies, so that a reader can check a result against it.
- **No modes, sub-agents or pages.** WHEN the work needs one, it is a workflow: PUT it in a procedural skill and NAME that skill (section 6.4), as `/write-better` names `/show-better`.
- **The description** SAYS when the work needs the skill, so that an agent loads it without the user's slash command.

#### Both kinds

- **Plain verbs over coined terms.** WRITE "ASK the user", not a term such as "send up" that needs its own definition.
- **No partial lists that add nothing.** USE "such as" only when the examples define the category; a list of examples that does not change what the agent does is noise.

### 6.9. Give modes and agents one frontmatter

WHEN a skill has kinds of work that need different rules, PUT each in `modes/<name>.md`. WHEN a skill starts other agents, PUT each agent's prompt in `agents/<name>.md`, not in `templates/`. `templates/` holds only documents the agent writes.

START every mode and agent file with this frontmatter, and no other fields:

```yaml
---
name: <the file name without .md>
description: <one sentence: when to use this mode, or what this agent does and who starts it>
---
```

An agent file ADDS:

```yaml
capabilities: [<what it needs, from: read files, run commands, write files, commit, search the web, sub-agents, message the starting agent>]
edits: <true | false — whether it may change the work it is given>
model: <the models to use, as examples from more than one vendor, such as "Fable, Astra or similar" or "Sonnet, Terra or similar">
model_reason: <one sentence: why this model for this agent>
```

CHOOSE each agent's model for its own work, not one rule for all agents of a kind. NAME the top tier, such as Fable or Astra, only for work that a strong model misses and where a miss is costly; NAME a cheap or mid-level model, such as Haiku or Sonnet, for mechanical work. BASE the choice on evidence where there is some, such as an eval of the agent on several models, and SAY in `model_reason` when there is none.

AFTER the frontmatter, an agent file HAS these sections, in this order: `## Input`, the named fields the starting agent fills in, each required; `## Messages`, only when the agent sends messages while it works or is limited in the messages it may send or act on: what it tells the starting agent, in plain words; `## Output`, what its one hand-back must contain. The input is strict, because the agent sees nothing else. Messages and output are plain language, because how agents talk depends on the harness: the starting agent's skill or mode SAYS how it acts on each kind of message and each outcome.

### 6.10. Store agent files as typed JSON

APPLY this to every file a skill writes for agent bookkeeping, for the conversation between a page and an agent, or for agents to read each other's work. A document a person reads as a deliverable stays Markdown: a design, a brief, a research report, an interview guide, an agent's prompt.

CHOOSE the container by who edits it:

1. ONE agent edits it and it holds many records: a JSONL file.
2. SEVERAL agents edit it at once and it holds many records: a folder of `<id>.json` files, one record each.
3. It holds one group of information: a single JSON file.
4. A page and ONE agent append to it, one line per write, through one script: a JSONL file. A page is not an agent, so this is not a rule 2 case.

GIVE every kind of file a JSON Schema, `<name>.schema.json`, that lists every field and its type, the allowed values, and the fields that depend on a status. A missing required field is an error, and so is a field the schema does not list: agents invent fields otherwise. KEEP schemas in the source module that uses them, or in the shared source. WRITE records with `better.pyz add` and `set`, which stamp and check them, and RUN `better.pyz check <path>` after a record you wrote by hand; the command that serves a page checks every record, and `add` creates folder entries. KEEP in a module only the checks that need its own knowledge, such as whether a slide can be drawn.

START every record with `type`, `at` (ISO 8601 UTC with Z, when it was first written, never changed), `by` (the agent's name, or `user` for what a page sends for the user; the creator, never changed) and, only on a kind another record points to, `id`. The command stamps `at` and `by` and assigns `id`, so an agent never types them. A kind that nothing points to has no `id`. An `id` is unique in its file or folder; in a folder of `<id>.json` files, the file is named after it.

FOLLOW these conventions in every kind:

- WRITE a missing value as `null`, and a list as an array. WRITE allowed values as exact lowercase strings that keep their words (`"bug fix"`), and field and type names in `snake_case`.
- LET a status drive the record's shape. Keep `status` a flat string, and put a field that exists only in some states at the top level: required in those states and rejected in the others. NEVER make a field null only because of the status.
- WRITE a field that takes different shapes, and is not a status, as an object tagged by `type`, never as a string that mixes an ID with fixed words.
- WRITE each fact once, and store a link on one side only. One exception: a code-better change holds a copy of its architect spec, and from `create` on the copy is the change's spec. A pointer names the other record's `id` in a field of its own, never in free text.
- WRITE the record a pointer names before the pointer, and CHECK that every pointer resolves. NEVER delete a record that others point to: give it a final status, such as withdrawn, with a pointer to what replaces it.
- WRITE one record per line, as ASCII JSON, and rewrite a record edited in place as a whole line. In a page conversation, a line that reuses an item's `id` is a new version of that item, and the latest wins; elsewhere an `id` is never reused.
- CREATE a folder entry with `add`, which makes it exclusively: it never overwrites an existing `<id>.json` and continues the counter from the highest existing ID.
- SHOW a record that fails its schema, with its file and line, and the records that pass; one bad record never hides the rest. A reader RETRIES once before it reports a parse error, in case it read a file mid-write. A page event the script rejects KEEPS the user's text on the page and SHOWS the reason, never "closed".
