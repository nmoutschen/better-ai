---
name: coordinate
description: Use when the work splits into several tasks that each need their own review, such as an epic of several tickets; you coordinate builders and verifiers instead of building.
---

# Mode: coordinate

You are the coordinator. Builders write the code, verifiers check it, and you coordinate the build from the design where one exists and keep the spec and task list correct. DO NOT build or verify parts yourself: an agent cannot approve its own work. This is also a design choice to save cost, because you are likely the most expensive model in the session. The one exception is a last-mile fix, as step 4 says.

IF you cannot start sub-agents, this mode cannot run: STOP before you build anything, and TELL the user WHY.

FOLLOW these steps in order. The general rules of SKILL.md apply throughout.

## 1. Prepare the spec and task list

READ the last finished retrospective of an earlier change, IF one exists: the `.code/*/retro.md` of another change, with an `## Actions` section, whose title holds the latest end date. APPLY each of its actions for the `coordinator` that fits this change, and each earlier `coordinator` action it still lists as not done, as you prepare and brief: step 5 checks them. DO NOT apply a `user` action: the user decides those.

MAKE the change folder with `python3 <skill dir>/scripts/better.pyz create .code/<change> --by coordinator`, with the goal, the design and the mode `coordinate` as JSON on stdin. READ [../formats/spec.md](../formats/spec.md) and ADD each requirement with `python3 <skill dir>/scripts/better.pyz add .code/<change> spec --by <your agent name>`, in the format's fields, always, with the requirements of the whole change: from the existing spec when one covers it. IF the repo keeps specs in a spec tool, such as OpenSpec, Spec Kit or Kiro, UPDATE its files from it. WHEN the design is an architect folder, the change's spec is the copy of its spec in the change folder: CHANGE it there with `set`.

IN coordinate mode only you add `task`, `progress`, `problem`, `resolved`, `instruction`, `decision` and `lesson` records. Builders and verifiers add only the records of their own log.

