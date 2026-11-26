# Language: Rust

USE the repository's toolchain, features, lint settings, test runner and CI commands first: where they differ from this file, they win. TREAT this file as a guide, not a rule.

## 1. Before you edit

- READ the imports, constructors, trait implementations and call sites around the code before you change a signature: most failed builds come from names, paths and methods a type does not have.
- CHECK each crate you add, by name and version, against `Cargo.toml`, `Cargo.lock` and the crate's documentation for that version. CHECK that each method you call exists in the resolved version and behaves as you expect there.

## 2. While you build

- RUN `cargo check` on the affected crate, with the features and targets the project supports. RUN `cargo test --no-run` WHEN you need the test binary to build too.
- RUN the focused test: `cargo test <name>`, or `cargo nextest run -E '<filterset>'` IF the project uses nextest.

## 3. Before you hand back

- RUN the project's format, Clippy, build and test commands as its CI runs them. IF the project uses nextest, ALSO RUN `cargo test --doc`: nextest does not run doctests.
- WHEN the change adds or updates a dependency, RUN `cargo audit` or `cargo deny check`, whichever the project uses.

## 4. Review once the checks pass

These pass the compiler and Clippy and can still be wrong. CHECK each in the diff:

- **`unsafe`.** The invariant the block relies on, the code that establishes it, the safe API that contains it, and a `# Safety` section on each unsafe function.
- **Ownership workarounds.** A `clone`, `Rc<RefCell<T>>` or `Arc<Mutex<T>>` added to satisfy the borrow checker: CHECK the ownership need it serves. A deep clone can copy large data, and `RefCell` turns a borrow error into a runtime panic.
- **Panics.** `unwrap`, `expect`, `panic!`, indexing and arithmetic that can overflow on a path that can fail: RETURN a `Result` there, and document errors and panics on public functions.
- **Async.** Where blocking work runs, that each lock guard drops before an `.await`, and what state is left IF the future is cancelled between two changes.
- **Discarded errors.** `let _ =` on a `Result`, and errors mapped to a default.

## 5. Checks to add when the change calls for them

| WHEN the change | ADD | Bound it by |
|---|---|---|
| holds a rule over many inputs, such as a round trip or a result that stays the same when applied twice | a property test with proptest or quickcheck | the number of cases and shrink iterations |
| parses input from outside the program | a cargo-fuzz target (needs a nightly toolchain), or bolero | `-runs` or `-max_total_time` |
| shares state between threads | a loom test of the invariant | its preemption bound |
| adds or changes `unsafe` code | a run of the tests under Miri: `cargo +nightly miri test` | it checks only the paths the tests run |
| changes the public API of a published crate | `cargo semver-checks` against the last release | |
| needs evidence that the tests catch faults | `cargo mutants --in-diff <diff file>` on the changed code | it is slow: run it on the diff only, once per task |
| holds a property worth proving, in a project with proof tooling | a Kani harness, or Verus, Prusti or Creusot where the project uses them | solver time; CHECK the specification against the request before you trust a proof |
