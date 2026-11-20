# Skill evaluation

Each case plants a small repository with one situation that a rule of a skill
covers, sends Claude Code a request, and grades whether it followed that rule.
The agent is the real Claude Code CLI, run in a Docker sandbox. Code checks
grade the result it left in the repository; an LLM judge reads the transcript
to grade how it worked. See `PRINCIPLES.md` for what a script grades and what
the judge grades, and `PLAN.md` for the plan behind it.

## Layout

```
evals/
  eval.py                 Inspect task: one sample per case and condition
  skill_evals/
    cases.py              case folders -> samples, condition prompts
    agent.py              runs Claude Code (or the scripted fake) in the sandbox
    transcript.py         stream-json -> Inspect messages, usage, cost, time
    sandbox/              Dockerfile, compose.yaml, allowlist proxy
    grading/              scorer.py, files.py (result checks), judge.py, reads.py (skill files read), loaded.py
  tools/
    validate_cases.py     replays good and bad runs through the result checks
    check_coverage.py     skill sections and files the cases point to
    report.py             pass rate per rule and condition, tokens, cost, time, judge agreement
  cases/<skill>/...       the cases
  judge_labels/           hand labels for judge validation
  tests/
```

## Running

Install the pinned packages from `evals/` with `uv sync --python 3.12` and
start Docker. Run from `evals/`:

```sh
uv run inspect eval eval.py -T skill=code-better --epochs 3 --max-samples 6 --no-fail-on-error
```

This runs the default conditions three times per case: no-skill, skill and
short-skill, and for a behavioural skill also skill-installed. The kind is
`metadata.kind` in the skill's frontmatter (see `PRINCIPLES.md`, section 7).

Task options (`-T name=value`):

| Option | Default | Meaning |
| --- | --- | --- |
| `skill` | required | Skill folder name, such as `code-better`. |
| `condition` | by the skill's kind | `no-skill`, `skill`, `one-sentence`, `short-skill`, `skill-installed`, or a list such as `no-skill,skill`. |
| `rule`, `cases` | all | Only one rule (`-T rule=report-accurately`) or some case ids (`-T cases=help-label,meter-zero`). |
| `agent` | `claude_code` | `fake` plays each case's first good replay instead; no model calls. |
| `model` | `sonnet` | Claude Code `--model` for the agent. |
| `judge_model` | a different model | `opus`, or `sonnet` when the agent runs Opus; `none` skips judges. The fake agent defaults to `none`. |
| `timeout` | `1800` | Seconds for one agent run. |

Inspect's own `--model` is not used: the CLI calls the API itself, so the task
sets Inspect's `none` model. A sample whose Claude Code run ends in an error,
such as a rate limit, is a sample error; add `--no-fail-on-error` to let the
rest of the run continue and `inspect eval-retry` to rerun it.

Conditions:

- **no-skill** sends the request as is.
- **skill** copies the skill, as is, into the agent user's
  `~/.claude/skills/<skill>/` and sends `/<skill> <request>`.
- **one-sentence** appends the one-sentence instruction for the case's first
  `source` from `cases/<skill>/one_sentence.yaml`, which holds one sentence per
  section or file of the current skill. Cases whose first source has no
  sentence are not run in this condition. It tells the agent which rule the
  case tests, so
  it is not run by default: use it on the rules where the skill trails the
  short skill, to tell whether the rule's wording or the rest of the skill is
  at fault.
- **short-skill** installs a skill with the same name and frontmatter whose
  body is every sentence of `one_sentence.yaml`, and sends `/<skill> <request>`
  like **skill**. It separates the skill's length from its content.
- **skill-installed** installs the skill like **skill** and sends the request
  as is, so the skill applies only if the agent loads it itself. It runs by
  default for behavioural skills, which agents are meant to load for the work
  without a command.

Sample ids are `<case-id>-<condition>`, such as `help-label-no-skill`.

### Plumbing run without a model

```sh
uv run inspect eval eval.py -T skill=code-better -T agent=fake --max-samples 8
```

