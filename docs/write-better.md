# `/write-better`

Writes or rewrites text so you understand it and can act on it: an answer, a report, a message or a document.

**Before**
> Following a review of the various handoff points between the skills, it appears there may be a few gaps that could be worth considering at some point.

**After**
> Two skills skip a handoff: design-better shows directions before reviewing them, and do-better drops the checks of the skill that made the work.

*An example rewrite: the main point first, in specific words.*

## What it does

- **Names your goal** for the text: understand, decide, do or learn.
- **Puts the main point first** and cuts what you don't need.
- **Uses plain, specific words**, one term per idea, and adds a table or diagram when the text describes how things relate.
- **Follows your `write-for-<name>` guide** when you have one.

For example:

```
/write-better the summary above
```

## Reference

<details>
<summary><b>When to use it</b></summary>

- An agent's answer or report is hard to read or act on.
- You have a document you want rewritten for its readers.
- You want a text reviewed without changes: it then follows [`/review-better`](review-better.md), with its own rules as what to look for.

Use a neighbouring skill instead when:

- You want to learn a topic over several turns: use [`/teach-better`](teach-better.md).
- A long, dense document needs visual panels before it: use [`/show-better`](show-better.md).

</details>

<details>
<summary><b>How to run it</b></summary>

- `/write-better` with no argument rewrites the agent's previous output.
- `/write-better <document>` rewrites that document.
- To review without rewriting, ask for a review of the text.

Example: `/write-better docs/onboarding.md`

Running it does not mean the text needs large changes. A text that already meets the rules keeps its length and structure.

</details>

<details>
<summary><b>What happens</b></summary>

1. **It looks up who will read the text**, from the conversation, project files and memories.
   - If you have a writing guide, such as `write-for-<name>`, it follows it. Where the two conflict, your guide wins.
   - A reading preference you stated wins over its general rules.
2. **It names the goal of the text**: you understand something, learn to do it yourself, take an action, or make a decision.
   - If the goal is unclear, it picks the most plausible one and states it next to the result.
   - It asks only when a wrong goal would waste much of your work.
3. **It writes:**
   - It adds the context you are missing, and says what each plan, file or result it mentions is.
   - It cuts padding and side material.
   - It states links between ideas, and moves details to appendices.
   - It opens with the main point, so you can stop after one or two sentences and still know the result.
   - It shapes the rest by the goal: a summary to understand, a question to attempt first to learn, numbered steps to act, a recommendation in one line to decide.
   - It uses common words, one term per concept, short sentences, exact numbers, and first-person statements of what it is unsure of.
4. **It checks the result.**
   - In a rewrite, it compares with the original. Every number, name, condition, limit and recommendation must still be there and mean the same.
   - It adds nothing the original did not contain.
   - It checks that the opening carries the main point.
   - It checks that you saw each thing the text mentions, or that the text says what it is.

</details>

<details>
<summary><b>What you get</b></summary>

- The rewritten text, or the new text.
- A one-sentence statement of the goal it assumed, if it had to choose one.
- For a review: where the text breaks the rules, the passage, and a proposed rewrite, with the text left unchanged.

It reports only the checks it performed. It does not claim the text is clearer because it reads more fluently.

</details>

<details>
<summary><b>Works with</b></summary>

It calls:

- Your `write-for-<name>` guide, if you have one from [`/interview-me`](interview-me.md).
- [`/ask-better`](ask-better.md) if it must ask about the goal.
- [`/decide-better`](decide-better.md) when the text is for a decision you make.
- [`/review-better`](review-better.md) to review a text without rewriting it.
- [`/teach-better`](teach-better.md) when the goal is to learn over several turns.
- [`/show-better`](show-better.md) to introduce a long, dense document with visual panels.

It is called by most skills, for the text you read:

- [`/code-better`](code-better.md) for its report and explanations.
- [`/design-better`](design-better.md) for the words in an interface and its report.
- [`/research-better`](research-better.md) to present its findings.
- [`/review-better`](review-better.md) for its report.
- [`/show-better`](show-better.md) to check the wording of panels.
- [`/teach-better`](teach-better.md) for explanations, and for answers when you want the result, not a lesson.
- [`/interview-me`](interview-me.md) for the wording of your guides.
- [`/do-better`](do-better.md) to check a correction to text.

</details>

<details>
<summary><b>What it needs</b></summary>

- **Reading the conversation, project files and memories** to know the reader.
- **Asking you.** With a structured question tool, it asks through it. Otherwise, it asks in plain text at the end of its response.
- **Editing the document**, for rewrites of a file.

</details>
