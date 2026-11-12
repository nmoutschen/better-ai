# Board files

A board is a directory. Each entry is its own small file, so several agents can write at the same time without overwriting each other. Each file holds one `key: value` per line. Copy the blocks below and replace the `<placeholders>`.

```
<board>/
  brief.md
  questions/<id>.md
  claims/<id>.md
  sources/<id>.md
  logs/<agent>.md
```

## IDs and ownership

- An ID is a prefix, the agent's name, and a counter: `Q-w2-4` is the fourth question that agent `w2` created. Use `coordinator` as your name when you coordinate. IDs never collide, so no agent needs to ask for one.
- Create new files freely. Edit only the files you created, the `owner`, `status`, and `summary` lines of a question you own, and your own log.
- The coordinator may edit any file to verify, merge, delete, or reprioritize.

## brief.md

```
topic: <TOPIC as the user stated it>
meaning: <the confirmed MEANING>
goal: <what the user must understand, learn, decide, or do>
limit: <a limit the user stated, or none>
stop-at: <high | medium | low>
collections: <the COLLECTIONs to search, such as web, or the name of a wiki>
missing: <COLLECTIONs the TOPIC needs that could not be searched, or none>
status: <running | checking | stopped>
```

`running`: workers research and verifiers check. `checking`: research has ended, workers stop, and verifiers check the remaining claims. `stopped`: all checks are done.

## questions/<id>.md

```
id: Q-<agent>-<n>
question: <one question>
priority: <high | medium | low>
status: <proposed | open | in progress | answered | contested | not found | unclear | out of scope>
owner: <agent name, or none>
origin: <user | meaning | goal | Q-... | S-...>
kind: <seed | frontier | challenge | chain | conflict | gap>
stakes: <which conclusion for the GOAL the answer could change>
done-when: <the evidence that would answer the question>
answer: <claim IDs, or none>
summary: <two or three sentences answering the question from the evidence, or none>
note: <why it was closed, rewritten, or dropped, or none>
```

## claims/<id>.md

```
id: C-<agent>-<n>
claim: <one sentence>
question: <Q-...>
source: <S-...>
quote: "<verbatim passage from the source>"
verified: <unchecked | verified | unverified>
checker: <verifier name, or none>
span: "<passage the verifier copied from the page, or none>"
hard: <yes | no | none>
reason: <why the claim is unverified, or source fields that differ from the page, or none>
```

A verifier, not the agent that recorded the claim, sets the last five lines.

## sources/<id>.md

```
id: S-<agent>-<n>
author: <people or organization, as the source names them>
date: <year, or year-month-day; n.d. if none>
title: <title>
publisher: <journal, publisher, or site name>
url: <URL>
type: <peer-reviewed | government | news | book | documentation | blog | vendor | other>
read: <raw | extracted | abstract | snippet | blocked>
trust: <high | medium | low>
trust-reason: <one line>
repeats: <S-... if it cites, copies, or summarizes that source, or none>
```

## logs/<agent>.md

One line per event, added at the end:

```
search "<query>" for <Q-...> — new terms: <terms, or none>
strategy change: <what changed and why>
frontier after <Q-...>: newer <Q-..., or none>; origin <Q-..., or none>; field <Q-..., or none>; region <Q-..., or none>; critics <Q-..., or none>
challenge after <Q-...>: <Q-..., or none>
chain after <Q-...>: <Q-..., or none>
gap: <what could not be found, and the queries tried>
```
