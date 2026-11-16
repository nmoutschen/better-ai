# Getting started

Start with `/interview-me`. Most of the other skills then call each other at the right step, so you rarely need to invoke them by name.

## 1. Run `/interview-me` once

```
/interview-me
```

It runs three short interviews about you. You can stop after any of them:

1. `write`: how you read. It writes a `write-for-<name>` skill.
2. `review`: how you review work. It writes a `review-for-<name>` skill.
3. `profile`: how you want agents to work for you. It writes a short text you paste into the always-on instructions of any AI tool.

Why first: [`/write-better`](write-better.md) follows your `write-for-<name>` guide for any text you read, and [`/review-better`](review-better.md) adds your `review-for-<name>` criteria to every review. Without them, both fall back to general rules. Bring real material if you have it, such as a document you liked or a review you wrote: the interview works from examples, not from general questions.

See [`/interview-me`](interview-me.md).

## 2. Work as usual, and name a skill when the task matches

| You want to | Use |
|---|---|
| Build or change code | [`/code-better`](code-better.md) |
| Design or build a page or screen | [`/design-better`](design-better.md) |
| Research a topic from sources | [`/research-better`](research-better.md) |
| Learn a topic so you can use it without AI | [`/teach-better`](teach-better.md) |
| Get a dense document introduced with visual panels | [`/show-better`](show-better.md) |
| Make a decision you will live with | [`/decide-better`](decide-better.md) |
| Review text, code, an interface or a plan | [`/review-better`](review-better.md) |
| Get text you can understand and act on | [`/write-better`](write-better.md) |

You rarely need to call these yourself:

- [`/ask-better`](ask-better.md) decides when to ask you a question, and how to ask it.
- [`/write-better`](write-better.md) writes the reports the other skills hand back.
- [`/review-better`](review-better.md) runs the reviews in `/code-better` and `/design-better`.
- [`/decide-better`](decide-better.md) runs the choices other skills bring you.

## 3. When the result is wrong, use `/do-better`

```
/do-better
```

It recovers what you meant, finds what is wrong, and fixes it. `/code-better`, `/design-better` and `/review-better` hand a rejected result to it.

## 4. Now and then, run `/improve-better`

```
/improve-better
```

It reads past sessions for instructions you repeated and corrections no rule covers, tests candidate changes to memory, instructions and skills, and proposes the ones that pass, or marks one as untested. Nothing changes without your approval. See [`/improve-better`](improve-better.md).
