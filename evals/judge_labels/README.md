# Judge labels

Hand labels for judged graders, one file per skill (`<skill>.yaml`). Read a
sample's transcript in Inspect View, decide the grader's verdict yourself, and
record it before looking at the judge's verdict:

```yaml
- sample: clinic-matching-skill   # sample id: <case-id>-<condition>
  epoch: 2                    # which run, when the eval ran with --epochs (default 1)
  grader: judge               # grader key, as in the score (judge, judge_2, any_of.2)
  agent_model: opus           # optional: needed when the logs hold runs of several agent models
  verdict: FAIL               # PASS or FAIL
  note: Asks about the two Alex Kim rows but proposes no outcome to confirm.
```

`uv run python -m tools.report LOG --labels judge_labels/<skill>.yaml` prints
the agreement per rubric (case and grader) and overall. A label must match exactly one run in the logs, by sample, epoch, grader and
`agent_model` when the label names one. A run whose judge errored, and a run that ended in a sample error,
count as matches. A label that matches no run, or several (two models, two logs of the same run), stops the report
before anything prints and names the runs it matched: add `agent_model` or pass `--latest`. A label whose one run
has no verdict is listed with the reason. Labels refer to sample
ids, so keep each file with the logs it was written from, or start a new file
for a new run.
