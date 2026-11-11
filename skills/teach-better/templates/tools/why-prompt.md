# Tool: why prompt

ASK the user why a fact or rule they just read is true, and let them build the explanation. Explanations the learner builds help more than explanations they are given.

## Use when

- The previous card states a fact or rule that the GOAL needs.
- You can check the explanation the user writes.

## Do not use

- Before the user has seen the fact or rule. The prompt asks them to explain a stated fact, not to guess it.
- As one prompt for a whole long reading. The effect fades when prompts are rare. ASK about each key fact or rule, or USE question stems.
- On every sentence of a card. ASK only about the facts and rules the GOAL needs.

## Steps

1. STATE the fact or rule on a `terms`, `text` or `example` card.
2. ON the next card, ASK "Why is <fact or rule> true?" or "Why does <cause> lead to <effect>?", one numbered question per fact or rule.
3. WAIT for the answer. DO NOT give the explanation in the same message.
4. CHECK each explanation, as in section 3.5 of SKILL.md.
5. FOR a wrong or missing explanation, GIVE a hint (section 3.3 of SKILL.md), not the explanation.
6. IF the explanation is still wrong after the hints, SHOW a correct explanation, and NAME what the user's explanation missed.

## On a page

```json
{"kind": "practice", "id": "<chunk-id>-why", "title": "Why is this true?",
 "blocks": [{"type": "p", "text": "Explain in your own words. You can look back at [the previous card](#<chunk-id>/<card number>)."},
            {"type": "list", "numbered": true, "items": ["Why is <fact or rule> true?"]}],
 "fields": [{"id": "why-1", "label": "1. Why is <fact or rule> true?"}]}
```

GIVE one field per question.

## In the chat

```
## Chunk <n> of <total>: <chunk title> · Card <n> of <total>: Why is this true?

Explain in your own words, by number:

1. Why is <fact or rule> true?
```
