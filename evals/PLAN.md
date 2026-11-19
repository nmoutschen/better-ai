# Evaluation plan: code-better

Status (2026-11-19): 79 cases cover every rule of the skill and have run on
Sonnet 5.5 in four conditions. The harness runs the real Claude Code CLI in a
Docker sandbox; a scripted fake agent runs the whole pipeline over every case and
condition without a model. The judge agreed with hand labels on 9 of 10 hard
calls; the one miss was a rubric fault, since fixed. See "Results so far" and
"Next steps" below.

## Goal

Measure whether the skill changes what an agent does in the situations its
rules are written for. Each case targets one rule and scores only that rule, so
a result says which instruction works, which does not, and which is not needed.

## Cases

A case is a planted situation: a small repository, a request written as a user
would write it, and the facts the agent should find in the files, such as a
README constraint, a caller with its own test, or a sample payload. Each case
has a `situation` line with the planted fact and the expected behaviour.

The code-better set has 79 cases covering every rule. Each rule has cases
where the rule should change the behaviour and, where it applies, a case where
it should not, such as a plain change that needs no question, design or plan.
Rules about long or shared work (3, 8.2, 8.3) are planted as one turn of a
longer task, such as a repository with a half-done plan.

Rubrics grade the outcomes the user asked about and the case's own rule. They
do not fail an agent for a mistake it made and then corrected, such as a test
run with a wrong flag that it ran again correctly, for true side remarks about
things the user did not ask about, or for doing what its harness requires, such
as not committing unasked. Each rubric lists its PASS conditions and its FAIL
conditions separately.

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
  instruction. It names the rule the case tests, so its score is an upper bound
  for that sentence, not a fair comparison with the skill. It is a diagnostic,
  not a default condition: run it on the rules where the skill trails the
  short skill, to tell whether the rule's wording or the rest of the skill is
  at fault.
- **short-skill:** a skill with the same name and frontmatter whose body is
  every sentence of `one_sentence.yaml`, installed and invoked like the skill.
  This separates the skill's length from its content.

A default run uses no-skill, skill and short-skill.

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

## Results so far (Sonnet 5.5, 2026-11-19)

79 cases × 4 conditions × 3 runs (948 runs, 0 errors). Each case and condition
uses its latest run with the current rubrics and skill: the no-skill and
one-sentence runs of the first 53 cases date from 2026-11-18 (rule 7.1 re-run
on 2026-11-19); everything else ran on 2026-11-19. Pass rate per case, compared
case by case (each case's runs averaged first; bootstrap 95% interval;
sign-flip permutation p-value, Holm-corrected):

| Comparison | Mean difference | 95% interval | p (Holm) |
| --- | --- | --- | --- |
| skill − no-skill | +0.232 | +0.148 to +0.325 | 0.0005 |
| one-sentence − no-skill | +0.232 | +0.135 to +0.329 | 0.0008 |
| short-skill − no-skill | +0.169 | +0.059 to +0.274 | 0.015 |
| skill − one-sentence | +0.000 | −0.076 to +0.076 | 1.0 |
| skill − short-skill | +0.063 | −0.008 to +0.139 | 0.24 |

Cost per agent run (Claude Code's reported price, judge excluded): no-skill
$0.035, one-sentence $0.035, short-skill $0.041, skill $0.059.

Readings:

- The skill raises the pass rate by 23 points over no skill. The tested rule's
  sentence alone does as well, but only because it names the rule the case
  tests; the short skill, which holds every sentence, gains 17 points, 6 fewer
  than the skill (not significant).
- Rule 4.2 was the skill's weakest rule (6 of 12) because sections 1.3 and 1.5
  let the agent choose error handling and state it as an assumption. Section
  4.2 now asks before building; the skill passes 12 of 12, with no rise in
  needless questions on the invocation cases (12 of 12).
- The skill still trails on 1.5 (asking costly gaps at once: 50% against 67%
  for one sentence) and 3 (planning work that spans sessions: 60% against 93%).
  In the failing runs it assumed a costly gap instead of asking, and started a
  multi-week migration without writing a plan.
- The short skill's 4.2 sentence makes it ask about every unstated failure,
  even when the request already specifies the main ones.
- Rules 1.2, 6.1, 7.1 and 8.2 pass in nearly every condition, even with the
  harder cases: Sonnet already does what they test.
- The 8.2 sentence first said "your raw notes on what you tried"; appended to a
  request for a handover, Sonnet's safeguards refused it as reasoning
  extraction. The reworded sentence and the skill text run normally.

Calibration of the cases found and fixed grading errors where a case failed an
agent for another rule's requirement, a rubric required a fact the agent might
never see, and a request named something the planted repository lacked. Claude
Code loads `AGENTS.md` into context itself, so a judge cannot see it being
read: cases that test reading the project's instructions plant them in
`CONTRIBUTING.md` or `docs/`.

## Next steps

1. Rules 1.5 and 3 in the skill: why the skill under-asks on costly gaps and
   under-plans multi-session work while its own sentences do not.
2. A random batch of hand labels for an overall judge error rate (the first ten
   were chosen where the judge disagreed with itself).
3. Harder cases for 1.2, 6.1, 7.1 and 8.2, other models, and the held-out set.
