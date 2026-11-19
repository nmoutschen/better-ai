# Eval principles

Use these principles to write or change the eval cases and graders of a skill. They are the author's choices for how skills are measured. `README.md` says how the harness works; this file says what each grader is for.

## 1. Grade with a script what a script can decide

GRADE with a script the facts an exact comparison decides: the diff, the files that must not change, a hidden check that the result works, whether a test the agent wrote fails once the bug is back, and exact values in a result, such as a total, a date or a word limit. GRADE with a script, too, what a pattern finds in the transcript's tool calls, such as which of the skill's own files the agent read. DO NOT grade with a pattern what a correct answer may say in other words: that is meaning, for the judge.

KEEP hidden checks out of the sandbox until grading, and RUN them on a copy of the final tree. A hidden check FAILS on the untouched repository, unless the case states why it passes there.

## 2. Grade with an LLM judge only what needs reading

USE the judge for what only reading can decide: the meaning of a text, in the reply or in a file the agent wrote, such as whether an email keeps a fact or a checklist puts its steps in a valid order; whether the agent asked before building and what it asked; whether its claims are true; whether it explained or held back; and whether it ran a check after its last edit to the files that check exercises.

GIVE the judge the request as the user wrote it, not the condition's prompt, the transcript as numbered steps, the final reply, the diff and the notes the agent wrote. RUN it on a different model from the agent's, with no tools. ITS last line is the verdict; anything else scores 0.

WRITE each rubric for one case and one rule: the planted facts, the numbered conditions to PASS, the conditions that FAIL, and what does not count. GRADE the outcomes the user asked for and the case's own rule. DO NOT fail an agent for a misstep it corrected itself, or for a true remark about something the user did not ask about.

## 3. Pair every judged case with a script check

GIVE every case at least one script check, so that an agent that does nothing, or says it did the work without doing it, cannot pass on the judge alone. IN a case about how the agent talks, such as how much it explains, a hidden check that the requested fix works carries the result, and the judge carries only the talk.

## 4. Trust the judge only once checked

COUNT judge verdicts as results only once hand labels, given blind to the condition, have been compared with them. REPORT that agreement with the results. WHEN the judge and a label disagree, FIX the rubric if the rubric caused it, then label again.

## 5. Grade capabilities, not one harness's tools

WRITE cases, rubrics and graders around the capabilities a skill names, such as reading a file, running a command, asking the user or starting a sub-agent, not around one harness's tool names. A question asked in plain text counts as asking; a file printed by a command counts as read; any way the harness starts a sub-agent counts. A script MAY grade an exact fact in the transcript, such as which file a tool call opened, even though tool calls differ between harnesses: MATCH every tool the harness offers for that capability. KEEP every harness fact, such as tool names and where the harness installs skills, in the one adapter for that harness, and IMPORT it into graders. DO NOT write harness facts in graders or case files, so that adding a harness changes only its adapter.

DO NOT fail an agent for doing what its harness requires, such as a permission step. WHEN a case depends on a capability the harness lacks, MARK the run as not applicable, not as failed.

REPORT results as results for the harness and model they ran on. A result in one harness is not a result for the skill in every harness.
