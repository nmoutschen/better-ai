# Tests

Run them from the repository root with the standard library only:

```
python3 tests/run.py
```

It runs each `tests/test_*.py` module as its own process, in parallel (`--jobs N`, default the number of CPUs), prints
the whole output of each failing module, then one summary line and the five slowest modules, and exits 1 on any
failure. Name modules to run only those (`python3 tests/run.py test_core`). `python3 -I -m unittest discover tests`
still runs everything in one process, one module after the other.

The exhaustive tests (every wrong value in every field, every exception in every function a command calls, and so on)
run a sample of their cases by default, about one in ten, the same on every run, with at least one case of every class
the test tells apart. Pull requests run that sample. To run every case, as the scheduled CI run does on Mondays and
Thursdays:

```
BETTER_AI_SWEEP=full python3 tests/run.py
```

A test picks its cases with `sweep.cases(items, key=...)` from `tests/sweep.py`; `key` gives an item's class.

The shared command in `src/better_ai/` is run from source by `tests/better.py`: `run(skill, *args, stdin=None, cwd=None,
env=None)` starts it with `python -I`, `src/` on `sys.path` and `BETTER_AI_SKILL` set. Run single modules without `-I`
(`python3 -m unittest tests.test_core`), since `-I` keeps the working directory off `sys.path`.

`tests/test_build.py` and `tests/test_smoke.py` check `tools/build.py` and `tools/smoke.py` on fixture repositories in
temporary folders. The build needs Python 3.12 or later, so on Python 3.10 the tests that build skip themselves (set
`BETTER_AI_PYTHON310` to a Python 3.10 to run the refusal test from a newer one). `tests/pyz.py` has
`build_into(tmp)`, for a test that needs the real `.pyz` files.
