# Board files

A board is a directory of JSON files. Questions, claims and sources are one file each, so several agents can write at the same time without overwriting each other. This file shows the fields of each record. Copy the lines below and replace the `<placeholders>`, and give each record as one line of JSON on stdin.

```
<board>/
  brief.json              one record
  decisions.jsonl         one line per decision; the coordinator writes it
  questions/<id>.json     one file per question
  claims/<id>.json        one file per claim
  sources/<id>.json       one file per source
  logs/<agent>.jsonl      one line per event; only that agent writes it
  conversation.jsonl      the user's messages and your replies
```

## Conventions

- A field with no value is `null` where a field may be null (`limit`, `note`, `repeats`, `date` of a source, `replaced_by` of a claim) and left out everywhere else. Never write `"none"` or an empty string. A list is an array, `[]` when empty.
- Write the target before the pointer: a source before a claim that cites it, a question before the claims and questions that name it. Every ID a record names must exist.
- Never delete a record others point to. Withdraw a claim (`status` `withdrawn`, `replaced_by` the claim that replaces it, or `null`), mark a source that copies another a duplicate (`status` `duplicate`, `replaced_by` the source to use), merge a question into another (`status` `merged`, `merged_into` the question that covers it).
- Edit only the records you added, the `owner`, `status`, `summary`, `gist` and `note` of a question you own, and your own log. The coordinator may edit any file to verify, merge, withdraw or reprioritize.

## brief.json

```
{"type": "brief", "topic": "<TOPIC as the user stated it>", "title": "<the topic in at most eight plain words, for the page's heading>", "short": "<the topic in two or three words, for the centre of the map>", "meaning": "<the confirmed MEANING>", "goal": "<what the user must understand, learn, decide, or do>", "limit": "<a limit the user stated, or null>", "stop_at": "<high | medium | low>", "collections": ["<a COLLECTION to search, such as web, or the name of a wiki>"], "missing": ["<a COLLECTION the TOPIC needs that could not be searched>"], "changes": [], "status": "<running | checking | stopped>"}
```

`changes` is `[]` while there is none. To record a change to the scope or method, `set` the brief with `{"changes": [{"text": "<the change>"}, <the earlier entries, as the brief shows them>]}`: the new entry comes first, and the command adds its time. `running`: workers research and verifiers check. `checking`: research has ended, workers stop, and verifiers check the remaining claims. `stopped`: all checks are done.

## decisions.jsonl

A choice only the user can make, asked during the run without stopping it. When its status changes, edit it with `set`.

```
{"type": "decision", "raised_by": "coordinator", "about": {"type": "board"}, "asked": "<what came up, in one short sentence>", "status": "waiting", "default": "<what you will do if the user does not answer, in one short sentence>", "deadline": "<+<minutes>m>"}
{"type": "decision", "raised_by": "coordinator", "about": {"type": "board"}, "asked": "<...>", "status": "defaulted", "default": "<...>", "deadline": "<as in the waiting line>"}
{"type": "decision", "raised_by": "coordinator", "about": {"type": "board"}, "asked": "<...>", "status": "answered", "default": "<...>", "deadline": "<as in the waiting line>", "answer": {"type": "page", "event": "<id of the user's answer in conversation.jsonl>"}}
{"type": "decision", "raised_by": "coordinator", "about": {"type": "board"}, "asked": "<...>", "status": "answered", "default": "<...>", "deadline": "<as in the waiting line>", "answer": {"type": "chat", "text": "<the user's words>"}}
```

`waiting`: waiting for the user until the deadline; the user can answer, or accept the default at once. `defaulted`: the deadline passed or the user accepted the default, and you applied it. `answered`: you applied the user's answer. The `answer` is the user's answer on the page, by the ID of its event, or their words from the chat.

## questions/<id>.json

The first line is a seed question that is proposed, open or out of scope, and the second a challenge question. The next lines change the first by status or by kind.

```
{"type": "question", "question": "<one question>", "title": "<the question in at most six plain words>", "priority": "<high | medium | low>", "status": "<proposed | open | out of scope>", "origin": {"type": "<user | meaning | goal>"}, "kind": "seed", "stakes": "<which conclusion for the GOAL the answer could change>", "done_when": "<the evidence that would answer the question>", "note": "<why it was closed, rewritten, or dropped, or null>"}
{"type": "question", "question": "<what evidence would contradict the answer>", "title": "<...>", "priority": "<...>", "status": "proposed", "origin": {"type": "question", "question": "<Q-... the answered question>"}, "kind": "challenge", "stakes": "<...>", "done_when": "<...>", "note": null}
{"type": "question", "question": "<...>", "title": "<...>", "priority": "<...>", "status": "in progress", "owner": "<agent name>", "origin": {"type": "<user | meaning | goal>"}, "kind": "seed", "stakes": "<...>", "done_when": "<...>", "note": null}
{"type": "question", "question": "<...>", "title": "<...>", "priority": "<...>", "status": "<answered | contested | not found | unclear>", "owner": "<agent name>", "summary": "<two or three sentences answering the question from the evidence>", "gist": "<the answer in one plain sentence of at most 20 words>", "origin": {"type": "<user | meaning | goal>"}, "kind": "seed", "stakes": "<...>", "done_when": "<...>", "note": null}
{"type": "question", "question": "<...>", "title": "<...>", "priority": "<...>", "status": "merged", "merged_into": "<Q-... that covers it>", "origin": {"type": "<user | meaning | goal>"}, "kind": "seed", "stakes": "<...>", "done_when": "<...>", "note": null}
{"type": "question", "question": "<...>", "title": "<...>", "priority": "<...>", "status": "proposed", "origin": {"type": "<question | source>", "<question | source>": "<Q-... | S-...>"}, "kind": "frontier", "raised_in": "<Q-... the question after which you raised it>", "lens": "<newer | origin | field | region | critics>", "stakes": "<...>", "done_when": "<...>", "note": null}
{"type": "question", "question": "<...>", "title": "<...>", "priority": "<...>", "status": "proposed", "origin": {"type": "<question | source | goal>", "<question | source>": "<Q-... | S-...>"}, "kind": "<chain | conflict | gap>", "raised_in": "<Q-... the question after which you raised it>", "stakes": "<...>", "done_when": "<...>", "note": null}
```

