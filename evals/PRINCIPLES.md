# Eval principles

Use these principles to write or change the eval cases and graders of a skill, and to report their results. They are the author's choices for how skills are measured. `README.md` says how the harness works; this file says what each grader is for.

## 1. Grade with a script what a script can decide

GRADE with a script the facts an exact comparison decides: the diff, the files that must not change, a hidden check that the result works, whether a test the agent wrote fails once the bug is back, and exact values in a result, such as a total, a date or a word limit. GRADE with a script, too, what a tool call states exactly, such as the skill's own files a read tool opened. WHERE the fact is which of the skill's files the agent read, and it can be in a shell command, such as a file printed by `cat` or a sub-agent, DO NOT parse the command with a pattern: it misses some reads and invents others. LET the script decide what it can, and ASK the judge about the rest, one call per sample and only when the script found something missing. DO NOT grade with a pattern what a correct answer may say in other words: that is meaning, for the judge.

KEEP hidden checks out of the sandbox until grading, and RUN them on a copy of the final tree. A hidden check FAILS on the untouched repository, unless the case states why it passes there.

## 2. Grade with an LLM judge only what needs reading

USE the judge for what only reading can decide: the meaning of a text, in the reply or in a file the agent wrote, such as whether an email keeps a fact or a checklist puts its steps in a valid order; whether the agent asked before building and what it asked; whether its claims are true; whether it explained or held back; and whether it ran a check after its last edit to the files that check exercises.

GIVE the judge the request as the user wrote it, not the condition's prompt, the transcript as numbered steps, the final reply, the diff and the notes the agent wrote. RUN it on a different model from the agent's, with no tools. ITS last line is the verdict; a reply whose last line is not one scores 0. A judge that timed out, errored or printed no reply is not a score: raise, so the sample is a sample error that `inspect eval-retry` reruns. A hidden check that times out is a fail.

WRITE each rubric for one case and one rule: the planted facts, the numbered conditions to PASS, the conditions that FAIL, and what does not count. GRADE the outcomes the user asked for and the case's own rule. DO NOT fail an agent for a misstep it corrected itself, or for a true remark about something the user did not ask about.

## 3. Pair every judged case with a script check

GIVE every case at least one script check, so that an agent that does nothing, or says it did the work without doing it, cannot pass on the judge alone. IN a case about how the agent talks, such as how much it explains, a hidden check that the requested fix works carries the result, and the judge carries only the talk.

## 4. Trust the judge only once checked

COUNT judge verdicts as results only once hand labels, given blind to the condition, have been compared with them. REPORT that agreement with the results. WHEN the judge and a label disagree, FIX the rubric if the rubric caused it, then label again.

## 5. Grade capabilities, not one harness's tools

WRITE cases, rubrics and graders around the capabilities a skill names, such as reading a file, running a command, asking the user or starting a sub-agent, not around one harness's tool names. A question asked in plain text counts as asking; a file printed by a command counts as read; any way the harness starts a sub-agent counts. A script MAY grade an exact fact in the transcript, such as which file a tool call opened, even though tool calls differ between harnesses: MATCH every tool the harness offers for that capability. KEEP every harness fact, such as tool names and where the harness installs skills, in the one adapter for that harness, and IMPORT it into graders. DO NOT write harness facts in graders or case files, so that adding a harness changes only its adapter.

DO NOT fail an agent for doing what its harness requires, such as a permission step. WHEN a case depends on a capability the harness lacks, MARK the run as not applicable, not as failed.

REPORT results as results for the harness and model they ran on. A result in one harness is not a result for the skill in every harness.

## 6. Name and map cases by behaviour

NAME each case after its situation, such as `order-ref-skipped-tests`, and SET its `rule` to the behaviour it tests, such as `report-accurately`, not to a section number of the skill. Section numbers change when a skill is restructured; the behaviour does not, so results stay comparable across rewrites.

MAP each case to where the skill states that behaviour now, in `source`, and to the skill files a skill run must read, in `reads`. WHEN the skill is restructured, UPDATE `source` and `reads`, and the one-sentence instructions keyed by source, in the same change.

## 7. Grade a skill by its kind

A skill's kind is `metadata.kind` in its frontmatter (see section 6.8 of the repository's `PRINCIPLES.md`). It sets what the cases look for and which conditions run by default.

FOR a **procedural** skill, PLANT a task the workflow covers and GRADE whether each step happened: the documents a step writes, the checks it runs, the sub-agents it starts and waits for, and the skill's own files it must read, listed under `reads`. A case targets one step an agent tends to skip.

