# `/improve-better`

Improves what your agent carries from one session to the next: memory, instructions files, skills and workflows.

```diff
 3. LOOK at the rendered page before you show it, and FIX each version that does not load, overlaps or is cut off.
+   FOR new directions, ALSO REVIEW them with modes/review.md before you show them, and FIX or DROP what the review confirms.
```
- **Evidence:** in one session the user asked by hand to review directions before seeing them.
- **Test:** checked against recorded sessions; in another session it would have added a review round.
- **Undo:** delete the added line.

*A proposal from the run that led to these docs: the change, its evidence, its test result and how to undo it.*

## When to use it

- You keep giving the agent the same instruction, or correcting the same mistake.
- You want to find routines the agent repeats by hand, or rules and skills that nobody uses, contradict each other or repeat each other.
- You want to improve one area, such as memory, one skill or one workflow.

Running it does not mean a change is needed. It can end with no proposal, and says so.

Use [`/do-better`](do-better.md) instead when you are pointing at a defect in the work in front of you. Use [`/interview-me`](interview-me.md) when you want the agent to learn how you read, review and want it to work by asking you.

## What you can do with it

| You want to | Run | You get |
|---|---|---|
| Improve your whole setup | `/improve-better` | Up to five tested proposals from recent sessions |
| Improve one area | `/improve-better memory` | Proposals limited to that area |
| Run it on a schedule or at the end of a session | Ask it to set that up | A proposal for how; it sets it up only after you approve |

In every run, it:

- **Finds candidate changes in past sessions.** Instructions you repeated, corrections no rule covers, and rules nothing uses.
- **Tests each change** on past tasks it was not built from, or against what you accepted before.
- **Proposes at most five changes**, each with its evidence, test result and how to undo it, and marks any it could not test.
- **Applies only what you approve**, and keeps a record so later runs can undo or retire a change.

## Your workflow

1. **Run it** now and then, or on one area that keeps going wrong.
2. **Settle any conflicts** between rules it raises first.
3. **Read each proposal**: the change, its evidence, its test result and how to undo it.
4. **Approve or reject each one.** Only an explicit approval counts. It applies what you approved, exactly as proposed.

## How long it takes

**How you work with it:** it runs on its own, then stops for your decision on each proposal.

| Work | Rough time |
|---|---|
| One area | 10–20 min |
| Whole setup, with replay tests | 20–60 min |
| Your decisions | A few minutes |

It takes longer with more past sessions to read, and when it replays past tasks to test a change.

## Reference

<details>
<summary><b>What happens</b></summary>

1. **It reads the evidence.** It reads past sessions, if your tool keeps them, plus memory, instructions files, the record of past runs, and the files it may change. If it cannot read past sessions, it says so and works from the current session and these files.
2. **It finds candidates.** Each candidate starts from evidence it can cite, such as an instruction you gave more than once, a correction no rule covers yet, or a rule no session used. Removing, merging and shortening rules count as much as adding them. It keeps only a handful of candidates.
3. **It tests each candidate.** Where it can, it replays past tasks the candidate was not built from, with and without the change, and counts what got worse as well as what got better. Otherwise it checks the change against what you accepted in past sessions. A separate check judges the change, not the step that wrote it. Changes that pass alone are then tested together.
4. **It keeps the setup small.** If a file would grow, it proposes what to remove or merge, with evidence that it is unused or repeated. It does not remove safety or permission rules on the strength of a replay test.
5. **It proposes.** You see at most five proposals, most important first. Conflicts between rules come before proposals, so you can settle them. Each proposal shows:
   - the exact change, as a diff or full text
   - the evidence it came from
   - the test and its result, including anything that got worse, or "untested" with the reason
   - how to undo it
6. **It asks you to decide on each one.** Only an explicit approval counts. Silence, or approval of a different proposal, does not.
7. **It applies and records.** It applies each approved change exactly as proposed, then checks that nothing else changed.

</details>

<details>
<summary><b>What you get</b></summary>

- Proposals with their evidence, test results and undo steps.
- Changes to the files you approved, and nothing else.
- A record of each run: the date, each proposal, its evidence and test result, and your decision. It keeps the record in its persistent memory if it has one, otherwise in a file in your working directory, whose path it tells you. Later runs read the record and don't re-propose a change you rejected unless there is new evidence.

</details>

<details>
<summary><b>Works with</b></summary>

- [`/ask-better`](ask-better.md) for how it asks you to approve or reject each proposal.
- It can change your personal skills, such as the `write-for-<name>` skill from [`/interview-me`](interview-me.md).
- It can change a skill whose source is in the repository you work in, following that repository's rules for changing skills.

</details>

<details>
<summary><b>What it needs</b></summary>

- **Past session logs** for the strongest evidence. Without them, it uses the current session and your persistent files, and says so.
- **Sub-agents** to judge changes apart from the step that wrote them. Without them, it writes the check before it writes the change and does not edit the check afterwards.
- **File access** to apply changes and keep the record. Without it, it gives you the record at the end and asks you to provide it to the next run.

It may propose, but never applies, changes to your tool's configuration, such as permissions, hooks or scheduled runs. If you want runs to start on their own, for example on a schedule or at the end of a session, it proposes how and sets it up only after you approve. A run that starts while you are away applies nothing and keeps its proposals for when you are back.

</details>
