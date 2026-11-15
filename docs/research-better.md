# `/research-better`

Researches a topic from sources instead of the model's training data, and writes a report with citations. It tracks questions, sources and claims on a research board, lets cheaper worker agents research in parallel, and has separate agents check each claim against the source page.

## When to use it

- To answer a question from sources: a topic to understand, a choice to make, a review of what is known.
- To answer a simple factual question, such as a date or a current value. It stops after one or two searches and answers in one or two sentences, naming the source.
- To research your organisation's own systems or decisions, from the internal tools your agent can reach, such as a wiki or ticket tracker.

Use something else nearby:

- To learn a topic yourself, use [`/teach-better`](teach-better.md). It calls `/research-better` first.
- To introduce the finished report with visual panels, use [`/show-better`](show-better.md).

## How to run it

```
/research-better <topic>
```

Example: `/research-better do code review checklists reduce defects?`.

Without an argument, it resumes from an existing research board, or restarts the previous research.

## What happens

1. **It searches before asking.** It runs a search or two with the topic's own words to see which meanings sources use. If the topic still has several meanings, it explains each and asks which one you meant.
2. **It picks the depth.** It chooses a goal and a stop level: `high` for a quick decision, `medium` by default, or `low` for an exhaustive review from what you need. It does not ask you for a budget, and says what it chose so you can correct it.
3. **It opens a board** in `.research/<topic-slug>/` and tells you the path. If it can, it opens a live view of the board in your browser.
4. **It seeds questions** from your question and from broad searches, including searches in other languages when the topic has sources there. Each question says what evidence would answer it.
5. **Workers research the questions.** Each records every query, source and claim on the board as it goes, with a verbatim quote for each claim. As they read, they add questions:
   - newer work, origins, other fields, other regions and critics
   - the works a key source cites and the works that cite it
   - for each key answer, a challenge question that looks for contradicting evidence
6. **Verifiers check claims while the research runs.** A verifier opens the source page, copies the passage the claim rests on, and judges the claim from it. The coordinating agent reads their flags and compares key claims with the copied passages.
7. **It stops** when no question at the stop level is still open, or when results stop adding anything new after one change of strategy. It does not stop because it found the answer it expected.
8. **It presents the findings** with APA citations, a reference list built only from the board, what each challenge question found, and the questions that remain open.

If a source it needs is unreachable (a missing tool, a login, an error), it does not fill the gap from other sources or from memory. It tells you and asks whether to wait, continue without it, or read sources you give it. It never puts internal names or text in a web search.

Without a live view, it posts one line in the chat each time a question closes.

## What you get

- A research board in `.research/<topic-slug>/`: the questions, sources, claims with quotes, search logs and verification results. It is not committed unless you ask, and a later session can resume from it.
- A live board page while the research runs, or progress lines in the chat.
- A report: the answer first, where sources disagree or evidence is weak, citations in APA style (7th edition), a reference list, and open questions or blocked sources that could change the answer.

## Works with

- [`/write-better`](write-better.md) writes the final report.
- [`/teach-better`](teach-better.md) calls `/research-better` before a lesson on a topic that is not trivial.

## What it needs

| Capability | Without it |
|---|---|
| Search and page reads | If a source the topic needs cannot be searched, it tells you and asks how to continue. It does not describe pages it could not open. |
| Sub-agents | It runs the research loop itself, one question at a time. |
| Background sub-agents | It starts a group of workers, waits for them, then starts the next group. |
| Choosing a worker's model | It runs workers on a cheaper model than its own when it can, and does not create or edit harness configuration without your permission. |
| Background commands and a browser that can reach the machine | It tells you how to start the live view yourself, or posts progress in the chat. |
| Writing files | It keeps the board in its working notes and restates it every few results. |
| Asking through a tool | It asks in plain text and waits for your answer. |
