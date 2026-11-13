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

## `/ask-better`

Decides when the agent should ask you a question, and how to ask it.

- Looks up what it can find itself, and asks only about what only you know.
- Raises conflicting instructions instead of resolving them silently.

## `/code-better`

Writes, checks and reviews code so it builds what you need.

- Writes requirements as concrete scenarios you can check, separate from the design and the plan.
- Changes only what the task needs, and never weakens tests.
- Checks the code against the requirements and fixes it, with a limit on attempts. Reviews it without the reasoning that wrote it.
- Reports its decisions, assumptions and checks, so you can still understand and maintain the code.

## `/design-better`

Designs, builds and checks an interface or page so the people who use it can do what they came for.

- Agrees the audience and their tasks with you as scenarios, and shows two or three rough directions before building.
- Keeps your existing design language.
- Checks the result by walking each scenario in the rendered page, by pointer, by keyboard and on a small screen. Automated checks and good looks do not show that people can use it.
- Reviews without the builder's reasoning, keeps only findings tied to a step where a person is stopped, and offers a short test with real people instead of simulating them.
- Creates or reviews a design language: colours, type, spacing and components as named values, checked against what was built.

## `/do-better`

Corrects work that doesn't meet your intent.

- Recovers your goal, finds what is actually wrong, and fixes it.
- Asks only when a decision blocks the work.

## `/improve-better`

Improves what persists across the agent's sessions, such as its memory, instruction files, skills and workflows, without waiting for a failure.

- Finds candidate changes in past sessions, including rules to remove.
- Tests each change on past tasks it was not built from, then tests the passing changes together.
- Proposes only tested changes, each with its evidence, test result and how to undo it, and applies only what you approve.

## `/interview-me`

Interviews you about how you read, how you review work, and how you want AI agents to work for you.

- Writes two personal skills: `write-for-<name>`, so agents write text you understand, and `review-for-<name>`, so they check work against your own criteria.
- Writes short profile instructions you can paste into any AI tool's always-on instructions, such as Claude's profile preferences: when to ask, how to source, how to state uncertainty and when to disagree.
- Works from your real documents, reviews and corrections, and from comparisons of concrete samples, not from general questions about your preferences.
- Records for each rule whether you chose it, showed it, or only said it.

Each interview runs on its own: `/interview-me write`, `/interview-me review` or `/interview-me profile`.

## `/research-better`

Researches a topic from sources instead of the model's training data, and writes a report.

- Tracks open questions and sources on a shared research board, and lets cheaper worker agents research in parallel.
- Workers add questions as they go: what sources point to in newer work, origins, other fields, other regions and critics; the works that key sources cite and that cite them; and a challenge question that looks for evidence against each key answer.
- Separate verifier agents check each claim: they open the source page, copy the passage the claim rests on, and judge the claim from it. The coordinating agent reads only their flags and compares key claims with the copied passages.

## `/show-better`

Introduces a dense document, such as a research paper, a strategy or a design doc, with a short sequence of visual panels you read before the document.

- Each panel shows a relation you would otherwise work out from the prose, in a form chosen from a wide range: concept maps, set diagrams, slope charts, distributions, hierarchies, quadrants and more.
- Renders as an HTML page or as plain text for a terminal.
- Checks every value against the source.

## `/teach-better`

Teaches you a new topic so you can use it later without AI.

- Gives hints and worked examples instead of answers, tests understanding with practice you do alone, and handles pushback when you want the answer.
- Picks extra teaching tools by your goal and the moment in the lesson: questions before the lesson, "why" prompts, "does it apply?" checks with near misses, example comparisons, question stems, mixed quizzes, and decision practice compared with cited experts.
- Introduces terms where they are needed, and builds examples and practice from the situations where you will use the topic.
- Ends with your own plans for when to use it, and a take-away to keep open while you do: when to use each rule, the steps, and practice tasks.

## `/write-better`

Rewrites the agent's output so you can understand and act on it.

- Names your goal, cuts what you don't need, puts the main point first, and uses plain, specific words.
