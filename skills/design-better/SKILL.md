---
name: design-better
description: Helps an AI agent design, build and check an interface or page, such as a web page, an app screen or a rendered report, so that the people who use it can do what they came for. Agrees the audience and their tasks with the user, shows rough directions before building, and checks the result by walking each task instead of trusting how it looks. Use show-better to introduce a document with visual panels, and write-better for the words in the interface.
argument-hint: "[INTERFACE OR TASK]"
---

# Design Better

IF invoked with an interface or a design task as argument, USE these instructions to design, build or change it.
IF invoked without argument, USE these instructions on the interface in the current conversation: CHECK the work done so far against sections 1, 5 and 6, THEN continue or correct it.
IF the interface to check is someone else's, WRITE its scenarios (section 1.3), THEN USE sections 5 and 6.

Being invoked does NOT mean a redesign, and does NOT mean you must build now. These instructions can end with a brief and questions for the user, or with a report that the interface already lets people do what they came for.

This skill uses two words for people. The user is the person you work for. The AUDIENCE is the people who will use the interface. They can be the same person.

## Principles

1. People judge an interface that looks good as easy to use, whether or not it is. Approval of how an interface looks, from the user or from you, does not show that the AUDIENCE can use it.
2. Generated interfaces do well on what automated checkers measure, such as contrast and the presence of alt text. They fail on meaning: what a control is called, what an image description says, whether headings and labels describe the content.
3. Every check finds only part of the problems: an automated checker, a review against a list of rules, a model looking at a screenshot, a test with a few people. Two reviewers of the same interface report largely different problems, and reviews report many problems that people do not have.
4. People judge more critically and more precisely when they compare concrete versions than when they see one version or describe what they want in words.
5. Few layout and type rules hold for every task and every AUDIENCE, and taste differs between people, including trained designers.
6. The brief (section 1.3), reusing the project's components (section 3.1), the stopping rules (section 5.4), and review in a fresh context (section 6.1) are design choices.

This skill names capabilities, not tools: reading files, asking the user, rendering a page and viewing it, operating a page by pointer and keyboard, running an automated accessibility checker, sub-agents, and writing files. FOR each capability you lack, FOLLOW the fallback the section gives.

FOR the code that implements the interface, FOLLOW `/code-better` if available. OTHERWISE, CHANGE only what the task needs and RUN the project's existing checks.

## 1. Brief: build the right interface

### 1.1. Name the GOAL

NAME what the AUDIENCE must be able to do with the interface, and what the user wants to achieve by providing it. DISTINGUISH this GOAL from the requested page. "A dashboard" is a request. "See which orders are late and open one" is a GOAL.

### 1.2. Read before deciding anything

READ the existing interface, its components, styles and design files, the content it must show, the project's instruction files, and earlier conversation. DO NOT ask the user what these sources answer.

TREAT an existing design language, such as its colours, typefaces, spacing and components, as a requirement the user owns. KEEP it. IF it conflicts with a rule in section 3, such as text contrast, DO NOT change it. REPORT the conflict once, with its effect on the AUDIENCE and one alternative, THEN FOLLOW the user's decision.

### 1.3. Write the audience and their tasks

IF the work is more than a small change with one obvious reading, THEN WRITE a brief with [templates/brief.md](templates/brief.md): the GOAL, the AUDIENCE, their scenarios, the content, the constraints, and your assumptions. IF you cannot write files, PUT the brief in your reply.

DESCRIBE the AUDIENCE by what they do and the conditions they do it in: the device, the input method, how much time they have, what they already know. DO NOT invent a fictional person, and DO NOT assign the AUDIENCE traits or conditions you guessed.

WRITE each scenario as one task from its start to an end the person can observe, with concrete data: who comes, what they came to do, and what they see or have when it is done. KEEP the scenarios few: a scenario earns its place only if a wrong guess on it would change what you build. Sections 4 to 6 check the interface against these scenarios.

### 1.4. Ask a few questions before building

USE `/ask-better` if available, THEN CONTINUE with section 2 once the user answers. OTHERWISE, ASK only what only the user knows and what changes the interface. ASK at most about three questions, all at once, before building. WRITE each one so the user can answer in a few words or by choosing. The first questions carry most of the value, and many or generic questions cost the user more than they give. TREAT the number as a guide, not a rule.

FOR every other gap, CHOOSE the most plausible option, PROCEED, and STATE the assumption next to the result it affects.

## 2. Direction: show before building

USE this section WHEN the interface is new, or the change alters its layout or flow, and the brief leaves more than one reasonable direction. FOR a small change inside an existing interface, FOLLOW its patterns and SKIP this section.

