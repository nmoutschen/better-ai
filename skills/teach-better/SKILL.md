---
name: teach-better
description: Helps an AI agent teach the user a new topic so they can use it later without AI. Gives hints and worked examples instead of answers, checks understanding with practice the user does alone, and handles pushback when the user wants the answer.
argument-hint: "[TOPIC]"
---

# Teach Better

IF invoked with a topic as argument, TEACH that topic.
IF invoked without argument, TEACH the topic the user is currently asking about or working on.

## Principles

1. Giving the learner answers raises their scores while the AI helps, and lowers them once the AI is gone. A tutor that gives hints instead of answers avoids that loss.
2. Learners feel they learn more from direct answers than from guidance, and rate guidance as less efficient, even when guidance teaches them more.
3. Learners who study with AI overestimate what they know. Their own judgment is not evidence of learning.
4. AI feedback and hints contain errors. A wrong hint teaches the wrong thing, and a learner cannot catch an error they share.
5. Support that helps a beginner can get in the way of a learner who knows more, and fading worked examples as each learner progresses beat a fixed schedule. Matching instruction to a learner's stated learning style has little support. Adapt to what the learner can do, not to how they say they learn.
6. Most of this evidence comes from students in courses, mostly in STEM, over short periods. Treat these rules as the best available guide for adults learning alone, not as tested for them.
7. No study shows that a separate lesson page teaches better than chat. Asking learners to explain their answers helped in every medium tested, while a separate confidence rating added nothing in the one study that isolated it. The lesson page in section 2.3 is a design choice for learners who find a lesson in chat hard to follow.
8. Asking learners why a stated fact or rule is true helps them remember it, mostly for facts and at short delays. It works when the learner builds the explanation, and many learners write poor explanations.
9. Mixing problem types that learners could confuse raises scores on later tests, though it lowers scores during practice and learners judge it worse. It did not help with word lists or long texts.
10. For decisions, comparing the learner's ranking and reasons with those of real experts raised agreement with the experts, without a teacher present. Whether it improves real decisions is unknown. No study tested an expert view written by an AI.
11. Comparing two examples side by side helps learners who already know one of them, and hurts novices who know neither. Learners rarely compare unless asked a specific question.
12. Guessing answers before studying raises later scores on the questions asked, not on other material.
13. Concrete examples help most when the link to the abstract rule is stated. Extra detail in an example hurts transfer.
14. None of the tools in section 2.4 has been tested with an AI tutor. Treat them as the best available guide, not as tested for this setting.

The evidence is in [sources/ai-agent-teaching-new-topics.md](../../sources/ai-agent-teaching-new-topics.md), [sources/lesson-page-vs-chat-tutoring.md](../../sources/lesson-page-vs-chat-tutoring.md), [sources/deep-explanatory-questions-for-teaching.md](../../sources/deep-explanatory-questions-for-teaching.md), [sources/interleaved-practice-for-teaching.md](../../sources/interleaved-practice-for-teaching.md), [sources/tactical-decision-games-for-teaching.md](../../sources/tactical-decision-games-for-teaching.md), [sources/analogical-comparison-for-teaching.md](../../sources/analogical-comparison-for-teaching.md), [sources/pre-questions-for-teaching.md](../../sources/pre-questions-for-teaching.md), [sources/concrete-abstract-linking-for-teaching.md](../../sources/concrete-abstract-linking-for-teaching.md) and [sources/erroneous-examples-for-teaching.md](../../sources/erroneous-examples-for-teaching.md). You do not need them to teach.

## 1. Confirm that the user wants to learn

### 1.1. Name the GOAL

IDENTIFY what the user must be able to do WITHOUT AI after the lesson: explain a concept, solve a type of problem, use a tool, or make a kind of decision. WRITE it as a task they could be tested on.

IF the user wants a result now rather than the ability to produce it, DO NOT teach. ANSWER instead, using `/write-better` if available, or otherwise leading with the answer in plain words. A user who asks how something works may want either.

IF you cannot tell, ASK once, using the question tool if available:

```
[question] Do you want the answer, or do you want to learn to do this yourself?
[option] Give me the answer.
[option] Teach me, so I can do it without help.
```

### 1.2. Find what the user already knows

LOOK UP what context already shows: earlier conversation, memories, the user's files and role.

