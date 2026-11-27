# `/architect-better`

Designs a feature or a change to a software system. You check how the system works today, agree what the change needs to do, and discuss the design on a live page.

![The live design page: tabs for Overview, Requirements, Containers, Flows, Perspectives, Decision records and Spec; the container diagram after the change, with new parts in terracotta, a removed part dashed, and security findings marked on the parts they concern; and a conversation with the architect on the right](img/architect-better-design.png)
*You check the diagrams before and after the change, see review findings on the parts they concern, and click any box, arrow or step to comment on it.*

## What it does

- **Draws the current system.** It checks the affected containers and flows against the code and asks you to correct the drawing. If all you need is a map of the system as it is, the work can stop there.
- **Agrees requirements with you.** It drafts observable scenarios for quality attributes, marks its guesses and shows where each requirement came from.
- **Shows options and trade-offs.** It recommends a design, explains why it rejected alternatives and records the main drawback of each recorded choice. When two designs are both worth weighing, it draws each one so you can switch between them and choose.
- **Tests what documentation cannot settle.** When a choice rests on how a tool or library behaves, it proposes a throwaway proof of concept with the questions it must answer, runs it once you agree, and writes what it observed into the design. A result that contradicts a choice comes back to you.
- **Reviews the design after you approve it.** It runs a separate review for each applicable perspective, such as security, failure handling, agent experience or API standards, and attaches findings to the affected parts.

## When to use it

Use it to design a feature or a structural change, such as adding a module, changing a data model or planning a migration. Use audit mode to review an existing design or check how a system matches its design.

```text
/architect-better move invoice exports to a background job
/architect-better audit the invoice export design
```

## The live page

Switch between Before and After in Containers and Flows, or between Before and each alternative design, with its strengths and drawbacks above the diagram. Overview lists the alternatives side by side. Click a box, arrow or step to comment. Confirm a guessed requirement or choose Change to correct a row. The agent replies under your message.

The Agents list at the top of the conversation shows each reviewer, proof of concept or spec check at work, and for how long.

Choose **Approve…** to approve the design, with your open comments, and start perspective reviews. When the design has alternatives, choose which one to build, or ask for a combination or for none of them; the alternatives you did not choose are recorded as rejected. When a finding appears, select its linked part to see where it applies. After a revision, **Review again…** shows what changed in the diagrams, the requirements or `design.md`, and reruns the perspectives those changes affect.

## What you get

- A design document with goals, diagrams, design choices and unresolved questions.
- Decision records with their drivers, chosen options, rejected alternatives and main drawbacks.
- An implementation spec with verifiable requirements and source links, ready for [`/code-better`](code-better.md).
- In audit mode, a report of findings tied to diagram parts. The audit makes no changes.

## How it is tested

Tested on 23 situations with Sonnet 5.5 (2026-11-21).

| What it does | Passed |
| --- | ---: |
| Asks about costly gaps at once, questions a solution that works against the goal, raises a conflict with a recorded decision, has the user confirm the current system before designing, and asks what to design when given no request | 83% |
| Draws the current system from the code, flags vendor claims no source supports, traces each requirement to its source, changes a disputed finding only on evidence, and audits the system against its design | 67% |
| Compares options with their drawbacks, states quality attributes as scenarios, lists every perspective, keeps the current system's part IDs in the change, and states failure cases in the spec | 93% |
| Reviews only an approved design, with a fresh reviewer per perspective, ties findings to diagram parts, and has a separate agent check the spec | 100% |
| Saves the design and decision records where and how the repo keeps them, designs nothing when the structure does not change, changes nothing in an audit, and says at hand-back what is approved, reviewed and still open | 87% |

<details>
<summary><b>Works with</b></summary>

- [`/ask-better`](ask-better.md) for the questions about gaps and requirements.
- [`/decide-better`](decide-better.md) when you choose between design options.
- [`/review-better`](review-better.md) to confirm the perspective reviewers' findings and to hold a finding you dispute.
- [`/write-better`](write-better.md) for the final report.
- [`/do-better`](do-better.md) when you reject the result.
- [`/code-better`](code-better.md) builds from the design and spec, and points you here for a structural change without a design.
- `/review-better` uses `/architect-better`'s checks when it reviews a software design.

</details>
