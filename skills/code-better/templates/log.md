# Agent card and log: <agent name>

<HOW TO FILL THIS IN — delete this block when done.
- The coordinator adds the card, `.code/<change>/logs/<agent name>.card.json`, before it starts the agent, with `python3 <skill dir>/scripts/better.pyz add <change folder> card --for <agent name>`. The agent adds one line for each event to `.code/<change>/logs/<agent name>.jsonl` with `python3 <skill dir>/scripts/better.pyz add <change folder> <type> --for <agent name>`. The lines below show the fields of each, as JSON on stdin. A verifier writes no `asked` or `blocked` line.
- Conventions: WRITE a missing value as `null`, a list as a JSON array, and a value that has a fixed set as one of its exact lowercase words. A field not shown below is an error. WRITE the record a pointer names before the pointer: the task of a card is in `tasks.jsonl` first.
- KEEP `text` to one short sentence.>

The card:

{"type": "card", "role": "<builder | verifier>", "task": "T<n>", "branch": "<branch>"}

The log:

{"type": "start", "text": "<what you begin with>"}
{"type": "step", "text": "<what you just did or found>"}
{"type": "asked", "text": "<what you sent the coordinator, in a few words>"}
{"type": "blocked", "text": "<what you need>"}
{"type": "handed_back", "result": "<builder: done | partly done | blocked; verifier: passes | fails>", "text": "<one short reason>"}
