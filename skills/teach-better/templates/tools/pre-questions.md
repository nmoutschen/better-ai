# Tool: pre-questions

BEFORE teaching a chunk, ASK the user to guess the answers to two or three questions about its key facts. THEN teach the chunk, which gives the answers. Guessing first raised later scores on those same questions. Pre-questions about concepts did not improve learning of the concepts.

## Use when

- The chunk teaches facts the user must know without looking them up, such as a limit, a default or a safety rule they need in the moment.
- The user has not studied the chunk yet.

## Do not use

- To prepare the user to apply a rule or method. The benefit stays with the facts asked, and does not reach application. USE the "does it apply?" tool after the chunk instead.
- For terms the user can look up when they need them.
- With questions that need inference or a full method. Factual questions helped more. FOR a complex problem, USE the attempt-first rule in section 3.1 of SKILL.md instead.
- When the chunk does not answer the question. The benefit depends on the user studying the answer afterwards.
- On every chunk. Learners judge the technique less useful than reading.

## Steps

1. PICK two or three facts from the chunk that the user must know without looking them up. WRITE one question per fact, answerable in a word, a number or a sentence.
2. ASK the user to write a guess for each, and SAY in one line that wrong guesses are expected and help them remember the answer.
3. WAIT for the guesses. DO NOT give a verdict or the answers. ON a page, WRITE the feedback with the verdict `noted` and one line saying that the next cards answer the questions.
4. TEACH the chunk. ON the card that gives each answer, POINT back to the question, such as "This answers pre-question 2."
5. IN the next quiz, TEST these facts inside a task that uses them, not as recall questions.

## On a page

```json
{"kind": "practice", "id": "<chunk-id>-pre", "title": "Before you start: guess",
 "blocks": [{"type": "p", "text": "Guess the answers before this chunk. Wrong guesses are expected: the next cards give the answers."}],
 "fields": [{"id": "pre-1", "type": "short", "label": "1. <question>"},
            {"id": "pre-2", "type": "short", "label": "2. <question>"}]}
```

USE a `choice` field instead of `short` IF the question has a few plausible answers.

Feedback, in `feedback/<id>.<n>.json`:

```json
{"verdict": "noted", "text": "Thanks. The next cards answer these questions."}
```

## In the chat

```
## Chunk <n> of <total>: <chunk title> · Before you start

Guess the answers, by number. Wrong guesses are expected: the next cards give the answers.

1. <question>
2. <question>
```
