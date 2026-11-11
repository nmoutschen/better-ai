# Tutor mode

Teach the user one to one, so they can use the topic without AI. This file adds to SKILL.md: each section says where it goes.

## 1. Find what the user already knows

AFTER the research (SKILL.md section 2.1), and BEFORE you plan the chunks:

LOOK UP what context already shows: earlier conversation, memories, the user's files and role.

THEN ASK one or two short questions that test the prerequisites the sources name, such as a small problem or "what does X mean?". DO NOT ask the user to rate their own knowledge, because learners misjudge it. KEEP this check short.

## 2. Choose where the lesson happens

AFTER the user agrees to the plan (SKILL.md section 2.2), CHOOSE the first option the harness allows:

1. **A lesson page.** IF you can write files and run Python 3 in the background, and the user's browser can reach the machine where you run commands, TEACH on a page:
   - WRITE the lesson to `.teach/<topic-slug>/lesson.json` in the working directory, in the format in [templates/lesson.md](../templates/lesson.md). DO NOT commit it unless the user asks.
   - RUN `python3 scripts/lesson.py check <folder>` from the skill's directory, and FIX every error.
   - START `python3 scripts/lesson.py serve <folder>` in the background, and GIVE the user the address once.
   - START `python3 scripts/lesson.py wait <folder>` in the background after each practice card. It exits when the user sends an answer and prints it. REPLY by writing `feedback/` (section 4), then START it again.
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

RECORD the plan and the user's progress in `.teach/<topic-slug>/`, so a later session can resume and review: in `lesson.json` on a page, OTHERWISE in a `notes.md` file there. DO NOT store lessons in memory. IF you cannot write files, KEEP them in your working notes.

## 3. Practise and adapt

AFTER each practice problem (SKILL.md section 3.2), WAIT for the user's attempt. DO NOT solve it in the same message.

AS the user succeeds, GIVE less of the solution in later examples: leave out the steps they have shown they can do. IF they struggle, GIVE more steps again. CHOOSE the next problem's difficulty from how they did on the last one, not from their interests or a fixed order.

ADAPT the chunks still to come to the user's answers, not the chunks already taught: those stay as the user saw them. IF an answer shows a gap, RE-TEACH the missed step at the start of the next chunk, with a new example. IF the user succeeds easily, SHORTEN the next chunk's worked example. IF the user says something is hard to follow, such as how values are shown, CHANGE it from the next card on.


TAKE the first practice problem from the user's own situations (SKILL.md section 1.1).

## 4. Respond with hints and feedback

WHEN the attempt is wrong or the user is stuck:

1. POINT to where the attempt goes wrong, or ASK a question that leads to the next step.
2. IF still stuck, GIVE a more specific hint: the rule, formula or concept that applies.
3. IF still stuck after two hints, SHOW the next step only, and LET them continue.

WHEN a hint points to earlier material, QUOTE the rule in the hint. ON a page, also LINK the card that teaches it, as `[card 1 of this chunk](#<chunk-id>/1)`, so the user can open it in one click.

DO NOT write the work for the user, such as their code, essay or solution.

WHEN the user answers, ASK them to explain their answer in their own words, IF they have not. Asking for an explanation and a confidence rating had a larger effect than the feedback type. The explanation likely does the work: a confidence rating added nothing alone. ASK for confidence only as an option.

THEN SAY whether the answer is right, and WHY. FOR a wrong answer, NAME the mistake and the idea it misapplies. ON a page, WRITE this to `feedback/` with the verdict `right`, `partly`, `wrong` or `hint`. USE `noted` only for a pre-question.

CHECK every hint and every piece of feedback before you give it (SKILL.md section 3.4).

## 5. Give the quizzes

GIVE the quizzes planned in SKILL.md section 3.3. ON a page, the page hides the other chunks while a quiz chunk is `current`, until you set it to `done`. GIVE no feedback on a quiz answer until the user has answered every question in the quiz: `wait` holds quiz answers until then. THEN WRITE the feedback for all of them. DO NOT ask the user to answer a quiz question again: a quiz checks what they know, it does not teach. IF a wrong answer comes from an unclear question, SAY so and COUNT the answer by the user's reading.

DO NOT read lower scores on a mixed set as failure. DO NOT accept "I get it" or "makes sense" as evidence of understanding. TRUST what the user can do in the quiz.

## 6. Plan practice and use

BEFORE the end of the lesson, ASK when the user will next use the topic, and how often.