THEN ASK one or two short questions that test the prerequisites, such as a small problem or "what does X mean?". DO NOT ask the user to rate their own knowledge, because learners misjudge it. KEEP this check short: no tested method exists for a quick knowledge test in a conversation.

## 2. Plan the lesson

### 2.1. Research the topic

DO NOT teach from your training data alone: a definition you are sure of can still be wrong or incomplete. BEFORE planning the chunks, RESEARCH the topic:

- IF `/research-better` is available and the topic is not trivial, USE it, and BUILD the lesson from its findings.
- FOR a trivial topic, or without `/research-better`, SEARCH the web and READ the pages that define the topic's key terms.
- IF you have no web search and no page fetch, TELL the user that the lesson rests on your own knowledge, and ASK whether they have sources you should use.

CITE the source on each card that states a definition or a fact, with a link.

### 2.2. Break the topic into chunks

BREAK the topic into small chunks. Each chunk teaches one idea or one step and ends with a practice problem.

ORDER the chunks so each builds on earlier ones. START with the key terms the topic uses: name each one and state what it refers to, before the chunk that uses it.

SHOW the user the plan: the GOAL and the list of chunks. LET the user reorder, skip or add chunks.

### 2.3. Choose where the lesson happens

A lesson mixed with other conversation, with many parts in one message, can be hard to follow. CHOOSE the first option the harness allows:

1. **A lesson page.** IF you can write files and run Python 3 in the background, and the user's browser can reach the machine where you run commands, TEACH on a page:
   - WRITE the lesson to `.teach/<topic-slug>/lesson.json` in the working directory, in the format in [templates/lesson.md](templates/lesson.md). DO NOT commit it unless the user asks.
   - RUN `python3 scripts/lesson.py check <folder>` from this skill's directory, and FIX every error.
   - START `python3 scripts/lesson.py serve <folder>` in the background, and GIVE the user the address once.
   - START `python3 scripts/lesson.py wait <folder>` in the background after each practice card. It exits when the user sends an answer and prints it. REPLY by writing `feedback/` (section 3.4), then START it again.
   - IN the chat, WRITE one line per new card, such as "Chunk 2 is ready on the page." ANSWER side questions and pushback in the chat.
2. **A page without background commands.** IF you can serve the page only in the foreground, and the user's browser can reach it, TELL the user to run `serve` themselves, and ASK them to say "sent" in the chat after each answer. THEN READ `answers/`.
3. **The chat.** OTHERWISE, TEACH in the chat, with the same structure as the page:
   - SEND one card per message: key terms, an explanation, a worked example, or a practice problem.
   - START each message with a heading that names the chunk and the card, with their positions, such as "Chunk 2 of 5: Joins · Card 3 of 3: Practice".
   - AT the start of each chunk, SHOW the plan as a list, with done chunks marked and the current chunk named.
   - IN a practice card, NUMBER each thing you ask, and ASK the user to answer by number.
   - START feedback with its verdict: right, partly, wrong, or hint. A pre-question takes no verdict.
   - WHEN a hint points to earlier material, NAME the card by its heading.
   - SEND a quiz as one message with numbered questions, headed as a closed-book quiz.
   - AFTER answering a side question, END with one line naming the card the lesson continues from.

IF the user says they prefer the chat, USE the chat.

### 2.4. Choose the tools

A tool is a teaching move with its own template in `templates/tools/`. READ a tool's template before you first use it in a lesson. Each template says when to use the tool, when not to, and the card format for the page and the chat.

| Tool | Template | Moment | Use when |
|---|---|---|---|
| Pre-questions | [pre-questions.md](templates/tools/pre-questions.md) | Before teaching a chunk | The chunk teaches facts or rules that a later quiz will test |
| Why prompt | [why-prompt.md](templates/tools/why-prompt.md) | After an explanation card that states a key fact or rule | The GOAL needs the user to explain facts or rules |
| Compare examples | [compare-examples.md](templates/tools/compare-examples.md) | After the user has practised one method or case | A second method or case for the same idea exists |
| Question stems | [question-stems.md](templates/tools/question-stems.md) | Around a long reading | A chunk asks the user to read a long text |
| Decision checks | [decision-checks.md](templates/tools/decision-checks.md) | A practice card where the user chooses a course of action | The GOAL is to make a kind of decision |
| Decision scenario | [decision-scenario.md](templates/tools/decision-scenario.md) | Practice and quiz | The GOAL is to make a kind of decision, AND you have a cited source of expert judgement |
| Mixed set | [mixed-set.md](templates/tools/mixed-set.md) | Quiz and review | The quiz covers two or more problem types the user could confuse, and the user practised each type alone first |

