# Static mode

Write a lesson page that readers study alone, with no tutor to answer them. The user is the author, not the learner. This file adds to SKILL.md: each section says where it goes.

No tutor reads the reader's answers, so the page carries what a tutor would say: hints, a worked solution, and the common wrong answers, each behind a click. Most readers try a question before opening its solution when the solution is one click away.

## 1. Name the audience

WITH the GOAL (SKILL.md section 1.1), FIND OUT from the user who the readers are, what they already know, and where they will use the topic. The GOAL and the situations are the readers', not the user's.

PICK one level of prior knowledge to write for. Worked examples help readers who are new to a topic and can hinder readers who know more, and no tested way exists for readers to pick their own level. IF the readers span levels, ASK the user to pick one, or to plan one lesson per level.

WRITE the audience and the prerequisites in `audience`, such as "Analysts who can write a SELECT query". DO NOT run the prerequisite check on the user.

## 2. Write the lesson

AFTER the user agrees to the plan (SKILL.md section 2.2):

- WRITE the lesson to `.teach/<topic-slug>/lesson.json` in the working directory, in the format in [templates/lesson.md](../templates/lesson.md), with its static fields. DO NOT commit it unless the user asks.
- WRITE every chunk's cards at once: there is no learner to adapt to.
- FADE the worked examples by plan: in later chunks, LEAVE OUT the steps that earlier chunks practised.
- FOR a tool, USE the "On a page" format in its template, and ADD the static fields of section 3. IGNORE the template's steps that wait for or reply to the learner.

## 3. Write what a tutor would say

ON each practice card (SKILL.md section 3.2):

1. **The answer box.** ASK for the answer and why in an open `text` field. A `choice` or `rank` field always comes with a `text` field for the reasoning: prompts that ask readers to explain work in print and when nobody checks, but multiple-choice prompts did not.
2. **`hints`.** WRITE up to three, from least to most help: one that points to where attempts go wrong or asks a question that leads to the next step, one that quotes the rule and LINKS the card that teaches it, and one that shows the next step only. DO NOT write a hint that gives the answer. Using help more than needed went with less learning. A reader who has not tried yet gets less from help, so the page asks them to answer before they open anything.
3. **`solution`.** WRITE every step with its reason, and QUOTE the rule each step uses. An explanation helped more than the right answer alone. DO NOT put the explanation anywhere else on the card: an explanation in view lowers the reader's incentive to explain it themselves.
4. **`wrong`.** LIST the wrong answers readers are likely to give: the ones the sources name, the near misses the chunk teaches, and the steps a worked example warns about. FOR each, NAME the idea it misapplies.

FOR a pre-question, WRITE a solution that says the next cards give the answers. FOR a why prompt, the solution is the explanation.

## 4. Quizzes, review and reference

WRITE the quizzes planned in SKILL.md section 3.3 as quiz chunks. The page asks the reader to answer every question in a quiz before opening its solutions.

Readers use self-tests less than they should, and nothing found shows that readers follow a review schedule on their own. AFTER the last quiz, WRITE the Review and Reference chunks (SKILL.md section 3.5):

- ASK the user how soon and how often readers will use the topic, and SUGGEST review dates by the gaps in [modes/tutor.md](tutor.md) section 6.
- PUT the `wrong` entries under "Mistakes to watch".
- IN the plans card's solution, SAY what a good plan names.

## 5. Check and build

CHECK every card, hint, solution and wrong answer as in SKILL.md section 3.4. No tutor will catch an error the page holds.

BUILD the page (SKILL.md section 3.5). IF you cannot run Python, WRITE `lesson.json` and GIVE the user the build command.

GIVE the user the page's path once, and ASK them to review it. DO NOT publish or upload the page unless the user asks. REPORT which checks you ran, and which claims or values you could not check.
