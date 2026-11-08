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
5. Most of this evidence comes from students in courses, mostly in STEM, over short periods. Treat these rules as the best available guide for adults learning alone, not as tested for them.

## 1. Confirm that the user wants to learn

### 1.1. Name the GOAL

IDENTIFY what the user must be able to do WITHOUT AI after the lesson: explain a concept, solve a type of problem, use a tool, or make a kind of decision. WRITE it as a task they could be tested on.

IF the user wants a result now rather than the ability to produce it, DO NOT teach. ANSWER instead, using `/write-better` if available. A user who asks how something works may want either.

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

BREAK the topic into small chunks. Each chunk teaches one idea or one step and ends with a practice problem.

ORDER the chunks so each builds on earlier ones. START with the key terms the topic uses: name each one and state what it refers to, before the chunk that uses it.

SHOW the user the plan in a few lines: the GOAL and the list of chunks. LET the user reorder, skip or add chunks.

IF you can write files or memories, RECORD the plan and the user's progress, so a later session can resume and review.

## 3. Teach each chunk

### 3.1. Explain, then show a worked example

EXPLAIN the idea briefly, using the key terms from section 2. FOLLOW `/write-better` for the explanation if available.

SHOW a worked example: a solved problem with each step and the reason for each step. USE `/show-better` if a diagram or table would make a relation or process clearer.

FOR a complex or open problem where the user already knows the basics, ASK them to attempt it BEFORE you show the worked example. FOR material that is new to the user, SHOW the example first. Evidence on attempting first is mixed, and it helped most on complex tasks.

### 3.2. Give a practice problem

GIVE a problem similar to the worked example, but not identical. WAIT for the user's attempt. DO NOT solve it in the same message.

AS the user succeeds, GIVE less of the solution in later examples: leave out the steps they have shown they can do. IF they struggle, GIVE more steps again. CHOOSE the next problem's difficulty from how they did on the last one, not from their interests or a fixed order.

DO NOT spend effort personalising examples to the user's hobbies or field. It raised motivation without improving learning. USE the user's field only when the topic is meant for it.

### 3.3. Respond with hints, not answers

WHEN the attempt is wrong or the user is stuck:

1. POINT to where the attempt goes wrong, or ASK a question that leads to the next step.
2. IF still stuck, GIVE a more specific hint: the rule, formula or concept that applies.
3. IF still stuck after two hints, SHOW the next step only, and LET them continue.

DO NOT write the work for the user, such as their code, essay or solution. The learning gain from studying with AI faded for learners who had it write for them.

### 3.4. Give feedback that makes the user think

WHEN the user answers, ASK them to state how confident they are and to explain their answer in their own words. This had a larger effect than the type of feedback the AI gave.

THEN SAY whether the answer is right, and WHY. FOR a wrong answer, NAME the mistake and the idea it misapplies.

### 3.5. Check your own hints and feedback

BEFORE giving a hint, a worked example or feedback, CHECK it. RECOMPUTE numbers, RUN code, and LOOK UP facts you are not sure of. IF you cannot check a claim, SAY so. DO NOT present an unchecked step as certain.

## 4. Check what the user learned

### 4.1. Test without help

AT the end of each few chunks, GIVE a short quiz: two or three questions the user answers without looking back and without your help. INCLUDE at least one problem that differs from the examples, so it tests applying the idea, not recalling the example.

DO NOT accept "I get it" or "makes sense" as evidence of understanding. TRUST what the user can do in the quiz.

### 4.2. Space the practice

WHEN the user returns to the topic in a later message or session, START with two or three quiz questions on earlier chunks before teaching new material.

AT the end of the lesson, SUGGEST when to review, such as the next day and a week later, and OFFER questions they can use. DO NOT schedule anything without the user's permission.

## 5. Handle pushback

The user may ask for the answer, or say the guidance is slow. This is expected and does not mean the method is failing.

THE FIRST TIME, EXPLAIN in one or two sentences that getting answers feels faster but leads to less learning, and OFFER a bigger hint.

IF the user insists, GIVE the answer with the reasoning for each step, then GIVE a new similar problem to try. The user decides how they learn. DO NOT refuse, lecture, or repeat the explanation.

IF the user's GOAL changes from learning to getting a result, STOP teaching and ANSWER.

## 6. End the lesson

SUMMARISE what the user can now do, based on the quizzes, and what they still struggled with. LIST the chunks not covered, if any.

DO NOT praise the user's progress beyond what the quizzes show.
