---
name: design-better
description: Helps an AI agent design, build and review an interface or page, such as a web page, an app screen or a rendered report, so that the people who use it can do what they came for, and create, apply and review the design language behind it. Agrees the audience and their tasks with the user, shows rough directions before building, and checks the result by walking each task instead of trusting how it looks. Use show-better to introduce a document with visual panels, and write-better for the words in the interface.
argument-hint: "[INTERFACE OR TASK]"
---

# Design Better

This file holds the practices every design task shares. The steps of each kind of task are in a mode file. READ the mode file that fits the task and FOLLOW it together with this file:

| Task | Mode file |
|---|---|
| Design, build or change an interface | [modes/build.md](modes/build.md) |
| Review an interface or a design language, yours or someone else's | [modes/review.md](modes/review.md) |
| Create, extend or change a design language | [modes/language.md](modes/language.md) |

IF invoked with an interface or a design task as argument, CHOOSE the mode from the task.
IF invoked without argument and the current conversation is building or changing an interface, USE the review mode on that interface, THEN continue or correct the work. OTHERWISE, ASK the user which interface or design language to work on, and whether to build, review or change it.

Being invoked does NOT mean a redesign, and does NOT mean you must build now. These instructions can end with a brief and questions for the user, or with a report that the interface already lets people do what they came for.

This skill uses two words for people. The user is the person you work for. The AUDIENCE is the people who will use the interface. They can be the same person.

## Principles

1. People judge an interface that looks good as easy to use, whether or not it is. Approval of how an interface looks, from the user or from you, does not show that the AUDIENCE can use it.
2. Generated interfaces do well on what automated checkers measure, such as contrast and the presence of alt text. They fail on meaning: what a control is called, what an image description says, whether headings and labels describe the content.
3. Every check finds only part of the problems: an automated checker, a review against a list of rules, a model looking at a screenshot, a test with a few people. Two reviewers of the same interface report largely different problems, and reviews report many problems that people do not have.
4. People judge more critically and more precisely when they compare concrete versions than when they see one version or describe what they want in words.
5. Few layout and type rules hold for every task and every AUDIENCE, and taste differs between people, including trained designers.
6. People overlook removing something as a way to improve it unless prompted to consider removal.
7. The brief (section 1.3) is a design choice. Each mode file names its own design choices.

This skill names capabilities, not tools: reading files, asking the user, running Python 3, rendering a page and viewing it, publishing a page, operating a page by pointer and keyboard, running an automated accessibility checker, sub-agents, and writing files. FOR each capability you lack, FOLLOW the fallback the section gives.

FOR the code that implements the interface, FOLLOW `/code-better` if available. OTHERWISE, CHANGE only what the task needs and RUN the project's existing checks.

## 1. Know the goal, the audience and what exists

### 1.1. Name the GOAL

NAME what the AUDIENCE must be able to do with the interface, and what the user wants to achieve by providing it. DISTINGUISH this GOAL from the requested page. "A dashboard" is a request. "See which orders are late and open one" is a GOAL.

### 1.2. Read before deciding anything

READ the existing interface, its components, styles and design files, the content it must show, the project's instruction files, and earlier conversation. DO NOT ask the user what these sources answer.

TREAT an existing design language, such as its colours, typefaces, spacing and components, as a requirement the user owns. KEEP it. IF it conflicts with a rule in section 2, such as text contrast, DO NOT change it. REPORT the conflict once, with its effect on the AUDIENCE and one alternative, THEN FOLLOW the user's decision. A change to a colour, typeface, type size, spacing value or component that the design language defines is a change to the design language, however small. DO NOT make it as a quick fix: WAIT for the user's decision.

The pages a design document chooses, and what each holds, are part of the structure (section 1.3), not of the design language. CHECK them against the GOAL instead of keeping them as a requirement.

IF no design language exists and the work covers more than one screen, ASK the user whether to create one first. IF they agree, FOLLOW [modes/language.md](modes/language.md) before building.

### 1.3. Write the audience and their tasks

IF the work is more than a small change with one obvious reading, THEN WRITE a brief with [templates/brief.md](templates/brief.md): the GOAL, the AUDIENCE, their scenarios, the content, the constraints, and your assumptions. IF you cannot write files, PUT the brief in your reply.

DESCRIBE the AUDIENCE by what they do and the conditions they do it in: the device, the input method, how much time they have, what they already know. DO NOT invent a fictional person, and DO NOT assign the AUDIENCE traits or conditions you guessed.

