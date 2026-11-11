# Tool: mixed set

MIX problems of different types in a quiz or a review, instead of grouping them by type. The user must first decide which method or category applies. Mixing raised scores on tests days to weeks later. It lowers scores during practice, and learners judge it worse.

## Use when

- The quiz or review covers two or more problem types that look alike but need different methods or categories.
- The user practised each type alone first, in its own chunk.

## Do not use

- For word lists, such as vocabulary. Mixing them helped less than grouping them.
- For long texts. Mixing texts showed no overall benefit.
- For unrelated topics, or to mix whole chunks. The benefit comes from comparing similar problems placed next to each other.
- When the user struggled on the last practice problem. GIVE more support first.

## Steps

1. LIST the problem types the quiz covers, and PICK the types the user could confuse.
2. WRITE at least one problem per type. CHECK that the wording does not give away the type.
3. ORDER the problems so that no two problems of the same type come one after the other.
4. DO NOT name the type or the chunk in a card title or a question. Choosing the method is part of the task.
5. ASK the user to name the method they chose and why, with their answer.
6. SAY in one line that the set mixes types on purpose, and that it feels harder.
7. WHEN the user picks the wrong method, NAME the feature that tells the two types apart. RE-TEACH only IF they pick the wrong method for the same type again. DO NOT read lower scores on a mixed set as failure: mixing is harder by design.

## On a page

```json
{"id": "<quiz-id>", "title": "Quiz: chunks <n> to <n>", "status": "current", "quiz": true,
 "cards": [{"kind": "practice", "id": "<quiz-id>-1", "title": "Question 1",
            "blocks": [{"type": "p", "text": "<problem>"}],
            "fields": [{"id": "method", "label": "Which method applies, and why"},
                       {"id": "answer", "label": "Your answer, and how you got it"}]}]}
```

## In the chat

```
## Quiz: chunks <n> to <n> (closed book)

These questions mix problem types on purpose. For each one, say which method applies and why, then answer. Answer by number.

1. <problem>
2. <problem>
```
