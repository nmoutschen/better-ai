# Evaluation plan: code-better

Status (2026-11-18): the rule cases, graders and harness are built and have run
on Sonnet 5.5. The harness runs the real Claude Code CLI in a Docker sandbox; a
scripted fake agent runs the whole pipeline over every case and condition without
a model. The judges have not yet been checked against hand labels, so their
scores are provisional. See "Results so far" and "Next steps" below.

## Goal

Measure whether the skill changes what an agent does in the situations its
rules are written for. Each case targets one rule and scores only that rule, so
a result says which instruction works, which does not, and which is not needed.

## Cases

A case is a planted situation: a small repository, a request written as a user
would write it, and the facts the agent should find in the files, such as a
README constraint, a caller with its own test, or a sample payload. Each case
has a `situation` line with the planted fact and the expected behaviour.

The code-better set has 53 cases across the rules that can be tested in one
agent turn: invocation, 1.1, 1.2, 1.3, 1.5, 2, 3, 4.1, 4.2, 5.1, 5.2, 5.4 and
7.1. Each rule has cases where the rule should change the behaviour and, where
it applies, a case where it should not, such as a plain change that needs no
question, design or plan. Rules 1.4, 5.3, 6.1, 7.2 and 8 have no cases yet.

## Graders

Graders split by what they look at:

1. **Code checks grade the result.** Files the task must not change, the size
   of the diff, hidden checks that call the submitted code, and whether a test
   the agent wrote fails once the planted bug is back. These read the Git diff
   and run code; they never interpret the transcript.
2. **A judge grades how the agent worked,** from the transcript: whether it
   read the files before editing, ran the checks on the final code, stopped
   repairing after the same failure twice, asked before building, and reported
   what it ran truthfully. Each rubric names the rule, the planted facts, the
   criteria and what does not count, and the judge runs on a different model
   from the agent.

A case fails an agent only for its own rule. For example, a hand-back case
(7.1) checks that the report is truthful about what was and was not checked;
it does not require the agent to have run a check, which belongs to 5.1 and
5.4, and it requires naming a planted cause only when the agent ran into it.

Earlier versions graded the process with code too (a Python run log, shell
parsing, mutants); that misread honest agents often enough that the process is
now the judge's job. Judge scores count only after the judge has been checked
against hand labels on real transcripts. Every case also has replays of good
and bad runs that the code checks must accept or reject, so a change that
breaks a case shows up before any model run.

## Conditions

- **no-skill:** the request as is.
- **skill:** the skill installed and invoked with `/code-better`. This measures
  what the skill does once loaded; whether it loads by itself is a separate
  test.
- **one-sentence:** the request plus one sentence from the rule's core
  instruction. This shows whether the full skill adds anything beyond the one
  sentence. Rules without a sentence are not run in this condition.

## Development and held-out sets

The current cases are the development set: they were written and repaired
while building the graders, and skill changes may be tested on them. Before
reporting a result, write a held-out set, new situations for the same rules,
written without looking at the agent's transcripts on the development set, and
use it only for the final comparison.

## Budget and rate limits

Runs use a Claude subscription through the real Claude Code CLI, which calls
the API itself; Anthropic's terms point automated use to API keys, so keep
subscription runs small. The plan has weekly limits: one full comparison (53
cases × 3 conditions, one run each, Sonnet agent and judge) used about 1% of a
weekly allowance; three runs per case used about 3%. Run two or three samples
in parallel: ten parallel sessions hit rate-limit (429) errors with an earlier
harness.

## Results so far (Sonnet 5.5, 2026-11-18)

53 cases × 3 conditions × 3 runs (477 samples, about 50 minutes, 0 errors).
Pass rate per case, compared case by case (each case's runs averaged first;
bootstrap 95% interval; sign-flip permutation p-value, Holm-corrected):

| Comparison | Mean difference | 95% interval | p (Holm) |
| --- | --- | --- | --- |
| skill − no-skill | +0.145 | +0.044 to +0.245 | 0.015 |
| one-sentence − no-skill | +0.208 | +0.101 to +0.321 | 0.002 |
| skill − one-sentence | −0.063 | −0.164 to +0.044 | 0.29 |

Readings, all provisional until the judge is checked against hand labels:

- The skill raises the pass rate over no skill.
- The one-sentence condition appends only the sentence for the rule the case
  tests, which tells the agent which behaviour matters; it is not a fair
  comparison with the skill, which must apply every rule. A fair version gives
  every case all the rule sentences.
- Rules 1.2, 4.1, 5.1 and 5.2 pass in every condition: their cases are too easy
  for this model and measure nothing.
- In rule 7.1 the skill condition scored lower (10 of 15 against 14 and 15):
  its reports left out failed attempts or claimed checks that did not run.

Calibration of the cases found and fixed grading errors where a case failed an
agent for another rule's requirement, a rubric required a fact the agent might
never see, and a request named something the planted repository lacked. Claude
Code loads `AGENTS.md` into context itself, so a judge cannot see it being
read: cases that test reading the project's instructions plant them in
`CONTRIBUTING.md`.

## Next steps

1. Fair short-skill condition: every case gets all the rule sentences.
2. Harder cases for rules 1.2, 4.1, 5.1 and 5.2.
3. Hand-label a sample of transcripts in `judge_labels/<skill>.yaml` before
   looking at the judge's verdicts, compare (`tools/report.py --labels`), fix
   rubrics, and report the agreement next to every result.
4. Look at rule 7.1 in the skill: whether the skill's checking guidance makes
   reports less accurate.
5. Cases for the uncovered rules (1.4, 5.3, 6.1, 7.2, 8.x), other models, and
   the held-out set.
