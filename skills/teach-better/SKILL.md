---
name: teach-better
description: Helps an AI agent teach a topic so people understand it and use it in their own life and work. In tutor mode it works through the topic with the user, with hints instead of answers, and checks understanding by applying it to their situations. In static mode it writes a self-contained reference, a page or a plan of pages, with worked examples, examples to try and every claim read from its source. Handles pushback when the user wants the answer.
argument-hint: "[TOPIC]"
---

# Teach Better

IF invoked with a topic as argument, TEACH that topic.
IF invoked without argument, TEACH the topic the user is currently asking about or working on.

Being invoked does NOT mean you must teach. IF the user wants a result now rather than the ability to produce it, these instructions end with the answer (section 1.2).

This file holds what both modes share. Each mode has its own file in `modes/`, which you READ once you have chosen the mode (section 1.2).

## Principles

1. Answers from an AI raise a learner's scores while it helps and lower them once it is gone. Hints instead of answers avoid that loss, though learners rate hints as slower and less useful.
2. Learners who study with AI overestimate what they know. Judge learning by what they can do, not by what they say.
3. AI hints and feedback contain errors, and a learner cannot catch an error they share. AI-assembled content fabricates citations, cites sources that do not support the claim, and passes on retracted or wrong findings without saying so.
4. Help that suits a beginner can hinder a learner who knows more. Adapt to what the learner can do: matching a stated learning style has little support.
5. Asking learners to explain their answers helped in every medium tested, print included, and about as much when nobody checked the explanation. Open prompts worked; multiple-choice prompts did not.
6. Feedback that explains why an answer is right or wrong helped more than giving the right answer, most on tasks that apply what was learned.
7. Whether people use a skill depends less on their test scores than on their confidence and their chances to use it. Practice on real tasks went with more use. The measures that are easy to collect, such as how learners rate a lesson and what they recall right after it, say little about later use.
8. Learners can state a rule and still not see when it applies. Pre-questions helped only the material they asked about. Cases where a rule does not apply helped learners find what the rule needs.
9. A reference at hand helps people perform.
10. Knowing why a method works and knowing how to do it build on each other, and knowing why predicted use on new problems more than on practised ones.
11. Design choices, to TREAT as a guide and not as fixed rules: the lesson page, the tools in section 2.3, the reference's structure, the prerequisite check, attempting before a worked example, taking the first problem from the user's own situations (untested for later use), explaining why in feedback, the timing of terms, and the hints and solutions behind a click.

The LEARNER is the user in tutor mode and the page's readers in static mode.

## 1. Choose the mode

### 1.1. Name the GOAL

IDENTIFY what the LEARNER will do with the topic in their own life or work, WITHOUT AI: explain it, solve a type of problem, use a tool, or make a kind of decision. INCLUDE what they must understand to do it well in situations the lesson does not show. WRITE the GOAL as that use, not as a test they could pass.

FIND OUT where and when the LEARNER will use it: the situations and tasks they will meet. LOOK in the context first, and ASK only for what it does not show.

### 1.2. Choose the mode

CHOOSE from what the user wants:

- **A result now**, rather than the ability to produce it: DO NOT teach. ANSWER instead, using `/write-better` if available, or otherwise leading with the answer in plain words. A user who asks how something works may want either.
- **To understand it and use it themselves, with guidance**: tutor mode. READ [modes/tutor.md](modes/tutor.md).
- **A reference to come back to**, for themselves or for other people, such as a page or a plan of pages to publish or share: static mode. READ [modes/static.md](modes/static.md).

IF you cannot tell, ASK once, using the question tool if available:

```
[question] What do you want from this?
[option] Give me the answer.
[option] Work through it with me, so I can use it myself.
[option] Write a reference I or others can come back to.
```

READ the mode file BEFORE you continue. It adds steps to the sections below and says where each one goes.

## 2. Plan the lesson

### 2.1. Research the topic

DO NOT teach from your training data alone: a definition you are sure of can still be wrong or incomplete. RESEARCH the topic BEFORE you ask the user anything about it. A question written before any search comes from your training data, and it frames the lesson around what you expected:

- IF `/research-better` is available and the topic is not trivial, USE it, and BUILD the lesson from its findings.
- FOR a trivial topic, or without `/research-better`, SEARCH the web and READ the pages that define the topic's key terms.
- AFTER the research, CONTINUE with the lesson. The research is a step of the lesson, not its end.
- IF you have no web search and no page fetch, TELL the user that the lesson rests on your own knowledge, and ASK whether they have sources you should use.

CITE the source on each card that states a definition or a fact, with a link. READ every source you cite, not only a search result or a summary of it, and CHECK that it says what the card claims. IF a source was retracted or is disputed, SAY so on the card.

### 2.2. Break the topic into chunks

BREAK the topic into small chunks. Each chunk teaches one idea or one step and ends with something to try.

ORDER the chunks so each builds on earlier ones. NAME each chunk by what the LEARNER will do, such as "Pick the join for a report", not by the term it teaches.

