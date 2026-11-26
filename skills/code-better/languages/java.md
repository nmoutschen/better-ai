# Language: Java

USE the repository's JDK, build wrapper, static checks, test setup and CI commands first: where they differ from this file, they win. TREAT this file as a guide, not a rule.

## 1. Before you edit

- USE the project's build wrapper, `./gradlew` or `./mvnw`, and the Java version it targets.
- CHECK each API you call exists in that Java version and in the declared version of its library. CHECK each Maven coordinate you add, group, artifact and version, against the repository it resolves from.

## 2. While you build

- COMPILE and RUN the focused test class: `./gradlew test --tests '<Class>'` or `./mvnw -Dtest='<Class>' test`.

## 3. Before you hand back

- RUN the project's full check as its CI runs it, such as `./mvnw verify` or `./gradlew check`, with the static checks it configures, such as Error Prone, SpotBugs, PMD or NullAway.
- READ the `javac` warnings on the changed code for raw types, unchecked operations, deprecation and removal.
- WHEN the change adds or updates a dependency, RUN the project's dependency scan, such as OWASP Dependency-Check.

## 4. Review once the checks pass

These pass the compiler and the static checks and can still be wrong. CHECK each in the diff:

- **Checker workarounds.** A cast, a raw type or `@SuppressWarnings` added to clear a warning: the evidence behind it. PUT a suppression on the narrowest declaration where it works, with a reason. USE no raw types in new code.
- **Exceptions.** An empty `catch`, a checked exception caught and dropped, and a wrapped exception that loses its cause.
- **Resources.** Streams, connections and locks closed on the failure path too, with try-with-resources, and the owner that closes them.
- **Futures.** Each returned `Future` or `CompletableFuture` is used, its failure reaches the caller, and each executor the change creates is shut down.
- **Nulls, equality and indexes.** A dereference of a value that can be null, `==` on objects, `equals` without a matching `hashCode`, and index bounds. TEST equality with two objects built separately that should be equal.
- **Shared state.** Fields that several threads use follow one synchronization rule.

## 5. Checks to add when the change calls for them

| WHEN the change | ADD | Bound it by |
|---|---|---|
| applies one rule to several distinct values | a JUnit `@ParameterizedTest` with the cases that exercise new behaviour | |
| holds a rule over many inputs, such as a round trip or a result that stays the same when applied twice | a property test with the project's library, such as jqwik or QuickTheories. jqwik's terms change from version 1.10: CHECK the installed version and its terms before you use it | the number of tries |
| parses input from outside the program | a Jazzer fuzz target | `-max_total_time` |
| shares state between threads | a jcstress test of the outcomes | its iteration settings |
| changes the public API of a published library | japicmp against the last release | |
| needs evidence that the tests catch faults | PIT, with `targetClasses` set to the changed classes | it is slow: run it on the changed classes only, once per task |
| holds a contract worth proving, in a project with proof tooling | JML checked by OpenJML, or KeY where the project uses it | CHECK the contract for behaviour it leaves out before you trust it |