### 2.1. Ask for the user's own direction first

ASK whether the user has a direction or references in mind BEFORE you show yours, because seeing examples first narrows what people consider. TREAT this order as a guide, not a rule. IF no design language exists, ASK for interfaces they like and dislike. PREFER pictures and examples over adjectives: people rarely have the words for a look they would recognise.

### 2.2. Show two or three rough directions

MAKE the directions differ in a way the user can see, such as the structure, the order of content, or what is prominent. DO NOT vary only a colour or a font. USE the same real content in each.

KEEP them rough: real structure and content, little styling. A rough version reveals largely the same problems as a finished one, and polish changes how people rate it. IF you can render, SHOW rendered versions. OTHERWISE, SHOW each direction as a plain text outline of the screen. TREAT two or three as a guide, not a rule.

### 2.3. Ask what is wrong, not how to fix it

ASK which direction serves each scenario best and what is wrong with each one. DO NOT ask the user to design the fix: people identify problems far more reliably than solutions. RECORD the chosen direction in the brief.

TREAT what the user picks about the look as this user's preference. It is not evidence that the interface works for the AUDIENCE.

## 3. Build

### 3.1. Change only what the task needs

PRESERVE the parts of an existing interface that the task does not require you to change. REUSE the project's components, tokens and patterns. IF none exist, DEFINE a small set of colours, type sizes and spacing values once, and USE only those.

FOR the words in the interface, such as labels, button text and messages, FOLLOW `/write-better` if available. OTHERWISE, USE the words the AUDIENCE uses, and NAME the action on the control that performs it.

### 3.2. Lay out the page for the task

TREAT the rules in this section as guides, not rules, because their effect depends on the task and the AUDIENCE.

- WHEN a person must find one thing, REMOVE or reduce the elements that compete with it.
- KEEP the density of content even across the page.
- MAKE every control look like something that can be clicked or tapped, and everything else look like it cannot.
- ON touch screens, MAKE targets about 9 mm or larger.
- PUT an element where the task leads the person. DO NOT rely on size or colour alone to get it noticed: people searching for something else miss prominent elements.
- DO NOT judge navigation by counting clicks or menu levels. JUDGE it by whether each step is obvious (section 5.1).

### 3.3. Text and colour

- DO NOT use small body text. No single size is right for everyone: larger text helps up to a point.
- AVOID very short lines of running text. AIM for about 55 to 70 characters per line. TREAT this as a guide, not a rule.
- KEEP the contrast between text and background high, at least the conventional 4.5 to 1 for normal text. Low contrast costs most for people with low vision and for small text.
- PREFER dark text on a light background for small text.
- DO NOT use colour as the only signal. ADD text, an icon or a shape.
- TREAT the choice between ordinary serif and sans serif typefaces as taste, and FOLLOW the design language. DO NOT choose a special typeface on the claim that it helps a group of readers.

### 3.4. Forms and feedback

- GIVE every field a visible label. Label position is a choice: PICK one and KEEP it across the form.
- PUT each error message next to the field it concerns. SAY what is wrong and what to enter instead.
- DO NOT validate a field before the person has finished typing in it. Whether to validate on leaving the field or on submit is a choice: PICK one and KEEP it.
- MARK which fields are required.
- WHEN an action takes time, SHOW that something is happening. DO NOT choose a loading pattern on the claim that it feels faster.

### 3.5. Make it work without sight or a mouse

Generated interfaces fail here more than anywhere else.

- USE native elements, such as buttons, links and inputs, before custom ones. GIVE every control a name that says what it does.
- WRITE headings that describe their sections, in order, and MARK the main regions of the page.
- TIE each label to its field in the markup.
- WRITE alt text that says what the image shows or does in this place. GIVE decorative images empty alt text. DO NOT add a description to every image.
- SET the language of the page.
- MAKE every action possible by keyboard, in an order that follows the task, with a visible focus.

WRITE names, labels and descriptions from the scenarios, because no checker can judge whether they mean anything.

## 4. Decide the cases the design leaves out

WALK each scenario step by step. AT each step, ASK what can go wrong or differ: no data yet, a lot of data, very long text, a slow or failed response, invalid input, no permission, the person going back or repeating the step, a small screen.

THEN CHECK each screen against a short list of states: empty, loading, error, partial, full and success. Each method finds cases the other misses. TREAT this section as a guide, not a rule.

FOR each case, DECIDE what the interface shows, and BUILD it. IF a case changes what happens to the person's data or work, TREAT it as a question for the user (section 1.4) or state it as an assumption.

