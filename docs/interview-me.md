# `/interview-me`

Interviews you about how you read, how you review work, and how you want agents to work for you, then writes personal guides agents follow.

```markdown
### 3. Put the question for the reader first

- Applies: any reply that needs a decision
- Does not apply: none found
- Evidence: chose — picked the version that opened with the question in 3 of 3 comparisons
```
*An example rule in the `write-for-<name>` guide it writes. Each rule records whether you chose it, showed it or only said it.*

## When to use it

- Once, when you start with these skills: [`/write-better`](write-better.md) and [`/review-better`](review-better.md) follow the guides it writes.
- Agents' text often needs rewriting before you can act on it.
- Agents check work differently from how you would.
- Agents ask, cite, guess or agree in ways you keep correcting.
- A rule in an existing guide no longer fits, or you corrected an agent in a way the guide does not cover.

Use [`/improve-better`](improve-better.md) instead to improve memory, instructions or skills from evidence in past sessions, without an interview.

## What you can do with it

| You want to | Run | You get |
|---|---|---|
| Run all three interviews | `/interview-me` | All three outputs below; you can stop after any interview |
| Teach agents how you read | `/interview-me write` | A `write-for-<name>` skill |
| Teach agents how you review | `/interview-me review` | A `review-for-<name>` skill |
| Tell any AI tool how to work for you | `/interview-me profile` | Short instructions to paste into its always-on settings |
| Change an existing guide | `/interview-me <path to the guide>` | The guide updated |

In every interview, it:

- **Works from your real material.** Documents you liked, reviews you wrote, corrections you made.
- **Asks you to compare concrete samples** instead of asking general questions about your preferences.
- **Shows you each guide before saving it**, so you can correct or delete rules.

## Your workflow

1. **Gather material** before you start: a document you found easy and one you found hard, a review you wrote, two or three times you corrected an agent.
2. **Run it** and share the material in one message.
3. **Answer its questions** about what you did with each piece.
4. **Pick between samples**: two short versions that differ in one thing. Say why.
5. **Check each guide** before it is saved: correct or delete rules, and choose where it goes.

## How long it takes

**How you work with it:** an interview. You are in the conversation the whole time, answering and choosing.

| Work | Rough time |
|---|---|
| One interview | 15–30 min |
| All three | 45–90 min |
| Update to one guide | 5–15 min |

It goes faster when you bring real material, and the guides rest on more evidence.

## Reference

<details>
<summary><b>What happens</b></summary>

1. **It reads what is already known.** It reads your memories, project instructions and any existing guides, and skips what they already answer. If a guide already covers the interview, it updates that guide instead.
2. **It asks for real material, in one message:**
   - `write`: a document you found easy to understand and act on, and one you found hard.
   - `review`: a piece of work you reviewed, with your comments.
   - `profile`: two or three times you corrected an agent's way of working, plus any always-on instructions you already use.

   If you have nothing at hand, it builds comparisons from your current work and says the guide will rest on less evidence.
3. **It walks through the material with you.** It asks what you did with each document, review or correction, and follows up on vague words like "clear" or "too long", surprises and "it depends".
4. **It shows you samples to compare.** Two short versions differ in one thing, and you pick one, say why, and say what you would do next. For `review`, you also mark each criterion as blocking or a preference.
5. **It shows you each guide before saving it.** You correct or delete rules. It reminds you once that your approval makes the guide yours but does not show that it works. The real test is whether later work needs fewer corrections.
6. **It asks where to save each file** and writes them only after you agree.

It does not ask about any condition, diagnosis or who you are, and does not guess your ability from how you write.

</details>

<details>
<summary><b>What you get</b></summary>

- **`write-for-<name>`**: a skill with rules for writing text you understand and act on. You save it where your tool loads personal skills, or in a project's skills folder.
- **`review-for-<name>`**: a skill with your review criteria, split into blocking criteria and preferences. Saved the same way.
- **`profile-for-<name>.txt`**: short first-person instructions to paste into any AI tool's always-on instructions, such as Claude's profile preferences. It covers when to ask, how to source, how to state uncertainty, when to disagree, what to check before reporting work done, and which actions to confirm. It points to your two skills instead of copying them.
- **`profile-for-<name>.md`**: the record behind the profile, kept next to it. Updates start from this file.
- **A report** of what each output was built from, and which interviews you skipped.

Each rule records its scope, one example, and whether you chose it in a comparison, showed it in your material, or only said it. Each guide states that it is about form, criteria or ways of working, and is not a reason for an agent to agree with you.

The profile is loaded into every conversation and can make agents agree with you more. You can remove a rule at any time with `/interview-me <path of the record>`.

</details>

<details>
<summary><b>Works with</b></summary>

- [`/write-better`](write-better.md) reads your `write-for-<name>` skill and follows it on top of its own rules. The guide also applies to [`/show-better`](show-better.md) panels.
- [`/review-better`](review-better.md) adds your `review-for-<name>` criteria to every review, and treats your blocking criteria as blocking findings.
- It uses `/write-better` to word the guides.
- [`/improve-better`](improve-better.md) can later propose changes to these personal skills.

</details>

<details>
<summary><b>What it needs</b></summary>

- **Your material.** Without it, the guides rest on comparisons and what you say.
- **A question tool**, if your tool has one, for offering options. Otherwise it asks in plain text.
- **File access** to save the guides. Without it, it gives each file in a code block with the path to save it to.

It never changes a tool's settings itself. You paste the profile instructions.

</details>
