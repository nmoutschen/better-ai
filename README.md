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

## `/code-better`

Writes, checks and reviews code so it builds what the user needs. It writes requirements as concrete scenarios the user can check, keeps the design and the plan separate from them, and changes only what the task needs. It verifies against the requirements in a bounded repair loop, never weakens tests, and reviews in a fresh context. It hands back a report of decisions, assumptions and checks, so the user can still understand and maintain the code.

## `/do-better`

Corrects work that doesn't meet the user's intent. It recovers the user's goal, finds what is actually wrong, and fixes it, asking only when a decision blocks the work.

## `/improve-better`

Improves what persists across the agent's sessions, such as its memory, instructions files, skills and workflows, without waiting for a failure. It finds candidate changes in evidence from past sessions, including rules to remove, tests each one against past tasks it was not built from, and tests the passing changes together. It proposes only tested changes, each with its evidence, test result and how to undo it, and applies only what the user approves.

## `/interview-me`

Interviews the user about how they read and how they review work. It then writes two personal skills, `write-for-<name>` and `review-for-<name>`, so that agents write text the user understands and check work against the user's own criteria. It works from the user's real documents and reviews, and from comparisons of concrete samples, not from general questions about preferences. Each rule in the guides records whether the user chose it, showed it, or only said it.

## `/research-better`

Researches a topic from sources instead of the model's training data. It tracks open questions and sources on a shared research board, lets cheaper worker agents research in parallel, then generates a report.

## `/show-better`

Introduces a dense document, such as a research paper, a strategy or a design doc, with a short sequence of visual panels read before the document. Each panel shows a relation the reader would otherwise work out from the prose, in a form chosen from a wide range: concept maps, set diagrams, slope charts, distributions, hierarchies, quadrants and more. It renders the presentation as an HTML page or as plain text for a terminal, and checks every value against the source.

## `/teach-better`

Teaches a topic so people understand it and use it in their own life and work, not to pass a test. In tutor mode it works through the topic with the user: hints and worked examples instead of answers, problems from the user's own situations, and checks that apply the topic to new cases with the reference open. It ends with a reference made for the user, and helps them learn from real attempts when they come back. In static mode it writes a self-contained reference, a page or a plan of pages, each with the same structure: summary, when to use it, core ideas with worked examples and examples to try, cases, common mistakes, limits, a quick reference and sources. Every claim is read from its source, and `lesson.py build` makes it one HTML file. It picks extra teaching tools by the goal and the moment: why prompts, "does it apply?" checks with near misses, example comparisons, question stems, mixed practice, decision practice, and pre-questions for facts the user must know by heart.

## `/write-better`

Rewrites the agent's output so the user can understand and act on it. It names the reader's goal, cuts what they don't need, puts the main point first, and uses plain, specific words.