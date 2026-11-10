# Tool: decision checks

BEFORE the user commits to a course of action, ASK them to state the goal, what they expect to happen, and the main risk and benefit. In one study, these prompts led decision makers to plan before acting, instead of moving from information straight to action. The evidence is one study, read as an abstract: TREAT this tool as a guide, not a rule.

## Use when

- The GOAL is to make a kind of decision.
- A practice card asks the user to choose a course of action, alone or inside a decision scenario.

## Do not use

- On problems with one right answer to check. USE a practice problem instead.

## Steps

1. GIVE the situation and the decision to make.
2. ASK for the four fields below, in this order, in one reply.
3. CHECK that each field is about this situation, not general advice.
4. CHECK the expected consequences against the lesson's explanation cards or the cited source. NAME any consequence the user missed, with the card or source that shows it.

## On a page

```json
{"kind": "practice", "id": "<chunk-id>-checks", "title": "<decision to make>",
 "blocks": [{"type": "p", "text": "<situation>"}],
 "fields": [{"id": "goal", "label": "What are you trying to achieve here?"},
            {"id": "choice", "label": "What would you do?"},
            {"id": "expect", "label": "What do you expect to happen next?"},
            {"id": "risk", "label": "What is the main risk, and the main benefit?"}]}
```

## In the chat

```
## Chunk <n> of <total>: <chunk title> · Card <n> of <total>: Decide

<situation>

Answer by number:

1. What are you trying to achieve here?
2. What would you do?
3. What do you expect to happen next?
4. What is the main risk, and the main benefit?
```
