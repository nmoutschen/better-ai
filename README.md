# Better* AI Skills

\*Based on what I personally consider better.

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

Decides when the agent should ask the user a question, and how to ask it. It looks up what the agent can find itself, asks only about what only the user knows, and raises conflicting instructions instead of resolving them silently.

## `/do-better`

Corrects work that doesn't meet the user's intent. It recovers the user's goal, finds what is actually wrong, and fixes it, asking only when a decision blocks the work.

## `/interview-me`

Interviews the user about how they read and how they review work. It then writes two personal skills, `write-for-<name>` and `review-for-<name>`, so that agents write text the user understands and check work against the user's own criteria. It works from the user's real documents and reviews, and from comparisons of concrete samples, not from general questions about preferences. Each rule in the guides records whether the user chose it, showed it, or only said it.

## `/research-better`

Researches a topic from sources instead of the model's training data. It tracks open questions and sources on a shared research board, lets cheaper worker agents research in parallel, then generates a report.

## `/show-better`

Introduces a dense document, such as a research paper, a strategy or a design doc, with a short sequence of visual panels read before the document. Each panel shows a relation the reader would otherwise work out from the prose, in a form chosen from a wide range: concept maps, set diagrams, slope charts, distributions, hierarchies, quadrants and more. It renders the presentation as an HTML page or as plain text for a terminal, and checks every value against the source.

## `/teach-better`

Teaches the user a new topic so they can use it later without AI. It gives hints and worked examples instead of answers, tests understanding with practice the user does alone, and handles pushback when the user wants the answer. It picks extra teaching tools by the user's goal and the lesson moment: pre-questions, why prompts, example comparisons, question stems, mixed quizzes, and decision practice compared with cited experts.

## `/write-better`

Rewrites the agent's output so the user can understand and act on it. It names the reader's goal, cuts what they don't need, puts the main point first, and uses plain, specific words.