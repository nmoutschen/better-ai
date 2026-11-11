# Tool: compare examples

SHOW two worked examples side by side, and ASK a specific question about what they share or how they differ. Comparing two examples beat studying them one at a time, but only for learners who already knew one of them.

## Use when

- The user has already studied and practised one method or case in an earlier card.
- A second method for the same problem, or a second case with the same principle, exists.

## Do not use

- For the first example of a new idea. Novices learned more from one example at a time.
- When the user already handles the domain well. Explicit comparison may add little for them.
- With two examples on separate cards, or a day apart. Delayed comparison gave the least learning.

## Steps

1. PICK the second example. PREFER a second method for the same problem over a second problem with the same method: comparing methods helped more.
2. CHECK that the two examples differ only in the aspect you want the user to notice, and that both are correct (section 3.4 of SKILL.md).
3. SHOW both examples on one card, aligned step by step in a table, with the same words for the same things.
4. ASK one or two specific questions about a named aspect, such as "Which step differs, and why do both reach the same answer?" or "What do both cases have in common that makes the rule apply?". DO NOT ask only "Compare these": learners rarely compare without a specific prompt.
5. WAIT for the answer, then CHECK it as a practice answer (section 4 of modes/tutor.md).
6. AFTER the comparison, STATE the principle in one or two sentences. Stating it after the comparison went with larger effects.

## On a page

```json
{"kind": "practice", "id": "<chunk-id>-compare", "title": "Compare two <methods or cases>",
 "blocks": [{"type": "table", "columns": ["Step", "<example A>", "<example B>"],
             "rows": [["<step>", "<A at this step>", "<B at this step>"]]},
            {"type": "list", "numbered": true, "items": ["<specific question>"]}],
 "fields": [{"id": "q-1", "label": "1. <specific question>"}]}
```

## In the chat

```
## Chunk <n> of <total>: <chunk title> · Card <n> of <total>: Compare

| Step | <example A> | <example B> |
|---|---|---|
| <step> | <A at this step> | <B at this step> |

Answer by number:

1. <specific question>
```
