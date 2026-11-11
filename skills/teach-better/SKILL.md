---
name: teach-better
description: Helps an AI agent teach the user a new topic so they can use it later without AI. Gives hints and worked examples instead of answers, checks understanding with practice the user does alone, and handles pushback when the user wants the answer.
argument-hint: "[TOPIC]"
---

# Teach Better

IF invoked with a topic as argument, TEACH that topic.
IF invoked without argument, TEACH the topic the user is currently asking about or working on.

## Principles

1. Answers from an AI raise a learner's scores while it helps and lower them once it is gone. Hints instead of answers avoid that loss, though learners rate hints as slower and less useful.
2. Learners who study with AI overestimate what they know. Judge learning by what they can do, not by what they say.
3. AI hints and feedback contain errors, and a learner cannot catch an error they share.
4. Help that suits a beginner can hinder a learner who knows more. Adapt to what the learner can do: matching a stated learning style has little support.
5. Asking learners to explain their answers helped in every medium tested. The lesson page is a design choice.
6. Whether people use a skill depends less on their test scores than on their confidence and their chances to use it. Practice on real tasks, plans for when to use a skill, and feedback on real use each went with more use.
7. A reference at hand helps people perform, but cannot tell them when to use it, and learners who expect to keep a record remember less of it. Skills decay without use, and spaced practice slows the decay.
8. The tools in section 2.4 and the take-away are design choices for an AI tutor. TREAT these rules as a guide, not as fixed rules.

## 1. Confirm that the user wants to learn

### 1.1. Name the GOAL

IDENTIFY what the user must be able to do WITHOUT AI after the lesson: explain a concept, solve a type of problem, use a tool, or make a kind of decision. WRITE it as a task they could be tested on.

FIND OUT where and when the user will use it: the situations and tasks they will meet. LOOK in the context first, and ASK only for what it does not show. USE these situations for practice problems, quizzes and the take-away. Whether people use a skill after training depends more on their chances to use it than on their test scores.

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

BUILD practice problems from the situations where the user will use the topic (section 1.1), once they have solved one generic problem. Training that resembled the work situation went with more use afterwards. DO NOT personalise problems to the user's hobbies or to fields where they will not use the topic: that raised motivation without improving learning.

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

AT the end of each few chunks, GIVE a short quiz: two or three questions the user answers without looking back and without your help. MAKE most questions tasks the user will do in the situations from section 1.1, and INCLUDE at least one problem that differs from the examples. Questions train the kind of task they ask for. ASK for a fact only when the user must know it without looking it up. IF the quiz covers problem types the user could confuse, CONSIDER the mixed set tool (section 2.4).

TELL the user before the first chunk that quizzes are closed-book. Learners who expected a closed-book test retained more. ON a page, PUT the quiz in its own chunk with `"quiz": true`: the page hides the other chunks until you set it to `done`. GIVE no feedback on a quiz answer until the user has answered every question in the quiz: `wait` holds quiz answers until then. THEN WRITE the feedback for all of them. DO NOT ask the user to answer a quiz question again: a quiz checks what they know, it does not teach. IF a wrong answer comes from an unclear question, SAY so and COUNT the answer by the user's reading.

DO NOT accept "I get it" or "makes sense" as evidence of understanding. TRUST what the user can do in the quiz.

### 4.2. Plan practice and use

BEFORE the end of the lesson, ASK when the user will next use the topic, and how often.

- IF the user will use it within days and regularly, real use is the practice. SUGGEST a first use as soon as possible: few chances to use a skill were the main barrier to using it, and reviews of training advise a short delay before first use. OFFER a follow-up session where the user brings a real attempt and gets feedback on it. Coaching on real work after training went with gains in what people did.
- IF the user will not use it for weeks or longer, PLAN three practice sessions, and PUT their dates in the take-away (section 6.2). SET the first gap to about a fifth to a third of the time until the user needs the skill when that is a week or a few weeks, and to about a twentieth to a tenth when it is a year. KEEP later gaps equal or growing. A gap that is too long costs much less than one that is too short.
- IF the user will use it rarely, SUGGEST one more session a few months after the last one. Unused procedural skills lost about half their gains in accuracy after six months.

