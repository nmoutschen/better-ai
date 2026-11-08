# Better* AI Skills

\*Based on what I personally consider better.

## `/ask-better`

Decides when the agent should ask the user a question, and how to ask it. It looks up what the agent can find itself, asks only about what only the user knows, and raises conflicting instructions instead of resolving them silently.

## `/do-better`

Corrects work that doesn't meet the user's intent. It recovers the user's goal, finds what is actually wrong, and fixes it, asking only when a decision blocks the work.

## `/research-better`

Researches a topic from sources instead of the model's training data. It tracks open questions and sources on a shared research board, lets cheaper worker agents research in parallel, then generates a report.

## `/show-better`

Decides when to show information as a table, chart or diagram instead of prose. It chooses the format by what the reader must do, designs it so it is read correctly, and checks generated chart code before showing it.

## `/teach-better`

Teaches the user a new topic so they can use it later without AI. It gives hints and worked examples instead of answers, tests understanding with practice the user does alone, and handles pushback when the user wants the answer.

## `/write-better`

Rewrites the agent's output so the user can understand and act on it. It names the reader's goal, cuts what they don't need, puts the main point first, and uses plain, specific words.