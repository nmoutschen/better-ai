# Tool: question stems

GIVE the user question stems before a long reading. AFTER the reading, ASK them to write questions about the main ideas with the stems, and to answer them. Generating questions helped when learners were trained and asked about concepts, not details.

## Use when

- A chunk asks the user to read a long text.

## Do not use

- When the user has not read the text yet. GIVE the stems before the reading, and ASK for questions after it.
- When the user's questions ask for details, such as a name, a number or a date. Questions about details gave no benefit. POINT this out and ASK for a question about a cause, a reason or a difference.

## Steps

1. BEFORE the reading, GIVE the stems and SAY that the user will write questions with them afterwards.
2. AFTER the reading, ASK for two or three questions about the main ideas, each built on a stem, and an answer to each.
3. CHECK each question: does it ask about a concept, a cause or a difference?
4. CHECK each answer, as in section 3.5 of SKILL.md. GIVE hints, not answers (section 3.3 of SKILL.md).

## Stems

```
Why does <...>?
How does <...> lead to <...>?
What would happen if <...>?
How is <...> different from <...>?
```

## On a page

```json
{"kind": "practice", "id": "<chunk-id>-questions", "title": "Your questions about the reading",
 "blocks": [{"type": "p", "text": "Write questions about the main ideas, using the stems below. Then answer each question."},
            {"type": "code", "text": "Why does <...>?\nHow does <...> lead to <...>?\nWhat would happen if <...>?\nHow is <...> different from <...>?"}],
 "fields": [{"id": "q-1", "label": "Question 1 and your answer"},
            {"id": "q-2", "label": "Question 2 and your answer"}]}
```

## In the chat

```
## Chunk <n> of <total>: <chunk title> · Card <n> of <total>: Your questions

Write two questions about the main ideas, using these stems. Then answer each one, by number.

- Why does <...>?
- How does <...> lead to <...>?
- What would happen if <...>?
- How is <...> different from <...>?
```
