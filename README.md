# Better* AI Skills

\*Based on what I personally consider better.

These skills change how an AI agent works with you: when it asks, how it codes, designs, researches, teaches and writes, and how it corrects and improves its own work.

## Installation

Claude Code:

```
/plugin marketplace add nmoutschen/better-ai
/plugin install better-ai@better-ai
```

Droid:

```sh
droid plugin marketplace add nmoutschen/better-ai
droid plugin install better-ai@better-ai
```

GitHub Copilot CLI:

```sh
copilot plugin marketplace add nmoutschen/better-ai
copilot plugin install better-ai@better-ai
```

Codex, Cursor, Gemini CLI, OpenCode and other harnesses:

```sh
npx skills add nmoutschen/better-ai -g
```

## Start here

Run `/interview-me` first, then work as usual. See [Getting started](docs/getting-started.md).

## Skills

Each skill's page says when to use it, what you can do with it, your workflow, and how long it takes.

| Skill | What it does | How it runs | Rough time |
|---|---|---|---|
| [`/interview-me`](docs/interview-me.md) | Interviews you about how you read, review and want agents to work, and writes personal guides other skills follow. | An interview with you | 15–30 min per interview |
| [`/ask-better`](docs/ask-better.md) | Decides when the agent should ask you a question, and how to ask it. | Changes how the agent answers | Part of the reply |
| [`/architect-better`](docs/architect-better.md) | Designs and audits software systems, with before and after diagrams you can comment on. | Live design session on a page | 30–60 min for a feature |
| [`/code-better`](docs/code-better.md) | Writes, checks, reviews and audits code so it builds what you need. | You agree scenarios, then it builds on its own | 10 min for a fix, 1–8 h for a project |
| [`/decide-better`](docs/decide-better.md) | Helps you make a decision yourself: asks which way you lean, checks the options against what matters to you, and gives its view with the main drawback. | Changes how the agent answers | Part of the reply |
| [`/design-better`](docs/design-better.md) | Designs and audits an interface or page and its design language, shows you versions side by side on a live page, and has `/code-better` build the design. | Live design session, then it builds on its own | 30–60 min for a new page |
| [`/discover-better`](docs/discover-better.md) | Takes your product idea to a brief for design, in versions: checks what it assumes against evidence, asks only what you can decide, and has you choose each move. | Guided sessions: you choose each move | 1–2 h per move, days to weeks with tests |
| [`/do-better`](docs/do-better.md) | Corrects work that doesn't meet your intent. | Changes how the agent answers | Part of the reply |
| [`/improve-better`](docs/improve-better.md) | Improves the agent's memory, instructions and skills and proposes changes for you to approve, each with its test result. | On its own, then you approve each proposal | 10–60 min |
| [`/research-better`](docs/research-better.md) | Researches a topic from sources on a shared board, with verified claims, and writes a report. | On its own, with a live board you can steer from | 20–60 min, up to 3 h |
| [`/review-better`](docs/review-better.md) | Reviews text, code, an interface, a plan or a report so each finding leads to an action. | On its own, then your choices | 5–60 min |
| [`/show-better`](docs/show-better.md) | Introduces a dense document with a short story of visual slides you can comment on. | Built on its own, then a live session you lead | 20–50 min |
| [`/write-better`](docs/write-better.md) | Writes or rewrites text so you can understand and act on it. | Changes how the agent answers | Part of the reply |
