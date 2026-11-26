# `/code-better`

Writes, checks, reviews and audits code so it builds what you need, and leaves you able to understand and maintain it.

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
- **Audits existing code** for technical debt and what to improve, ranked by what each finding costs you, without changing the code.

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
- You want to know what to improve in existing code, such as its technical debt.

Use a neighbouring skill instead when:

- The change adds an interface or changes its screens, layout or flow: use [`/design-better`](design-better.md) first. It designs the change with you, then has `/code-better` build it.
- You only want a review of finished work of any kind: [`/review-better`](review-better.md) runs the review, and `/code-better` adds what to look for in code.
- You rejected a result and want it corrected: use [`/do-better`](do-better.md).

</details>

<details>
<summary><b>How to run it</b></summary>

- `/code-better <task>` does that task.
- `/code-better` with no argument checks the coding work in the current conversation, then continues or corrects it.
- To check someone else's code, give it the diff or the pull request.
- `/code-better audit <path>` audits that part of the code, or the whole repository without a path.

Example: `/code-better add a --dry-run flag to the deploy script`

Running it does not mean code gets written right away. It can stop at requirements and questions, or at a report that the request works against your goal.

</details>

<details>
<summary><b>What happens</b></summary>

1. **It names your goal.** If your request names a solution, such as "add a cache", it names the need behind it. If that solution works against the need, it says so once, with one alternative, then follows your decision.
2. **It reads first.** It reads the code the change touches, its callers and tests, and the project's instruction and contribution files. It does not ask you what those files answer.
3. **It writes requirements as scenarios.** For anything beyond a small fix with one obvious reading, it writes scenarios with concrete inputs and expected results, such as Given/When/Then. You can check them without reading code.
4. **It asks about gaps only you can fill.** These are behaviours you would notice, such as errors, limits or what happens to existing data. It asks them all at once, before building, by showing the scenarios they affect. It decides implementation details within the agreed design and states its other assumptions next to the result.
5. **It points you to `/architect-better` for structural changes without a design.** This applies to a new module, data model, dependency or migration. It builds from the resulting design and spec once both exist.
6. **It writes a plan only for long or shared work.** This means work over several sessions or agents.
7. **It writes the code.** It changes only what the task needs, and lists other things worth changing instead of changing them.
8. **It checks the code.** It runs the affected tests, a check per scenario, a smoke check, and the project's existing static checks. For Rust, Python, TypeScript and Java, a short language file tells it which checks to run while it builds and before it hands back, what to review once they pass, and which extra checks a change calls for, such as a property test, a fuzz target or an API compatibility check. It uses those where your project already has the tool and proposes them otherwise. Your repository's own settings come first. For a refactor, it also runs the old and the new code on the same inputs and compares the results. It stops after about three rounds of fixes, or when the same check fails twice for the same reason, and reports what fails. It never edits or skips tests to make them pass. When you add or change a requirement, it re-runs the checks of every earlier scenario.
9. **It gets a separate review.** The reviewer sees only the diff, the requirements and the code, not the agent's reasoning.
10. **It reports back** and offers to explain how the change works.

When the work splits into several tasks that each need their own review, such as an epic of several tickets, it coordinates instead of building: builder agents write each task on its own branch, verifier agents check each one, and the coordinating agent keeps the spec and task list correct. When a verifier finds a bug that has likely siblings, such as other entry points that can fail the same way, the coordinator has the whole kind fixed in one place, with a test that finds every instance, instead of patching each one. When a task proves hard, because a verifier finds a known bug class again, finds a blocking security issue, or fails it a second time, the coordinator moves the task to a more capable model, with a fresh agent and every earlier finding, and tells you why in the conversation. It makes small late fixes itself, test first, instead of starting another agent for each. For structural changes that need a design, the coordinator points you to `/architect-better` and coordinates the build from its design and spec.

</details>

<details>
<summary><b>The live dashboard</b></summary>

When it coordinates several agents, it opens a dashboard in your browser, if it can run a command in the background. The dashboard updates as the agents work:

