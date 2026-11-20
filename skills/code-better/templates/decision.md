# Decision: <id>

<HOW TO FILL THIS IN — delete this block when done.
- Save each in .code/<change>/decisions/<id>.md, one file per decision or question. Only the coordinator writes them.
- WRITE one for each decision you take within what the user agreed, and one for each question you ask the user. The id is D-<n>, counting up.
- WHEN the user answers a question, SET status to answered and COPY their answer. WHEN the user replies to a decision and that changes it, REVISE `decision` in place.>

```
id: D-<n>
at: <ISO time, such as 2026-11-20T14:05:00>
from: <the agent that raised it, or coordinator>
task: <task number, or none>
asked: <what came up, in one short sentence>
decision: <what you decided, in one short sentence, or none for a question to the user>
status: <decided | waiting | answered>
answer: <the user's answer, or none>
```

`decided`: you decided it yourself. `waiting`: you asked the user and wait for the answer. `answered`: the user answered and you applied it.
