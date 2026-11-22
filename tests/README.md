# Tests

Run them from the repository root with the standard library only:

```
python3 -I -m unittest discover tests
```

The exhaustive tests (every wrong value in every field, every exception in every function a command calls, and so on)
run a sample of their cases by default, about one in ten, the same on every run, with at least one case of every class
the test tells apart. Pull requests run that sample. To run every case, as the scheduled CI run does on Mondays and
Thursdays:

```
BETTER_AI_SWEEP=full python3 -I -m unittest discover tests
```

A test picks its cases with `sweep.cases(items, key=...)` from `tests/sweep.py`; `key` gives an item's class.

`tests/test_build.py` and `tests/test_smoke.py` check `tools/build.py` and `tools/smoke.py` on fixture repositories in
temporary folders. The build needs Python 3.12 or later, so on Python 3.10 the tests that build skip themselves (set
`BETTER_AI_PYTHON310` to a Python 3.10 to run the refusal test from a newer one). `tests/pyz.py` has
`build_into(tmp)`, for a test that needs the real `.pyz` files.