`owner` is there from `in progress` on and left out before. `summary` and `gist` are there once the question is `answered`, `contested`, `not found` or `unclear`, and left out before. `merged_into` is only on `merged`. `raised_in` is only on `frontier`, `chain`, `conflict` and `gap` questions, and `lens` only on `frontier`. `origin` has the `type` shown and, for a question or a source, the ID under the key of the same name. A question's claims are the claims whose `question` names it.

## claims/<id>.json

A verifier, not the agent that recorded the claim, sets everything after `status` `unchecked`.

```
{"type": "claim", "claim": "<one sentence>", "question": "<Q-...>", "source": "<S-...>", "quote": "<verbatim passage from the source>", "status": "unchecked"}
{"type": "claim", "claim": "<...>", "question": "<Q-...>", "source": "<S-...>", "quote": "<...>", "status": "checking", "checker": "<verifier name>"}
{"type": "claim", "claim": "<...>", "question": "<Q-...>", "source": "<S-...>", "quote": "<...>", "status": "verified", "checker": "<verifier name>", "span": "<passage the verifier copied from the page>", "hard": "<true | false>", "differs": "<source fields that differ from the page, with the page's values; leave out if none>"}
{"type": "claim", "claim": "<...>", "question": "<Q-...>", "source": "<S-...>", "quote": "<...>", "status": "unverified", "checker": "<verifier name>", "hard": "<true | false>", "reason": "<which check failed and why>", "span": "<passage the verifier copied, if it found one>", "blocked": "<true if the page could not be read; leave out otherwise>"}
{"type": "claim", "claim": "<...>", "question": "<Q-...>", "source": "<S-...>", "quote": "<...>", "status": "withdrawn", "replaced_by": "<C-... or null>"}
```

`hard` and `blocked` are the JSON values `true` or `false`, not text. A `withdrawn` claim keeps only the fields shown: its checker, span and reason go.

## sources/<id>.json

```
{"type": "source", "author": "<people or organization, as the source names them>", "date": "<year, year-month, year-month-day, n.d. if the source has none, or null if you have not copied it yet>", "title": "<title>", "publisher": "<journal, publisher, or site name>", "url": "<URL>", "ids": [{"type": "<doi | arxiv | pmid | isbn>", "<doi | arxiv | pmid | isbn>": "<the identifier>"}], "category": "<peer-reviewed | preprint | working paper | dataset | government | news | book | documentation | blog | vendor | other>", "read": "<raw | extracted | abstract | snippet | blocked>", "trust": "<high | medium | low>", "trust_reason": "<one line>", "repeats": "<S-... if it cites, copies, or summarizes that source, or null>", "status": "kept"}
{"type": "source", "author": "<...>", "date": "<...>", "title": "<...>", "publisher": "<...>", "url": "<...>", "ids": [], "category": "<...>", "read": "<...>", "trust": "<...>", "trust_reason": "<...>", "repeats": null, "status": "duplicate", "replaced_by": "<S-... to use instead>"}
```

`ids` lists the identifiers a retraction check can look the work up by, one object per identifier, with the identifier under the key named by its `type`; it is `[]` for a page with none.

## logs/<agent>.jsonl

One line per event, added at the end. A line holds `type` and the fields of its kind.

```
{"type": "search", "query": "<the query>", "question": "<Q-...>", "new_terms": ["<a term the results revealed>"]}
{"type": "frontier", "after": "<Q-... you just closed>", "empty_lenses": ["<a lens no source points to>"]}
{"type": "challenge", "after": "<Q-... you just closed>"}
{"type": "chain", "after": "<Q-... you just closed>"}
{"type": "gap", "text": "<what could not be found>", "queries": ["<a query you tried>"]}
{"type": "strategy", "text": "<what changed and why>"}
{"type": "stop", "text": "<why you stopped while questions were left>"}
{"type": "failure", "collection": "<the COLLECTION that failed>", "text": "<what failed>"}
{"type": "checked", "claim": "<C-... you checked>"}
```

`frontier`, `challenge` and `chain` record that you ran that check after closing the question named by `after`; `empty_lenses` lists the lenses that found nothing. A `checked` line records that you checked a claim; the verdict lives on the claim.
