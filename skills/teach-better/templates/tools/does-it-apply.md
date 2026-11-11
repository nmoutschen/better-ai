# Tool: does it apply?

GIVE the user three or four short situations from their own work, and ASK, for each one, whether the rule or method of the chunk applies, and why. INCLUDE at least one near miss: a situation that looks like the others but lacks a feature the rule needs. This tool is a design choice.

## Use when

- The user has solved one practice problem of the chunk.
- The GOAL needs the user to recognise, in their own work, when to use the rule or method.
- You know two or more situations where the user will use the topic (section 1.1 of SKILL.md).

## Do not use

- Before the user has seen the rule and a worked example.
- When the user struggled on the last practice problem. GIVE more support first.
- When the rule applies to every case the user will meet.
- With a near miss you cannot justify. CHECK each verdict against the rule's conditions and a source (section 3.5 of SKILL.md).

## Steps

1. LIST the features a situation must have for the rule to apply.
2. WRITE three or four situations, each in one or two sentences, in the user's words for their work, not the field's terms. MAKE at least one a near miss that lacks one feature, and at least one a case the rule covers that looks different from the worked example.
3. ORDER them so the near miss is not first or last. DO NOT label them.
4. ASK, for each situation, "Does <rule or method> apply? Why or why not?"
5. WAIT for the answers. THEN GIVE a verdict per situation, and NAME the feature that decides it.
6. IF the user misses a near miss, ADD the feature it lacks to the take-away's "When to use this" table (section 6.2 of SKILL.md).

## On a page

```json
{"kind": "practice", "id": "<chunk-id>-applies", "title": "Does it apply?",
 "blocks": [{"type": "p", "text": "For each situation, say whether <rule or method> applies, and why."},
            {"type": "list", "numbered": true, "items": ["<situation>", "<situation>", "<situation>"]}],
 "fields": [{"id": "s-1", "type": "choice", "label": "1. Does it apply?", "options": ["Applies", "Does not apply"]},
            {"id": "s-1-why", "label": "1. Why"},
            {"id": "s-2", "type": "choice", "label": "2. Does it apply?", "options": ["Applies", "Does not apply"]},
            {"id": "s-2-why", "label": "2. Why"}]}
```

## In the chat

```
## Chunk <n> of <total>: <chunk title> · Card <n> of <total>: Does it apply?

For each situation, say whether <rule or method> applies, and why. Answer by number.

1. <situation>
2. <situation>
3. <situation>
```
