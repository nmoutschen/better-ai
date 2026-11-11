# Static mode

Write a self-contained reference that people come back to when they need the topic: a page, or a plan of pages. It has no quizzes, no answer boxes and no schedule. The user may be its reader or its author. This file adds to SKILL.md: each section says where it goes.

## 1. Name the readers

WITH the GOAL (SKILL.md section 1.1), FIND OUT from the user who the readers are, what they already know, and where they will use the topic. The GOAL and the situations are the readers'. WRITE the readers and what they need to know first in the top-level `audience`.

PICK one level of prior knowledge to write for. Worked examples help readers new to a topic and can hinder readers who know more, and no tested way exists for readers to pick their own level. IF the readers span levels, ASK the user to pick one, or to plan one reference per level.

## 2. Choose a page or a plan

WITH the chunks (SKILL.md section 2.2), CHOOSE the size:

- A **page** IF the topic fits in one module of the structure below.
- A **plan** OTHERWISE: one module per page, ordered from simple to complex whole tasks. PREFER a plan when the topic is broad, so that each page stays focused.

MAKE each page of a plan stand on its own. A reader comes to it from a search or a link, not only from the page before. NAME the pages it builds on in its Summary, and LINK them. Readers who followed a fixed course order completed less often than readers who chose their own path.

SHOW the user the list of pages before writing.

## 3. Follow the structure

EVERY page follows the same structure, in this order, so readers know where to look. READ [templates/reference.md](../templates/reference.md) for the cards.

1. **Summary.** What the topic lets the reader do, who it is for, and what they need to know first.
2. **When to use this.** The situations, the signs that it applies, and the near misses where it does not. A reference cannot tell the reader when to open it.
3. **Core ideas.** One block per idea, always in the same order: the idea in plain words, then its term (SKILL.md section 2.2); why it works (SKILL.md section 3.1); a worked example; then an example to try.
4. **Cases.** Real, cited cases where the topic mattered.
5. **Common mistakes.** Each with the idea it misapplies.
6. **Limits and disagreements.** Where the evidence is thin, where sources disagree, and what the page does not cover.
7. **Quick reference.** The steps as a checklist, or a table, for the reader who already knows the topic. A checklist helped most for steps people rarely use.
8. **Sources.** Every source the page cites.

LEAVE OUT a part only when it has nothing to hold, such as Cases when no documented case exists. DO NOT invent a case to fill it.

## 4. Write the examples to try

AFTER each worked example, ADD an example to try: a problem like the worked example in a different situation, with its solution behind a click (SKILL.md section 3.2). Most readers try a problem before opening a solution that is one click away.

- **Solution.** WRITE every step with its reason, and QUOTE the rule each step uses. An explanation helped more than the right answer alone.
- **Hints**, optional. Up to three, from least to most help: one that points to where attempts go wrong, one that quotes the rule, and one that shows the next step only. DO NOT write a hint that gives the answer: using help more than needed went with less learning.
- **Common wrong answers.** The wrong answers readers are likely to give, each with the idea it misapplies.

DO NOT put the solution anywhere else on the card: an explanation in view lowers the reader's incentive to work it out.

FOR a tool (SKILL.md section 2.3), WRITE its question as an example to try, with its answer as the solution, and IGNORE the template's steps that wait for or reply to the learner. A why prompt's solution is the explanation; a "does it apply?" example's solution gives the verdict per situation and the feature that decides it.

## 5. Ground every claim

FOLLOW SKILL.md section 2.1 for every card. A page lives on without a tutor to correct it, so:

- CITE a source for every fact, number, definition and case, and READ it in full. A search result or a fetch tool's summary is a lead, not a source.
- CHECK that the cited passage says what the card claims, with the same numbers and conditions.
- PUT what the sources do not settle in "Limits and disagreements", not in the Core ideas as fact.
- MARK an example as invented when it is.

## 6. Check and build

CHECK every card, hint, solution and wrong answer as in SKILL.md section 3.3.

WRITE the reference to `.teach/<topic-slug>/lesson.json`, in the format in [templates/lesson.md](../templates/lesson.md): one chunk per page, one card per part of the structure. DO NOT commit it unless the user asks. RUN `python3 scripts/lesson.py check <folder>` and then `python3 scripts/lesson.py build <folder>` from the skill's directory. It writes `site/index.html`, one file that needs no server. IF you cannot run Python, WRITE `lesson.json` and GIVE the user the build command.

GIVE the user the page's path once, and ASK them to review it. DO NOT publish or upload it unless the user asks. REPORT which checks you ran, and which claims you could not check.
