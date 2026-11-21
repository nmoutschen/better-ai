# `/review-better`

Reviews work, such as text, code, an interface, a plan or a research report, so that each finding leads to a fix, an answer or a decision.

```markdown
- Scenario and step: See it, the caption under the screenshot
- What I did: compared the caption with the image and with SKILL.md 1.5
- What happened: the caption names thumbs up or down; the image shows two
  versions and no thumbs controls (they appear with three or more)
- Why it slows the person: the caption names a control they cannot find
- Proposed fix: drop the thumbs from the caption
```
*A finding from the review of these docs. Each finding names the check behind it and an action.*

## What it does

- **Agrees what the review is for**, and looks for the few problems that would stop the work reaching its goal.
- **Uses a separate reviewer**, from a different model when it can, and backs each finding with a check it ran.
- **Fixes what is simple, asks what only the author knows**, and lays out the options when there are several.
- **Adds your `review-for-<name>` criteria** when you have them.

For example:

```
/review-better docs/design-better.md
```

## Reference

<details>
<summary><b>When to use it</b></summary>

- You want a review of a file, a diff, a pull request, a link or work in the conversation.
- You want findings you can act on, not a long list of remarks.

The method is the same for all work. The skill for the kind of work adds what to look for:

| Work | What to look for comes from |
|---|---|
| Code, a diff or a pull request | [`/code-better`](code-better.md) |
| An interface or a design language | [`/design-better`](design-better.md) |
| A software design, or a system against its design | [`/architect-better`](architect-better.md) |
| Text you read | [`/write-better`](write-better.md) |

For a plan, a specification or a research report, it writes three to six kinds of problem from the work's goal and requirements.

If you rejected a review and want it corrected, use [`/do-better`](do-better.md).

</details>

<details>
<summary><b>How to run it</b></summary>

- `/review-better <work>` reviews that work. The work can be a file, a diff, a pull request or a link.
- `/review-better` with no argument reviews the work in the current conversation. If there is none, it asks you what to review.

Example: `/review-better https://github.com/acme/app/pull/42`

A review can end with no findings. It then says so in one sentence, with what it checked and how.

</details>

<details>
<summary><b>What happens</b></summary>

1. **It names two goals.** One is what the review must let the author do, such as ship, decide or improve. The other is what the work's own reader must do. It reads what the work answers to: the request, requirements, brief, sources, and decisions already made. A decision already made is not a finding. If the work's goal is unclear and nothing answers it, it asks you one question.
2. **It names the author.** If the work belongs to someone other than you or the agent, it proposes changes instead of making them, unless you ask.
3. **It writes a short list** of the kinds of problem that would stop the work from reaching its goal.
4. **A separate reviewer reads the work.** This is a sub-agent that sees the work, the goals and the list, but not the agent's reasoning or verdict. When it can, it uses the most capable model, and a different model from the one that made the work. For a thorough review, or when a miss would be costly, it runs a second independent review. After fixes, it checks the fixes instead of running another full review.
5. **It confirms each finding.** It runs the code, reproduces the problem, opens the source, recomputes the number, or quotes the exact passage. A finding it cannot confirm stays in the report, marked unconfirmed, with what would settle it.
6. **It acts on each finding by kind:**
   - a simple fix with one right answer: it fixes it and lists the fix
   - something only the author knows: it asks
   - several reasonable fixes: it explains them, recommends one, and asks you to choose
   - anything else: it proposes a specific change
7. **It holds a finding you dispute without evidence.** It changes a finding only when your argument adds evidence or shows the finding misread the work. It opens any source you cite before counting it.

</details>

<details>
<summary><b>What you get</b></summary>

A report that leads with whether the work reaches its goal, and what blocks it if not. Then it lists:

- the fixes it made
- the findings, ordered by effect, each labelled **blocking** or **suggestion**, with where, what is wrong, its effect and the action
- questions and choices for the author
- unconfirmed findings, listed separately

It ends with what it did not read, run or check. It adds no praise to soften findings. It names what works only when a fix could remove it.

</details>

<details>
<summary><b>Works with</b></summary>

It calls:

- [`/code-better`](code-better.md), [`/design-better`](design-better.md), [`/architect-better`](architect-better.md) or [`/write-better`](write-better.md) for what to look for, by kind of work.
- Your `review-for-<name>` guide, if you have one from [`/interview-me`](interview-me.md). Its criteria are added, and its blocking criteria become blocking findings.
- [`/decide-better`](decide-better.md) and [`/ask-better`](ask-better.md) when you must choose between fixes.
- [`/write-better`](write-better.md) for the report.
- [`/do-better`](do-better.md) when you reject the review.

It is called by:

- [`/code-better`](code-better.md) for its review step.
- [`/design-better`](design-better.md)'s audit mode and its review of the chosen direction and of each built interface.
- [`/architect-better`](architect-better.md)'s design and audit modes, to confirm the perspective reviewers' findings.
- [`/write-better`](write-better.md) when you ask for a review of a text without a rewrite.

</details>

<details>
<summary><b>What it needs</b></summary>

- **Reading files, running commands and opening sources** to confirm findings.
- **Sub-agents, and choosing their model.** Without sub-agents, it reviews in a separate pass after the work is done. It rereads the goal and the list first, then reads the work as if someone else made it.
- **Asking you.**
- **Editing the work**, for simple fixes in work it may change.

</details>
