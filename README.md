# Better* AI Skills

\*Based on what I personally consider better.

## `/ask-better`

Decides when the agent should ask the user a question, and how to ask it. It looks up what the agent can find itself, asks only about what only the user knows, and raises conflicting instructions instead of resolving them silently.

## `/do-better`

Corrects work that doesn't meet the user's intent. It recovers the user's goal, finds what is actually wrong, and fixes it, asking only when a decision blocks the work.

## `/research-better`

Researches a topic from sources instead of the model's training data. It tracks open questions and sources on a shared research board, lets cheaper worker agents research in parallel, then generates a report.

## `/write-better`

Rewrites the agent's output so the user can understand and act on it. It names the reader's goal, cuts what they don't need, puts the main point first, and uses plain, specific words.