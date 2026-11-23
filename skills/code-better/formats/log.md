# Agent card and log records

The coordinator ADDS the card before it starts the agent, with `python3 <skill dir>/scripts/better.pyz add <change folder> card --for <agent name> --by coordinator`. The agent ADDS one record for each event with `python3 <skill dir>/scripts/better.pyz add <change folder> <type> --for <agent name>`, where `<type>` is `start`, `step`, `asked`, `blocked` or `handed_back`. The fields of each are below, as JSON on stdin. A verifier adds no `asked` or `blocked` record.

- GIVE a missing value as `null`, a list as a JSON array, and a value that has a fixed set as one of its exact lowercase words. A field not shown below is an error. ADD the record a pointer names before the pointer. ADD the card before the log records that name its task.
- KEEP `text` to one short sentence.

The card:

{"type": "card", "role": "<builder | verifier>", "task": "T<n>", "branch": "<branch>"}

The log:

{"type": "start", "text": "<what you begin with>"}
{"type": "step", "text": "<what you just did or found>"}
{"type": "asked", "text": "<what you sent the coordinator, in a few words>"}
{"type": "blocked", "text": "<what you need>"}
{"type": "handed_back", "result": "<builder: done | partly done | blocked; verifier: passes | fails>", "text": "<one short reason>"}