The fake agent carries out each case's `replays/good-*.yaml` actions in the
sandbox as the agent user, prints them as Claude Code stream-json, and the rest
of the pipeline runs unchanged: transcript conversion, every grader except the
judge (scored NaN), and the report. Every result check should pass.

## Sandbox

`skill_evals/sandbox/compose.yaml` builds one image (Python 3.12, Node, git, ruff 0.17.5 and
Claude Code at the version pinned in the `Dockerfile`, currently 2.1.327) and
starts a fresh container for each sample. The sandbox sits on an internal
network with no route out; a tinyproxy container forwards HTTPS only to the
hosts in `proxy-allow.txt` (only `api.anthropic.com`). Claude Code runs with
`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`, `DISABLE_TELEMETRY`,
`DISABLE_ERROR_REPORTING` and `DISABLE_AUTOUPDATER` set.

Before the agent starts, the planted files are committed as the starting
commit, owned by the non-root `agent` user, whose home is empty apart from the
skill of the skill condition: no CLAUDE.md, memory or skills of this repository.
Claude Code's own bundled skills are still present, and only the skill under
test is installed, so links to its sibling skills (such as `/ask-better`) take
their fallback. The agent runs
`claude -p "<prompt>" --output-format stream-json --verbose` in `/work` with
`--permission-mode bypassPermissions` and WebSearch and WebFetch disallowed.

## Authentication

The agent and the judge use a Claude subscription token through the real CLI.
Put `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`) or
`ANTHROPIC_AUTH_TOKEN` in `evals/.env`; Inspect loads it into its process
environment, and the harness passes it to the CLI as `CLAUDE_CODE_OAUTH_TOKEN`.
Anthropic's terms point automated use to API keys; a subscription token suits
small personal runs, not large or shared ones.

The token is kept out of the eval log:

- it is written to a 0600 file in the user's sandbox home by a sandbox call
  made with Inspect's event recording switched off, so the call and its input
  are not logged;
- the image's `run-claude` wrapper reads and deletes the file and starts
  `claude` with the token in its environment, so the logged command has no
  token in its arguments or environment;
- Claude Code's output goes to a file that is read back without recording,
  and every text from it, judge records and grader notes included, passes
  through `transcript.redact`, which replaces `sk-ant-…` strings and the token
  value itself.

The agent's own commands inherit the token in their environment (Claude Code's
subprocess scrubbing needs bubblewrap, which cannot create namespaces in an
unprivileged container), so redaction is what keeps it out of the transcript
if the agent prints its environment. After a run, check:
`unzip -p logs/<file>.eval | grep -c sk-ant-` should print 0.

## Budget and rate limits

Each sample is one Claude Code session plus one judge call per judged grader.
Earlier, ten parallel sessions hit rate limits (429) with the previous harness.
Six ran without errors on 2026-11-19; use `--max-samples 6`, and lower it if
samples fail with 429s.
Claude Code retries 429s itself; a run that still fails becomes a sample error.
Expect the token to hit its usage cap during long runs, and plan runs so a cap
stops a run between models rather than in the middle of one.

## Case files

```
cases/<skill>/<case-id>/
  case.yaml   id, rule, source, reads, situation, request, graders, optional validation
  repo/       the planted files, copied into the sandbox
  checks/     hidden files that graders reference by path
  replays/    good-*.yaml and bad-*.yaml runs for validate_cases.py and the fake agent
  earlier/    optional: the agent's earlier work, for skills that correct it, such as do-better
    before/       the files as they were before that work
    message.txt   its commit message, such as the agent's hand-back report
```

With `earlier/`, the sandbox starts with two commits: `before/`, then `repo/`
with `message.txt` as its message. The agent finds its earlier work as the last
commit, and graders compare against that commit, so a case states the earlier
work in the repository instead of in a conversation the harness would have to
replay.

