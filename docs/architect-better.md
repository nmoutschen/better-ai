# `/architect-better`

Designs a feature or a change to a software system. You check how the system works today, agree what the change needs to do, and discuss the design on a live page.

![The live design page: tabs for Overview, Requirements, Containers, Flows, Perspectives, Decision records and Spec; the container diagram after the change, with new parts in terracotta, a removed part dashed, and security findings marked on the parts they concern; and a conversation with the architect on the right](img/architect-better-design.png)
*You check the diagrams before and after the change, see review findings on the parts they concern, and click any box, arrow or step to comment on it.*

## What it does

- **Draws the current system.** It checks the affected containers and flows against the code and asks you to correct the drawing.
- **Agrees requirements with you.** It drafts observable scenarios for quality attributes, marks its guesses and shows where each requirement came from.
- **Shows options and trade-offs.** It recommends a design, explains why it rejected alternatives and records the main drawback of each recorded choice.
- **Reviews the design after you approve it.** It runs a separate review for each applicable perspective, such as security, observability or API standards, and attaches findings to the affected parts.

## When to use it

Use it to design a feature or a structural change, such as adding a module, changing a data model or planning a migration. Use audit mode to review an existing design or check how a system matches its design.

```text
/architect-better move invoice exports to a background job
/architect-better audit the invoice export design
```

## The live page

Switch between Before and After in Containers and Flows. Click a box, arrow or step to comment. Confirm a guessed requirement or choose Change to correct a row. The agent replies under your message.

Choose **Approve…** to start perspective reviews. When a finding appears, select its linked part to see where it applies. After a revision, **Review again…** shows what changed and reruns the perspectives those changes affect.

## What you get

- A design document with goals, diagrams, design choices and unresolved questions.
- Decision records with their drivers, chosen options, rejected alternatives and main drawbacks.
- An implementation spec with verifiable requirements and source links, ready for [`/code-better`](code-better.md).
- In audit mode, a report of findings tied to diagram parts. The audit makes no changes.

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
