# Board records

A board holds records of five types, `brief`, `decision`, `question`, `claim` and `source`, and a log for each agent. ADD each with `python3 <skill dir>/scripts/better.pyz add <board> <type> --by <your agent name>`, its fields as JSON on stdin; for a log line, use `--for <the log's agent name>` instead of `--by`. CHANGE one with `python3 <skill dir>/scripts/better.pyz set <board> <id>`, or `set <board> brief --by coordinator` for the brief, which only the coordinator changes. IF it refuses a record, FIX the record and RUN it again. This file shows the fields of each type: copy a line and replace the `<placeholders>`.

## Conventions

- A field with no value is `null` where a field may be null (`limit`, `note`, `repeats`, `date` of a source, `replaced_by` of a claim) and left out everywhere else. Never give `"none"` or an empty string. A list is an array, `[]` when empty.
- ADD the target before the pointer: a source before a claim that cites it, a question before the claims and questions that name it. Every ID a record names must exist.
- Never delete a record others point to. Withdraw a claim (`status` `withdrawn`, `replaced_by` the claim that replaces it, or `null`), mark a source that copies another a duplicate (`status` `duplicate`, `replaced_by` the source to use), merge a question into another (`status` `merged`, `merged_into` the question that covers it).
- CHANGE only the records you added, the `owner`, `status`, `summary`, `gist` and `note` of a question you own, and your own log. The coordinator may change any record to verify, merge, withdraw or reprioritize.

## brief (the coordinator adds it)

```
{"type": "brief", "topic": "<TOPIC as the user stated it>", "title": "<the topic in at most eight plain words, for the page's heading>", "short": "<the topic in two or three words, for the centre of the map>", "meaning": "<the confirmed MEANING>", "goal": "<what the user must understand, learn, decide, or do>", "limit": "<a limit the user stated, or null>", "stop_at": "<high | medium | low>", "collections": ["<a COLLECTION to search, such as web, or the name of a wiki>"], "missing": ["<a COLLECTION the TOPIC needs that could not be searched>"], "changes": [], "status": "<running | checking | stopped>"}
```

`changes` is `[]` while there is none. To record a change to the scope or method, `set` the brief with `{"changes": [{"text": "<the change>"}, <every earlier entry, exactly as the brief shows it>]}`. GIVE the new entry without `at`. `running`: workers research and verifiers check. `checking`: research has ended, workers stop, and verifiers check the remaining claims. `stopped`: all checks are done.

## decision (the coordinator adds it)

A choice only the user can make, asked during the run without stopping it. When its status changes, CHANGE it with `set`.

```
{"type": "decision", "raised_by": "coordinator", "about": {"type": "board"}, "asked": "<what came up, in one short sentence>", "status": "waiting", "default": "<what you will do if the user does not answer, in one short sentence>", "deadline": "<+<minutes>m>"}
{"type": "decision", "raised_by": "coordinator", "about": {"type": "board"}, "asked": "<...>", "status": "defaulted", "default": "<...>", "deadline": "<as in the waiting line>"}
{"type": "decision", "raised_by": "coordinator", "about": {"type": "board"}, "asked": "<...>", "status": "answered", "default": "<...>", "deadline": "<as in the waiting line>", "answer": {"type": "page", "event": "<id of the user's answer on the page>"}}
{"type": "decision", "raised_by": "coordinator", "about": {"type": "board"}, "asked": "<...>", "status": "answered", "default": "<...>", "deadline": "<as in the waiting line>", "answer": {"type": "chat", "text": "<the user's words>"}}
```

`waiting`: waiting for the user until the deadline; the user can answer, or accept the default at once. `defaulted`: the deadline passed or the user accepted the default, and you applied it. `answered`: you applied the user's answer. The `answer` is the user's answer on the page, by the ID of its event, or their words from the chat.

## question

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

## claim

A verifier, not the agent that added the claim, sets everything after `status` `unchecked`. SET a claim `verified` with `set --raw <file>`, the file of the page text the verifier read: the command refuses unless each passage of the `span` occurs in that file and the `quote`'s words occur in one passage of the `span`, and it adds the file's `sha256`. GIVE no `sha256` yourself.

```
{"type": "claim", "claim": "<one sentence>", "question": "<Q-...>", "source": "<S-...>", "quote": "<verbatim passage from the source>", "status": "unchecked"}
{"type": "claim", "claim": "<...>", "question": "<Q-...>", "source": "<S-...>", "quote": "<...>", "status": "checking", "checker": "<verifier name>"}
{"type": "claim", "claim": "<...>", "question": "<Q-...>", "source": "<S-...>", "quote": "<...>", "status": "verified", "checker": "<verifier name>", "span": "<passage the verifier copied from the page>", "hard": "<true | false>", "differs": "<source fields that differ from the page, with the page's values; leave out if none>"}
{"type": "claim", "claim": "<...>", "question": "<Q-...>", "source": "<S-...>", "quote": "<...>", "status": "unverified", "checker": "<verifier name>", "hard": "<true | false>", "reason": "<which check failed and why>", "span": "<passage the verifier copied, if it found one>", "blocked": "<true if the page could not be read; leave out otherwise>"}
{"type": "claim", "claim": "<...>", "question": "<Q-...>", "source": "<S-...>", "quote": "<...>", "status": "withdrawn", "replaced_by": "<C-... or null>"}
```