`rule` names the behaviour the case tests, such as `report-accurately` or
`ask-costly-gaps-at-once`, independent of how the skill is organised, so the
report's pass rates per rule compare across rewrites. `source` lists where
that rule lives in the current skill: `SKILL.md#<section>` for a numbered
step, the slug of a named heading such as `SKILL.md#ask-the-user`,
`SKILL.md#invocation`, or another file of the skill folder, such as
`modes/bug-fix.md`. `reads` lists the skill's own files the
skill condition should read in this case, such as its mode file and
`agents/verifier.md`; an entry may be a list of alternatives, of which one is
enough, such as `[modes/feature.md, modes/bug-fix.md]`. `check_coverage.py`
fails on a source or read that does not exist and lists the sections and files
no case points to.
`situation` records the planted fact and the expected behaviour. A grader's
`files` map gives paths relative to the case folder; `cases.py` reads them into
the grader specs. `checks/` is never copied into the sandbox before grading.

Write the request as a user would: keep the user's real constraints and put the
facts the agent should find in the planted files. Each case scores one rule:
its `all` value is the score for that rule, and a case fails an agent only for
its own rule. Cases protect only the planted files the task must not change,
never reject new tests or notes, and accept equivalent evidence.

## Graders

The rule's scorer, `grade_cases`, holds one value per grader and `all`, which
passes when every grader that applies passes. Repeated types get numbered keys (`judge_1`, `judge_2`).
NaN marks a grader that does not apply, such as a judge in a run without
judging; the task's metric averages only the samples where a grader applies.

Result checks (`grading/files.py`) read the submitted tree against the
starting commit or run a hidden check on a disposable copy of it:

| Type | Fields | Pass condition |
| --- | --- | --- |
| `file_unchanged` | `path` | The file is in the starting commit and has no change. |
| `file_keeps` | `path` | Every non-blank planted line is still there, in order, ignoring indentation. |
| `file_contains`, `file_not_contains` | `path`, `pattern` | The file exists and matches, or does not match, the regex. |
| `planted_unchanged` | optional `except` | No planted file changed, except those matching the listed patterns. New files are allowed. |
| `notes_only` | | Every changed or new file is a Markdown note: no code or data changed. |
| `no_commit` | | HEAD is still the planted commit: no commit, reset or rewritten history. |
| `diff_max_lines` | `max` | Added plus removed lines in planted files are within the limit. |
| `command_passes`, `command_fails` | `cmd`, optional `files`, `timeout` | The Bash command exits zero, or nonzero, on a copy of the submitted tree. |
| `catches_bug` | `restore` or `files`, optional `tests` | A test file the agent added or changed passes on the submitted code and fails on an assertion once the bug is back (planted files restored, or replaced by `files`). |
| `any_of` | `graders` | The first listed grader that passes passes it; later ones, such as a judge, do not run. |
| `ran_after_last_edit` | `pattern` | A shell command matching the regex ran after the agent's last edit (`grading/commands.py`). Reads the transcript, not the tree. |

Hidden commands find their files under `$GRADE_FILES` and the planted commit
in `$START_COMMIT`. Use `PYTHONPATH=. python "$GRADE_FILES/check.py"` to let a
hidden test import a planted module. A timeout (60 seconds or the spec's
`timeout`) or a sandbox error scores 0 and is listed under `notes` in the
score metadata.

The judge (`type: judge`, field `rubric`, optional `observe: {cmd: ...}`)
grades how the agent worked: what it read before editing, what it ran on the
final code, whether a test catches the bug, whether it stopped repairing,
asked, or reported truthfully. It is `claude -p` with no tools, run as a
separate sandbox user with an empty home and a judge system prompt. It reads
the request, the transcript as numbered steps (each command with its result
and exit code, each edit, each read with its range), the final reply, the Git
diff against the starting commit, the Markdown notes the agent wrote, and with
`observe` the output of a command run on a copy of the tree. Its last line
must be exactly `VERDICT: PASS` or `VERDICT: FAIL`; anything else scores 0 and
is marked malformed. Score metadata keeps each judge's reply, verdict, model,
tokens and cost under `judges`.

Write each rubric for one case and one rule: name the rule, the planted facts,
the numbered criteria the run must meet, and what does not count. Order
matters only where the rule needs it; the judge is told that a check ran on the
final code when it ran after the last edit to the files it exercises.