![The live dashboard: figures for tasks done, open questions and how long the change has run; a timeline with one row per task in three tables, working, pending and merged, each lane showing its builds as sand bars whose thickness follows how much the branch changed, its verifies in terracotta, failed rounds marked R1, R2, and merges; and a conversation with the coordinator on the right](img/code-better-dashboard.png)

- **The figures** at the top: tasks done (merged into the coordinator's branch), open questions, and how long the change has run. Click the open questions to jump to the first one.
- **The timeline**, one row per task, in three tables: Working (an agent has started on it), Pending (not started yet) and Merged. Each row shows the task's mode, its title and its status: building, verifying, waiting on another task, waiting on you, or quiet when its branch and its builder have shown no change for 30 minutes. Its lane shows each build as a sand bar that grows thicker when more lines of its branch change in five minutes (read from git, not from what the agent reports), a dotted line where nothing changed, each verify in terracotta, a fix by the coordinator in umber, a red line marked R1, R2… where a verifier failed a round, and a green line where the task was merged. Hover or focus a round's mark to read why it failed. Choose 1 h, 2 h, 6 h or All at the top right to change how much time the timeline shows.
- **A task's detail**: click a row, or press Enter on it, for its requirements and check, its branch's changes, and each round newest first, with its agent, its logged steps and times, and the verifier's findings, blocking or not. Ask about the task from its detail.
- **The conversation** with the coordinating agent: write to it, reply to any message, and see each message move from seen to answered. Messages on both sides show Markdown, such as lists, tables and code. Each decision the coordinator takes on its own shows there, and you can reply to change it. Its questions to you come last, next to the message box, until you answer. It also asks them in the chat and waits for your answer from either place.

The dashboard reads the change's folder, `.code/<change>/`, and keeps running until you tell the agent you are done with it.

</details>

<details>
<summary><b>What you get</b></summary>

- The code change, kept to one purpose.
- Its working files in `.code/<change>/`, typed JSON checked against a schema when the skill adds or changes each record, in the formats of the skill:
  - **Change and requirements**: `code.json` holds your goal, the design and the mode. `spec.jsonl` holds the requirements, each with its source and its check, the gaps with what you were asked about each, and the design items with no requirement.
  - **Plan**: `tasks.jsonl` holds the tasks with a check for each, `progress.jsonl` the progress and open problems, and `instructions.jsonl` what you told it about how to work.
  - **Next steps**: `next-steps.jsonl` holds the work outside the change.
  - **Decisions**: `decisions.jsonl` holds each decision it took and each question it asked you.
  - When it coordinates agents: each agent's card and log in `logs/`, `lessons.jsonl` with the bug classes its verifiers found and the rule for each (every builder and verifier gets it), and your conversation with the coordinator (`conversation.jsonl`).
  - **Retrospective**: before any builder starts, the coordinator writes in `retro.md` what it expects: time, agents and review rounds, each with a range, and the benefit with a signal that would show it. Before it hands back, it completes the file: each figure against what it expected and against earlier changes, what went well and what could be better, whether the last retrospective's actions were done and worked, and the next actions, each with where it belongs. The next coordinated change starts from it, and the actions that need you come to you as next steps.
- For structural changes, the design and spec from `/architect-better` that the build follows.
- A report:
  - what changed and why, in terms of the requirements
  - the design decisions and assumptions
  - each check run and its result, and each scenario it could not check
  - what it listed instead of changing

  The report keeps three things apart: meeting the requirements, passing the checks, and your acceptance.
- For an audit, no code change. Instead:
  - every finding, with its evidence and a proposed task, in `.code/audit/<date>/findings.jsonl`, with the facts it rests on in `evidence.jsonl` and the goal and commit in `audit.json`, for an agent to pick up later
  - a short report with what costs you now and the five to ten findings of highest value

</details>

<details>
<summary><b>Works with</b></summary>

It calls:

- [`/ask-better`](ask-better.md) when it checks requirements with you.
- [`/review-better`](review-better.md) to run the review and the audit, with `/code-better`'s list of what to look for in code.
- [`/decide-better`](decide-better.md) when it asks you about implementation decisions.
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