Learners rarely plan practice themselves, and daily reminder messages did not make them practise. Learners who chose a program that a system scheduled completed most of it. IF the harness can schedule a task, OFFER to start each session on its date. OTHERWISE, OFFER to add the dates to the user's calendar. TREAT this as a guide. DO NOT schedule anything without the user's permission.

WHEN the user returns to the topic in a later message or session:

1. ASK what they did with the topic since the lesson. IF they used it, ASK for the attempt, and GIVE feedback on it as in section 3.4.
2. GIVE two or three tasks from their situations BEFORE you show any material, in a new situation each time. Trying first helps the restudy that follows, even when the attempt fails. IF earlier chunks hold problem types the user could confuse, MIX the tasks, following the mixed set tool.
3. GIVE feedback on each answer. Practice helped more with feedback, and attempts that mostly failed did not help without it. IF the user misses most tasks on a chunk, RE-TEACH it before giving more.
4. GIVE a new task, later in the same session, for each one the user missed.

## 5. Handle pushback

The user may ask for the answer, or say the guidance is slow. This is expected and does not mean the method is failing.

THE FIRST TIME, EXPLAIN in one or two sentences that getting answers feels faster but leads to less learning, and OFFER a bigger hint.

IF the user insists, GIVE the answer with the reasoning for each step, then GIVE a new similar problem to try. The user decides how they learn. DO NOT refuse, lecture, or repeat the explanation.

IF the user's GOAL changes from learning to getting a result, STOP teaching and ANSWER.

## 6. End the lesson

### 6.1. Say what the user can do

SUMMARISE what the user can now do, based on the quizzes, and what they still struggled with. FOR a decision scenario, REPORT agreement with the cited experts, not decision skill: the link between the two is untested. LIST the chunks not covered, if any.

DO NOT praise the user's progress beyond what the quizzes show.

### 6.2. Give a take-away

AFTER the last quiz, GIVE the user a take-away: a reference they keep open while they use the topic, without AI. The user can decline it.

1. **Timing.** DO NOT mention the take-away before the last quiz is done, and DO NOT give it before then. Learners who expect to keep a record remember less of what it holds, and the user must still recognise without it when a rule applies. IF the user asks for notes during the lesson, SAY that a take-away comes after the last quiz, and that the quizzes stay closed-book. IF the user still wants notes now, GIVE them, as in section 5. IF the lesson ends before the last quiz, GIVE the take-away when it ends.
2. **The user's plans first.** ASK the user to write, without looking back, one to three plans in the form "When <situation>, I will <step from the lesson>." SAY it is optional. CHECK that each plan names a situation from section 1.1 and a step the lesson taught, and ASK the user to fix a plan that does not. THEN ASK the user to picture the first situation and say what they will do. Plans in this if-then form raised use of trained skills, most when the person was motivated and rehearsed the plan. ON a page, ASK in a `practice` card with one `text` field.
3. **Write the take-away.** READ [templates/take-away.md](templates/take-away.md) and FOLLOW its format. LEAD with when to use the topic: the situations, the signs that a rule applies, and the user's plans. A reference cannot tell the user when to open it. THEN GIVE the steps as a checklist, each rule with its conditions, a short account of why it works, one worked example per chunk, and the mistakes the user made. A checklist helped most for steps people rarely use, and knowing why a procedure works helped with new cases. END with practice tasks from the user's situations, with their dates from section 4.2 and worked solutions kept apart.
4. **Keep it to the lesson.** INCLUDE only what the lesson taught and the user practised. CITE the same sources as the cards. CHECK every rule, example and answer as in section 3.5: the user will use the take-away without AI, with no one to catch an error.
5. **Deliver it.** IF you can write files, WRITE it to `.teach/<topic-slug>/take-away.md` and GIVE the user its path once. IF the user wants it elsewhere or in another format, FOLLOW that. ON a page, ALSO ADD it as the last chunk, titled "Take-away", with a `text` card per section. OTHERWISE, SEND it in the chat as one message.
6. **Use it once.** GIVE one task from the user's situations to do with the take-away open, and GIVE feedback. About a third of trainees given an aid did not use it, and the authors concluded that people need practice in when and how to use one.

The format of a take-away is a design choice.

### 6.3. Close the lesson

ON a page, SET the lesson's `status` to `ended`, so the server stops.
