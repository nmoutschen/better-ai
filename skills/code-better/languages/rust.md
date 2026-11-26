# Language: Rust

The repository's toolchain, features, lint settings, test runner and CI commands come first: where they differ from this file, they win.

## 1. Before you edit

- READ the imports, constructors, trait implementations and call sites around the code before you change a signature: names, paths and methods a type does not have are a common cause of failed builds.

## 2. While you build

- RUN `cargo check` on the affected crate, with the features and targets the project supports. WHEN you need the test binary to build too, RUN `cargo test --no-run`.
- RUN the focused test: `cargo test <name>`. IF the project uses nextest, RUN `cargo nextest run -E '<filterset>'` instead.

## 3. Before you hand back

- RUN the project's format, Clippy, build and test commands as its CI runs them. IF the project uses nextest, ALSO RUN `cargo test --doc`: nextest does not run doctests.
- WHEN the change adds or updates a dependency, RUN `cargo audit` or `cargo deny check`, whichever the project uses.
- WHEN the change adds or changes `unsafe` code, RUN the tests that reach it under Miri, `cargo +nightly miri test`: it checks only the paths those tests run.

## 4. Review once the checks pass

These pass the compiler and Clippy and can still be wrong. CHECK each in the diff:

- **`unsafe`.** The invariant the block relies on, the code that establishes it, the safe API that contains it, and a `# Safety` section on each unsafe function.
- **Ownership workarounds.** A `clone`, `Rc<RefCell<T>>` or `Arc<Mutex<T>>` added to satisfy the borrow checker: CHECK the ownership need it serves. A deep clone can copy large data, and `RefCell` turns a borrow error into a runtime panic.
- **Panics.** `unwrap`, `expect`, `panic!`, indexing and arithmetic that can overflow on a path that can fail: RETURN a `Result` there, and document errors and panics on public functions.
- **Async.** Where blocking work runs, that each lock guard drops before an `.await`, and what state is left IF the future is cancelled between two changes.
- **Discarded errors.** `let _ =` on a `Result`, and errors mapped to a default.

## 5. Checks to add when the change calls for them

WHEN the change calls for one of these checks, USE its tool IF the project already uses it. OTHERWISE, LIST the check and its tool as a proposed next step: a new test tool is a choice for the project.

| WHEN the change | Check | Bound it by |
|---|---|---|
| applies one rule to several distinct values | one `rstest` test with a `#[case]` for each value, or one test that loops over a table of cases, with the values that exercise new behaviour |  |
| holds a rule over many inputs, such as a round trip or a result that stays the same when applied twice | a property test with proptest or quickcheck | the number of cases and shrink iterations |
| depends on a sequence of operations | a proptest-state-machine test against a simple model | the number of transitions |
| shares state between threads, or depends on the order of async operations | a loom test of the invariant, for threads | its preemption bound |
| parses input from outside the program | a cargo-fuzz target (needs a nightly toolchain), or bolero | `-runs` or `-max_total_time` |
| changes the public API of a published package | `cargo semver-checks` against the last release, and the tests of the crates that call it |  |
| needs evidence that the tests catch faults | `cargo mutants --in-diff <diff file>` on the changed code | it is slow: run it on the diff only |
| holds a contract worth proving | a Kani harness, or Verus, Prusti or Creusot; CHECK the specification against the request before you trust a proof | solver time |
