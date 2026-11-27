# `/design-better`

Designs and audits an interface so the people who use it can do what they came for, and has `/code-better` build it.

![The compare page: two versions of an orders list side by side, "A, one list" and "B, late orders first", with a conversation panel on the right](img/design-better-compare.png)
*You compare versions on one page, and click any part of a version to comment on it or Decide.*

## When to use it

- To design a new interface or change one: its screens, what they hold, their layout or their flow. A web page, an app screen, a rendered report.
- To audit an interface or a design language, yours or someone else's.
- To create, extend or change a design language: the named colours, type, spacing and components that give a set of interfaces one look.

Running it does not mean a redesign. A run can end with a brief and a few questions for you, or with a report that the interface already works for its audience.

Use something else nearby:

- For a small change inside one screen, such as a clearer label, [`/code-better`](code-better.md) is enough. If you call `/design-better` for it, it applies its design rules and hands the change to `/code-better` without a brief.
- To introduce a dense document with visual panels, use [`/show-better`](show-better.md).
- For the words in the interface, such as labels, button text and messages, `/design-better` calls [`/write-better`](write-better.md) itself.

## What you can do with it

| You want to | Run | You get |
|---|---|---|
| Design or change an interface | `/design-better the orders page` | Versions to compare, a design, the built interface, and a report of each scenario walked |
| Audit an interface or a design language | `/design-better audit the settings page` | Findings in order, each with a proposed fix; nothing changed |
| Create or change a design language | `/design-better a design language for our admin tools` | A design language document, with values shared by the document and the code |
| Check the interface work in this conversation | `/design-better` | The work audited, then continued or corrected |

In every design, it:

- **Agrees the tasks first.** A short brief of who uses the page and what they come to do, as scenarios with real data.
- **Shows you versions to choose from.** For a new page or a layout change, two or three rough directions side by side on one page before anything is built.
- **Hands the build to `/code-better`**, with one requirement per scenario.
- **Accepts the result by using it.** A separate reviewer walks every scenario in the built interface, by pointer, by keyboard and on a small screen, and what fails goes back to `/code-better`.
- **Keeps your design language.** When a rule, such as text contrast, clashes with it, it tells you and follows your decision.

## Your workflow