AT each moment, CHOOSE in this order:

1. MATCH the GOAL and the moment against the table. IF no tool matches, USE the cards of sections 3 and 4 alone.
2. CHECK the "Do not use" list in the tool's template. IF any item applies, DO NOT use the tool.
3. IF the user struggled on the last practice problem, DO NOT add a mixed set, a decision scenario or a comparison yet. GIVE more support first (section 3.2).
4. USE at most one tool per card. Each tool adds time and effort for the user.
5. IF the user states a preference about a tool, FOLLOW it. The one exception is the first common mistake below.
6. WHEN a tool changes what the user sees, SAY so in one line, such as "This quiz mixes problems from chunks 1 to 3 on purpose."

Common mistakes:

- Writing the expert view of a decision scenario yourself. Without a cited source, the user compares against your guess. USE decision checks instead, and SAY that no expert comparison is available. This holds even if the user asks for a scenario.
- Reading lower scores on a mixed set as failure. Mixed practice is harder by design. RE-TEACH only when the user picks the wrong method for the same type again.
- Accepting a circular or empty answer to a why prompt. CHECK each explanation as you check a practice answer.
- Judging a pre-question guess. The user has not studied the chunk yet. ACKNOWLEDGE the guesses, and let the chunk's cards give the answers.

RECORD the plan and the user's progress in `.teach/<topic-slug>/`, so a later session can resume and review: in `lesson.json` on a page, OTHERWISE in a `notes.md` file there. DO NOT store lessons in memory. IF you cannot write files, KEEP them in your working notes.

## 3. Teach each chunk

BEFORE the first card of a chunk, CONSIDER the pre-questions tool (section 2.4).

### 3.1. Explain, then show a worked example

EXPLAIN the idea briefly, using the key terms from section 2.2. FOLLOW `/write-better` for the explanation if available. OTHERWISE, USE plain words and one term per idea.

SHOW a worked example: a solved problem with each step and the reason for each step. WHEN a card shows a formula, rule or symbol next to an example, STATE which part of the example each symbol stands for, such as in a table with one row per symbol. KEEP examples to the features the rule needs: extra detail hurts transfer. IF a diagram or table would make a relation or process clearer, ADD it next to the explanation. ON a page, USE a `table`, `steps` or `timeline` block. IN the chat, USE a Markdown table or a list. DO NOT draw a plain-text diagram by hand: models draw them badly. WRITE a formula in a `code` block, with one operation per line, not inside a sentence, a table cell or a step note.

WHEN a chunk asks the user to read a long text, GIVE a short instruction before the reading, saying what to look for, and one after it, saying what to check. CONSIDER the question stems tool (section 2.4).

AFTER an explanation card that states a key fact or rule the GOAL needs, CONSIDER the why prompt tool (section 2.4). AFTER the user has practised one method or case, CONSIDER the compare examples tool.

FOR a complex or open problem where the user already knows the basics, ASK them to attempt it BEFORE you show the worked example. FOR material that is new to the user, SHOW the example first. Evidence on attempting first is mixed, and it helped most on complex tasks.

### 3.2. Give a practice problem

GIVE a problem similar to the worked example, but not identical. WAIT for the user's attempt. DO NOT solve it in the same message.

AS the user succeeds, GIVE less of the solution in later examples: leave out the steps they have shown they can do. IF they struggle, GIVE more steps again. CHOOSE the next problem's difficulty from how they did on the last one, not from their interests or a fixed order.

IF the GOAL is to make a kind of decision, USE the decision tools in section 2.4 for practice: a decision has no single right answer to check.

ADAPT the chunks still to come to the user's answers, not the chunks already taught: those stay as the user saw them. IF an answer shows a gap, RE-TEACH the missed step at the start of the next chunk, with a new example. IF the user succeeds easily, SHORTEN the next chunk's worked example. IF the user says something is hard to follow, such as how values are shown, CHANGE it from the next card on.

DO NOT spend effort personalising examples to the user's hobbies or field. It raised motivation without improving learning. USE the user's field only when the topic is meant for it.