## 5. Verify

### 5.1. Walk every scenario in the rendered interface

IF you can render and operate the interface, WALK each scenario from start to end: with a pointer, then with the keyboard only, then at the smallest screen width in the brief. AT each step, CHECK that the next action is visible and named in the AUDIENCE's words, and that the interface shows the result of the action.

A scenario counts as walked only if you operated the interface. Reading the code or looking at a screenshot does not count. IF you cannot render or operate it, SAY so. DO NOT describe how the page looks or behaves. LIST the walks for the user to do.

Completing a scenario yourself shows that it can be completed. It does not show where a person would hesitate or fail, because agents complete tasks that people struggle with.

### 5.2. Run a checker and fix what it reports

IF an automated accessibility checker is available, RUN it on the rendered interface and FIX what it reports. A clean run covers a minority of accessibility problems. DO NOT report the interface as accessible from it. IF none is available, SAY so, and RELY on sections 5.1 and 5.3.

### 5.3. Read the markup for meaning

READ the names of controls, the labels, the headings and the alt texts in the order assistive technology gives them, without the visual page. CHECK that each one says what the thing is or does in its scenario.

### 5.4. Bound the fix loop

AFTER each round of fixes, WALK all scenarios again, not only the one that failed, because fixing one problem in an interface often creates another.

STOP fixing and REPORT when:

1. The same problem remains after two attempts.
2. About three rounds of fixes have not made every scenario pass.
3. A fix breaks a scenario that passed before.

DO NOT change a scenario or drop a check so that the walk passes. IF a scenario looks wrong, STOP, EXPLAIN why, and ASK the user.

### 5.5. Use screenshots for defects, not for quality

LOOK at screenshots to find visible defects, such as overlap, clipped text, unreadable text and broken layout. DO NOT treat your judgment of a screenshot, or another model's, as evidence that the interface is easy to use or well designed.

## 6. Review

### 6.1. Review in a fresh context

IF you can start a sub-agent, GIVE a fresh reviewer only the interface and the brief, with [templates/review-brief.md](templates/review-brief.md). DO NOT give it your reasoning or your conversation with the user. A cheaper model can review, but it must not share your context.

OTHERWISE, REVIEW in a separate pass after verification: RE-READ the brief first, THEN walk the interface as if someone else built it.

IF the interface is important enough for more than one review, RUN the same review again independently. DO NOT give reviewers different characters or temperaments instead: repeated independent reviews find most of what such roles find. TREAT this as a guide, not a rule.

### 6.2. Treat findings as candidates

KEEP a finding only if it names the scenario and step, what the reviewer did, what happened, and why that stops or slows the person. REPRODUCE it in the rendered interface before fixing it.

A finding that only names a broken rule, with no step where a person is stopped, is unconfirmed. Most such findings are not problems people have. DROP it only when you can show it is wrong. OTHERWISE, REPORT it as unconfirmed.

ORDER findings by their effect on the AUDIENCE completing a scenario.

### 6.3. Do not simulate people

DO NOT take, or give a reviewer, the role of a person with a disability, a neurodivergent profile, an age or an emotional state to predict how such a person would experience the interface. Such roles produce stereotypes and do not match the people they imitate.

FOR these AUDIENCES, FOLLOW section 3.5 and the published accessibility guidance for the platform, and RECOMMEND a test with people from that AUDIENCE (section 7.2).

## 7. Hand back

### 7.1. Report what the user must act on

USE `/write-better` if available. OTHERWISE, lead with the result. THEN REPORT:

1. In one sentence, which scenarios you walked and how. Each scenario that fails or that you could not walk, and why.
2. The decisions the user owns: each conflict between the design language and a rule (section 1.2), and each assumption that changed what you built.
3. The unconfirmed review findings.

DISTINGUISH three things, and DO NOT claim one from another: the scenarios can be completed, the checks pass, and the AUDIENCE can use the interface. Only a test with people shows the third.

### 7.2. Offer a test with people

WHEN the interface is new or its main flow changed, and people other than the user will use it, OFFER a short test: the user watches three to five people from the AUDIENCE try the scenarios without help, and notes where each one hesitates or fails. GIVE the scenarios as tasks worded without the labels the interface uses. IF the AUDIENCE has distinct groups, SUGGEST a few people from each.

SAY that such a test finds the common problems, not all of them. IF the user has said they do not want this, FOLLOW that instead.

IF the user rejects the result, USE `/do-better` if available. OTHERWISE, FIND what the result misses from the user's feedback and the brief, and CORRECT it.
