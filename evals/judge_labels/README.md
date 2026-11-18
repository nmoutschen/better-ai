# Judge labels

Hand labels for judged graders, one file per skill (`<skill>.yaml`). Read a
sample's transcript in Inspect View, decide the grader's verdict yourself, and
record it before looking at the judge's verdict:

```yaml
- sample: clinic-matching-skill   # sample id: <case-id>-<condition>
  grader: judge               # grader key, as in the score (judge, judge_2, any_of.2)
  verdict: FAIL               # PASS or FAIL
  note: Asks about the two Alex Kim rows but proposes no outcome to confirm.
```

`uv run python -m tools.report LOG --labels judge_labels/<skill>.yaml` prints
the agreement per rubric (case and grader) and overall. Labels refer to sample
ids, so keep each file with the logs it was written from, or start a new file
for a new run.
