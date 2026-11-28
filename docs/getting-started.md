# Getting started

Start with `/interview-me`. Most of the other skills then call each other at the right step, so you rarely need to invoke them by name.

## 1. Run `/interview-me` once

```
/interview-me
```

It runs three short interviews about you. You can stop after any of them:

1. `write`: how you read. It writes a `write-for-<name>` skill.
2. `review`: how you review work. It writes a `review-for-<name>` skill.
3. `profile`: how you want agents to work for you. It writes a short text you paste into the always-on instructions of any AI tool.

Why first: [`/write-better`](write-better.md) follows your `write-for-<name>` guide for any text you read, and [`/review-better`](review-better.md) adds your `review-for-<name>` criteria to every review. Without them, both fall back to general rules. Bring real material if you have it, such as a document you liked or a review you wrote: the interview works from examples, not from general questions.

See [`/interview-me`](interview-me.md).

## 2. Work as usual, and name a skill when the task matches

| You want to | Use | How it runs | Rough time |
|---|---|---|---|
| Shape a product idea into a brief for design | [`/discover-better`](discover-better.md) | Guided sessions: you choose each move | 1–2 h per move, days to weeks with tests |
| Design a feature or a structural change | [`/architect-better`](architect-better.md) | Live design session on a page | 30–60 min for a feature |
| Build or change code | [`/code-better`](code-better.md) | You agree scenarios, then it builds on its own | 10 min for a fix, 1–8 h for a project |
| Design or build a page or screen | [`/design-better`](design-better.md) | Live design session, then it builds on its own | 30–60 min for a new page |
| Research a topic from sources | [`/research-better`](research-better.md) | On its own, with a live board you can steer from | 20–60 min, up to 3 h |
| Get a dense document introduced with visual panels | [`/show-better`](show-better.md) | Built on its own, then a live session you lead | 20–50 min |
| Review text, code, an interface or a plan | [`/review-better`](review-better.md) | On its own, then your choices | 5–60 min |
| Make a decision you will live with | [`/decide-better`](decide-better.md) | Changes how the agent answers | Part of the reply |
| Get text you can understand and act on | [`/write-better`](write-better.md) | Changes how the agent answers | Part of the reply |

You rarely need to call these yourself:

- [`/ask-better`](ask-better.md) decides when to ask you a question, and how to ask it.
- [`/write-better`](write-better.md) writes the reports the other skills hand back.
- [`/review-better`](review-better.md) runs the reviews in `/code-better` and `/design-better`.
- [`/decide-better`](decide-better.md) runs the choices other skills bring you.

### Live pages and their own agent

`/architect-better`, `/code-better`, `/design-better`, `/discover-better`, `/research-better` and `/show-better` open a live page in your browser when it can reach the machine the agent runs on. The page has its own agent, run by the same harness as your chat (Claude Code, Codex, Cursor, Devin, Droid or OpenCode). It reads what you write in the page and answers there, so your chat stays free.

- **Approvals.** When the page's agent or one of its workers needs a tool call your harness would ask you about, a pop-up on the page shows who asks, the tool and its arguments, with Allow once, Allow for this session and Deny. The tab title starts with "Waiting for you" until you answer.
- **Stop and Start.** The Agents section shows what the agents are doing. Stop ends them and denies any request waiting for you; what they recorded is kept. Start has them read your messages again. When they stop on their own, for example because the harness is not logged in, the section says why and what to do.
- **Reopen the page.** The page works in one tab. To get it back, ask the agent in your chat to reopen it: it runs `link`, which opens a new tab and disconnects the old one. After 30 minutes with no tab open, the page closes; ask the agent in your chat to serve it again.

## 3. When the result is wrong, use `/do-better`

```
/do-better
```

It recovers what you meant, finds what is wrong, and fixes it. `/code-better`, `/design-better` and `/review-better` hand a rejected result to it.

## 4. Now and then, run `/improve-better`

```
/improve-better
```

It reads past sessions for instructions you repeated and corrections no rule covers, tests candidate changes to memory, instructions and skills, and proposes the ones that pass, or marks one as untested. Nothing changes without your approval. See [`/improve-better`](improve-better.md).
