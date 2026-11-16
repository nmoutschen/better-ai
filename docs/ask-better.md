# `/ask-better`

Decides whether the agent should ask you a question before working, and how to ask it.

> **Who should the docs serve first?**
>
> 1. **Deciding to install**: someone sizing up the plugin: what each skill does and why it is different.
> 2. **Already installed**: someone using a skill: how to run it, what happens, what they get.
> 3. **Both equally**: pages serve both readers.

*A question from planning these docs, in the form this skill asks for: one decision only the user could make, with what each option means.*

## What it does

- **Looks things up first.** It reads the code, documents, earlier conversation and memory, and asks you nothing these answer.
- **Asks only what only you know**, when the answer changes the result and a wrong guess would be costly. Otherwise it goes ahead and states its assumption.
- **Asks early and all at once**, with each question answerable in a few words or by choosing.
- **Raises conflicting instructions** to you instead of picking one.

For example, before a task with an unclear target:

```
/ask-better clean up the old branches
```

## Reference

<details>
<summary><b>When to use it</b></summary>

- Before the agent starts a task that may be unclear.
- When an agent guessed wrong on an earlier task, or asked you things it could have looked up.

Running it does not mean a question is needed. It often ends with the agent going ahead and stating its assumptions.

Other skills use it at the point where they ask you something, so you rarely need to call it yourself (see Works with below).

</details>

<details>
<summary><b>How to run it</b></summary>

- `/ask-better <request>` checks that request before starting it.
- `/ask-better` with no argument checks the current task before more work is done on it.

Example: `/ask-better clean up the old branches`

</details>

<details>
<summary><b>What happens</b></summary>

1. **It lists what the result depends on**: your goal, the exact target, the scope, how you will judge the result, and constraints such as format or deadlines. It treats its own assumptions as unknown.
2. **It looks up what it can.** It reads the code, documents, earlier conversation, memories and instruction files. It does not ask you where a file is or how the project is built.
3. **It looks for conflicts and problems.**
   - A request that names an intent but not a target, such as "fix the config", counts as unknown.
   - Two instructions that cannot both be met get raised to you.
   - If your approach works against your goal, it says so once, with evidence and one alternative, then follows your decision.
4. **It decides whether to ask.** It asks only when all three hold:
   - only you can answer
   - the answer changes what it does
   - a wrong guess would be costly or hard to notice

   Otherwise it goes ahead and states the assumption next to the result, with what you would see if it were wrong.
5. **It asks few, specific questions.**
   - Usually no more than three, all in one message, before the work that depends on them.
   - Each offers two to four concrete options, with its recommendation first and that option's main drawback.
   - Each says why it is asked, so it makes sense on its own.
6. **During the task**, it asks new questions between steps, not in the middle of one. While it waits, it continues only work that does not depend on the answer and is easy to undo.

</details>

<details>
<summary><b>What you get</b></summary>

- Either the work, with each assumption stated next to the result it affects,
- or a short set of questions with options, through a structured question tool if there is one.
- A note when two of your instructions conflict, quoting both.
- One list of requirements that combines your request and your answers. The agent keeps it for the whole task and does not ask again about what you answered.

</details>

<details>
<summary><b>Works with</b></summary>

It calls [`/decide-better`](decide-better.md) when a question asks you to make a decision that is yours.

It is called by:

- [`/code-better`](code-better.md) when it checks requirements with you.
- [`/design-better`](design-better.md) for its questions before building.
- [`/do-better`](do-better.md) when a correction needs a decision from you.
- [`/review-better`](review-better.md) when you must choose between fixes.
- [`/write-better`](write-better.md) when it must ask about the goal of a text.
- [`/improve-better`](improve-better.md) when it asks you to approve or reject each proposal.

</details>

<details>
<summary><b>What it needs</b></summary>

- **Reading files, the conversation, memories and instruction files**, to look up what it can.
- **Asking you.** With a structured question tool, such as `AskUserQuestion`, it asks through it. Otherwise, it asks in plain text at the end of its response.

</details>
