# Tool: decision scenario

GIVE the user a situation and a set of options. ASK them to rank the options and give their reasons. THEN SHOW how experts ranked them and why, from a cited source, and ASK the user to compare. Comparing with real experts raised agreement with the experts, without a teacher present. Whether it improves real decisions is unknown.

## Use when

- The GOAL is to make a kind of decision.
- You have a cited source of expert judgement for this situation, such as published guidance, a case review, or a named expert's analysis that ranks or argues for options.

## Do not use

- Without a cited source. DO NOT write the expert view yourself, even if the user asks: the user would compare against your guess. USE decision checks instead, and SAY that no expert comparison is available.
- When the source does not cover the options you would list. LIST only options the source discusses.
- When the user struggled on the last practice problem. GIVE more support first.

## Steps

1. FIND the source. PREFER a documented case, so the expert view belongs to that exact situation.
2. WRITE the situation: what is happening, what the decision maker knows, and what they must decide now.
3. LIST three to five numbered options, including options the source advises against.
4. ASK the user to rank the options, and to give the reasons for their first choice and what they paid attention to. ADD the decision checks fields IF the GOAL needs planning.
5. WAIT for the answer.
6. SHOW the source's choice and reasons, with a link, and a table that sets the user's ranking next to the source's.
7. IF the experts disagree among themselves, SHOW the minority view too: a decision can have more than one defensible answer.
8. ASK the user what the experts paid attention to that they did not.
9. IF the user's own experience conflicts with the source, SAY who the experts are and in what situations they decide.

Verdict on a page: `right` IF the user's first choice matches the source's first choice, OTHERWISE `partly`. DO NOT use `wrong`: the score measures agreement with the source, not the quality of the decision.

## On a page

```json
{"kind": "practice", "id": "<chunk-id>-scenario", "title": "<decision to make>",
 "blocks": [{"type": "p", "text": "<situation>"},
            {"type": "list", "numbered": true, "items": ["<option>", "<option>", "<option>"]}],
 "fields": [{"id": "first", "label": "Your first choice (option number)"},
            {"id": "second", "label": "Your second choice (option number)"},
            {"id": "last", "label": "Your last choice (option number)"},
            {"id": "why", "label": "Why you chose your first choice, and what you paid attention to"}]}
```

Feedback, in `feedback/<id>.<n>.json`:

```json
{"verdict": "right | partly", "text": "<the source's choice and reasons, with a link to the source>",
 "blocks": [{"type": "table", "columns": ["Option", "Your rank", "Experts' rank"], "rows": [["<option>", "<rank>", "<rank>"]]},
            {"type": "p", "text": "What did the experts pay attention to that you did not?"}]}
```

## In the chat

```
## Chunk <n> of <total>: <chunk title> · Card <n> of <total>: Decide

<situation>

Options:

1. <option>
2. <option>
3. <option>

Answer by number:

1. Rank the options, from best to worst.
2. Why did you choose your first choice, and what did you pay attention to?
```
