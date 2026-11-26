# Language: Java

The repository's JDK, build wrapper, static checks, test setup and CI commands come first: where they differ from this file, they win.

## 1. Before you edit

- USE the project's build wrapper, `./gradlew` or `./mvnw`, and the Java version it targets. CHECK each API you call exists in that Java version.
- CHECK each Maven coordinate you add, its group, artifact and version, against the repository it resolves from.

## 2. While you build

- COMPILE and RUN the focused test class: `./gradlew test --tests '<Class>'`, or `./mvnw -pl <module> -am -Dtest='<Class>' -Dsurefire.failIfNoSpecifiedTests=false test`.

## 3. Before you hand back

- RUN the project's full check as its CI runs it, such as `./mvnw verify` or `./gradlew check`, with the static checks it configures, such as Error Prone, SpotBugs, PMD or NullAway.
- READ the `javac` warnings on the changed code for raw types, unchecked operations, deprecation and removal. IF the build does not set `-Xlint:rawtypes,unchecked,deprecation,removal`, COMPILE once with it without committing the change: without it, `javac` reports unchecked and deprecated uses only as a summary note, and raw types not at all.
- WHEN the change adds or updates a dependency, RUN the project's dependency scan, such as OWASP Dependency-Check.

## 4. Review once the checks pass

These pass the compiler and the static checks and can still be wrong. CHECK each in the diff:

- **Checker workarounds.** A cast, a raw type or `@SuppressWarnings` added to clear a warning: the evidence behind it. PUT a suppression on the narrowest declaration where it works. USE no raw types in new code.
- **Exceptions.** An empty `catch`, a checked exception caught and dropped, and a wrapped exception that loses its cause.
- **Resources.** Streams, connections and locks closed on the failure path too, with try-with-resources, and the owner that closes them.
- **Futures.** Each returned `Future` or `CompletableFuture` is used, its failure reaches the caller, and each executor the change creates is shut down.
- **Nulls, equality and indexes.** A dereference of a value that can be null, `==` on objects, `equals` without a matching `hashCode`, and index bounds. TEST equality with two objects built separately that should be equal.
- **Shared state.** Fields that several threads use follow one synchronization rule.

## 5. Checks to add when the change calls for them

WHEN the change calls for one of these checks, USE its tool IF the project already uses it. OTHERWISE, LIST the check and its tool as a proposed next step: a new test tool is a choice for the project.

| WHEN the change | Check | Bound it by |
|---|---|---|
| applies one rule to several distinct values | a JUnit `@ParameterizedTest` with the values that exercise new behaviour |  |
| holds a rule over many inputs, such as a round trip or a result that stays the same when applied twice | a property test with the project's library, such as jqwik or QuickTheories | the number of tries |
| depends on a sequence of operations | a jqwik action chain against a simple model | the chain's maximum length |
| shares state between threads, or depends on the order of async operations | a jcstress test of the outcomes, for threads | its iteration settings |
| parses input from outside the program | a Jazzer fuzz target | `-max_total_time` |
| changes the public API of a published package | japicmp against the last release, and the tests of the code that calls it |  |
| needs evidence that the tests catch faults | PIT, with `targetClasses` set to the changed classes | it is slow: run it on the changed classes only |
| holds a contract worth proving | JML checked by OpenJML, or KeY; CHECK the contract for behaviour it leaves out before you trust it |  |

jqwik's terms change from version 1.10. CHECK the installed jqwik version and its terms. IF they forbid use by an AI agent, USE another property-test library the project has, or LIST the check as a proposed next step.
