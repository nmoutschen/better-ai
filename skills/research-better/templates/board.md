# Board files

A board is a directory of JSON files. Questions, claims and sources are one file each, so several agents can write at the same time without overwriting each other. The schemas in `schemas/`, next to `templates/`, are the authority for every field, type and allowed value: this file shows the shape of each record, and `schema.py` rejects what does not match. Copy the lines below and replace the `<placeholders>`. Write each record as one line of JSON.

```
<board>/
  brief.json              one record
  decisions.jsonl         one line per decision; the coordinator writes it
  questions/<id>.json     one file per question
  claims/<id>.json        one file per claim
  sources/<id>.json       one file per source
  logs/<agent>.jsonl      one line per event; only that agent writes it
  conversation.jsonl      written by board.py: the user's messages and your replies
```

## Conventions

- Every record starts with `type`, `at` and `by`. `at` is the time you first wrote the record, in UTC with a Z (`YYYY-MM-DDTHH:MM:SSZ`); `by` is your name, `coordinator` for the coordinator. Neither changes when a record is rewritten.
- A field with no value is `null` where its schema allows null (`limit`, `note`, `repeats`, `date` of a source, `replaced_by` of a claim) and left out everywhere else. Never write `"none"` or an empty string. A list is an array, `[]` when empty.
- An ID is a prefix, the agent's name and a counter: `Q-<agent>-<n>` is the `<n>`th question that agent created; a decision is `D<n>`. The file name is `<id>.json`, and the same ID is inside it. Create a file exclusively, so it fails when the file exists, and continue your counter from your highest existing ID: read the folder first, and take the next number if the create fails.
- Write the target before the pointer: a source before a claim that cites it, a question before the claims and questions that name it. Every ID a record names must exist.
- Never delete a record others point to. Withdraw a claim (`status` `withdrawn`, `replaced_by` the claim that replaces it, or `null`), mark a source that copies another a duplicate (`status` `duplicate`, `replaced_by` the source to use), merge a question into another (`status` `merged`, `merged_into` the question that covers it).
- Edit only the files you created, the `owner`, `status`, `summary`, `gist` and `note` of a question you own, and your own log. The coordinator may edit any file to verify, merge, withdraw or reprioritize.
- AFTER every write to a JSON or JSONL file in the board, RUN `python3 <skill dir>/scripts/schema.py check <file>` and FIX every error before your next step. `<skill dir>` is the folder with SKILL.md.

## brief.json

```
{"type": "brief", "at": "<UTC time>", "by": "coordinator", "topic": "<TOPIC as the user stated it>", "title": "<the topic in at most eight plain words, for the page's heading>", "short": "<the topic in two or three words, for the centre of the map>", "meaning": "<the confirmed MEANING>", "goal": "<what the user must understand, learn, decide, or do>", "limit": "<a limit the user stated, or null>", "stop_at": "<high | medium | low>", "collections": ["<a COLLECTION to search, such as web, or the name of a wiki>"], "missing": ["<a COLLECTION the TOPIC needs that could not be searched>"], "changes": [{"at": "<UTC time>", "text": "<a change to the scope or method made during the run>"}], "status": "<running | checking | stopped>"}
```

`changes` is newest first, and `[]` while there is none. `running`: workers research and verifiers check. `checking`: research has ended, workers stop, and verifiers check the remaining claims. `stopped`: all checks are done.

## decisions.jsonl

A choice only the user can make, asked during the run without stopping it. When its status changes, rewrite its line in place; its `at` stays.

```
{"type": "decision", "at": "<UTC time>", "by": "coordinator", "id": "D<n>", "asked": "<what came up, in one short sentence>", "default": "<what you will do if the user does not answer, in one short sentence>", "deadline": "<UTC time when the default applies>", "status": "pending"}
{"type": "decision", "at": "<UTC time>", "by": "coordinator", "id": "D<n>", "asked": "<...>", "default": "<...>", "deadline": "<UTC time>", "status": "default"}
{"type": "decision", "at": "<UTC time>", "by": "coordinator", "id": "D<n>", "asked": "<...>", "default": "<...>", "deadline": "<UTC time>", "status": "changed", "answer": {"type": "page", "event": "<id of the user's answer in conversation.jsonl>"}}
{"type": "decision", "at": "<UTC time>", "by": "coordinator", "id": "D<n>", "asked": "<...>", "default": "<...>", "deadline": "<UTC time>", "status": "changed", "answer": {"type": "chat", "text": "<the user's words>"}}
```

