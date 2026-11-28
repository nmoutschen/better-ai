---
name: explore
description: Use when the user wants to learn a field and see where the reading leads, rather than answer one question.
---

# Explore mode

In explore mode the research follows the topics that the sources raise, beyond the TOPIC the user gave. The result is the trail of what the sources led to, not one answer. Every step of SKILL.md applies, with the same evidence rules, except where this file replaces a rule. Each rule below names the step it replaces.

A topic enters the board only because a source raises it. An agent that adds topics it expects to matter maps its training data, not the field.

## 1. Set the goal and the stop level (step 1)

SET the GOAL to what the user wants to learn about the field. SET the stop level to `medium` unless the user asks for a quick look (`high`) or an exhaustive map (`low`).

## 2. Record the mode on the board (step 2)

SET `mode` to `explore` in the brief, so that workers and a later session follow this file's rules.

## 3. Bound the run (steps 5.5 and 6.2)

A topic's DEPTH is the number of `raised_in` steps from it to a seed question. A seed question has depth 0, a question raised after it depth 1.

KEEP questions to a depth of 3, unless the user stated another limit. SET a proposed question deeper than that out of scope, with `beyond depth` in its `note`, so the user can reopen it from the live view.

APPLY the stop rules of step 5.5 to the questions within the depth. DO NOT stop because the user's first question is answered.

## 4. Add the topics the sources raise (steps 5.3 and 6.2)

WHEN a source you read raises a topic outside the TOPIC, such as a method, a debate, a related problem or a field it relies on, ADD a question about it, kind `frontier`, with `topic` in `lens`, the source in `origin` and the question you were working on in `raised_in`. This replaces "within the TOPIC and MEANING" in step 5.3. The three checks still run.

ADD such a question only when a source you read names the topic. DO NOT add a topic from your own expectations, from what a field usually covers, or from the search results' text. IF you expect a topic that no source raised, it stays off the board.

SET each question's priority from how strongly the sources point to its topic, not from its stakes for the GOAL:

- `high`: two or more independent sources raise it, or one source treats it as central, such as in its title, its aims or a section of its own.
- `medium`: one source discusses it at some length.
- `low`: a source mentions it in passing.

WRITE in `stakes` what the topic adds to the user's understanding of the field. WHEN you review the board (step 6.2), RAISE a question's priority as more independent sources raise its topic.

## 5. Set scope by depth, not by topic (steps 5.4 and 6.2)

DO NOT set a question out of scope because it is outside the TOPIC or does not serve the user's first question. SET a question out of scope only when it is deeper than the bound, when it is a `topic` question that no source you read raises, when later findings made it irrelevant, or when the user dropped its branch. WHEN the user asks to drop a branch, SET the open and proposed questions on it out of scope, with the user's reason in `note`. WHEN the user asks to keep a topic, SET its question's priority to `high`. WHEN the user asks to end the run, SET the brief's `status` to `checking` (step 6.2).

## 6. Present the map (step 7)

PRESENT the findings as a map of the branches, starting from the seed questions. FOR each branch, GIVE the path from its seed question to each topic on it, by the questions' titles, the source that raised each topic, and a summary of what the branch found, with its citations. THEN LIST the topics set out of scope as beyond depth, as leads for a later run. The rules of step 7 for claims, citations, the reference list and open questions apply.
