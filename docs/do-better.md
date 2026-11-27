# `/do-better`

Corrects work the agent gave you that misses what you wanted, and hands back the corrected work.

> I stopped the page too early, sorry. Both items were accepted and I took that to mean you were done. Restarting it now with the built page so you can send your feedback again.

*A correction from building these docs, in the form this skill asks for: own the error in plain words, say what changes, and fix it.*

## When to use it

- The agent's answer, document, design or code does not do what you asked, and you want it fixed now.
- You rephrased or repeated a request, and the result still misses.
- The agent finds a defect in work it already delivered. It checks that the defect is real, tells you in one sentence what is wrong and what it affects, then fixes it.

`/code-better`, `/design-better` and `/review-better` send a result you reject here, so you may get it without naming it.

Use [`/improve-better`](improve-better.md) instead when you want the fix to last across later sessions, for example in memory, instructions or a skill. `/do-better` corrects the work in front of you.

## What you can do with it

| You want to | Run | You get |
|---|---|---|
| Have the agent find what is wrong itself | `/do-better` | The corrected work, with one sentence on what changed |
| Point at what is wrong | `/do-better the summary dropped the cost comparison I asked for` | The same; your description counts as evidence, not as a full diagnosis |
| Retry after a correction that still missed | `/do-better` again | A fix that checks every requirement and correction so far, and changes its approach where the work went wrong |

In every correction, it:

- **Works out your goal** from the request, your feedback and the context.
- **Finds what is actually wrong** before changing anything, and checks competing explanations.
- **Hands back the corrected work**, checked the way the skill for that work would check it.
- **Asks only when a decision blocks the fix**, with a few concrete choices.

## Your workflow

1. Run it when a result misses, with or without a description of what is wrong.
2. Answer its question if two readings of your request lead to different fixes.
3. Read the corrected work and the sentence on what changed.
4. If it still misses, run it again.

## Reference

<details>
<summary><b>What happens</b></summary>

1. **It rereads the context.** It reads your original request, later corrections, your preferences and memories, and examples you accepted or rejected. It does not ask you to repeat what is already there.
2. **It names your goal.** It separates what you need to understand, decide or do from the deliverable itself, and keeps unknowns as unknowns.
3. **It finds the mismatch.** It compares the work with your request, for example a changed scope, missing information, an assumption stated as fact, or an approach you had rejected. It keeps what was right and changes only what the mismatch affects.
4. **It checks disputed facts.** If your complaint states a fact, it writes down what its work claimed and why, then checks against a source, a test or your earlier words. It changes the work for a fact that holds. If your fact is wrong, it says so once, with the evidence, and follows your decision.
5. **It asks only when it must.** If two readings of your request lead to different fixes, it asks one short question before redoing the work, often with two to four choices you can answer with a word or a number.
6. **It fixes and checks.** It revises the work and checks the fix against your goal and requirements. For code, an interface or text, it checks the fix the way `/code-better`, `/design-better` or `/write-better` check that kind of work. It does not call the fix done until a check has run.
7. **It replies.** It leads with the corrected result, adds one sentence on what changed, and owns its error in plain words, such as "I misread X". It does not blame you, the request or the tools.

If you run `/do-better` again on the same task, it treats the last revision as failed. It lists every requirement from the original request and each correction, checks the work against all of them, and changes its approach at the step where the work went wrong.

</details>

<details>
<summary><b>What you get</b></summary>

- The corrected work, in the same form you asked for.
- One sentence naming what changed.
- Any assumption it made, when that assumption affects how you should judge the result.
- What it did not read, run or change, when it says the fix is complete.

It writes no separate files or records.

</details>

<details>
<summary><b>Works with</b></summary>

- [`/ask-better`](ask-better.md) for the one question it asks when a decision blocks the fix.
- [`/code-better`](code-better.md), [`/design-better`](design-better.md) and [`/write-better`](write-better.md) for checking a fixed piece of code, interface or text.
- `/code-better`, `/design-better` and [`/review-better`](review-better.md) send you here when you reject their result.

</details>

<details>
<summary><b>What it needs</b></summary>

Nothing beyond what the original task used. It reads the conversation and any files the work touched, and checks with the sources, tests or tools available.

- If a tool or permission blocks part of the fix, it delivers what it can and names the blocker in one sentence.
- Running `/do-better` does not let it publish, send messages, delete work or act outside the scope you already gave it.

</details>