`pending`: waiting for the user until the deadline; the user can answer, or accept the default at once. `default`: the deadline passed or the user accepted the default, and you applied it. `changed`: you applied the user's answer. The `answer` is the user's answer on the page, by the ID of its event, or their words from the chat.

## questions/<id>.json

The first line is a seed question that is proposed, open or out of scope, and the second a challenge question. The next lines change the first by status or by kind.

```
{"type": "question", "at": "<UTC time>", "by": "<agent name>", "id": "Q-<agent>-<n>", "question": "<one question>", "title": "<the question in at most six plain words>", "priority": "<high | medium | low>", "status": "<proposed | open | out of scope>", "origin": {"type": "<user | meaning | goal>"}, "kind": "seed", "stakes": "<which conclusion for the GOAL the answer could change>", "done_when": "<the evidence that would answer the question>", "note": "<why it was closed, rewritten, or dropped, or null>"}
{"type": "question", "at": "<UTC time>", "by": "<agent name>", "id": "Q-<agent>-<n>", "question": "<what evidence would contradict the answer>", "title": "<...>", "priority": "<...>", "status": "proposed", "origin": {"type": "question", "question": "<Q-... the answered question>"}, "kind": "challenge", "stakes": "<...>", "done_when": "<...>", "note": null}
{"type": "question", "at": "<UTC time>", "by": "<agent name>", "id": "Q-<agent>-<n>", "question": "<...>", "title": "<...>", "priority": "<...>", "status": "in progress", "owner": "<agent name>", "origin": {"type": "<user | meaning | goal>"}, "kind": "seed", "stakes": "<...>", "done_when": "<...>", "note": null}
{"type": "question", "at": "<UTC time>", "by": "<agent name>", "id": "Q-<agent>-<n>", "question": "<...>", "title": "<...>", "priority": "<...>", "status": "<answered | contested | not found | unclear>", "owner": "<agent name>", "summary": "<two or three sentences answering the question from the evidence>", "gist": "<the answer in one plain sentence of at most 20 words>", "origin": {"type": "<user | meaning | goal>"}, "kind": "seed", "stakes": "<...>", "done_when": "<...>", "note": null}
{"type": "question", "at": "<UTC time>", "by": "<agent name>", "id": "Q-<agent>-<n>", "question": "<...>", "title": "<...>", "priority": "<...>", "status": "merged", "merged_into": "<Q-... that covers it>", "origin": {"type": "<user | meaning | goal>"}, "kind": "seed", "stakes": "<...>", "done_when": "<...>", "note": null}
{"type": "question", "at": "<UTC time>", "by": "<agent name>", "id": "Q-<agent>-<n>", "question": "<...>", "title": "<...>", "priority": "<...>", "status": "proposed", "origin": {"type": "<question | source>", "<question | source>": "<Q-... | S-...>"}, "kind": "frontier", "raised_in": "<Q-... the question after which you raised it>", "lens": "<newer | origin | field | region | critics>", "stakes": "<...>", "done_when": "<...>", "note": null}
{"type": "question", "at": "<UTC time>", "by": "<agent name>", "id": "Q-<agent>-<n>", "question": "<...>", "title": "<...>", "priority": "<...>", "status": "proposed", "origin": {"type": "<question | source | goal>", "<question | source>": "<Q-... | S-...>"}, "kind": "<chain | conflict | gap>", "raised_in": "<Q-... the question after which you raised it>", "stakes": "<...>", "done_when": "<...>", "note": null}
```

`owner` is there from `in progress` on and left out before. `summary` and `gist` are there once the question is `answered`, `contested`, `not found` or `unclear`, and left out before. `merged_into` is only on `merged`. `raised_in` is only on `frontier`, `chain`, `conflict` and `gap` questions, and `lens` only on `frontier`. `origin` has the `type` shown and, for a question or a source, the ID under the key of the same name. A question's claims are the claims whose `question` names it.

## claims/<id>.json

A verifier, not the agent that recorded the claim, sets everything after `status` `unchecked`.

