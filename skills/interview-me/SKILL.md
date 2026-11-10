---
name: interview-me
description: Interviews the user about how they read and how they review work, then writes two personal skills from what it learns, write-for-<name> and review-for-<name>, so agents write text the user understands and acts on and check work the way the user would. Works from the user's real documents and reviews and from comparisons of concrete samples, not from general questions about their preferences.
argument-hint: "[write | review | PATH-TO-EXISTING-GUIDE]"
---

# Interview Me

IF invoked without argument, USE these instructions to interview the user for both guides: `write-for-<name>` (section 3) and `review-for-<name>` (section 4).
IF invoked with `write` or `review`, RUN only that part.
IF invoked with the path of an existing guide, UPDATE that guide (section 6).

The GOAL is that the user DOES less explaining later: agents that load the guides write text this user understands and acts on, and check work against the criteria this user applies. The guides are only a means to that.

Being invoked does NOT mean a long interview or new rules are needed. IF the existing guides already cover what the user wants, these instructions can end with no change.

## Principles

1. What people say helps them can differ from what does help them. Learners preferred, and felt they learned more from, the format that taught them less.
2. The criteria people state for judging work only partly match the criteria their actual judgments reveal, and experts leave out much of what they do when they describe it.
3. Comparing concrete work samples and justifying the choice made tacit quality criteria partly explicit. Walking through one real incident, and asking about the options the person rejected, revealed the reasons behind their actions.
4. Recall of past behaviour is imperfect, even for recent days. A document the user wrote or reacted to is stronger evidence than their memory of it.
5. A hypothetical question shows what a person knows a situation requires. It is weaker evidence of what they will do or prefer.
6. AI interviewers produce answers of about the same quality as human interviewers. Their main failure is not following up on surprising or unclear answers. Agree/disagree questions give lower-quality answers than questions about the item itself, and answers get worse late in a long questionnaire.
7. A user profile stored in an LLM's memory made it more agreeable and made it personalize where it should not. Examples of output the user approved carried most of the benefit of a profile.
8. Users accepting a summary of their interview shows that they accept it, not that it is accurate.
9. No study tests an AI interviewing a user about their own reading or reviewing. These rules come from classrooms, hiring interviews, surveys and LLM preference studies. TREAT them as the best available guide.

## 1. Prepare

### 1.1. Look up what is already known

READ the conversation, memories, project instructions, and any existing writing guide or `write-for-*` or `review-for-*` skill first. LIST what they already say about how the user reads and reviews.

DO NOT ask about anything they already answer. IF an existing guide covers the part being run, SWITCH to updating it (section 6).

### 1.2. Collect real material

ASK the user for real material, in one message:

1. FOR `write`: a document they found easy to understand and act on, and one they found hard. Documents written for them by anyone count, including earlier AI output.
2. FOR `review`: a piece of work they reviewed, with the comments they gave, such as a pull request, a marked-up draft, or a feedback message.

READ each item before the interview. IF you cannot open it, ASK the user to paste it. NOTE what each item shows, such as the length of its opening, how it uses headings, or which comments ask for a change before approval. These notes are not rules yet.

IF the user has no material at hand, CONTINUE with the comparisons in sections 3.2 and 4.2, built from a topic in their current work. SAY that the guide will rest on fewer kinds of evidence.

## 2. How to ask

APPLY these rules to every question in sections 3 and 4.

### 2.1. Ask about one thing, in its own terms

ASK about the item itself, such as "How long should the first paragraph be?", not "Do you agree that short openings are better?". People tend to agree with a statement they are offered.

ASK about one thing per question. GIVE each answer you need its own question. IF you use a structured question tool, such as `AskUserQuestion`, OFFER concrete options and LET the user write their own. OTHERWISE, ASK in plain text.

DO NOT suggest the answer you expect, and DO NOT praise or judge the user's answers.

### 2.2. Follow up before moving on

FOLLOW UP, with one question, WHEN an answer:

1. Uses a vague quality word, such as "clear", "concise", "too long", "professional" or "readable". ASK what it looked like in a specific document.
2. Surprises you, or contradicts what their material showed. ASK about the difference. DO NOT resolve it yourself.
3. States a rule with no example. ASK for the last time it mattered.
4. Says "it depends". ASK what it depends on.

### 2.3. Respect the user's time and limits

PUT the questions whose answers change the guide most first. AFTER each part, OFFER to stop and write the guides from what you have. Answers get worse as an interview gets long.

DO NOT ask the user to disclose a condition, a diagnosis, or anything about who they are. DO NOT infer their ability or background from how they write. ASK only about documents, reviews and the choices they make about them.

## 3. Part A: how the user reads (`write-for`)

### 3.1. Walk through a real document

FOR each document from section 1.2, ASK the user to describe what happened when they read it: what they did first, where they slowed down, and what they did afterwards. LET them answer without interrupting, except for a short clarification.

THEN PROBE the points where they made a choice:

