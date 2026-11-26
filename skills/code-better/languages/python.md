# Language: Python

The repository's Python version, environment, lint and type settings, test runner and CI commands come first: where they differ from this file, they win.

## 1. Before you edit

- USE the project's interpreter and environment, such as its virtual environment, uv, Poetry or tox, for every command.
- CHECK the distribution name of each dependency you add against the name you import: they can differ.

## 2. While you build

- RUN the configured linter and type checker on the changed files, such as `ruff check` and `mypy` or `pyright`.
- RUN the focused test: `pytest <path>::<test> -x`, or `pytest -k '<expression>'`. `pytest --lf` runs the last failures again, and the whole suite when none are stored.
- WHERE the project's tests allow it, TEST with the real objects and value shapes the code receives, not stand-ins for them: a missing attribute or a wrong type at an interface is a common failure that stand-ins hide.

## 3. Before you hand back

- RUN the project's full lint, type and test commands as its CI runs them, including the tests of the error paths the change touches.
- RUN the changed entry point in an environment built only from the declared dependencies, such as a fresh virtual environment, `uv run --isolated` or CI: an import of an undeclared dependency passes where the package happens to be installed.
- WHEN the change adds or updates a dependency, RUN the project's dependency scan, such as `pip-audit`.
- TIME the run with and without `pytest -n` from pytest-xdist, and USE it only IF it is faster: each worker collects the tests and repeats session setup.

## 4. Review once the checks pass

These pass the linter and the type checker and can still be wrong. CHECK each in the diff:

- **Type escapes.** Each new `Any`, `cast` or `# type: ignore`: the evidence behind it. A `cast` checks nothing at runtime. SCOPE each ignore to its error code, such as `# type: ignore[attr-defined]`.
- **Errors.** A bare or broad `except`, an exception caught and dropped, and what the caller sees when the operation fails. TEST one failing operation.
- **Resources and defaults.** Files, connections and locks closed on the failure path too, with `with` or `finally`. A mutable default argument.
- **Async.** A coroutine that is never awaited, a task created without keeping a reference to it, a blocking call inside async code, and how cancellation and failures reach the caller.

## 5. Checks to add when the change calls for them

WHEN the change calls for one of these checks, USE its tool IF the project already uses it. OTHERWISE, LIST the check and its tool as a proposed next step: a new test tool is a choice for the project.

| WHEN the change | Check | Bound it by |
|---|---|---|
| applies one rule to several distinct values | `pytest.mark.parametrize` with the values that exercise new behaviour, not every combination |  |
| holds a rule over many inputs, such as a round trip or a result that stays the same when applied twice | a Hypothesis property test (`@given`) | `max_examples`, and a time limit on the test run, since replay and shrinking add calls |
| depends on a sequence of operations | a Hypothesis `RuleBasedStateMachine` against a simple model | `stateful_step_count` |
| shares state between threads, or depends on the order of async operations | no tool in common use controls the schedule: TEST each order you can name, forcing it with `threading.Barrier` or `asyncio.Event` |  |
| parses input from outside the program | an Atheris fuzz target | libFuzzer's `-runs` or `-max_total_time` |
| changes the public API of a published package | `griffe check` against the last release, and the tests of the code that calls it |  |
| needs evidence that the tests catch faults | mutmut or Cosmic Ray on the changed module | it is slow: run it on the changed module only |
| holds a contract worth proving | CrossHair on the contract, in deterministic code, or Nagini; a clean CrossHair run is bounded evidence, not a proof | CrossHair's time limit |
