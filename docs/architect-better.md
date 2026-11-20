# `/architect-better`

Designs a feature or a change to a software system. You check how the system works today, agree what the change needs to do, and discuss the design on a live page.

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
