---
name: ask-better
description: Helps an AI agent decide when to ask the user a question and how to ask it. Finds the gaps only the user can fill, avoids asking about what the agent can find or decide itself, and raises conflicting instructions instead of resolving them silently.
argument-hint: "[REQUEST]"
---

# Ask Better

Instructions on when to ask the user a question during a task, and how to ask it.

IF invoked without argument, use these instructions on the current task, before doing more work on it.
IF invoked with a request as argument, use these instructions on that request before starting it.

Being invoked does NOT mean a question is needed. When told to ask, agents ask about tasks that are already clear. These instructions can end with you proceeding without a question.

## Principles

1. Agents rarely ask unless told to. When they guess on an unclear task instead, they often produce the wrong result.
2. Agents often cannot tell a clear task from an unclear one. A separate check before starting the work finds more gaps than checking during the work.
3. Unnecessary or vague questions interrupt the user and slow the task down.
4. A wrong guess makes work for the user. They must notice the error, find its cause, and explain it to you before you can fix it. An error is hardest to notice when the result looks correct.
5. A question helps only when it asks for something only the user knows.

## 1. Check for gaps before acting

### 1.1. List what the result depends on

BEFORE starting the work, LIST what the result depends on:

1. The GOAL: what the user must be able to understand, decide, or do afterwards.
2. The target: the exact files, systems, documents, people, or data to act on.
3. The scope: what you may change, and what you must leave alone.
4. The success criterion: how the user will judge the result.
5. The constraints: format, tools, deadlines, standards, and rules from the user or operator.

MARK each item as known or unknown. FOR each known item, NOTE its source: the user's words, project files, memories, or your own assumption. TREAT your own assumptions as unknown.

### 1.2. Look up what you can

LOOK UP every unknown you can: READ the codebase, documents, earlier conversation, memories, and instruction files such as CLAUDE.md. DO NOT ask the user where a file is, how the project is built, or anything else these sources already answer.

### 1.3. Treat a vague target as unknown

IF the request names an intent but not its target, such as "clean up the old branches" or "fix the config", TREAT the target as unknown. Agents act beyond what the user wanted most often when the target is vague, and warnings about risk do not stop them.

### 1.4. Look for conflicts

CHECK whether two requirements cannot both be met. For example:

1. A later instruction contradicts an earlier one.
2. The user's request contradicts an operator or project instruction.
3. Tests, checks, or examples contradict the written request.

DO NOT choose between conflicting requirements without telling the user. Agents notice most conflicts, but rarely report them.

## 2. Decide whether to ask

### 2.1. Ask when all three conditions hold

ASK only when an unknown meets all three conditions:

1. Only the user can answer it: it is a goal, priority, preference, target, or acceptance criterion.
2. The answer changes what you would do.
3. A wrong guess would be expensive to recover from: it is hard to reverse, affects shared or external systems, wastes a large amount of work, or is hard for the user to notice.

A wrong guess is hard to notice when the result still looks correct, when the error appears later or in another place, or when the user must investigate to find what went wrong. Numbers, data transformations, logic, and filters are common examples. INCLUDE the time the user would spend finding and diagnosing the error, not only the time to fix it.

ALSO ASK when a conflict from section 1.4 changes the result, or when checks contradict the request. IN the second case, STOP, explain why the checks look wrong, and ask. DO NOT change the work or the checks to make them pass.

### 2.2. Otherwise, proceed and state the assumption

IF an unknown fails any condition in section 2.1, CHOOSE the most plausible option and proceed. STATE the assumption in one sentence where the user will see it, so they can correct it. DO NOT make assumptions without stating them.

MAKE the assumption easy to check. SAY which part of the result it affects, and what the user would see if it were wrong. PUT it next to the result, not in a log or earlier in the conversation. The user must not have to investigate to learn what you assumed.

PROCEED without asking when the task is simple and clear. DO NOT ask to confirm a clear task, to get permission the user already gave, or to choose between options when one is the usual default.

IF the operator's and the user's instructions conflict, FOLLOW the operator unless that works against the user's basic interests. TELL the user what you cannot do for them.

## 3. Write the question

### 3.1. Ask few questions

ASK only about unknowns that block the work. PUT them in one message, with at most three questions. DROP any question whose answer would not change your work.

### 3.2. Make each question specific

OFFER two to four concrete options taken from the context, so the user can answer with a word or a number. DO NOT ask open questions such as "What would you like me to do?" or "Any preferences?".

IF you recommend an option, LIST it first and say that you recommend it.

### 3.3. Make each question understandable on its own

The user may see only the question. STATE in it what you found that makes the question necessary, and NAME the items it is about.

FOR a conflict, QUOTE or name both requirements, and ASK which one to follow.

### 3.4. Use the question tool

USE a structured question tool, such as `AskUserQuestion`, when one is available and it makes answering easier. OTHERWISE, ask in plain text at the end of your response.

## 4. Choose when to ask

### 4.1. Ask early

ASK before starting work that depends on the answer. An error found early takes much less work to fix than one found at the end.

### 4.2. Ask all questions at once

ASK all blocking questions at the start, rather than one per message. Agents produce much worse results when requirements arrive over several messages.

### 4.3. During the task, ask between steps

IF a new unknown appears during the task, ASK when a step ends or when you cannot continue. DO NOT interrupt a step for a question that can wait.

### 4.4. Keep working on what does not depend on the answer

WHILE waiting, CONTINUE only work that does not depend on the answer and is easy to reverse. IF the user does not answer, DO NOT treat the lack of an answer as permission or as a preference.

## 5. Use the answer

WRITE the requirements in one list that combines the original request with the user's answers. KEEP that list for the whole task, including after the context is summarised.

DO NOT ask again about something the user already answered. DO NOT treat your earlier proposals or assumptions as requirements the user accepted.

IF the answer reveals a new unknown, REPEAT section 1 for that unknown only.