`hard` and `blocked` are the JSON values `true` or `false`, not text. A `withdrawn` claim keeps only the fields shown: its checker, span and reason go, with `--unset`. A claim that stops being `verified` loses its `sha256`.

## source

```
{"type": "source", "author": "<people or organization, as the source names them>", "date": "<year, year-month, year-month-day, n.d. if the source has none, or null if you have not copied it yet>", "title": "<title>", "publisher": "<journal, publisher, or site name>", "url": "<URL>", "ids": [{"type": "<doi | arxiv | pmid | isbn>", "<doi | arxiv | pmid | isbn>": "<the identifier>"}], "category": "<peer-reviewed | preprint | working paper | dataset | government | news | book | documentation | blog | vendor | other>", "read": "<raw | extracted | abstract | snippet | blocked>", "trust": "<high | medium | low>", "trust_reason": "<one line>", "repeats": "<S-... if it cites, copies, or summarizes that source, or null>", "status": "kept"}
{"type": "source", "author": "<...>", "date": "<...>", "title": "<...>", "publisher": "<...>", "url": "<...>", "ids": [], "category": "<...>", "read": "<...>", "trust": "<...>", "trust_reason": "<...>", "repeats": null, "status": "duplicate", "replaced_by": "<S-... to use instead>"}
```

`ids` lists the identifiers a retraction check can look the work up by, one object per identifier, with the identifier under the key named by its `type`; it is `[]` for a page with none.

### category

SET `category` from what the page shows about where the work appeared, not from how good it looks:

- `peer-reviewed`: an article in a journal or conference proceedings that the page names.
- `preprint`: a paper posted on a server such as arXiv, SSRN, bioRxiv or OSF. IT STAYS `preprint` unless the page names its published version, such as a journal reference or the DOI of the published article: THEN SET `peer-reviewed` and ADD that DOI to `ids`.
- `working paper`: a paper in an institution's series, such as NBER, a central bank or a university department.
- `documentation`: reference pages that describe how a product, API, standard or law works, by whoever maintains it.
- `vendor`: a company's other material about its own products, such as marketing pages, case studies, white papers and its own benchmark posts.
- `government`: by a government body or an intergovernmental organization.
- `news`: by a news organization.
- `blog`: posts by a person or team, outside a news organization's editing, about things they do not sell.
- `dataset`, `book`: as named. `other`: none of the above.

### trust

`trust` rates the work itself: how far its content can be believed, whichever claim the board takes from it. Whether a claim says more than the source shows is the verifier's check on the claim, not part of `trust`.

ANSWER these four checks from the page, one at a time, BEFORE you set the level:

1. **Origin**: does the source produce what the board takes from it, such as its own study, data, product, rules or decisions, or does it report what another source produced? IF it reports, SET `repeats` when that source is on the board, and LOOK for the original.
2. **Method**: for results, such as a measurement, a rate, an effect or a comparison, does the page show how they were obtained: the design, the sample and its size, the data or code?
3. **Interest**: do the author, the publisher or the funder gain if the results come out a certain way, such as a company evaluating its own product or a study funded by the maker of what it tests? Does the page say so?
4. **Standing**: has the work been retracted, withdrawn or corrected, or does the page contradict its own data?

THEN SET the level from the answers:

- `high`: the source produces what it reports; IF it reports results, it shows how they were obtained, and they rest neither on a small sample, under about 50 people or cases, nor on self-reports alone; no one behind it gains from the results, or it describes its own product, rules or decisions without evaluating them; and nothing in check 4 applies.
- `low`: any of these: retracted or withdrawn; it reports results without saying where they come from; it gives results with no method; or someone behind it gains from the results and the page gives no data that others could check.
- `medium`: everything else, such as a study with a small sample, a survey of self-reports, a study funded by an interested party that discloses this, or a secondary source that names its source and reports it faithfully.

DO NOT raise or lower `trust` for the `category`, the venue's or author's prestige, citation counts, or how polished the page is. The same company's reference page and its benchmark post are two sources and can get two levels.

WRITE in `trust_reason` the answers that set the level, in one line, such as "own RCT; method shown; n=16, small; no stake" for a `medium`.

## log lines

ADD one record per event, with `--for` the log's agent name; only that agent adds its own. A record holds `type` and the fields of its kind.

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
