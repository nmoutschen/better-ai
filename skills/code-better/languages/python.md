# Language: Python

USE the repository's Python version, environment, lint and type settings, test runner and CI commands first: where they differ from this file, they win. TREAT this file as a guide, not a rule.

## 1. Before you edit

- USE the project's interpreter and environment, such as its virtual environment, uv, Poetry or tox, for every command.
- CHECK each import you add against the declared dependencies, and the distribution name against the import name. CHECK each library call you change against the installed version of that library.

## 2. While you build

- RUN the configured linter and type checker on the changed files, such as `ruff check` and `mypy` or `pyright`.
- RUN the focused test: `pytest <path>::<test> -x`, `pytest -k '<expression>'`, or `pytest --lf` to run the last failures again.
- TEST with the real objects and value shapes the code receives WHERE the project's tests allow it, not stand-ins for them: most failures are a missing attribute or a wrong type at an interface.

## 3. Before you hand back

- RUN the project's full lint, type and test commands as its CI runs them, including the tests of the error paths the change touches.
- RUN the changed entry point in the project's environment: an import of an undeclared dependency fails there and not in your shell.
- WHEN the change adds or updates a dependency, RUN `pip-audit`.
- USE `pytest -n` from pytest-xdist only WHEN a timed run shows it is faster: each worker collects the tests and repeats session setup.

## 4. Review once the checks pass

These pass the linter and the type checker and can still be wrong. CHECK each in the diff:

- **Type escapes.** Each new `Any`, `cast` or `# type: ignore`: the evidence behind it. A `cast` checks nothing at runtime. SCOPE each ignore to its error code, such as `# type: ignore[attr-defined]`.
- **Errors.** A bare or broad `except`, an exception caught and dropped, and what the caller sees when the operation fails. TEST one failing operation.
- **Resources and defaults.** Files, connections and locks closed on the failure path too, with `with` or `finally`. A mutable default argument.
- **Async.** A coroutine that is never awaited, a task created without keeping a reference to it, a blocking call inside async code, and how cancellation and failures reach the caller.

## 5. Checks to add when the change calls for them

| WHEN the change | ADD | Bound it by |
|---|---|---|
| applies one rule to several distinct values | `pytest.mark.parametrize` with the cases that exercise new behaviour, not every combination | |
| holds a rule over many inputs, such as a round trip or a result that stays the same when applied twice | a Hypothesis property test (`@given`) | `max_examples`, and a time limit, since replay and shrinking add calls |
| depends on a sequence of operations | a Hypothesis `RuleBasedStateMachine` against a simple model | `stateful_step_count` |
| parses input from outside the program | an Atheris fuzz target | libFuzzer's `-runs` or `-max_total_time` |
| changes the public API of a published package | `griffe check` against the last release | |
| needs evidence that the tests catch faults | mutmut or Cosmic Ray on the changed module | it is slow: run it on the changed module only, once per task |
| holds a contract worth checking, in deterministic code | CrossHair on the contract, or Nagini where the project uses it | CrossHair's time limit: a clean run is bounded evidence, not a proof |