FOR a **behavioural** skill, GRADE the qualities its rules ask of the result and of the agent's conduct, not the order of the work. A behavioural skill also does harm by applying a rule where it does not fit, so WRITE two kinds of case:

- a case where the rule should change the result, such as a text whose main point comes last;
- a guard case where applying the rule harms, such as a text that is already clear and must keep its length, its facts and its structure.

A behavioural skill's cases list no `reads`: its rules are in SKILL.md. RUN the `skill-installed` condition as well, which installs the skill and sends the request without its slash command, because agents are meant to load a behavioural skill for the work by themselves. REPORT how often the agent loaded it, and the pass rate with and without it, so a failure to load is told apart from a failure to follow.

## 8. Read the run before blaming the skill

BEFORE changing a skill because a case fails, READ the failing runs: the judge's reasons, the final reply and the transcript. A failure may come from the grader, the case or the harness instead:

- a grader that cannot see what the agent wrote, such as notes in a folder Git ignores;
- a transcript that hides who did a step, such as a sub-agent's work shown as the agent's;
- a check stricter than the rule, such as a file that must stay unchanged when adding a test to it is allowed;
- a harness tool that keeps a run open, such as a scheduled wake-up;
- a request that can be read two ways.

FIX the grader, the case or the adapter WHEN that is the cause, and VALIDATE the case with its scripted runs. CHANGE the skill only for a failure the agent's own behaviour explains.

## 9. Test a skill change on a pilot before a full run

STATE each skill change as a hypothesis: the behaviour it should change, the evidence for it, and the cases that show it. RUN those cases, and a fixed set of about ten cases that covers the skill's main steps, a few times each, and COMPARE them with the same cases before the change. CHANGE one thing at a time where you can. RUN the full eval only once the pilots reach a satisfactory rate, and KEEP the pilot logs to compare against.

## 10. Report results in a pull request by the skill's priorities

A pull request that changes a skill or its cases REPORTS its eval results in this form. Its readers are the public: STATE the results, and DO NOT address the maintainer, such as with a verdict or "your call". DO NOT link private pages or research.

OPEN with one or two sentences that give the result and what was tested, such as "Leaves correct work alone more often (+28 points). No other clear change. Tested on 28 cases with Sonnet 5.5." DO NOT list the harness version, judge agreement, run counts or error counts in the text.

GROUP the cases into the skill's priority categories, in the order `cases/<skill>/priorities.yaml` lists them. WHEN a skill has no such file, ASK the maintainer for the order and WRITE the file before reporting. EVERY case of the skill is in exactly one category. A lower category may lose where a higher one gains, so DO NOT sum or weight categories into one score. A category holds several cases; a rule with one case is not a category.

SHOW two things:

- a chart of the change in each category, new minus old (or skill minus no skill for a new skill), as a dot with its 95% interval over cases, with one note: "A 95% interval crossing zero means no clear change". The case is the unit: AVERAGE a case's runs first;
- a table with the category, its number of cases, the pass rate in percent in each condition, and a centred Change column that holds only a mark and the number: ▲ +28, ▼ −12, or a bare = when the interval crosses zero.

| Category | Cases | No skill | Short skill | Before | After | Change |
| --- | ---: | ---: | ---: | ---: | ---: | :---: |
| 1 Owns the error | 6 | 5% | 60% | 82% | 73% | = |
| 4 Leaves correct work alone | 5 | 40% | 74% | **31%** | **59%** | ▲ +28 |

COPY `.github/PULL_REQUEST_TEMPLATE/eval-results.md` into the pull request description. PRINT the table with `uv run python -m tools.report <logs> --latest --pr --chart chart.svg`, adding `--before <logs of the skill before the change>` for a change to an existing skill, and HOST the chart on the `pr-screenshots` branch. RUN every condition in the table on the same cases with the same number of runs. BOLD the numbers that carry the opening sentence. LEAVE OUT per-rule and per-case rows, cost and p-values.

## 11. Report results in a skill's docs by what it does

A skill's docs page REPORTS its eval results as a short "How it is tested" section: one sentence on what was tested, such as "Tested on 28 situations with Sonnet 5.5 (2026-11-21).", then one row per priority category, in order, with what the skill does and how often it passed. DESCRIBE what the skill does for the reader: DO NOT compare with no skill, and DO NOT add a chart.

| What it does | Passed |
| --- | ---: |
| Says plainly that it made the error | 73% |
| Fixes what the evidence supports, checks the fix, and asks only when blocked | 80% |

TAKE the row text from each category's `does` in `priorities.yaml`, and PRINT the table with `uv run python -m tools.report <logs> --latest --docs`.