WRITE each scenario as one task from its start to an end the person can observe, with concrete data: who comes, what they came to do, and what they see or have when it is done. KEEP the scenarios few: a scenario earns its place only if a wrong guess on it would change what you build. Every mode checks the interface against these scenarios.

The structure is part of the design: which pages exist, what each holds, and how they link. WRITE it in the brief. FOR each page and each main part of a page, NAME the scenario it serves, THEN ASK whether it should stay, merge with another, or go (Principle 6). A page or part that serves no scenario, repeats another, or follows how its content was produced instead of what the AUDIENCE comes to do, is a candidate to merge or remove. TREAT the last point as a question to settle with the user, not a rule: organising pages by task beats organising them by subject in some studies and not in others, and the labels matter at least as much as the grouping.

### 1.4. Ask a few questions before building

USE `/ask-better` if available, THEN CONTINUE with the mode file once the user answers. OTHERWISE, ASK only what only the user knows and what changes the interface. ASK at most about three questions, all at once, before building. WRITE each one so the user can answer in a few words or by choosing. The first questions carry most of the value, and many or generic questions cost the user more than they give. TREAT the number as a guide, not a rule.

WHEN a question is about how something looks, such as a colour, a layout or a component, SHOW the versions by section 1.5, and ASK the user to choose between them. DO NOT ask from a text description or a text sketch when you can render.

FOR every other gap, CHOOSE the most plausible option, PROCEED, and STATE the assumption next to the result it affects.

### 1.5. Show versions on one page

WHEN you show the user versions to choose between, or a change before and after, PUT them on one rendered page, side by side, because people judge a version more critically when they see it among others. Showing every version at the same screen sizes and scale, in the order you give, is a design choice.

1. WRITE each version as its own HTML file, with the same real content and the project's styles. FOR a before and after, SAVE a copy of the page before you change it.
   WHEN versions differ in only part of a page, WRITE each version as that part, with enough of its surroundings to place it, so it shows at a size where its text can be read. LABEL under each version what differs from the others. IF the change is small inside the part shown, also MARK where it is, with the same mark at the same place in every version, so the user finds it without searching and no version stands out. KEEP the mark out of the interface itself.
2. RUN `python3 scripts/compare.py A=<file> B=<file> --question "<what the user decides>" --width <widest screen> --width <smallest screen in the brief> --out .design/<slug>/index.html` from this skill's directory, with the output path in the working directory. A version can also be an address the user's browser can reach. FOR a before and after, LABEL them `Before=` and `After=`: the page then also offers to switch between them in the same place, which shows small changes at one spot better than looking from one to the other. Versions with other labels are shown side by side only, because switching loses that advantage when the layout moves between versions. DO NOT commit the page unless the user asks.
3. LOOK at the rendered page before you show it, and FIX each version that does not load, overlaps or is cut off.
4. IF you can publish a page for the user, PUBLISH it and GIVE the link. IF the script warns that a version links files by relative path, PUT those files' content into the version first, because a published page cannot reach them. OTHERWISE, OPEN the page with `--open` and GIVE its path.
5. ASK the question in your reply too, so the user can answer in a few words.

IF you cannot run Python but can render, WRITE one HTML page that shows the versions side by side at the same width. IF you cannot render, SHOW each version as a plain text outline, and SAY that the choice may change once it is rendered.

## 2. Design rules

### 2.1. Lay out the page for the task

TREAT the rules in this section as guides, not rules, because their effect depends on the task and the AUDIENCE.

- WHEN a person must find one thing, REMOVE or reduce the elements that compete with it.
- KEEP the density of content even across the page.
- MAKE every control look like something that can be clicked or tapped, and everything else look like it cannot.
- ON touch screens, MAKE targets about 9 mm or larger.
- PUT an element where the task leads the person. DO NOT rely on size or colour alone to get it noticed: people searching for something else miss prominent elements.
- DO NOT judge navigation by counting clicks or menu levels. JUDGE it by whether each step is obvious (section 3.1).

### 2.2. Text and colour

- DO NOT use small body text. No single size is right for everyone: larger text helps up to a point.
- AVOID very short lines of running text. AIM for about 55 to 70 characters per line. TREAT this as a guide, not a rule.
- KEEP the contrast between text and background high, at least the conventional 4.5 to 1 for normal text. Low contrast costs most for people with low vision and for small text.
- PREFER dark text on a light background for small text.
- DO NOT use colour as the only signal. ADD text, an icon or a shape.
- TREAT the choice between ordinary serif and sans serif typefaces as taste, and FOLLOW the design language. DO NOT choose a special typeface on the claim that it helps a group of readers.

### 2.3. Forms and feedback

