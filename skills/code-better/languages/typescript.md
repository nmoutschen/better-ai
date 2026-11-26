# Language: TypeScript

The repository's resolved `tsconfig`, lint configuration, test runner, bundler and CI commands come first: where they differ from this file, they win.

## 1. Before you edit

- READ the project's resolved `tsconfig`: which `strict` flags are on, its module and module resolution settings, and whether `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes` are on, since `strict` does not turn them on.

## 2. While you build

- RUN the project's type check, such as `tsc --noEmit -p <project>`.
- RUN the focused tests with the project's runner, such as `vitest related --run <files>`, `jest --findRelatedTests <files>` or `node --test <file>`.
- WHEN you fix a type or lint finding, RUN the behaviour test of that code too: clearing a diagnostic can change what the code does, such as awaiting a promise that used to run on its own.

## 3. Before you hand back

- RUN the project's full type check, typed lint and the full test run as its CI runs them: selecting tests by import misses tests that load the changed file through a computed import.
- WHEN the change touches the build, configuration, modules, imports or path aliases, START the real entry point with the project's runtime or bundler: `paths` does not rewrite emitted imports, and a named import from a CommonJS module can fail under Node.
- WHEN the change adds or updates a dependency, RUN `npm audit`, or the project's package manager's equivalent.

## 4. Review once the checks pass

These pass the type checker and the linter and can still be wrong. CHECK each in the diff:

- **Type escapes.** Each new `any`, `as`, `as unknown as`, non-null `!` or `@ts-ignore`: the evidence behind it. USE `@ts-expect-error` with a reason instead of `@ts-ignore`: it fails once the error it hides is gone.
- **Data from outside the program.** JSON, request bodies, environment variables and stored data: a type assertion is erased and checks nothing at runtime. VALIDATE with the project's parser or validator, and TEST a valid and an invalid input.
- **Promises.** Each promise is awaited, returned or handled. `void` on a promise leaves its rejection unhandled, and so does an async function passed where a callback returns `void`. TEST the rejection. WHEN the order of async operations matters, TEST the order too.
- **Errors and cleanup.** A `catch` variable is `unknown`: NARROW it before use. CHECK that cleanup runs on failure, with `finally` or `using`.
- **Deprecated APIs.** A reference marked `@deprecated`, which typed lint can flag: CHECK the API of the installed version.

## 5. Checks to add when the change calls for them

WHEN the change calls for one of these checks, USE its tool IF the project already uses it. OTHERWISE, LIST the check and its tool as a proposed next step: adding a test tool adds a dependency.

| WHEN the change | Check | Bound it by |
|---|---|---|
| applies one rule to several distinct values | `test.each` or `it.each` with the cases that exercise new behaviour | |
| holds a rule over many inputs, such as a round trip or a result that stays the same when applied twice | a fast-check property test; KEEP a counterexample it finds as a regression test, with its seed and path | `numRuns` |
| depends on the order of async operations | fast-check's scheduler | `numRuns` |
| parses input from outside the program | a Jazzer.js fuzz target | its run count or time limit |
| changes the public API of a published package | an API Extractor report compared with the last release, and the tests of the code that calls it | |
| needs evidence that the tests catch faults | StrykerJS on the changed files, in incremental mode | it is slow: run it on the changed files only |