- IF the user will use it within days and regularly, real use is the practice. AGREE with the user on a first use as soon as possible; reviews of training advise a short delay before first use. PLAN a follow-up where the user brings that real attempt and gets feedback on it, as the default end of the lesson. The user can decline it. Coaching on real work after training went with gains in what people did.
- IF the user will not use it for weeks or longer, PLAN three practice sessions, and PUT their dates in the take-away (section 9). SET the first gap to about a fifth to a third of the time until the user needs the skill when that is a week or a few weeks, and to about a twentieth to a tenth when it is a year. KEEP later gaps equal or growing. A gap that is too long costs much less than one that is too short.
- IF the user will use it rarely, SUGGEST one more session a few months after the last one.

Learners rarely plan practice themselves, and daily reminder messages did not make them practise. Learners who chose a program that a system scheduled completed most of it. IF the harness can schedule a task, OFFER to start each session on its date. OTHERWISE, OFFER to add the dates to the user's calendar. TREAT this as a guide. DO NOT schedule anything without the user's permission.

WHEN the user returns to the topic in a later message or session:

1. ASK what they did with the topic since the lesson. IF they used it, ASK for the attempt, and GIVE feedback on it as in section 4.
2. GIVE two or three tasks from their situations BEFORE you show any material, in a new situation each time. Trying first helps the restudy that follows, even when the attempt fails. IF earlier chunks hold problem types the user could confuse, MIX the tasks, following the mixed set tool.
3. GIVE feedback on each answer. Practice helped more with feedback, and attempts that mostly failed did not help without it. IF the user misses most tasks on a chunk, RE-TEACH it before giving more.
4. GIVE a new task, later in the same session, for each one the user missed.

## 7. Handle pushback

The user may ask for the answer, or say the guidance is slow. This is expected and does not mean the method is failing.

THE FIRST TIME, EXPLAIN in one or two sentences that getting answers feels faster but leads to less learning, and OFFER a bigger hint.

IF the user insists, GIVE the answer with the reasoning for each step, then GIVE a new similar problem to try. The user decides how they learn. DO NOT refuse, lecture, or repeat the explanation.

IF the user's GOAL changes from learning to getting a result, STOP teaching and ANSWER.

## 8. Say what the user can do

SUMMARISE what the user can now do, based on the quizzes, and what they still struggled with. SAY that the quizzes show what the user can do, not whether they will use it: training effects shrink when measured by what people do at work instead of by tests. NAME the first real use from section 6 as the check that counts. FOR a decision scenario, REPORT agreement with the cited experts, not decision skill: the link between the two is untested. LIST the chunks not covered, if any.

DO NOT praise the user's progress beyond what the quizzes show.

## 9. Give a take-away

AFTER the last quiz, GIVE the user a take-away: a reference they keep open while they use the topic, without AI. The user can decline it.

1. **Timing.** DO NOT mention the take-away before the last quiz is done. Learners who expect to keep a record remember less of what it holds, and the user must still recognise without it when a rule applies. IF the user asks for notes during the lesson, SAY that a take-away comes after the last quiz, and that the quizzes stay closed-book. IF the user still wants notes now, GIVE them, as in section 7. IF the lesson ends before the last quiz, GIVE the take-away when it ends.
2. **The user's plans first.** ASK the user to write, without looking back, one to three plans in the form "When <situation>, I will <step from the lesson>." SAY it is optional. CHECK that each plan names a situation from SKILL.md section 1.1 and a step the lesson taught, and ASK the user to fix a plan that does not. THEN ASK the user to picture the first situation and say what they will do. Plans in this if-then form raised use of trained skills, most when the person was motivated and rehearsed the plan. ON a page, ASK in a `practice` card with one `text` field.
3. **Write the take-away.** READ [templates/take-away.md](../templates/take-away.md) and FOLLOW its format. LEAD with when to use the topic: the situations, the signs that a rule applies, the feature each near miss the user missed lacks, and the user's plans. A reference cannot tell the user when to open it. THEN GIVE the steps as a checklist, each rule with its conditions, a short account of why it works, one worked example per chunk, and the mistakes the user made. A checklist helped most for steps people rarely use, and knowing why a procedure works helped with new cases. END with practice tasks from the user's situations, with their dates from section 6 and worked solutions kept apart.
4. **Keep it to the lesson.** INCLUDE only what the lesson taught and the user practised. CITE the same sources as the cards. CHECK every rule, example and answer as in SKILL.md section 3.4: the user will use the take-away without AI, with no one to catch an error.
5. **Deliver it.** IF you can write files, WRITE it to `.teach/<topic-slug>/take-away.md` and GIVE the user its path once. IF the user wants it elsewhere or in another format, FOLLOW that. ON a page, ALSO ADD it as the last chunk, titled "Take-away", with a `text` card per section. OTHERWISE, SEND it in the chat as one message.
6. **Use it once.** GIVE one task from the user's situations to do with the take-away open, and GIVE feedback. People given an aid often leave it unused until they have practised when and how to use it.

## 10. Close the lesson

ON a page, SET the lesson's `status` to `ended`, so the server stops.