- GIVE every field a visible label. Label position is a choice: PICK one and KEEP it across the form.
- PUT each error message next to the field it concerns. SAY what is wrong and what to enter instead.
- DO NOT validate a field before the person has finished typing in it. Whether to validate on leaving the field or on submit is a choice: PICK one and KEEP it.
- MARK which fields are required.
- WHEN an action takes time, SHOW that something is happening. DO NOT choose a loading pattern on the claim that it feels faster.

### 2.4. Make it work without sight or a mouse

Generated interfaces fail here more than anywhere else.

- USE native elements, such as buttons, links and inputs, before custom ones. GIVE every control a name that says what it does.
- WRITE headings that describe their sections, in order, and MARK the main regions of the page.
- TIE each label to its field in the markup.
- WRITE alt text that says what the image shows or does in this place. GIVE decorative images empty alt text. DO NOT add a description to every image.
- SET the language of the page.
- MAKE every action possible by keyboard, in an order that follows the task, with a visible focus.

WRITE names, labels and descriptions from the scenarios, because no checker can judge whether they mean anything.

### 2.5. Words

FOR the words in the interface, such as labels, button text and messages, FOLLOW `/write-better` if available. OTHERWISE, USE the words the AUDIENCE uses, and NAME the action on the control that performs it.

## 3. Check the interface, not its looks

### 3.1. Walk every scenario in the rendered interface

IF you can render and operate the interface, WALK each scenario from start to end: with a pointer, then with the keyboard only, then at the smallest screen width in the brief. AT each step, CHECK that the next action is visible and named in the AUDIENCE's words, and that the interface shows the result of the action.

A scenario counts as walked only if you operated the interface. Reading the code or looking at a screenshot does not count. BEFORE you conclude that you cannot operate it, LOOK for a way to drive a browser in the environment, such as a headless browser, a browser automation library or the browser's debugging protocol, and USE it. IF you still cannot render or operate it, SAY so. DO NOT describe how the page looks or behaves. LIST the walks for the user to do.

Completing a scenario yourself shows that it can be completed. It does not show where a person would hesitate or fail, because agents complete tasks that people struggle with.

### 3.2. Read the markup for meaning

READ the names of controls, the labels, the headings and the alt texts in the order assistive technology gives them, without the visual page. CHECK that each one says what the thing is or does in its scenario.

### 3.3. Run a checker and fix what it reports

IF an automated accessibility checker is available, RUN it on the rendered interface and FIX what it reports. A clean run covers a minority of accessibility problems. DO NOT report the interface as accessible from it. IF none is available, SAY so, and RELY on sections 3.1 and 3.2.

### 3.4. Use screenshots for defects, not for quality

LOOK at screenshots to find visible defects, such as overlap, clipped text, unreadable text and broken layout. DO NOT treat your judgment of a screenshot, or another model's, as evidence that the interface is easy to use or well designed.

### 3.5. Do not simulate people

DO NOT take, or give a reviewer, the role of a person with a disability, a neurodivergent profile, an age or an emotional state to predict how such a person would experience the interface. Such roles produce stereotypes and do not match the people they imitate.

FOR these AUDIENCES, FOLLOW section 2.4 and the published accessibility guidance for the platform, and RECOMMEND a test with people from that AUDIENCE (section 4.2).

## 4. Hand back

### 4.1. Report what the user must act on

USE `/write-better` if available. OTHERWISE, lead with the result.

WHEN the change alters how the interface looks and you can render, the result is a page that shows each changed screen before and after the change (section 1.5). KEEP the text to the points below.

THEN REPORT:

1. In one sentence, which scenarios you walked and how. Each scenario that fails or that you could not walk, and why.
2. The decisions the user owns: each conflict between the design language and a rule (section 1.2), and each assumption that changed what you built.
3. The unconfirmed review findings.

DISTINGUISH three things, and DO NOT claim one from another: the scenarios can be completed, the checks pass, and the AUDIENCE can use the interface. Only a test with people shows the third.

### 4.2. Offer a test with people

WHEN the interface is new or its main flow changed, and people other than the user will use it, OFFER a short test: the user watches three to five people from the AUDIENCE try the scenarios without help, and notes where each one hesitates or fails. GIVE the scenarios as tasks worded without the labels the interface uses. IF the AUDIENCE has distinct groups, SUGGEST a few people from each.

SAY that such a test finds the common problems, not all of them. IF the user has said they do not want this, FOLLOW that instead.

IF the user rejects the result, USE `/do-better` if available. OTHERWISE, FIND what the result misses from the user's feedback and the brief, and CORRECT it.