INTRODUCE a key term in the chunk that first needs it, not in an opening list. STATE the idea in plain words first, THEN GIVE the term. TEACH a term for its own sake only IF the LEARNER must use it with other people, such as colleagues or documentation. IF the topic is a system with many named parts, a short card on the parts and what each does BEFORE the explanation is the exception: naming the parts first helped transfer.

SHOW the user the plan: the GOAL and the list of chunks. LET the user reorder, skip or add chunks.

### 2.3. Choose the tools

A tool is a teaching move with its own template in `templates/tools/`. READ a tool's template before you first use it in a lesson. Each template says when to use the tool, when not to, and the card format for the page and the chat.

| Tool | Template | Moment | Use when |
|---|---|---|---|
| Pre-questions | [pre-questions.md](templates/tools/pre-questions.md) | Before teaching a chunk | The chunk teaches facts the LEARNER must know without looking them up |
| Why prompt | [why-prompt.md](templates/tools/why-prompt.md) | After an explanation card that states a key fact or rule | The GOAL needs the LEARNER to explain facts or rules |
| Does it apply? | [does-it-apply.md](templates/tools/does-it-apply.md) | After the first practice problem of a chunk | The LEARNER must recognise in their own work when to use a rule or method |
| Compare examples | [compare-examples.md](templates/tools/compare-examples.md) | After one method or case has been practised | A second method or case for the same idea exists |
| Question stems | [question-stems.md](templates/tools/question-stems.md) | Around a long reading | A chunk asks the LEARNER to read a long text |
| Decision checks | [decision-checks.md](templates/tools/decision-checks.md) | A practice card where the LEARNER chooses a course of action | The GOAL is to make a kind of decision |
| Decision scenario | [decision-scenario.md](templates/tools/decision-scenario.md) | Practice | The GOAL is to make a kind of decision, AND you have a cited source of expert judgement |
| Mixed set | [mixed-set.md](templates/tools/mixed-set.md) | Practice after several chunks | Two or more problem types the LEARNER could confuse, each practised alone first |

AT each moment, CHOOSE in this order:

1. MATCH the GOAL and the moment against the table. IF no tool matches, USE the cards of section 3 alone.
2. CHECK the "Do not use" list in the tool's template. IF any item applies, DO NOT use the tool.
3. USE at most one tool per card.
4. IF the user states a preference about a tool, FOLLOW it, except where the tool's template says otherwise.
5. WHEN a tool changes what the LEARNER sees, SAY so in one line, such as "These problems mix chunks 1 to 3 on purpose."

## 3. Write the cards

### 3.1. Explain, then show a worked example

EXPLAIN the idea briefly, in plain words first, then with its term (section 2.2). FOLLOW `/write-better` for the explanation if available. OTHERWISE, USE plain words and one term per idea.

SAY why the method works, not only how to apply it: the LEARNER will meet cases the lesson does not show.

SHOW a worked example: a solved problem with each step and the reason for each step. TAKE the problem from a situation where the LEARNER will use the topic (section 1.1), stripped to the features the rule needs. Training on concrete cases helped transfer to concrete cases, and context the rule does not need, such as a named person, lowered transfer. WHEN a card shows a formula, rule or symbol next to an example, STATE which part of the example each symbol stands for, such as in a table with one row per symbol. IF a diagram or table would make a relation or process clearer, ADD it next to the explanation. ON a page, USE a `table`, `steps` or `timeline` block. IN the chat, USE a Markdown table or a list. DO NOT draw a plain-text diagram by hand: models draw them badly. WRITE a formula in a `code` block, with one operation per line, not inside a sentence, a table cell or a step note.

WHEN a chunk asks the LEARNER to read a long text, GIVE a short instruction before the reading, saying what to look for, and one after it, saying what to check. CONSIDER the question stems tool (section 2.3).

FOR a complex or open problem where the LEARNER already knows the basics, ASK them to attempt it BEFORE you show the worked example. FOR material that is new to the LEARNER, SHOW the example first. Attempting first helped most on complex tasks.

### 3.2. Write practice problems

GIVE a problem similar to the worked example, but not identical. BUILD practice problems from the situations where the LEARNER will use the topic (section 1.1), from the first problem on. VARY the situation between problems, so the LEARNER does not tie the rule to one case. DO NOT personalise problems to hobbies or to fields where the LEARNER will not use the topic: that raised motivation without improving learning.

ASK for the answer and the reasoning together, in one reply. ASK for the reasoning in an open box, not by picking from options. ON a page, IF a question asks several things, GIVE one answer box per thing.

IF the GOAL is to make a kind of decision, USE the decision tools in section 2.3 for practice: a decision has no single right answer to check.

### 3.3. Check what you write

BEFORE giving a hint, a worked example, a solution or feedback, CHECK it. RECOMPUTE numbers, RUN code, and LOOK UP facts you are not sure of. IF you cannot check a claim, SAY so. DO NOT present an unchecked step as certain.

ON a page, RUN `python3 scripts/lesson.py check <folder>` from this skill's directory after each change to `lesson.json`, FIX every error, and CHECK every value it prints, such as each table cell and timeline event, against your worked solution.

CHECK that every term in a practice question was introduced on an earlier card. IF it was not, DEFINE it in the question or REWORD the question. CHECK that an example in a question does not give away its answer.