## Skill files read

A second scorer, `skill_reads` (`grading/reads.py`), checks in the skill
condition whether the agent read every skill file the case lists under
`reads`, other than `SKILL.md`, which the slash command loads. A read is a
Read tool call on a file in `~/.claude/skills/<skill>/`, or a Bash command
that prints one (`cat`, `head`, `sed`...), by the agent or by a sub-agent; the
tool names and the skills folder come from `agent.py`. It scores 1 or 0, with
the files read and the missing ones in its metadata, and gives no score in
other conditions or in cases that expect no reads. It is a separate scorer, as
Inspect advises for an independent judgment, so the rule's `all` is unchanged.
The report fails a skill run that missed a read and also shows its rule-only
score.

## Skill loaded without a command

A third scorer, `skill_loaded` (`grading/loaded.py`), scores the
skill-installed condition only: 1 when the agent or a sub-agent called the
harness's skill tool with the skill's name, or read the installed SKILL.md, and
0 otherwise. The skill tool's name comes from `agent.py`. The report shows how
many runs loaded the skill and the pass rate with and without it.

## Lint issues added

A fourth scorer, `lint_issues_added` (`grading/lint.py`), observes code quality
in every case and condition without grading it. On a copy of the final tree it
runs `grading/new_lint_issues.py`, which lists the ruff issues in the Python
files the agent added or changed that the planted version of those files did
not have, with a fixed rule set (pyflakes, bugbear and pycodestyle's statement
and syntax errors) that ignores the repository's own configuration. Its value
is the count; runs that change no Python file get no score. The report shows
the mean per condition. The sandbox image ships ruff at the version in
`uv.lock`, so cases can also declare ruff as the project's linter: the `lint-*`
cases grade with the same script, using the repository's own configuration.

## Judge validation

Judge verdicts count only once the judge has been checked against hand labels.
Label judged graders of real runs in `judge_labels/<skill>.yaml` (format in
`judge_labels/README.md`), then:

```sh
uv run python -m tools.report logs/<file>.eval --labels judge_labels/code-better.yaml
```

prints the agreement per rubric and overall.

## Report

```sh
uv run python -m tools.report logs/<dir>/*.eval [more.eval ...] [--latest]
```

prints the pass rate of `all` per rule and condition, the paired comparisons
between conditions, cost and time per condition, the skill files read in the
skill condition (per expected file, and files read where no case expects
them), one line per sample with
tokens (input, output, cache read, cache write), agent cost, judge cost and
time, the totals, any sample errors, and per condition how many runs committed or rewrote
history. Every sample records its commits under `side_actions` in the score metadata; only cases
that use `no_commit` score it. With `--latest`, each case and
condition keeps only the runs of the most recently started log that has it, so
a re-run after a fix replaces the runs it fixes; without it, every run of every
log counts.

## Contributing

Naming: names say what a thing is or does. Do not use letters or codes that
stand for concepts, such as `A`/`B`/`C` for conditions or `r` for a result;
write `no-skill`, `condition`, `sample_result`. This applies to code, case
files, metadata keys and docs alike.

### Local checks

From `evals/`:

```sh
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv run python -m tools.check_coverage code-better
uv run python -m tools.validate_cases code-better
```

Ruff requires docstrings on every module, class and function (Google style),
type annotations, and a complexity of at most 10 per function. Ruff and
pytest skip `cases/`: the planted repositories and hidden checks are
deliberately imperfect code, run only inside a sandbox.

`validate_cases.py` replays every case's runs in a local temporary directory.
Good runs must pass every result check, bad runs and a run that does nothing
must fail one, and each hidden `command_passes` check must fail on the
untouched repository unless `case.yaml` lists it under
`validation.hidden_checks_pass_untouched`. Cases where only the judge can fail
a do-nothing run, such as cases about asking first, set
`validation.do_nothing_fails_only_by_judge`. Top-level judges are skipped; a
judge inside `any_of` is assumed to pass, or to fail when the replay sets
`judge: false`. Rubric wording is not checked by replays: that is what judge
validation is for.