```
{"type": "claim", "at": "<UTC time>", "by": "<agent name>", "id": "C-<agent>-<n>", "claim": "<one sentence>", "question": "<Q-...>", "source": "<S-...>", "quote": "<verbatim passage from the source>", "status": "unchecked"}
{"type": "claim", "at": "<UTC time>", "by": "<agent name>", "id": "C-<agent>-<n>", "claim": "<...>", "question": "<Q-...>", "source": "<S-...>", "quote": "<...>", "status": "checking", "checker": "<verifier name>"}
{"type": "claim", "at": "<UTC time>", "by": "<agent name>", "id": "C-<agent>-<n>", "claim": "<...>", "question": "<Q-...>", "source": "<S-...>", "quote": "<...>", "status": "verified", "checker": "<verifier name>", "span": "<passage the verifier copied from the page>", "hard": "<true | false>", "differs": "<source fields that differ from the page, with the page's values; leave out if none>"}
{"type": "claim", "at": "<UTC time>", "by": "<agent name>", "id": "C-<agent>-<n>", "claim": "<...>", "question": "<Q-...>", "source": "<S-...>", "quote": "<...>", "status": "unverified", "checker": "<verifier name>", "hard": "<true | false>", "reason": "<which check failed and why>", "span": "<passage the verifier copied, if it found one>", "blocked": "<true if the page could not be read; leave out otherwise>"}
{"type": "claim", "at": "<UTC time>", "by": "<agent name>", "id": "C-<agent>-<n>", "claim": "<...>", "question": "<Q-...>", "source": "<S-...>", "quote": "<...>", "status": "withdrawn", "replaced_by": "<C-... or null>"}
```

`hard` and `blocked` are the JSON values `true` or `false`, not text. A `withdrawn` claim keeps only the fields shown: its checker, span and reason go.

## sources/<id>.json

```
{"type": "source", "at": "<UTC time>", "by": "<agent name>", "id": "S-<agent>-<n>", "author": "<people or organization, as the source names them>", "date": "<year, year-month, year-month-day, n.d. if the source has none, or null if you have not copied it yet>", "title": "<title>", "publisher": "<journal, publisher, or site name>", "url": "<URL>", "ids": [{"type": "<doi | arxiv | pmid | isbn>", "<doi | arxiv | pmid | isbn>": "<the identifier>"}], "category": "<peer-reviewed | preprint | working paper | dataset | government | news | book | documentation | blog | vendor | other>", "read": "<raw | extracted | abstract | snippet | blocked>", "trust": "<high | medium | low>", "trust_reason": "<one line>", "repeats": "<S-... if it cites, copies, or summarizes that source, or null>", "status": "kept"}
{"type": "source", "at": "<UTC time>", "by": "<agent name>", "id": "S-<agent>-<n>", "author": "<...>", "date": "<...>", "title": "<...>", "publisher": "<...>", "url": "<...>", "ids": [], "category": "<...>", "read": "<...>", "trust": "<...>", "trust_reason": "<...>", "repeats": null, "status": "duplicate", "replaced_by": "<S-... to use instead>"}
```

`ids` lists the identifiers a retraction check can look the work up by, one object per identifier, with the identifier under the key named by its `type`; it is `[]` for a page with none.

## logs/<agent>.jsonl

One line per event, added at the end. A line holds `type`, `at` and `by` and the fields of its kind.

```
{"type": "search", "at": "<UTC time>", "by": "<agent name>", "query": "<the query>", "question": "<Q-...>", "new_terms": ["<a term the results revealed>"]}
{"type": "frontier", "at": "<UTC time>", "by": "<agent name>", "after": "<Q-... you just closed>", "empty_lenses": ["<a lens no source points to>"]}
{"type": "challenge", "at": "<UTC time>", "by": "<agent name>", "after": "<Q-... you just closed>"}
{"type": "chain", "at": "<UTC time>", "by": "<agent name>", "after": "<Q-... you just closed>"}
{"type": "gap", "at": "<UTC time>", "by": "<agent name>", "text": "<what could not be found>", "queries": ["<a query you tried>"]}
{"type": "strategy", "at": "<UTC time>", "by": "<agent name>", "text": "<what changed and why>"}
{"type": "stop", "at": "<UTC time>", "by": "<agent name>", "text": "<why you stopped while questions were left>"}
{"type": "failure", "at": "<UTC time>", "by": "<agent name>", "collection": "<the COLLECTION that failed>", "text": "<what failed>"}
{"type": "checked", "at": "<UTC time>", "by": "<verifier name>", "claim": "<C-... you checked>"}
```

`frontier`, `challenge` and `chain` record that you ran that check after closing the question named by `after`; `empty_lenses` lists the lenses that found nothing. A `checked` line records that you checked a claim; the verdict lives on the claim.