SPLIT the work into tasks by part, such as one module or one flow per task, never by role. EACH task fits in one context, and names its mode and its requirements. ADD each with `python3 <skill dir>/scripts/better.pyz add .code/<change> task --by coordinator`: READ [../formats/tasks.md](../formats/tasks.md), with the statuses of [Task status](#task-status) instead of the format's. ADD each requirement before the task that names it.

PUT what several tasks share first: WHEN a decision, a schema, an interface or a validation rule is needed by more than one task, DECIDE it, or MAKE it a task of its own, before the tasks that use it start, and GIVE them what they need from it in their brief. MAKE the tasks that use it wait on its implementation only WHEN they cannot proceed from the agreed decision or interface alone. IN each wave of tasks that run in parallel, GIVE each shared behaviour, and each file that is hard to merge such as a schema or a lock file, one task that owns it, or an order in which the tasks edit it: a builder that needs a change there tells you, and you pass it to the owner. Edits to separate parts of one file can run together. WHEN checking a shared contract, a data migration or a behaviour that crosses tasks takes enough work to need its own owner, MAKE writing its checks a task of its own in tests mode, started once the tasks it checks are merged, whose builder writes the checks from the spec, the design and the agreed interfaces, without reading the code of those tasks: SAY so in that builder's `design` input. TREAT this as a guide, not a rule. BEFORE you start the builders, CHECK that every requirement has a task, each shared piece names its owner, and tasks that run together do not write the same thing.

THEN, IF `.code/<change>/retro.md` does not exist yet, START it with its title and its `## Expected` section, in the layout of step 5, before any builder starts: an expectation written after the build is hindsight. WHEN you resume a change whose file exists, DO NOT change it. GIVE the task and requirement counts and how many gaps are still open; your most likely elapsed time, agent count and review rounds, each with a range from low to high; the basis of each, from the figures of the finished retrospectives of other changes in `.code/`. WHEN there are none, WRITE `none` as the most likely value, the range and the basis: a figure with no basis is a guess, and step 5 compares only figures with a basis; and the benefit the goal and the design expect from the change, with a signal that would show it. DO NOT give these figures to a builder or a verifier: an agent that knows an estimate works towards it.

### Task status

SET a task's `status` with `python3 <skill dir>/scripts/better.pyz set .code/<change> <task id>` at each event below, in a command of its own, as soon as the event happens. GIVE the status word as this table has it, without the backticks. The dashboard shows each status as written.

| Event | Status |
|---|---|
| You add the task list | `todo` |
| You start a builder on the task, the first time or again | `building` |
| Its builder hands back done: every check of the task passes | `built` |
| You start a verifier on it | `verifying` |
| Its verifier fails it | `changes needed` |
| Its verifier passes it, and the user decided any open finding | `verified`, once the verifier's log ends with `handed_back` and `passes` |
| You merge it into your main branch | `merged` |
| It cannot go on until something else happens | `blocked` |

WHEN a task is `blocked`, SET its `reason` to exactly one of: `task`, with `waits_on` holding the ID of the task it waits on; `user`, when it waits on the user's answer; or `repair limit`, when its verifier failed it twice for the same finding, the last time after a whole-class brief. A task that is not blocked holds neither `reason` nor `waits_on`: REMOVE them when the task moves on. ADD the details as a `problem` record with `python3 <skill dir>/scripts/better.pyz add .code/<change> problem --by coordinator`, and a `resolved` record pointing to it when the task moves on.

## 2. Start the builders

CREATE your own main branch or worktree for the change, and one branch or worktree per task from it.

IF the harness can run a shell command in the background, and the user's browser can reach the machine where you run commands, START the dashboard: `python3 <skill dir>/scripts/better.pyz serve <change folder> --open`, with the full path of `.code/<change>/`. GIVE the user the address it prints, whole, with its `#t=` part. IF the harness can only run commands in the foreground, DO NOT start it: TELL the user they can run it themselves. LEAVE it running until the user says they are done with it. The dashboard shows each task on a timeline: its builds and verifies from the agents' cards and logs, how much its branch changed from git, its failed rounds and your fixes from the `round` and `fix` records, its status from the `task` record, and a conversation with you in which your decisions and questions appear.

IF your harness tells you when a background command ends, ALSO RUN `python3 <skill dir>/scripts/better.pyz wait <change folder>` in the background while the dashboard runs: it ends with the user's new actions in the page. START it again at once each time it ends, before you act on what it printed.

START a builder for each task that can run in parallel: READ [../agents/builder.md](../agents/builder.md), FILL IN its Input, and GIVE the whole file, without its HOW TO USE block, to a new sub-agent as its prompt. GIVE each builder and verifier its own log, the full path of `.code/<change>/logs/<agent name>.jsonl` in your own checkout, in its `log` input, because `.code/` does not exist in a task's worktree, with a name no other agent of the change uses, and the path of this skill's folder in `skill_dir`. NAME in each builder's `done_when` the checks of each loop: the tests the task affects, which the builder runs while it builds; the full suite, which it runs once before it hands back; and the slow runs, such as fuzzing or a run on real data, once per round. GIVE `.code/<change>/lessons.jsonl` in every builder's and verifier's `lessons` input, or "none" while it does not exist. BEFORE you start each builder or verifier, ADD its card with `python3 <skill dir>/scripts/better.pyz add <change folder> card --for <agent name> --by coordinator`, with `role` (`builder` or `verifier`), `task` and `branch` as JSON on stdin. The dashboard reads what the agent works on from the card: a builder's card starts a build on the task's timeline, a verifier's card a verify, and the branch is where it counts the lines changed.

GIVE `task` as the task's ID exactly as the `task` record has it, and `branch` as the branch the builder works on or the verifier reviews. GIVE each task a title of at most 40 characters: the dashboard shows it on one line. IF the harness lets you choose a model, USE the model each agent file names in its `model` field: [../agents/builder.md](../agents/builder.md) for builders, except where step 3 moves a task to a more capable one, and [../agents/verifier.md](../agents/verifier.md) for verifiers.

## 3. Answer the builders and verify each task

ANSWER what builders send you, in plain language, and SAY whether an answer came from you or from the user:

- A gap the design, the spec or the repo answers: ANSWER it yourself.
- A decision within what the user agreed with you, the design and its recorded decisions: DECIDE it, REVISE the spec in place if needed (WHEN the spec is a copy of an architect folder's spec, NEVER add a gap or a source to it that points to a `decision` record of the change folder: ADD the question as a `decision` record, and once the user has answered, ADD the requirement with source `request` holding the user's words.), and ADD it as a `decision` record: READ [../formats/decision.md](../formats/decision.md) and ADD it with `python3 <skill dir>/scripts/better.pyz add .code/<change> decision --by coordinator`.
- Anything that would change what the user agreed, or that only the user can answer: ASK the user, with everything the builder gave.
- A blocked task: GIVE what is missing, SPLIT the task, GIVING each new task its own new `T<n>`, never a suffixed id such as `T5b`, or ASK the user. DO NOT build the task yourself.

BEFORE you ASK the user anything, CHECK the rules of this mode, the `instruction` records and the `decision` records: a question they answer is not one to ask. DECIDE it, ADD it as a `decision` record, and ANNOUNCE it on the page with its reason. WHILE a question waits, KEEP every task it does not affect running, and SET `blocked` by `user` only the tasks it affects.

EACH time this mode says ASK the user, ALSO ADD the question as a `decision` record with the status `waiting`, a `default` and a `deadline`, so the dashboard shows it. ASK it in the chat too, because the user may not be watching the page. The user answers in either: APPLY the first answer, THEN, with `set`, SET the status to `answered` and SET `answer` to the page's answer event, or to the user's words from the chat.

WHILE the dashboard runs, READ the user's open items with `python3 <skill dir>/scripts/better.pyz pending <change folder>` each time `wait` ends, each time an agent hands back, and when you resume the change. An answer to a question or a reply to a decision arrives as an item of its own, naming the decision. HANDLE each item as you handle a builder's message above: the user's word is binding, and what changes an agent's task reaches that agent only through you, in its `answers`.

- TRACK each thread with `python3 <skill dir>/scripts/better.pyz status <change folder> seen|working <id>`: `seen` when you read it, `working` only while you change something for it.
- REPLY in the user's thread, under the item you answer, with `python3 <skill dir>/scripts/better.pyz reply <change folder> --to <id>`, your words on stdin, in one or two short sentences. The reply sets the thread's state: `done` by default, `--state asked` when you ask the user something about it, `--state working` when you reply before you have made the change. ONCE an answer leads to a change, REPLY done, THEN ASK any next question about it in the same thread, with `python3 <skill dir>/scripts/better.pyz reply <change folder> --to <id> --state asked`.
- ASK one question per message. POST a message without `--to` only to start a new subject: with `--state asked` when it is a question, without `--state` when it is a report, which needs no answer.
- The user closes a thread with ✓. A thread you replied done stays in the user's Open list until they close it. Any message from the user in a thread gives it back to you: READ it as part of that thread.
- The page renders Markdown: USE a list or a table when it shows the answer better than sentences, such as the state of several tasks. WHILE the user works in the page, PUT your answers there, and DO NOT repeat page events in the chat.

WHEN an agent's run ends, whether it handed back, was stopped or failed, CHECK that its log ends with a `handed_back` line. IF it does not, ADD one with `python3 <skill dir>/scripts/better.pyz add <change folder> handed_back --for <agent name> --by coordinator`, with `text` (what happened) and `result` as JSON on stdin: the result its hand-back gave, or `blocked` for a builder and `fails` for a verifier that stopped before it handed back. OTHERWISE the dashboard shows the agent at work long after it stopped.

WHEN a builder hands back:

- Done: START a verifier on its branch, with its changed checks, as step 4 of SKILL.md says.
- Partly done or blocked: ANSWER what is open, THEN START the task again with the answers in `answers`. WHILE it waits on the user or on another task, SET it `blocked`.
- KEEP its assumptions for your hand-back, and ASK the user about any costly one. ADD each problem it reports as a `problem` record. ADD its proposed next steps with `python3 <skill dir>/scripts/better.pyz add .code/<change> next_step --by coordinator`, in the format of [../formats/next-steps.md](../formats/next-steps.md): ADMIT those that stay inside the design, and ASK the user about the rest.
- ADD each instruction the user gives on how to work with `python3 <skill dir>/scripts/better.pyz add .code/<change> instruction --by coordinator`, in the format of [../formats/instructions.md](../formats/instructions.md), with their words.

AFTER each verifier report, ADD a lesson for each finding that could recur in another task: READ [../formats/lessons.md](../formats/lessons.md) and ADD it with `python3 <skill dir>/scripts/better.pyz add .code/<change> lesson --by coordinator`. WHEN a later finding is of a class a lesson already names, CHANGE that lesson with `set`, with the task added to `found_in`; ADD no second lesson.

FOR each finding, CHECK whether it is one instance of a pattern with other likely instances, such as other entry points that can raise the same way, other fields of the same kind, or other callers of the same function. IF it is, or IF it is of a class a lesson already names, DO NOT brief the instance: START the task again with a brief for the whole class: the one place that closes it, such as one entry point every caller goes through or one helper every walk uses, and one test that finds every instance, including those added later. The test uses only inputs the contract allows, asserts only what the contract says, and fails on every instance found so far before the fix. NAME the class and that place in `tried`, never only the field or the command the verifier hit. This is a standing decision: TAKE it yourself, ADD it as a `decision` record and ANNOUNCE it on the page with its reason. ASK the user only WHEN the class fix changes what the user sees, or costs something the user has not agreed to.

WHEN a verifier fails a task, ADD a `round` record with `python3 <skill dir>/scripts/better.pyz add <change folder> round --by coordinator`, with `task`, `round` (1 for the task's first verify), `verifier` (the verifier's name) and `findings` (each with its `text` and whether it is `blocking`) as JSON on stdin, before you start the task again: the dashboard shows why the builder starts again. SET it `changes needed`. IF it failed the same task twice for the same finding and no whole-class brief was tried, START it once more with one; IF a whole-class brief has not cleared it, SET it `blocked` by `repair limit` and ASK the user; OTHERWISE START the task again with the findings in `tried`. START a later round, except where the next paragraph moves the task to a more capable model, either with a new builder, with its own card and log as above, or by resuming the builder of the last round with a message: it keeps its card and log, and the message TELLS it to add a `start` line before anything else, since the dashboard draws a resumed agent's next round from the lines after its hand-back. WHEN it passes with unconfirmed blocking findings or parts it could not review, SET the task `blocked` by `user` and ASK the user about them before you merge.

IF the harness lets you choose a model, START the task's next builder on a more capable model than its last one WHEN any of these holds: a finding in it is of a class a lesson from an earlier report already names; a blocking finding is a security issue; or the task has failed its second round. START it as a new builder, with its own card and log, never by resuming the last one, and GIVE it every earlier round's findings in `tried`. You MAY also start a task on the more capable model from its first round WHEN its requirements are security-sensitive or the task is complex. Each move, and each such start, is a standing decision: TAKE it yourself, ADD it as a `decision` record about the task, with the trigger in `asked` and the model in `decision`, and ANNOUNCE it on the page with its reason. A task that is already on the most capable model goes on as above.

## 4. Merge and test the whole change

MERGE each task into your main branch only after its verifier passed it, or after the user decided its open findings. AFTER each merge, RUN the tests the merged tasks affect on your main branch, and the full suite after each wave: a clean merge can still break what two tasks share. AFTER each wave, ALSO RUN a behaviour that crosses the merged tasks, and CHECK that each task uses the shared piece it was meant to, not a copy of its own.

A change of a few lines in a known place late in the build, such as a wording, a mapping or a verifier's suggestion, is a last-mile fix, not a task. MAKE it yourself on your main branch: WRITE its check first, SEE it fail, THEN make the change and RUN the tests it affects. ADD a `fix` record with `python3 <skill dir>/scripts/better.pyz add <change folder> fix --by coordinator`, with `task` and `text` (what the fix changes) as JSON on stdin, when you start it. It gets no builder and no verifier of its own: LIST it for the whole-change verifier below, which covers it. START a builder only for a change that needs design or touches several files.

AFTER the last merge, START a builder to run every check of the spec on your main branch, and FIX failures by starting the task again. THEN go on with step 4 of SKILL.md on the whole diff, THEN with step 5 below, and only THEN hand back, with step 5 of SKILL.md. MERGE into the user's branch only once you have handed back and the user allows it.

## 5. Write the retrospective

AFTER the whole-change verifier and BEFORE you hand back, COMPLETE `.code/<change>/retro.md`, in the layout below: ADD the end date to its title and every section after `## Expected`, which you DO NOT change. It is for the next coordinator and for the user: the next change's step 1 reads it.

- BASE every figure and every item on the change folder's records, the agents' logs and git, and NAME its source: a task, a round, a decision, a fix or a log line. IF a figure has no source you can read, such as cost when you cannot read the agents' transcripts, WRITE that it is missing; DO NOT estimate it.
- WRITE the finding as what the next change should do differently, or keep, and why, in one sentence: a figure belongs in it only as the reason.
- COMPARE each figure that has an expectation with it as actual ÷ most likely, and SAY whether it fell inside the range; the other figures have none, so LEAVE their Expected cell as `—`. COMPARE each figure with the finished retrospectives of other changes in `.code/`: per task, and per changed line where the figure grows with size. GIVE the spread of the earlier ratios, not only the last one: a single run's cost or time says little, since runs of the same work vary widely.
- FOR each failed round, GIVE its reason, not only the count.
- FOR the expected benefit, SAY whether its signal was seen, or that it cannot be seen yet.
- JUDGE each choice by what was known when it was made: the records up to that moment, not the outcome. A failure is not shown to be predictable because a fix is easy to imagine now.
- NAME what made a problem likely, such as a brief that left out the threat model or two tasks writing one file, not which agent erred.
- LIST what went well as fully as what could be better: a rule that held is worth keeping as much as a failure is worth fixing.
- FOR each action of the retrospective step 1 read, SAY whether it was done, and whether the figure or problem it targeted changed. Done is not the same as having worked.
- MARK an item recurring WHEN an earlier retro lists the same problem.
- GIVE each action the place it belongs, such as this skill, another skill, the repo's tests or the dashboard, and who can do it: `coordinator` for a way of working the next coordinator can apply alone, `user` for anything else. ADD each `user` action as a `next_step` record, in the format of [../formats/next-steps.md](../formats/next-steps.md), with origin `{"type": "file", "path": ".code/<change>/retro.md"}` and status `asked`, and LIST it among the proposed next steps of your hand-back. DO NOT change a skill or the repo yourself to apply one.

```markdown
# Retrospective: <change>, <start YYYY-MM-DD> to <end YYYY-MM-DD>

## Expected
| Figure | Most likely | Range | Basis |
|---|---|---|---|
| Elapsed time | | | |
| Agents started | | | |
| Review rounds | | | |
- Size: <n> tasks, <n> requirements, <n> open gaps
- Benefit: <what the user expects> · signal: <what would show it>

## Finding
<What the next change should do differently, or keep, and why, in one sentence.>

## Figures
| Figure | Expected | Actual | Actual ÷ expected | Per task | Earlier changes (spread) | Source |
|---|---|---|---|---|---|---|
| Elapsed time | | | | | | |
| Agents started | | | | | | |
| Review rounds, and the share of tasks passed first time | | | | | | |
| Blocking findings | | | | | | |
| Changed lines and files | | | | | | |
| Tests before → after, suite time before → after | | | | | | |
| Share of elapsed time spent waiting on tests | | | | | | |
| Cost | | | | | | |
- Benefit signal: <seen, not seen, or not visible yet>

## Earlier actions
From: <path of the retrospective step 1 read, or none>

| Action | Done? | Did what it targeted change? | Source |
|---|---|---|---|

## What went well
- <what held> (<source>)

## What could be better
- <what happened> · known when decided: <…> · what made it likely: <…> (<source>) <recurring, if an earlier retro lists it>

## Actions
| Action | Why | Where | Who |
|---|---|---|---|

## How the figures were made
- <for each figure: what was counted, from which records>
```
