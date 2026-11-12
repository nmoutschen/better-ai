---
name: interview-me
description: Interviews the user about how they read, how they review work, and how they want AI agents to work for them, then writes what it learns as personal guides, write-for-NAME and review-for-NAME (NAME is the user's name), and as short profile instructions the user can paste into any AI tool, so agents write text the user understands and acts on, check work the way the user would, and ask, source and disagree the way the user needs. Works from the user's real documents, reviews and corrections, and from comparisons of concrete samples, not from general questions about their preferences.
argument-hint: "[write | review | profile | PATH-TO-EXISTING-GUIDE]"
---

# Interview Me

IF invoked without argument, RUN the three interviews in this order, and OFFER to stop after each one:

1. `write`: how the user reads. FOLLOW [write.md](write.md). It writes the `write-for-<name>` skill.
2. `review`: how the user reviews work. FOLLOW [review.md](review.md). It writes the `review-for-<name>` skill.
3. `profile`: how the user wants agents to work for them. FOLLOW [profile.md](profile.md). It writes profile instructions: a short text the user pastes into the always-on instructions of any AI tool, such as Claude's profile preferences. It runs last because the profile points to the two skills.

IF invoked with `write`, `review` or `profile`, RUN only that interview.
IF invoked with the path of an existing guide or profile record, UPDATE it (section 5).

The steps in this file apply to every interview. Each interview file adds the material to collect, the questions to ask, and the rules for its output.

The GOAL is that the user DOES less explaining and correcting later: agents write text this user understands and acts on, check work against this user's criteria, and work the way this user needs. The guides and the profile are only a means to that.

Being invoked does NOT mean a long interview or new rules are needed. IF the existing guides or profile already cover what the user wants, these instructions can end with no change.

## Principles

1. What people say helps them, and the criteria they state for judging work, only partly match what helps them and what their actual judgments reveal. Learners preferred, and felt they learned more from, the format that taught them less, and experts leave out much of what they do when they describe it.
2. Comparing concrete work samples and justifying the choice made tacit quality criteria partly explicit. Walking through one real incident revealed the reasons behind a person's actions.
3. Recall of past behaviour is imperfect, even for recent days. A document the user wrote or reacted to is stronger evidence than their memory of it.
4. AI interviewers produce answers of about the same quality as human interviewers. Their main failure is not following up on surprising or unclear answers.
5. A user profile in an LLM's context made it more agreeable and made it personalize where it should not. The model mirrored the user's views only when the context let it infer them.
6. Users accepting a summary of their interview shows that they accept it, not that it is accurate.
7. These rules adapt methods from other settings to an AI interviewing a user about their own reading, reviewing, and use of AI. TREAT them as a guide, not as fixed rules.

## 1. Prepare

### 1.1. Look up what is already known

READ the conversation, memories, project instructions, and any existing writing guide, `write-for-*` or `review-for-*` skill, profile record, or profile instructions first. LIST what they already say about how the user reads, reviews, and wants agents to work.

DO NOT ask about anything they already answer. IF an existing guide or profile covers the interview being run, SWITCH to updating it (section 5).

### 1.2. Collect real material

ASK the user, in one message, for the material the interview file lists.

READ each item before the interview. IF you cannot open it, ASK the user to paste it. NOTE what each item shows, such as the length of its opening, which review comments ask for a change before approval, or what an agent did before the user corrected it. These notes are not rules yet.

IF the user has no material at hand, CONTINUE with the comparisons in the interview file, built from a topic in their current work. SAY that the output will rest on fewer kinds of evidence.

## 2. How to ask

APPLY these rules to every question in every interview.

### 2.1. Ask about one thing, in its own terms

ASK about the item itself, such as "How long should the first paragraph be?", not "Do you agree that short openings are better?". Agree/disagree questions give lower-quality answers than questions about the item itself.

ASK about one thing per question. IF you use a structured question tool, such as `AskUserQuestion`, OFFER concrete options and LET the user write their own. OTHERWISE, ASK in plain text.

DO NOT suggest the answer you expect, and DO NOT praise or judge the user's answers.

### 2.2. Follow up before moving on

FOLLOW UP, with one question, WHEN an answer:

1. Uses a vague quality word, such as "clear", "concise", "too long", "professional" or "readable". ASK what it looked like in a specific document.
2. Surprises you, or contradicts what their material showed. ASK about the difference. DO NOT resolve it yourself.
3. States a rule with no example. ASK for the last time it mattered.
4. Says "it depends". ASK what it depends on.

### 2.3. Ask about the options the user rejected

WHEN the user describes a choice, ASK what they rejected, such as "Was there another way this could have been done that would have been worse?". Asking about the options a person rejected revealed the reasons behind their actions.

### 2.4. Use hypotheticals only for scope

ASK hypotheticals only to find when a rule applies, such as "Would this change for an urgent message?". DO NOT record a hypothetical answer as a preference by itself: it shows what the person knows a situation requires, not what they will do or prefer.

### 2.5. Respect the user's time and limits

PUT the questions whose answers change the output most first. AFTER each interview, OFFER to stop and write the output from what you have. Answers get worse as an interview gets long.

DO NOT ask the user to disclose a condition, a diagnosis, or anything about who they are. DO NOT infer their ability or background from how they write. ASK only about documents, reviews, agent behaviour, and the choices they make about them.

## 3. Write the output

### 3.1. Write each rule from evidence

FOLLOW the template the interview file names. FOLLOW `/write-better` for the wording if available. OTHERWISE, USE plain words, one term per concept, and literal statements.

WRITE each rule with:

1. The rule, as an instruction to an agent.
2. When it applies, and when it does not.
3. Its evidence: **chose** (the user picked it in a comparison or could act on it), **shown** (their material, review comments or corrections show it), or **said** (they stated it). IF the evidence contradicts itself, WRITE the rule from what the user chose or showed, and RECORD what they said next to it.
4. One example the user approved or wrote, taken from the interview or their material. Examples of output the user approved carry most of the benefit of a profile.

### 3.2. Leave out what the output must not contain

DO NOT write traits, such as "the user is detail-oriented" or "the user is an expert". WRITE the behaviour the trait was meant to cause instead, with its scope.

DO NOT write anything the user did not confirm, any condition or diagnosis, or any view the user holds on a topic. The guides and the profile are about form, criteria and ways of working, and SAY that they are not a reason to agree with the user.

KEEP each guide short enough to read in a few minutes. A rule earns its place only when it changes what an agent would do without it. The guides and the profile adjust general skills, such as `/write-better` and `/code-better`, for one user; DO NOT repeat those skills' rules.

### 3.3. Confirm the output with the user

SHOW the user each guide or profile before saving it. ASK them to correct or delete rules. SAY, once, that their approval makes the output theirs but does not show that it works: the test is whether later output needs fewer corrections.

### 3.4. Save the output

USE the name the user gives in the names `write-for-<name>`, `review-for-<name>` and `profile-for-<name>`; OTHERWISE PROPOSE one from the context.

PROPOSE where to save each file. The interview file says which kind of location fits. IF you do not know where the user's harness loads skills, ASK the user. WRITE the files only after the user agrees, because they change how every later agent behaves.

IF you cannot write files, GIVE each file in a code block, with the path where the user should save it.

## 4. Report

STATE what the output was built from: which documents, reviews and corrections you read, how many comparisons the user made, and which interviews were skipped. IF an output rests only on what the user said, SAY so.

DO NOT claim the guides or the profile will improve the output.

## 5. Update an existing guide or profile

READ the guide or the profile record. IF the user gives profile instructions without a record, LOOK for the record next to them; OTHERWISE TREAT every rule in them as **said**. ASK what prompted the update: a correction the user made, a new kind of document or task, or a rule that no longer fits.

RUN only the steps of the interview file that concern the rules in question. WHEN later feedback contradicts a rule, REPLACE the rule, even if the user approved it before. Feedback on real output outweighs what the interview found.

DO NOT rewrite rules the update does not concern. SHOW the user the changed rules before saving them. FOR a profile, UPDATE the record first, then WRITE the profile instructions again from it.
