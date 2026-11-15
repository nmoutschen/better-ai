# `/teach-better`

Teaches you a new topic so you can use it later without AI. It gives hints and worked examples instead of answers, checks what you learned with practice you do alone, and ends with a take-away you keep open while you use the topic.

## When to use it

- When you want to be able to do something yourself: explain a concept, solve a kind of problem, use a tool, or make a kind of decision.
- When you come back to a topic you learned before, to practise it.

If you want a result now rather than the ability to produce it, it does not teach. It answers instead, through [`/write-better`](write-better.md). If it cannot tell which you want, it asks once: "Do you want the answer, or do you want to learn to do this yourself?"

## How to run it

```
/teach-better <topic>
```

Example: `/teach-better SQL joins for the weekly sales report`.

Without an argument, it teaches the topic you are asking about or working on.

## What happens

1. **It names the goal** as a task you could be tested on, and asks where and when you will use it, if the context does not show that.
2. **It researches the topic** before asking you anything about it, with [`/research-better`](research-better.md) for a topic that is not trivial. Each card that states a definition or fact cites its source.
3. **It checks what you know** with one or two short questions, such as a small problem. It does not ask you to rate your own knowledge.
4. **It shows the plan:** the goal and a list of small chunks, each named by what you will do. You can reorder, skip or add chunks.
5. **It teaches each chunk.** Each chunk has an explanation in plain words, a worked example and a practice problem:
   - When you get stuck, you get a hint, not the answer.
   - When you answer, it asks you to explain your answer in your own words.
   - Terms come in the chunk that first needs them.
6. **It adds teaching tools when they fit your goal:**
   - questions before a chunk
   - "why?" prompts
   - "does it apply?" checks with near misses
   - comparisons of two examples
   - question stems for a long reading
   - decision checks, and decision scenarios compared with a cited expert view
   - mixed quizzes
7. **It quizzes you closed-book** every few chunks. It gives no feedback until you have answered every question. "I get it" does not count; the quiz does.
8. **It plans practice:**
   - If you will use the topic soon, it agrees a first real use with you and offers a follow-up on that attempt.
   - If you won't use it for weeks, it plans three practice sessions with dates.
   - It offers to schedule them, or to add them to your calendar.
9. **It ends with a take-away**, after the last quiz:
   - It first asks you to write one to three plans, such as "When <situation>, I will <step>".
   - It writes the take-away, then gives you one task to do with it open.

If you ask for the answer, it explains once why hints help and offers a bigger hint. If you insist, it gives the answer with the reasoning for each step, then a similar problem to try. You decide how you learn.

When you return to the topic later, it asks what you did with it, gives you tasks before showing any material, and re-teaches a chunk you mostly miss.

## What you get

- A lesson page in your browser, or the same lesson in the chat, one card per message, with headings like "Chunk 2 of 5: Joins · Card 3 of 3: Practice". Say you prefer the chat and it uses the chat.
- The lesson and your progress in `.teach/<topic-slug>/` (`lesson.json` for a page, `notes.md` otherwise), so a later session can resume. It is not committed unless you ask.
- A take-away at `.teach/<topic-slug>/take-away.md`: when to use the topic and the signs a rule applies, your plans, the steps as a checklist, and practice tasks with dates when practice is planned.
- A summary of what you can now do, based on the quizzes, and what you still struggled with.

## Works with

- [`/research-better`](research-better.md) researches a topic that is not trivial before the lesson.
- [`/write-better`](write-better.md) writes the answer when you want a result, not a lesson, and the explanations.
- [`/write-better`](write-better.md) sends you here when the goal is to learn something over several turns.

## What it needs

| Capability | Without it |
|---|---|
| Web search or page fetch | It tells you the lesson rests on its own knowledge, and asks whether you have sources it should use. |
| Python 3 in the background and a browser that can reach the machine | If it can serve the page only in the foreground, it asks you to run the server and say "sent" after each answer. Otherwise it teaches in the chat. |
| Writing files | It keeps the plan and your progress in its working notes, and sends the take-away in the chat. |
| Scheduling tasks | It offers to add the practice dates to your calendar. |
