# `/code-better`

Writes, checks and reviews code so it builds what you need, and leaves you able to understand and maintain it.

```markdown
### Late orders first

- Given: 142 orders, of which #4821 is 2 days late and #4830 is 1 day late
- When: support opens the orders page
- Then: #4821 and #4830 appear above the list, under "Late now"
- Source: user
```
*A scenario from the requirements it agrees with you before writing code. It checks the finished code against each one.*

## What it does

- **Agrees requirements as scenarios** with concrete data you can check, separate from the design and the plan.
- **Keeps the change small.** It changes only what the task needs, and never weakens a test to make it pass.
- **Checks the code against the scenarios**, with a limit on fix attempts, and has a separate reviewer read the diff.
- **Reports its decisions, assumptions and checks**, so you can maintain the code.

For example:

```
/code-better show late orders first on the orders page
```

## Reference

<details>
<summary><b>When to use it</b></summary>

- You want the agent to write or change code.
- You want the agent to check coding work already done in the conversation.
- You want a review of someone else's code, such as a diff or a pull request.

Use a neighbouring skill instead when:

- The code builds an interface or a page: use [`/design-better`](design-better.md). It follows `/code-better` for the code itself.
- You only want a review of finished work of any kind: [`/review-better`](review-better.md) runs the review, and `/code-better` adds what to look for in code.
- You rejected a result and want it corrected: use [`/do-better`](do-better.md).

</details>

<details>
<summary><b>How to run it</b></summary>

- `/code-better <task>` does that task.
- `/code-better` with no argument checks the coding work in the current conversation, then continues or corrects it.
- To check someone else's code, give it the diff or the pull request.

Example: `/code-better add a --dry-run flag to the deploy script`

Running it does not mean code gets written right away. It can stop at requirements and questions, or at a report that the request works against your goal.

</details>

<details>
<summary><b>What happens</b></summary>

1. **It names your goal.** If your request names a solution, such as "add a cache", it names the need behind it. If that solution works against the need, it says so once, with one alternative, then follows your decision.
2. **It reads first.** It reads the code the change touches, its callers and tests, and the project's instruction and contribution files. It does not ask you what those files answer.
3. **It writes requirements as scenarios.** For anything beyond a small fix with one obvious reading, it writes scenarios with concrete inputs and expected results, such as Given/When/Then. You can check them without reading code.
4. **It asks about gaps only you can fill.** These are behaviours you would notice, such as errors, limits or what happens to existing data. It asks them all at once, before building, by showing the scenarios they affect. It decides internal design itself and states its other assumptions next to the result.
5. **It shows the design when the change adds structure.** This applies to a new module, data model, dependency or migration. If you will maintain the code, it shows you the decisions that change behaviour, cost or risk before building.
6. **It writes a plan only for long or shared work.** This means work over several sessions or agents.
7. **It writes the code.** It changes only what the task needs, and lists other things worth changing instead of changing them.
8. **It checks the code.** It runs the affected tests, a check per scenario, a smoke check, and the project's existing static checks. It stops after about three rounds of fixes, or when the same check fails twice for the same reason, and reports what fails. It never edits or skips tests to make them pass. When you add or change a requirement, it re-runs the checks of every earlier scenario.
9. **It gets a separate review.** The reviewer sees only the diff, the requirements and the code, not the agent's reasoning.
10. **It reports back** and offers to explain how the change works.

</details>

<details>
<summary><b>What you get</b></summary>

- The code change, kept to one purpose.
- When the change needs them, these files, from the skill's templates:
  - **Requirements**: the need, what changes for you, scenarios, constraints, out of scope, assumptions.
  - **Design**: the approach, diagrams of only the parts the change touches, main flows, data changes, decisions.
  - **Plan**: tasks with a check for each, progress notes, open questions.
- A report:
  - what changed and why, in terms of the requirements
  - the design decisions and assumptions
  - each check run and its result, and each scenario it could not check
  - what it listed instead of changing

  The report keeps three things apart: meeting the requirements, passing the checks, and your acceptance.

</details>

<details>
<summary><b>Works with</b></summary>

It calls:

- [`/ask-better`](ask-better.md) when it checks requirements with you.
- [`/review-better`](review-better.md) to run the review, with `/code-better`'s list of what to look for in code.
- [`/write-better`](write-better.md) for the final report and for explanations.
- [`/do-better`](do-better.md) when you reject the result.

It is called by:

- [`/design-better`](design-better.md) for the code behind an interface.
- [`/review-better`](review-better.md) when the work under review is code, a diff or a pull request.
- [`/do-better`](do-better.md) to check a correction to code.

</details>

<details>
<summary><b>What it needs</b></summary>

- **Reading files and running commands and tests.** Without running code, it says so, describes no results it did not see, and lists the checks you should run.
- **Writing files.** Without it, it puts the requirements in its reply.
- **Asking you.**
- **Sub-agents.** It uses them for the review and for independent reading. Without them, it rereads the requirements and reads the diff as if someone else wrote it.

</details>