1. What they skipped, reread, or looked up, and why.
2. What they would have changed about the document, and what they would have kept.
3. Whether they could act on it without asking anyone, and what was missing if not.

ASK what they rejected: "Was there another way this could have been written that would have been worse?" The reasons behind a choice show most clearly in the options a person did not take.

### 3.2. Compare versions

WRITE two short versions of the same passage. TAKE it from the user's own material when possible. CHANGE one thing between the two versions, such as where the main point appears, the length, the use of a list, the technical terms, or the amount of context. CHANGING one thing at a time makes the reason for the choice clear. This is a design choice, not a tested rule.

FOR each pair, ASK:

1. Which version they would rather receive.
2. Why, in their own words.
3. What they would do next after reading each one. IF they could act on one and not the other, RECORD that: it is stronger evidence than which one they liked.

DO NOT tell the user which version follows `write-better` or any rule. COVER the dimensions where the user's material and answers disagree, or where they gave no answer, first.

### 3.3. Check the scope with hypotheticals

ASK hypotheticals only to find when a rule applies, such as "Would this change for an urgent message?" or "for a topic you know well?". DO NOT record a hypothetical answer as a preference by itself.

## 4. Part B: how the user reviews (`review-for`)

### 4.1. Walk through a real review

FOR the work from section 1.2, ASK the user to describe how they reviewed it: what they looked at first, what made them comment, and what made them approve or reject it. LET them answer without interrupting.

THEN, FOR each of their comments, ASK:

1. Whether it had to be fixed before approval, or was a suggestion.
2. What they saw that made them write it.
3. What a version that needed no comment would have looked like.

ASK what they did not comment on and why. Criteria a reviewer applies but does not state often show up in what they let pass.

### 4.2. Compare two samples

SHOW two versions of a small piece of work in the user's domain, such as two functions, two paragraphs, or two plans. TAKE them from the user's material or from your own work in this conversation when possible. MAKE them differ on one point that the walk-through did not settle.

ASK which one they would approve, which comment they would write on the other, and whether that comment blocks approval. A reviewer's comparison with a justification brings out criteria they cannot list from memory.

### 4.3. Separate blocking criteria from preferences

LIST the criteria found so far. ASK the user to mark each one as blocking, meaning the work is not approved until it is fixed, or as a preference. DO NOT ask them to rate criteria on a scale: a scale lets every criterion look important.

## 5. Write the guides

### 5.1. Write each rule from evidence

FOLLOW the templates [templates/write-for.md](templates/write-for.md) and [templates/review-for.md](templates/review-for.md). FOLLOW `/write-better` for the wording if available. OTHERWISE, USE plain words, one term per concept, and literal statements.

WRITE each rule with:

1. The rule, as an instruction to an agent.
2. When it applies, and when it does not. A rule with no scope gets applied where it does not belong.
3. Its evidence: **chose** (the user picked it in a comparison or could act on it), **shown** (their material or their review comments show it), or **said** (they stated it). IF the evidence contradicts itself, WRITE the rule from what the user chose or showed, and RECORD what they said next to it.
4. One example the user approved or wrote, taken from the interview or their material. Examples of output the user approved carry most of the benefit of a profile.

### 5.2. Leave out what the guide must not contain

DO NOT write traits, such as "the user is detail-oriented" or "the user is an expert". WRITE the behaviour the trait was meant to cause instead, with its scope.

DO NOT write anything the user did not confirm, any condition or diagnosis, or any view the user holds on a topic. The guides are about form and criteria. A stored profile made models more agreeable, so the guides SAY that they are not a reason to agree with the user.

KEEP each guide short enough to read in a few minutes. A rule earns its place only when it changes what an agent would do without it.

### 5.3. Confirm the guide with the user

SHOW the user each guide before saving it. ASK them to correct or delete rules. SAY, once, that their approval makes the guide theirs but does not show that it works: the test is whether later output needs fewer corrections.

### 5.4. Save the guides as skills

NAME the skills `write-for-<name>` and `review-for-<name>`. USE the name the user gives; OTHERWISE PROPOSE one from the context.

PROPOSE where to save each skill: a folder where the user's harness loads personal skills, or a project's skills folder if the guide is for one project. IF you do not know where the harness loads skills, ASK the user. WRITE the files only after the user agrees, because skills change how every later agent behaves.

IF you cannot write files, GIVE each guide in a code block, with the path where the user should save it.

## 6. Update an existing guide

READ the guide. ASK what prompted the update: a correction the user made, a new kind of document, or a rule that no longer fits.

RUN only the parts of sections 3 and 4 that concern the rules in question. WHEN later feedback contradicts a rule, REPLACE the rule, even if the user approved it before. Feedback on real output outweighs what the interview found.

DO NOT rewrite rules the update does not concern. SHOW the user the changed rules before saving them.

## 7. Report

STATE what the guides were built from: which documents and reviews you read, how many comparisons the user made, and which parts were skipped. IF a part rests only on what the user said, SAY so.

DO NOT claim the guides will improve the output. They are untested until agents use them and the user corrects less, or more.