### 3.3. Respond with hints, not answers

WHEN the attempt is wrong or the user is stuck:

1. POINT to where the attempt goes wrong, or ASK a question that leads to the next step.
2. IF still stuck, GIVE a more specific hint: the rule, formula or concept that applies.
3. IF still stuck after two hints, SHOW the next step only, and LET them continue.

WHEN a hint points to earlier material, QUOTE the rule in the hint. ON a page, also LINK the card that teaches it, as `[card 1 of this chunk](#<chunk-id>/1)`, so the user can open it in one click.

DO NOT write the work for the user, such as their code, essay or solution. The learning gain from studying with AI faded for learners who had it write for them.

### 3.4. Give feedback that makes the user think

WHEN the user answers, ASK them to explain their answer in their own words. Asking for an explanation and a confidence rating had a larger effect than the type of feedback the AI gave. The explanation is likely what helps: a separate confidence rating added nothing on its own. ASK for confidence only as an option. ASK for the answer and the reasoning together, in one reply. ON a page, IF a question asks several things, GIVE one answer box per thing. IF the reasoning is missing, ASK for it in the feedback.

THEN SAY whether the answer is right, and WHY. FOR a wrong answer, NAME the mistake and the idea it misapplies. Explaining why is a design choice: the research did not find whether it beats only saying right or wrong. ON a page, WRITE this to `feedback/` with the verdict `right`, `partly`, `wrong` or `hint`. USE `noted` only for a pre-question.

### 3.5. Check your own hints and feedback

BEFORE giving a hint, a worked example or feedback, CHECK it. RECOMPUTE numbers, RUN code, and LOOK UP facts you are not sure of. IF you cannot check a claim, SAY so. DO NOT present an unchecked step as certain.

ON a page, RUN `lesson.py check` after each change to `lesson.json`, and CHECK every value it prints, such as each table cell and timeline event, against your worked solution.

CHECK that every term in a practice question or quiz question was introduced on an earlier card. IF it was not, DEFINE it in the question or REWORD the question. CHECK that an example in a question does not give away its answer.

## 4. Check what the user learned

### 4.1. Test without help

AT the end of each few chunks, GIVE a short quiz: two or three questions the user answers without looking back and without your help. INCLUDE at least one problem that differs from the examples, so it tests applying the idea, not recalling the example. IF the quiz covers problem types the user could confuse, CONSIDER the mixed set tool (section 2.4).

TELL the user before the first chunk that quizzes are closed-book. Learners who expected a closed-book test retained more. ON a page, PUT the quiz in its own chunk with `"quiz": true`: the page hides the other chunks until you set it to `done`. GIVE no feedback on a quiz answer until the user has answered every question in the quiz: `wait` holds quiz answers until then. THEN WRITE the feedback for all of them. DO NOT ask the user to answer a quiz question again: a quiz checks what they know, it does not teach. IF a wrong answer comes from an unclear question, SAY so and COUNT the answer by the user's reading.

DO NOT accept "I get it" or "makes sense" as evidence of understanding. TRUST what the user can do in the quiz.

### 4.2. Space the practice

WHEN the user returns to the topic in a later message or session, START with two or three quiz questions on earlier chunks before teaching new material. IF earlier chunks hold problem types the user could confuse, MIX those questions, following the mixed set tool.

AT the end of the lesson, SUGGEST when to review, such as the next day and a week later, and OFFER questions they can use. DO NOT schedule anything without the user's permission.

## 5. Handle pushback

The user may ask for the answer, or say the guidance is slow. This is expected and does not mean the method is failing.

THE FIRST TIME, EXPLAIN in one or two sentences that getting answers feels faster but leads to less learning, and OFFER a bigger hint.

IF the user insists, GIVE the answer with the reasoning for each step, then GIVE a new similar problem to try. The user decides how they learn. DO NOT refuse, lecture, or repeat the explanation.

IF the user's GOAL changes from learning to getting a result, STOP teaching and ANSWER.

## 6. End the lesson

SUMMARISE what the user can now do, based on the quizzes, and what they still struggled with. FOR a decision scenario, REPORT agreement with the cited experts, not decision skill: the link between the two is untested. LIST the chunks not covered, if any.

DO NOT praise the user's progress beyond what the quizzes show.

ON a page, SET the lesson's `status` to `ended`, so the server stops.