![The design-better workflow: your steps on the top lane, the agent's on the bottom lane, in order](img/design-better-workflow.svg)
*Your steps are on the top lane, the agent's on the bottom one. The terracotta outline marks where your input matters most.*

1. **Start it** with the interface or the task people do in it.
2. **Check the brief**: the audience, their scenarios, and which pages stay, merge or go. Answer its few questions.
3. **Compare directions** on the live page: comment on any part, and choose one version, a combination or none with Decide.
4. **Decide the review findings** on the chosen direction, and the empty, loading and error states.
5. **Let it build.** `/code-better` builds the design without you, and a reviewer walks every scenario in the result.
6. **Read the report**, and run the short test with three to five people it offers for a new interface.

## How long it takes

**How you work with it:** a live design session. You compare versions and comment on a page while the agent revises them. Once you choose, the build and its review run without you.

| Work | Rough time |
|---|---|
| Small change with a design rule applied | 10–20 min |
| New page or changed flow, from brief to built | 30–60 min |
| Design language | 30–60 min, mostly with you |
| Audit | 15–45 min, without you |

It takes longer with each round of directions, and when the walk of the built interface sends problems back to `/code-better`, for at most three rounds.

## Reference

<details>
<summary><b>What happens</b></summary>

1. **It reads first.** It reads the existing interface, its styles, components and design files, the content, and the project's instructions. It does not ask you what these already answer.
2. **It writes a brief** in `.design/<slug>/brief.md`: the goal, the audience, a few scenarios (one task each, from start to an end you can observe, with real data), and the pages and what each holds. It asks whether each page or part should stay, merge or go.
3. **It asks a few questions.** At most about three, all at once, each answerable in a few words. A question about how something looks becomes versions you choose between, not a text description.
4. **In design mode:**
   - It first asks whether you have a direction or references in mind, then shows two or three rough directions that differ in structure or emphasis, not only in colour.
   - Once you choose a direction, a separate reviewer checks it against the scenarios and usability rules in the background, while the agent works out the states and the design. You get its confirmed findings, each with a proposed fix, and decide which to apply: you may like a direction that people would struggle to use.
   - It decides the empty, loading, error and other edge states with you.
   - It writes `.design/<slug>/design.md`: the chosen direction, the screens and their states, and the requirements, one per scenario plus what only the code can meet, such as labels tied to fields and keyboard access.
   - `/code-better` builds it and its verifier checks the code. Visual changes to an existing interface come in small batches, each shown before and after.
   - A separate reviewer walks every scenario in the built interface. Each confirmed problem that stops or slows a scenario goes back to `/code-better`, the rest are listed as open, and the reviewer walks all scenarios again, for at most three rounds.
5. **In audit mode**, a separate reviewer gets the interface, the brief and your decisions, not the agent's reasoning. It walks each scenario and reads the labels and headings without the visual page. A finding counts only if it names a step where a person is stopped or slowed. Pages that should merge or go come first. Nothing is changed.
6. **In language mode**, it asks what the interfaces must express, in your words, shows directions that depart from its own default, and writes the values in tables, one name per value shared by the document and the code.
7. **You compare versions on one page.** Versions appear side by side, one screen size at a time: the page opens on the size most of the audience uses, and you switch to the others in the top bar. The page keeps your choice when it reloads. When your browser runs on the same machine, the page is served live:
   - Click any part of a version to comment on it.
   - Give each version a thumbs up or down when there are three or more.
   - Choose one version, a combination or none with Decide.
   - The agent replies under your comment and marks it seen, working or done. Accept a done item with the ✓ next to Reply, or reply under it to send it back.
   - Every message, the agent's included, can be answered with Reply. The conversation opens at the latest message, and what you are typing survives new replies.
   - Open lists what is not accepted yet, and the agent's questions until you answer them.
   - New versions load by themselves once you stop typing. If the agent's server stops, a strip under the bar says the canvas is closed.

</details>

<details>
<summary><b>What you get</b></summary>

- A brief at `.design/<slug>/brief.md`, and in design mode a design at `.design/<slug>/design.md`.
- A compare page at `.design/<slug>/index.html`, with your feedback appended to `conversation.jsonl` next to it. Git sees it as untracked: commit it or ignore it as you choose.
- In design mode, the interface built by `/code-better`. When a change alters how it looks, a page showing each changed screen before and after, and the same screenshots in the pull request when the change goes into one.
- A short report:
  - which scenarios it walked and how, and which failed or could not be walked
  - the decisions that are yours: conflicts with the design language, and assumptions that changed the build
  - the reviewer's open findings, and those it could not confirm
- For a new interface or a changed main flow that other people will use, an offer of a short test: you watch three to five people from the audience try the scenarios. When the pages or their names change, it offers a tree test instead, and after a test leads to changes, a second short round.
- In audit mode, the findings in order, each with a proposed fix, and what works and must be kept.
- In language mode, a design language document with values in tables, one name per value shared by the document and the code.

The report keeps three claims apart: the scenarios can be completed, the checks pass, and the audience can use the interface. Only a test with people shows the last one.

</details>

<details>
<summary><b>Works with</b></summary>

- [`/code-better`](code-better.md) builds the design, and fixes what the reviewer finds.
- [`/ask-better`](ask-better.md) for the questions before building.
- [`/write-better`](write-better.md) for the words in the interface and for the final report.
- [`/review-better`](review-better.md) to run the reviewer, with no change to the work.
- [`/do-better`](do-better.md) when you reject the result.
- `/review-better` uses `/design-better`'s checks when it reviews an interface or a design language.

</details>

<details>
<summary><b>What it needs</b></summary>

| Capability | Without it |
|---|---|
| Python 3 | If it can still render, it writes one HTML page with the versions side by side at the same width. |
| A browser that can reach the machine | It publishes the page, whose Copy all button copies your feedback for the chat. If it cannot publish, it opens the page and gives you its path. |
| Rendering a page | It shows each version as a plain text outline and says the choice may change once rendered. |
| Being told about your feedback as it arrives | It asks you to say "sent" in the chat, then reads your feedback from `conversation.jsonl`. |
| Operating the page by pointer and keyboard | It looks for a headless browser or automation library first. If none works, it marks the work not finished and lists the walks for you to do. |
| An accessibility checker | It says none ran, and relies on the walks and reading the markup. |
| Sub-agents | It stops and marks the work not finished: the review needs a reviewer that did not design the interface. |
| Writing files | It stops and marks the work not finished. |

</details>

<details>
<summary><b>How it is tested</b></summary>

Tested on 18 situations with Sonnet 5.5 (2026-11-21).

| What it does | Passed |
| --- | ---: |
| Checks the interface the way its users meet it: does their tasks in it, reads what its labels and pages say, and reports what stops them. Claims only what it checked, and suggests a test with real people for the rest | 72% |
| Puts the user's direction, design language and decisions first, and asks few questions, each costly to get wrong | 89% |
| Follows the skill's design rules in the design, the directions and the build | 89% |

</details>
